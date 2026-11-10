"""XZ stream framing, integrity validation, and recursive decoded-content analysis."""

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
from polyfile.lzmastream import inflate_lzma
from polyfile.polyfile import Match, register_parser

XZ_MAGIC = b"\xfd7zXZ\0"


def _header(stream: FileStream) -> tuple[RawRegion, int]:
    start = stream.tell()
    data = stream.read(12)
    region = RawRegion("xz_header", start, len(data), data)
    if len(data) != 12 or data[:6] != XZ_MAGIC:
        raise DecodeError("invalid or truncated XZ header", regions=(region,))
    fields = (
        RawRegion("magic", start, 6, data[:6]),
        RawRegion("stream_flags", start + 6, 2, data[6:8]),
        RawRegion("header_crc32", start + 8, 4, int.from_bytes(data[8:], "little")),
    )
    region = RawRegion("xz_header", start, 12, children=fields)
    if data[6] or data[7] & 0xF0:
        raise DecodeError("reserved XZ stream flags are set", regions=(region,))
    if zlib.crc32(data[6:8]) != int.from_bytes(data[8:], "little"):
        raise DecodeError("invalid XZ header CRC32", regions=(region,))
    return region, data[7] & 0x0F


def _footer(stream: FileStream, end: int) -> tuple[RawRegion, int]:
    with stream.save_pos():
        stream.seek(end - 12)
        data = stream.read(12)
    index_size = (int.from_bytes(data[4:8], "little") + 1) * 4
    fields = (
        RawRegion("footer_crc32", end - 12, 4, int.from_bytes(data[:4], "little")),
        RawRegion("backward_size", end - 8, 4, index_size),
        RawRegion("stream_flags", end - 4, 2, data[8:10]),
        RawRegion("footer_magic", end - 2, 2, data[10:]),
    )
    return RawRegion("xz_footer", end - 12, 12, children=fields), index_size


def _member(
    stream: FileStream, output: OutputBuffer, max_memory: int | None
) -> RawRegion:
    start = stream.tell()
    fields: tuple[RawRegion, ...] = ()
    try:
        header, check = _header(stream)
        fields = (header,)
        end = inflate_lzma(
            stream, output, start, format="xz", max_memory=max_memory, check_id=check
        )
    except DecodeError as error:
        fields = fields or error.regions
        region = RawRegion("xz_stream", start, stream.tell() - start, children=fields)
        raise DecodeError(str(error), status=error.status, regions=(region,)) from error
    footer, index_size = _footer(stream, end)
    index_start = end - 12 - index_size
    fields += (
        RawRegion("blocks", start + 12, index_start - start - 12),
        RawRegion("index", index_start, index_size),
        footer,
    )
    return RawRegion("xz_stream", start, end - start, children=fields)


def _padding(stream: FileStream) -> RawRegion:
    start = stream.tell()
    while stream.tell() < len(stream):
        data = stream.read(CHUNK_SIZE)
        count = len(data) - len(data.lstrip(b"\0"))
        if count != len(data):
            stream.seek(stream.tell() - len(data) + count)
            break
    region = RawRegion("padding", start, stream.tell() - start)
    if region.length % 4:
        raise DecodeError(
            "XZ stream padding must be a multiple of four zero bytes", regions=(region,)
        )
    return region


def decode_xz(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decode checked XZ streams separated or followed by legal stream padding.

    Args:
        stream: Encoded XZ bytes, positioned at the first stream.
        max_output: Optional maximum length of the concatenated decoded bytes.
        max_memory: Optional liblzma memory allowance, enforced by the native decoder.
        max_members: Optional maximum number of XZ streams, excluding padding.

    Returns:
        Complete decoded output and physical stream and padding regions.

    Raises:
        DecodeError: If framing, integrity, backend support, or a limit fails.
    """
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    while stream.tell() < len(stream):
        with stream.save_pos():
            padding = members > 0 and stream.read(1) == b"\0"
        try:
            if padding:
                regions.append(_padding(stream))
                continue
            if max_members is not None and members >= max_members:
                raise DecodeError(
                    f"XZ stream count exceeds the limit of {max_members}",
                    status="limited",
                )
            regions.append(_member(stream, output, max_memory))
            members += 1
        except DecodeError as error:
            raise DecodeError(
                str(error), status=error.status, regions=tuple(regions) + error.regions
            ) from error
    if not members:
        raise DecodeError("empty input contains no XZ stream")
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser("application/x-xz")
def parse_xz(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map XZ framing and recursively analyze its completely validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_xz)
