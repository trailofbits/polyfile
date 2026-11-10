"""LRZIP 0.6/0.7 framing and recursive analysis through a version-qualified helper."""

import hashlib
import re
import shutil
from collections.abc import Iterator
from functools import partial
from pathlib import Path

from polyfile.compression import DecodeError, DecodeResult, RawRegion, parse_compressed
from polyfile.external import run_helper
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, register_parser

LRZIP_VERSION = re.compile(rb"^lrzip version (\d+)\.(\d+)\.(\d+)(?:\r?\n|$)")
LRZIP_ENVIRONMENT = {"LRZIP": "NOCONFIG"}
HEADER_FIELDS = (
    ("magic", 0, 4),
    ("major_version", 4, 5),
    ("minor_version", 5, 6),
    ("uncompressed_size", 6, 14),
    ("streaming", 14, 15),
    ("reserved", 15, 16),
    ("lzma_properties", 16, 21),
    ("md5_present", 21, 22),
    ("encryption", 22, 23),
    ("last_block", 23, 24),
)


def find_lrzip(*, helper_timeout: float | None = None) -> str:
    """Find an installed LRZIP 0.7.3 or newer executable.

    Args:
        helper_timeout: Optional timeout for the fixed version-query invocation.

    Returns:
        The absolute path of the supported installed helper.

    Raises:
        DecodeError: If the helper is missing, unsupported, or exceeds its timeout.
    """
    found = shutil.which("lrzip")
    if found is not None:
        executable = str(Path(found).resolve())
        try:
            with FileStream(b"") as stream:
                version = run_helper(
                    stream,
                    (executable, "--version"),
                    max_output=8192,
                    helper_timeout=helper_timeout,
                    environment=LRZIP_ENVIRONMENT,
                )
        except DecodeError as error:
            if error.status == "limited":
                raise
        else:
            matched = LRZIP_VERSION.search(version)
            if matched is not None and tuple(map(int, matched.groups())) >= (0, 7, 3):
                return executable
    raise DecodeError(
        "LRZIP decoding requires lrzip 0.7.3 or newer installed on PATH",
        status="unsupported",
    )


def _stream_flags_valid(data: bytes) -> bool:
    if data[5] == 6:
        return data[14] == 0 and data[23] == 0
    return data[14] in (0, 1) and data[23] in (0, 1) and bool(data[14] or data[23])


def _validate_header(data: bytes, region: RawRegion) -> int:
    if data[:4] != b"LRZI":
        raise DecodeError("invalid LRZIP signature", regions=(region,))
    if (data[4], data[5]) not in ((0, 6), (0, 7)):
        raise DecodeError(
            f"unsupported LRZIP archive version {data[4]}.{data[5]}",
            status="unsupported",
            regions=(region,),
        )
    if data[22]:
        raise DecodeError(
            "encrypted LRZIP archives are unsupported",
            status="unsupported",
            regions=(region,),
        )
    if data[21] not in (0, 1) or data[15] or not _stream_flags_valid(data):
        raise DecodeError(
            "invalid LRZIP header flags or reserved bytes", regions=(region,)
        )
    size = int.from_bytes(data[6:14], "little", signed=True)
    if size < 0:
        raise DecodeError("negative LRZIP uncompressed size", regions=(region,))
    return size


def _first_chunk(stream: FileStream, header: bytes, body_end: int) -> RawRegion:
    start = stream.tell()
    prefix_size = 2 if header[5] == 6 else 3
    prefix = stream.read(prefix_size)
    if len(prefix) != prefix_size or not 1 <= prefix[0] <= 8:
        raise DecodeError("invalid or truncated LRZIP chunk-offset width")
    width = prefix[0]
    if header[5] == 7 and prefix[1] > 2:
        raise DecodeError("invalid LRZIP chunk prefilter")
    final = prefix[-1]
    if final not in (0, 1):
        raise DecodeError("invalid LRZIP chunk end flag")
    size = stream.read(width)
    if len(size) != width or stream.tell() > body_end:
        raise DecodeError("truncated LRZIP chunk size")
    if header[5] == 7 and header[14] and final != header[23]:
        raise DecodeError("LRZIP chunk and streaming-block end flags disagree")
    chunk_size = int.from_bytes(size, "little", signed=width == 8)
    if chunk_size < 0:
        raise DecodeError("negative LRZIP chunk size")
    fields = [RawRegion("offset_width", start, 1, width)]
    if prefix_size == 3:
        fields.append(RawRegion("prefilter", start + 1, 1, prefix[1]))
    fields.extend(
        (
            RawRegion("last_chunk", start + prefix_size - 1, 1, final),
            RawRegion(
                "chunk_capacity",
                start + prefix_size,
                width,
                chunk_size,
            ),
        )
    )
    return RawRegion(
        "rzip_chunk_header", start, prefix_size + width, children=tuple(fields)
    )


