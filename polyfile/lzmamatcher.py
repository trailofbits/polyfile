"""Legacy LZMA-alone framing and bounded recursive decoded-content analysis."""

from collections.abc import Iterator

from polyfile.compression import (
    DecodeError,
    DecodeResult,
    OutputBuffer,
    RawRegion,
    parse_compressed,
)
from polyfile.fileutils import FileStream
from polyfile.lzmastream import inflate_lzma
from polyfile.polyfile import Match, register_parser

UNKNOWN_SIZE = (1 << 64) - 1


def _header(stream: FileStream) -> tuple[RawRegion, int | None]:
    start = stream.tell()
    data = stream.read(13)
    region = RawRegion("lzma_alone_header", start, len(data), data)
    if len(data) != 13:
        raise DecodeError("truncated LZMA-alone header", regions=(region,))
    size = int.from_bytes(data[5:13], "little")
    fields = (
        RawRegion("properties", start, 1, data[0]),
        RawRegion("dictionary_size", start + 1, 4, int.from_bytes(data[1:5], "little")),
        RawRegion(
            "uncompressed_size",
            start + 5,
            8,
            "unknown" if size == UNKNOWN_SIZE else size,
        ),
    )
    region = RawRegion("lzma_alone_header", start, 13, children=fields)
    if data[0] >= 225:
        raise DecodeError("invalid LZMA-alone properties byte", regions=(region,))
    lc, lp = data[0] % 9, (data[0] // 9) % 5
    if lc + lp > 4:
        raise DecodeError(
            f"unsupported LZMA-alone properties lc={lc}, lp={lp}: liblzma requires lc+lp<=4",
            status="unsupported",
            regions=(region,),
        )
    return region, None if size == UNKNOWN_SIZE else size


def _member(
    stream: FileStream, output: OutputBuffer, max_memory: int | None
) -> DecodeResult:
    start = stream.tell()
    fields: tuple[RawRegion, ...] = ()
    try:
        header, size = _header(stream)
        fields = (header,)
        if (
            size is not None
            and output.remaining is not None
            and size > output.remaining
        ):
            raise DecodeError(
                f"declared LZMA-alone size {size} exceeds the decoded-output allowance",
                status="limited",
            )
        end = inflate_lzma(stream, output, start, format="alone", max_memory=max_memory)
        if end != len(stream):
            raise DecodeError(
                "trailing data or concatenated LZMA-alone streams are not supported"
            )
        data = output.finish()
        if size is not None and len(data) != size:
            raise DecodeError(
                f"LZMA-alone size mismatch: declared {size}, decoded {len(data)}"
            )
    except DecodeError as error:
        fields = fields or error.regions
        region = RawRegion(
            "lzma_alone_stream", start, stream.tell() - start, children=fields
        )
        raise DecodeError(str(error), status=error.status, regions=(region,)) from error
    fields += (RawRegion("compressed_data", start + 13, end - start - 13),)
    region = RawRegion("lzma_alone_stream", start, end - start, children=fields)
    return DecodeResult(data, (region,), 1)


def decode_lzma_alone(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decode one legacy LZMA-alone file using its known-size or streamed ending.

    Args:
        stream: Encoded LZMA-alone bytes, positioned at their header.
        max_output: Optional maximum decoded length.
        max_memory: Optional native decoder memory allowance; None is unlimited.
        max_members: Optional allowance for the single stream in this format.

    Returns:
        Validated decoded bytes and their physical header and encoded-data regions.

    Raises:
        DecodeError: If framing, backend support, a declared size, or a limit fails.
    """
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "LZMA-alone stream exceeds the member allowance", status="limited"
        )
    return _member(stream, OutputBuffer(max_output), max_memory)


@register_parser("application/x-lzma")
def parse_lzma_alone(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map LZMA-alone framing and recursively analyze complete decoded bytes."""
    yield from parse_compressed(stream, parent, decode_lzma_alone)
