"""Validated 7z framing and recursive member analysis through isolated py7zr."""

import json
import struct
import sys
import zlib
from importlib.metadata import PackageNotFoundError, version
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict, cast

from polyfile.compression import DecodeError, RawRegion, match_decoded
from polyfile.external import run_helper
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Submatch, register_parser

SIGNATURE = b"7z\xbc\xaf\x27\x1c"
HEADER_SIZE = 32
_MAX_HEADER = 1 << 28
_MAX_MEMBERS = 1 << 23


class _Member(TypedDict):
    name: str
    size: int
    directory: bool
    special: bool
    crc: int | None


class _Metadata(TypedDict):
    members: list[_Member]
    packed: list[list[int]]
    packed_header: list[list[int]]


def _signature(stream: FileStream) -> tuple[RawRegion, int, int]:
    stream.seek(0)
    header = stream.read(HEADER_SIZE)
    if len(header) != HEADER_SIZE or not header.startswith(SIGNATURE):
        raise DecodeError("7z signature header is truncated or invalid", member_count=0)
    if header[6] != 0:
        raise DecodeError("unsupported 7z major version", status="unsupported", member_count=0)
    crc, offset, size, checksum = struct.unpack("<IQQI", header[8:])
    if zlib.crc32(header[12:]) != crc:
        raise DecodeError("7z start-header checksum mismatch", member_count=0)
    offset += HEADER_SIZE
    if offset > len(stream) or size > len(stream) - offset:
        raise DecodeError("7z next header lies outside the archive", member_count=0)
    stream.seek(offset)
    remaining, actual = size, 0
    while remaining:
        chunk = stream.read(min(remaining, 64 * 1024))
        actual = zlib.crc32(chunk, actual)
        remaining -= len(chunk)
    if actual != checksum:
        raise DecodeError("7z next-header checksum mismatch", member_count=0)
    fields = (
        RawRegion("signature", 0, 6),
        RawRegion("version", 6, 2, f"{header[6]}.{header[7]}"),
        RawRegion("start_header_crc", 8, 4, crc),
        RawRegion("next_header_offset", 12, 8, offset - HEADER_SIZE),
        RawRegion("next_header_size", 20, 8, size),
        RawRegion("next_header_crc", 28, 4, checksum),
    )
    return RawRegion("signature_header", 0, HEADER_SIZE, children=fields), offset, size


def _helper(stream: FileStream, parent: Match, operation: str, bound: int) -> bytes:
    try:
        installed = version("py7zr")
    except PackageNotFoundError as error:
        raise DecodeError(
            "install py7zr==1.1.4 to decode 7z archives", status="unsupported"
        ) from error
    if installed != "1.1.4":
        raise DecodeError("7z decoding requires py7zr==1.1.4", status="unsupported")
    context = parent.analysis_context
    limits = context.limits
    total = (
        None
        if limits.max_total_bytes is None
        else max(0, limits.max_total_bytes - context.total_bytes)
    )
    allowances = (context.remaining_members, limits.max_member_bytes, total)
    script = str(Path(__file__).with_name("_sevenzip_helper.py"))
    command = (
        sys.executable,
        "-I",
        script,
        operation,
        *("none" if value is None else str(value) for value in allowances),
    )
    stream.seek(0)
    try:
        return run_helper(
            stream,
            command,
            max_output=bound,
            max_memory=limits.max_codec_memory,
            helper_timeout=limits.helper_timeout,
        )
    except DecodeError as error:
        for status in ("unsupported", "limited"):
            if str(error).startswith(f"external decoder failed: {status}:"):
                error.status = status
        raise


def _metadata(stream: FileStream, parent: Match, header_size: int) -> _Metadata:
    remaining = parent.analysis_context.remaining_members
    count = _MAX_MEMBERS if remaining is None else min(remaining, _MAX_MEMBERS)
    # The pinned backend bounds decoded headers and file counts. JSON can expand one
    # header character to six bytes; the remaining term covers fixed per-entry metadata.
    bound = 6 * max(header_size, _MAX_HEADER) + 256 * count
    result = json.loads(_helper(stream, parent, "metadata", bound))
    return cast(_Metadata, result)


def _admission(parent: Match) -> str | None:
    context = parent.analysis_context
    depth = context.limits.max_depth
    if depth is not None and parent.analysis_depth >= depth:
        return f"7z decoding exceeds --max-depth={depth}"
    if context.remaining_members == 0:
        return "7z member count exceeds the remaining analysis allowance"
    return None


def _regions(metadata: _Metadata, offset: int, parent: Match) -> Iterator[Match]:
    for index, (start, length) in enumerate(metadata["packed"]):
        if start < HEADER_SIZE or start + length > offset:
            raise DecodeError("7z packed stream overlaps its next header", member_count=0)
        yield Submatch("packed_stream", index, start - HEADER_SIZE, length, parent=parent)
    for start, length in metadata["packed_header"]:
        yield Submatch("packed_header", None, start - HEADER_SIZE, length, parent=parent)


def _members(
    metadata: _Metadata,
    data: bytes,
    header: Match,
    parent: Match,
) -> Iterator[Match]:
    offset = 0
    for info in metadata["members"]:
        entry = Submatch("member", info, 0, 0, parent=header, display_name=info["name"])
        reason = parent.analysis_context.claim_entry()
        entry.analysis_member_counted = True
        yield entry
        length = 0 if info["directory"] else info["size"]
        start = offset
        offset += length
        if reason is not None:
            entry.analysis_status, entry.analysis_message = "limited", reason
        elif not info["directory"]:
            allowance = parent.analysis_context.member_limit
            if allowance is not None and length > allowance:
                entry.analysis_status = "limited"
                entry.analysis_message = "7z member exceeds the remaining decoded-byte allowance"
            else:
                yield from match_decoded(entry, data[start:offset], member_counted=True)


@register_parser("application/x-7z-compressed")
def parse_sevenzip(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map validated 7z headers and streams, then recursively analyze decoded members.

    Args:
        stream: Archive bytes positioned at the beginning of the identified source.
        parent: The 7z archive match receiving physical and decoded children.

    Yields:
        Framing, member metadata, and independently sourced decoded contents.
    """
    try:
        signature, offset, size = _signature(stream)
        yield from signature.matches(parent)
        encoded = Submatch("encoded_data", None, HEADER_SIZE, offset - HEADER_SIZE, parent=parent)
        yield encoded
        header = Submatch("next_header", None, offset, size, parent=parent)
        yield header
        end = offset + size
        if end < len(stream):
            yield Submatch("trailing_data", None, end, len(stream) - end, parent=parent)
        reason = _admission(parent)
        if reason is not None:
            parent.analysis_status, parent.analysis_message = "limited", reason
            return
        metadata = _metadata(stream, parent, size)
        yield from _regions(metadata, offset, encoded)
        length = sum(info["size"] for info in metadata["members"] if not info["directory"])
        data = _helper(stream, parent, "extract", length)
        if len(data) != length:
            raise DecodeError("7z decoder returned an unexpected decoded size", member_count=0)
        yield from _members(metadata, data, header, parent)
    except DecodeError as error:
        parent.analysis_status, parent.analysis_message = error.status, str(error)
