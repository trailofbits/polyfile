"""Gzip member framing, integrity validation, and recursive decoding."""

import zlib
from collections.abc import Iterator

from polyfile.compression import (
    CHUNK_SIZE,
    DecodeError,
    DecodeResult,
    OutputBuffer,
    RawRegion,
    parse_compressed,
)
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, register_parser

GZIP_MAGIC = b"\x1f\x8b"
GZIP_MEMORY = 64 * 1024


def _read_exact(stream: FileStream, length: int, field: str) -> bytes:
    data = stream.read(length)
    if len(data) != length:
        raise DecodeError(
            f"truncated gzip {field} at byte offset {stream.tell() - len(data)}"
        )
    return data


def _terminated(stream: FileStream, field: str) -> bytes:
    data = bytearray()
    while stream.tell() < len(stream):
        part = stream.read(CHUNK_SIZE)
        end = part.find(b"\0")
        if end >= 0:
            stream.seek(stream.tell() - len(part) + end + 1)
            data.extend(part[: end + 1])
            return bytes(data)
        data.extend(part)
    raise DecodeError(f"unterminated gzip {field}")


def _header(stream: FileStream) -> tuple[RawRegion, ...]:
    start = stream.tell()
    header = _read_exact(stream, 10, "header")
    if header[:2] != GZIP_MAGIC:
        raise DecodeError(f"invalid gzip signature at byte offset {start}")
    if header[2] != 8:
        raise DecodeError(
            f"unsupported gzip compression method {header[2]}", status="unsupported"
        )
    if header[3] & 0xE0:
        raise DecodeError(f"reserved gzip flags are set at byte offset {start + 3}")
    fields = [
        RawRegion("magic", start, 2, header[:2]),
        RawRegion("compression_method", start + 2, 1, header[2]),
        RawRegion("flags", start + 3, 1, header[3]),
        RawRegion("mod_time", start + 4, 4, int.from_bytes(header[4:8], "little")),
        RawRegion("extra_flags", start + 8, 1, header[8]),
        RawRegion("os", start + 9, 1, header[9]),
    ]
    if header[3] & 4:
        offset = stream.tell()
        size = _read_exact(stream, 2, "extra length")
        fields.append(
            RawRegion("extra_length", offset, 2, int.from_bytes(size, "little"))
        )
        offset = stream.tell()
        extra = _read_exact(stream, int.from_bytes(size, "little"), "extra field")
        fields.append(RawRegion("extras", offset, len(extra), extra))
    for mask, name in ((8, "name"), (16, "comment")):
        if header[3] & mask:
            offset = stream.tell()
            data = _terminated(stream, name)
            fields.append(RawRegion(name, offset, len(data), data))
    if header[3] & 2:
        offset = stream.tell()
        crc = _read_exact(stream, 2, "header checksum")
        fields.append(
            RawRegion("header_crc16", offset, 2, int.from_bytes(crc, "little"))
        )
    return tuple(fields)


def _inflate(stream: FileStream, output: OutputBuffer, start: int) -> int:
    stream.seek(start)
    decoder = zlib.decompressobj(31)
    while not decoder.eof:
        chunk = decoder.unconsumed_tail or stream.read(CHUNK_SIZE)
        if not chunk:
            raise DecodeError(f"truncated gzip member at byte offset {start}")
        try:
            data = decoder.decompress(chunk, output.next_size)
        except zlib.error as error:
            raise DecodeError(
                f"invalid gzip member at byte offset {start}: {error}"
            ) from error
        output.append(data)
    end = stream.tell() - len(decoder.unused_data)
    stream.seek(end)
    return end


def _member(stream: FileStream, output: OutputBuffer) -> RawRegion:
    start = stream.tell()
    fields = list(_header(stream))
    body_start = stream.tell()
    try:
        end = _inflate(stream, output, start)
    except DecodeError as error:
        region = RawRegion(
            "gzip_member", start, len(stream) - start, children=tuple(fields)
        )
        raise DecodeError(str(error), status=error.status, regions=(region,)) from error
    fields.append(RawRegion("body", body_start, end - body_start - 8))
    with stream.save_pos():
        stream.seek(end - 8)
        trailer = _read_exact(stream, 8, "trailer")
    fields.extend(
        (
            RawRegion("body_crc32", end - 8, 4, int.from_bytes(trailer[:4], "little")),
            RawRegion(
                "len_uncompressed", end - 4, 4, int.from_bytes(trailer[4:], "little")
            ),
        )
    )
    return RawRegion("gzip_member", start, end - start, children=tuple(fields))


def _padding(stream: FileStream) -> RawRegion:
    start = stream.tell()
    while stream.tell() < len(stream):
        if stream.read(CHUNK_SIZE).strip(b"\0"):
            raise DecodeError(f"non-gzip trailing data at byte offset {start}")
    return RawRegion("padding", start, len(stream) - start)


def decode_gzip(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decodes concatenated gzip members with complete framing and integrity checks.

    Args:
        stream: The gzip stream to decode.
        max_output: Optional maximum size of the concatenated decoded content.
        max_memory: Optional codec-memory allowance; gzip needs at most 64 KiB.
        max_members: Optional maximum number of gzip members.

    Returns:
        The validated concatenated output and physical member regions.

    Raises:
        DecodeError: If framing, integrity, or a configured resource limit fails.
    """
    if max_memory is not None and max_memory < GZIP_MEMORY:
        raise DecodeError(
            "gzip requires a 64 KiB codec-memory allowance", status="limited"
        )
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    while stream.tell() < len(stream):
        with stream.save_pos():
            magic = stream.read(2)
        try:
            if regions and magic.startswith(b"\0"):
                regions.append(_padding(stream))
            else:
                if max_members is not None and members >= max_members:
                    raise DecodeError(
                        f"gzip member count exceeds the limit of {max_members}",
                        status="limited",
                    )
                regions.append(_member(stream, output))
                members += 1
        except DecodeError as error:
            raise DecodeError(
                str(error), status=error.status, regions=tuple(regions) + error.regions
            ) from error
    if not regions:
        raise DecodeError("empty input contains no gzip member")
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser("application/gzip")
def parse_gzip(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps gzip framing and recursively analyzes its validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_gzip)
