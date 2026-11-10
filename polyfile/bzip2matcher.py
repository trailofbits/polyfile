"""Validated streaming bzip2 decoding and recursive content analysis."""

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

BZIP2_MAGIC = b"BZh"
END_MAGIC = b"\x17\x72\x45\x38\x50\x90"


def _header(stream: FileStream, max_memory: int | None) -> tuple[RawRegion, ...]:
    start = stream.tell()
    data = stream.read(4)
    fields = [RawRegion("magic", start, min(3, len(data)), data[:3])]
    if len(data) != 4:
        raise DecodeError("truncated bzip2 header", regions=tuple(fields))
    if data[:3] != BZIP2_MAGIC or not 49 <= data[3] <= 57:
        raise DecodeError(
            "invalid bzip2 signature or block size", regions=tuple(fields)
        )
    block_size = (data[3] - 48) * 100_000
    fields.append(RawRegion("block_size", start + 3, 1, block_size))
    memory = 100_000 + 4 * block_size
    if max_memory is not None and max_memory < memory:
        raise DecodeError(
            f"bzip2 block size {block_size} requires a {memory}-byte codec-memory allowance",
            status="limited",
            regions=tuple(fields),
        )
    return tuple(fields)


def _inflate(stream: FileStream, output: OutputBuffer, start: int) -> int:
    try:
        import bz2
    except ImportError as error:
        raise DecodeError(
            "bzip2 decoding requires Python built with the bz2 module",
            status="unsupported",
        ) from error
    decoder = bz2.BZ2Decompressor()
    stream.seek(start)
    while not decoder.eof:
        chunk = stream.read(CHUNK_SIZE) if decoder.needs_input else b""
        if decoder.needs_input and not chunk:
            raise DecodeError(f"truncated bzip2 stream at byte offset {start}")
        try:
            output.append(decoder.decompress(chunk, max_length=output.next_size))
        except OSError as error:
            raise DecodeError(
                f"invalid bzip2 stream at byte offset {start}: {error}"
            ) from error
    end = stream.tell() - len(decoder.unused_data)
    stream.seek(end)
    return end


def _framing(stream: FileStream, start: int, end: int) -> tuple[RawRegion, ...]:
    with stream.save_pos():
        stream.seek(start + 4)
        header = stream.read(10)
    if header[:6] == END_MAGIC:
        return (
            RawRegion("end_marker", start + 4, 6, header[:6]),
            RawRegion(
                "combined_crc32", start + 10, 4, int.from_bytes(header[6:], "big")
            ),
        )
    return (
        RawRegion("block_magic", start + 4, 6, header[:6]),
        RawRegion("block_crc32", start + 10, 4, int.from_bytes(header[6:], "big")),
        RawRegion("compressed_data", start + 14, end - start - 14),
    )


def _member(
    stream: FileStream, output: OutputBuffer, max_memory: int | None
) -> RawRegion:
    start = stream.tell()
    fields: tuple[RawRegion, ...] = ()
    try:
        fields = _header(stream, max_memory)
        end = _inflate(stream, output, start)
    except DecodeError as error:
        fields = fields or error.regions
        region = RawRegion(
            "bzip2_stream", start, stream.tell() - start, children=fields
        )
        raise DecodeError(str(error), status=error.status, regions=(region,)) from error
    fields += _framing(stream, start, end)
    return RawRegion("bzip2_stream", start, end - start, children=fields)


def decode_bzip2(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decode concatenated bzip2 streams and validate all block and stream checksums.

    Args:
        stream: Encoded bzip2 bytes, positioned at the first stream.
        max_output: Optional maximum length of the concatenated decoded bytes.
        max_memory: Optional libbz2 workspace allowance in bytes, checked before allocation.
        max_members: Optional maximum number of concatenated streams.

    Returns:
        Complete validated output and the physical stream framing regions.

    Raises:
        DecodeError: If integrity, framing, truncation, or a configured limit fails.
    """
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    while stream.tell() < len(stream):
        try:
            if max_members is not None and len(regions) >= max_members:
                raise DecodeError(
                    f"bzip2 stream count exceeds the limit of {max_members}",
                    status="limited",
                )
            regions.append(_member(stream, output, max_memory))
        except DecodeError as error:
            raise DecodeError(
                str(error),
                status=error.status,
                regions=tuple(regions) + error.regions,
            ) from error
    if not regions:
        raise DecodeError("empty input contains no bzip2 stream")
    return DecodeResult(output.finish(), tuple(regions), len(regions))


@register_parser("application/x-bzip2")
def parse_bzip2(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map bzip2 stream framing and recursively analyze validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_bzip2)
