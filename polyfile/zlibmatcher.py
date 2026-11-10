"""Validate zlib framing and recursively analyze decoded content."""

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

ZLIB_MEMORY = 64 * 1024


def _header(stream: FileStream) -> RawRegion:
    start = stream.tell()
    data = stream.read(2)
    if len(data) != 2:
        raise DecodeError("truncated zlib CMF/FLG header")
    cmf, flg = data
    if cmf & 15 != 8 or cmf >> 4 > 7:
        raise DecodeError("invalid zlib compression method or window size")
    if int.from_bytes(data, "big") % 31:
        raise DecodeError("invalid zlib CMF/FLG check bits")
    children = (RawRegion("cmf", start, 1, cmf), RawRegion("flg", start + 1, 1, flg))
    if flg & 32:
        dictionary = stream.read(4)
        if len(dictionary) != 4:
            raise DecodeError("truncated zlib preset dictionary identifier")
        region = RawRegion(
            "zlib_header",
            start,
            6,
            children=children
            + (
                RawRegion(
                    "dictionary_id", start + 2, 4, int.from_bytes(dictionary, "big")
                ),
            ),
        )
        raise DecodeError(
            "zlib stream requires an external preset dictionary",
            status="unsupported",
            regions=(region,),
        )
    return RawRegion("zlib_header", start, 2, children=children)


def _inflate(stream: FileStream, output: OutputBuffer, start: int) -> int:
    stream.seek(start)
    decoder = zlib.decompressobj()
    while not decoder.eof:
        chunk = decoder.unconsumed_tail or stream.read(CHUNK_SIZE)
        if not chunk:
            raise DecodeError("truncated zlib stream before its Adler-32 checksum")
        try:
            output.append(decoder.decompress(chunk, output.next_size))
        except zlib.error as error:
            raise DecodeError(
                f"invalid zlib stream or Adler-32 checksum: {error}"
            ) from error
    return stream.tell() - len(decoder.unused_data)


def decode_zlib(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decode one complete zlib stream, rejecting trailing bytes.

    Args:
        stream: Encoded zlib bytes.
        max_output: Optional maximum decoded content size.
        max_memory: Optional codec-memory allowance; at least 64 KiB is required.
        max_members: Optional member allowance; zlib contains one stream.

    Returns:
        Validated decoded bytes and physical framing regions.

    Raises:
        DecodeError: If validation fails, a dictionary is required, or a limit is reached.
    """
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "zlib member count exceeds its analysis allowance", status="limited"
        )
    if max_memory is not None and max_memory < ZLIB_MEMORY:
        raise DecodeError(
            "zlib requires a 64 KiB codec-memory allowance", status="limited"
        )
    start = stream.tell()
    header = _header(stream)
    output = OutputBuffer(max_output)
    try:
        end = _inflate(stream, output, start)
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=(header,)) from error
    with stream.save_pos():
        stream.seek(end - 4)
        checksum = int.from_bytes(stream.read(4), "big")
    regions = (
        header,
        RawRegion("compressed_data", start + 2, end - start - 6),
        RawRegion("adler32", end - 4, 4, checksum),
    )
    if end != len(stream):
        raise DecodeError(
            f"unexpected trailing data after zlib stream at byte offset {end}",
            regions=regions + (RawRegion("trailing_data", end, len(stream) - end),),
        )
    return DecodeResult(output.finish(), regions, member_count=1)


@register_parser("application/zlib")
def parse_zlib(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map a zlib stream and recursively analyze its validated content."""
    yield from parse_compressed(stream, parent, decode_zlib)