def _framing(
    stream: FileStream,
) -> tuple[tuple[RawRegion, ...], int, bytes | None]:
    start = stream.tell()
    data = stream.read(24)
    header = RawRegion("lrzip_header", start, len(data), data)
    if len(data) != 24:
        raise DecodeError("truncated LRZIP header", regions=(header,))
    fields = tuple(
        RawRegion(name, start + first, last - first, data[first:last])
        for name, first, last in HEADER_FIELDS
    )
    header = RawRegion("lrzip_header", start, 24, children=fields)
    size = _validate_header(data, header)
    digest_size = 16 if data[21] else 0
    body_end = len(stream) - digest_size
    if body_end <= stream.tell():
        raise DecodeError("truncated LRZIP encoded data or MD5", regions=(header,))
    try:
        chunk = _first_chunk(stream, data, body_end)
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=(header,)) from error
    encoded = RawRegion("encoded_chunks", stream.tell(), body_end - stream.tell())
    body = RawRegion(
        "lrzip_body", start + 24, body_end - start - 24, children=(chunk, encoded)
    )
    regions = (header, body)
    digest = None
    if digest_size:
        stream.seek(body_end)
        digest = stream.read(16)
        regions += (RawRegion("md5", body_end, 16, digest.hex()),)
    return regions, size, digest


def _verify_output(decoded: bytes, size: int, digest: bytes | None) -> None:
    if size and len(decoded) != size:
        raise DecodeError(
            f"LRZIP size mismatch: declared {size}, decoded {len(decoded)}"
        )
    if (
        digest is not None
        and hashlib.md5(decoded, usedforsecurity=False).digest() != digest
    ):
        raise DecodeError("LRZIP MD5 mismatch")


def decode_lrzip(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
    helper_timeout: float | None = None,
) -> DecodeResult:
    """Decode one unencrypted LRZIP 0.6/0.7 archive through the installed helper.

    Args:
        stream: Encoded archive positioned at its LRZI header.
        max_output: Optional maximum decoded size.
        max_memory: Optional hard helper address-space ceiling, supported on Linux.
        max_members: Optional allowance for this one LRZIP archive.
        helper_timeout: Optional timeout for each fixed helper invocation.

    Returns:
        Complete decoded bytes and their physical encoded framing regions.

    Raises:
        DecodeError: If framing, helper availability, integrity, or a limit fails.
    """
    start = stream.tell()
    if start >= len(stream) or max_members == 0:
        raise DecodeError(
            "LRZIP archive is absent or exceeds the member allowance",
            status="invalid" if start >= len(stream) else "limited",
            member_count=0,
        )
    regions, size, digest = _framing(stream)
    try:
        if max_output is not None and size > max_output:
            raise DecodeError(
                f"declared LRZIP size {size} exceeds the decoded-output allowance",
                status="limited",
            )
        executable = find_lrzip(helper_timeout=helper_timeout)
        stream.seek(start)
        decoded = run_helper(
            stream,
            (executable, "-Q", "-d", "-o", "-", "-p", "1"),
            max_output=max_output,
            max_memory=max_memory,
            helper_timeout=helper_timeout,
            environment=LRZIP_ENVIRONMENT,
        )
        _verify_output(decoded, size, digest)
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=regions) from error
    return DecodeResult(decoded, regions)


@register_parser("application/x-lrzip")
def parse_lrzip(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map LRZIP framing and recursively analyze its completely decoded contents."""
    decoder = partial(
        decode_lrzip, helper_timeout=parent.analysis_context.limits.helper_timeout
    )
    yield from parse_compressed(stream, parent, decoder)
