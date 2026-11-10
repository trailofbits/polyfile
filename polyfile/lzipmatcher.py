"""Native lzip version 1 framing and recursively analyzed raw-LZMA payloads."""

import lzma
import struct
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

LZIP_MAGIC = b"LZIP"
LZMA_STATE_ALLOWANCE = 128 * 1024


def _dictionary_size(code: int) -> int:
    exponent = code & 0x1F
    if not 12 <= exponent <= 29:
        raise DecodeError(f"invalid lzip dictionary encoding 0x{code:02x}")
    base = 1 << exponent
    size = base - (base >> 4) * (code >> 5)
    if not 4096 <= size <= 512 * 1024 * 1024:
        raise DecodeError(f"invalid lzip dictionary size {size}")
    return size


def _header(stream: FileStream) -> tuple[int, RawRegion]:
    start = stream.tell()
    data = stream.read(6)
    region = RawRegion("lzip_header", start, len(data), data)
    if len(data) != 6:
        raise DecodeError(f"truncated lzip header at offset {start}", regions=(region,))
    if data[:4] != LZIP_MAGIC:
        raise DecodeError(
            f"invalid lzip signature at offset {start}", regions=(region,)
        )
    fields = (
        RawRegion("magic", start, 4, data[:4]),
        RawRegion("version", start + 4, 1, data[4]),
        RawRegion("coded_dictionary_size", start + 5, 1, data[5]),
    )
    region = RawRegion("lzip_header", start, 6, children=fields)
    if data[4] != 1:
        raise DecodeError(
            f"lzip version {data[4]} is unsupported",
            status="unsupported",
            regions=(region,),
        )
    try:
        dictionary = _dictionary_size(data[5])
    except DecodeError as error:
        raise DecodeError(str(error), regions=(region,)) from error
    return dictionary, region


def _decompressor(dictionary: int, max_memory: int | None) -> lzma.LZMADecompressor:
    required = dictionary + LZMA_STATE_ALLOWANCE
    if max_memory is not None and required > max_memory:
        raise DecodeError(
            f"lzip needs a {required}-byte codec allowance, exceeding "
            f"--max-codec-memory={max_memory}",
            status="limited",
        )
    return lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": dictionary,
                "lc": 3,
                "lp": 0,
                "pb": 2,
            }
        ],
    )


def _inflate(
    stream: FileStream, output: OutputBuffer, decoder: lzma.LZMADecompressor
) -> tuple[int, int, int]:
    size, crc = 0, 0
    while not decoder.eof:
        chunk = stream.read(CHUNK_SIZE) if decoder.needs_input else b""
        if decoder.needs_input and not chunk:
            raise DecodeError(
                "truncated lzip LZMA stream: missing end-of-stream marker"
            )
        try:
            data = decoder.decompress(chunk, output.next_size)
        except lzma.LZMAError as error:
            raise DecodeError(f"invalid lzip LZMA stream: {error}") from error
        output.append(data)
        size += len(data)
        crc = zlib.crc32(data, crc)
    end = stream.tell() - len(decoder.unused_data)
    stream.seek(end)
    return end, size, crc


def _trailer(stream: FileStream, start: int, size: int, crc: int) -> RawRegion:
    offset = stream.tell()
    data = stream.read(20)
    region = RawRegion("lzip_trailer", offset, len(data), data)
    if len(data) != 20:
        raise DecodeError("truncated lzip member trailer", regions=(region,))
    checksum, data_size, member_size = struct.unpack("<IQQ", data)
    fields = (
        RawRegion("crc32", offset, 4, checksum),
        RawRegion("decoded_size", offset + 4, 8, data_size),
        RawRegion("member_size", offset + 12, 8, member_size),
    )
    region = RawRegion("lzip_trailer", offset, 20, children=fields)
    for actual, expected, name in (
        (crc, checksum, "CRC32"),
        (size, data_size, "decoded size"),
        (stream.tell() - start, member_size, "member size"),
    ):
        if actual != expected:
            raise DecodeError(
                f"lzip {name} mismatch: expected {expected}, got {actual}",
                regions=(region,),
            )
    return region


def _member(
    stream: FileStream, output: OutputBuffer, max_memory: int | None
) -> tuple[RawRegion, int]:
    start = stream.tell()
    dictionary, header = _header(stream)
    regions = [header]
    try:
        decoder = _decompressor(dictionary, max_memory)
        end, size, crc = _inflate(stream, output, decoder)
        regions.append(RawRegion("lzma_stream", start + 6, end - start - 6))
        regions.append(_trailer(stream, start, size, crc))
    except DecodeError as error:
        raise DecodeError(
            str(error), status=error.status, regions=tuple(regions) + error.regions
        ) from error
    region = RawRegion(
        "lzip_member", start, stream.tell() - start, children=tuple(regions)
    )
    return region, size


def decode_lzip(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decodes validated lzip v1 members using fixed raw-LZMA1 properties.

    Args:
        stream: The encoded lzip input.
        max_output: Optional concatenated-output allowance.
        max_memory: Optional dictionary plus decoder-state allowance.
        max_members: Optional number of member attempts, including invalid members.

    Returns:
        Validated concatenated bytes with physical header, body, and trailer regions.

    Raises:
        DecodeError: If framing, integrity, supported-version, or a resource check fails.
    """
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    empty = False
    while stream.tell() < len(stream):
        try:
            if max_members is not None and members >= max_members:
                raise DecodeError(
                    f"lzip member count exceeds {max_members}", status="limited"
                )
            members += 1
            region, size = _member(stream, output, max_memory)
            regions.append(region)
            empty = empty or size == 0
            if members > 1 and empty:
                raise DecodeError(
                    "empty members are invalid in a multimember lzip file"
                )
        except DecodeError as error:
            raise DecodeError(
                str(error),
                status=error.status,
                member_count=members,
                regions=tuple(regions) + error.regions,
            ) from error
    if not regions:
        raise DecodeError("empty input contains no lzip member", member_count=0)
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser("application/x-lzip")
def parse_lzip(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps lzip members and recursively analyzes validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_lzip)
