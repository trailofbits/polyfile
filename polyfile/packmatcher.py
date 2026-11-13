"""UNIX pack Huffman-tree framing, signature dispatch, and recursive decoding."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from polyfile.compression import (
    CHUNK_SIZE,
    DecodeError,
    DecodeResult,
    OutputBuffer,
    RawRegion,
    parse_compressed,
)
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.magic import MagicMatcher, TestType
from polyfile.polyfile import Match, register_parser

PACK_MAGIC = b"\x1f\x1e"
OLD_PACK_MAGIC = b"\x1f\x1f"
PACK_MIME = "application/x-unix-pack"
PACK_MEMORY = 4 * CHUNK_SIZE

with ExactNamedTempfile(
    rb"""0 string \037\036 packed data
!:mime application/x-unix-pack
!:ext z
>2 belong >1 \b, %d characters originally
>2 belong =1 \b, %d character originally
0 string \037\037 old packed data
!:mime application/x-unix-pack
""",
    name="UnixPackMimeMatcher",
) as _definition:
    MagicMatcher.DEFAULT_INSTANCE.add(Path(_definition), test_type=TestType.BINARY)


def _region(start: int, fields: list[RawRegion]) -> RawRegion:
    return RawRegion(
        "pack_header", start, sum(field.length for field in fields), children=tuple(fields)
    )


def _failure(
    message: str, start: int, fields: list[RawRegion], *, status: str = "invalid"
) -> DecodeError:
    return DecodeError(message, status=status, regions=(_region(start, fields),))


def _header(stream: FileStream) -> tuple[int, int, int, list[RawRegion]]:
    start = stream.tell()
    magic = stream.read(2)
    fields = [RawRegion("magic", start, len(magic), magic)]
    if len(magic) < 2:
        raise _failure("truncated UNIX pack signature", start, fields)
    if magic == OLD_PACK_MAGIC:
        raise _failure(
            "old UNIX pack (1f 1f) decoding is unsupported", start, fields, status="unsupported"
        )
    if magic != PACK_MAGIC:
        raise _failure("invalid UNIX pack signature", start, fields)
    fixed = stream.read(5)
    declared_size = int.from_bytes(fixed[:4], "big")
    fields.append(RawRegion("decoded_size", start + 2, min(4, len(fixed)), declared_size))
    if len(fixed) > 4:
        fields.append(RawRegion("max_code_length", start + 6, 1, fixed[4]))
    if len(fixed) != 5:
        raise _failure("truncated UNIX pack size or code length", start, fields)
    width = fixed[4]
    if width == 0:
        raise _failure("invalid UNIX pack maximum code length zero", start, fields)
    if width > 25:
        raise _failure(
            f"UNIX pack maximum code length {width} exceeds the supported limit",
            start,
            fields,
            status="unsupported",
        )
    return start, declared_size, width, fields


@dataclass(frozen=True)
class _Tree:
    header: RawRegion
    declared_size: int
    bases: tuple[int, ...]
    offsets: tuple[int, ...]
    literals: bytes


def _tree_codes(
    counts: bytes, start: int, fields: list[RawRegion]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    available, offset = 1, 0
    bases: list[int] = []
    offsets: list[int] = []
    for index, count in enumerate(counts):
        available = available * 2 - count - (2 if index == len(counts) - 1 else 0)
        if available < 0:
            raise _failure("oversubscribed UNIX pack Huffman tree", start, fields)
        bases.append(available)
        offsets.append(offset)
        offset += count
    if available:
        raise _failure("incomplete UNIX pack Huffman tree", start, fields)
    return tuple(bases), tuple(offsets)


def _framing(stream: FileStream) -> _Tree:
    start, declared_size, width, fields = _header(stream)
    counts = stream.read(width)
    fields.append(RawRegion("leaves_per_length", start + 7, len(counts), counts))
    if len(counts) != width:
        raise _failure("truncated UNIX pack Huffman counts", start, fields)
    literals_count = sum(counts) + 1
    if literals_count > 256:
        raise _failure("UNIX pack Huffman tree has too many literals", start, fields)
    bases, offsets = _tree_codes(counts, start, fields)
    offset = stream.tell()
    literals = stream.read(literals_count)
    fields.append(RawRegion("literals", offset, len(literals), literals))
    if len(literals) != literals_count:
        raise _failure("truncated UNIX pack Huffman literals", start, fields)
    return _Tree(_region(start, fields), declared_size, bases, offsets, literals)


class _Bits:
    def __init__(self, stream: FileStream) -> None:
        self.stream = stream
        self.buffer = b""
        self.index = 0
        self.value = 0
        self.left = 0
        self.position = stream.tell()

    def read(self) -> int:
        if not self.left:
            if self.index == len(self.buffer):
                self.buffer = self.stream.read(CHUNK_SIZE)
                self.index = 0
                if not self.buffer:
                    raise DecodeError("truncated UNIX pack Huffman stream: missing EOF code")
            self.value = self.buffer[self.index]
            self.index += 1
            self.left = 8
            self.position += 1
        self.left -= 1
        return (self.value >> self.left) & 1

    def finish(self) -> int:
        self.stream.seek(self.position)
        return self.position


def _symbol(bits: _Bits, tree: _Tree) -> int:
    code = 0
    for base, offset in zip(tree.bases, tree.offsets, strict=True):
        code = code * 2 + bits.read()
        if code >= base:
            return offset + code - base
    raise DecodeError("invalid UNIX pack Huffman code")


def _body(stream: FileStream, tree: _Tree, output: OutputBuffer) -> int:
    start = stream.tell()
    bits = _Bits(stream)
    size = 0
    pending = bytearray()
    try:
        while True:
            symbol = _symbol(bits, tree)
            if symbol == len(tree.literals):
                if size != tree.declared_size:
                    raise DecodeError("UNIX pack decoded length does not match its declared size")
                output.append(bytes(pending))
                return bits.finish()
            size += 1
            if size > tree.declared_size:
                raise DecodeError("UNIX pack decoded length exceeds its declared size")
            pending.append(tree.literals[symbol])
            if len(pending) == CHUNK_SIZE:
                output.append(bytes(pending))
                pending.clear()
    except DecodeError as error:
        region = RawRegion("huffman_data", start, bits.position - start)
        raise DecodeError(str(error), status=error.status, regions=(tree.header, region)) from error


def _member(stream: FileStream, output: OutputBuffer, max_memory: int | None) -> RawRegion:
    start = stream.tell()
    tree = _framing(stream)
    if max_memory is not None and max_memory < PACK_MEMORY:
        raise DecodeError(
            f"UNIX pack needs a {PACK_MEMORY}-byte codec workspace allowance",
            status="limited",
            regions=(tree.header,),
        )
    if output.remaining is not None and tree.declared_size > output.remaining:
        raise DecodeError(
            f"declared UNIX pack size {tree.declared_size} exceeds the output allowance",
            status="limited",
            regions=(tree.header,),
        )
    body_start = stream.tell()
    end = _body(stream, tree, output)
    body = RawRegion("huffman_data", body_start, end - body_start)
    return RawRegion("pack_member", start, end - start, children=(tree.header, body))


def decode_pack(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decodes modern UNIX pack members with bounded canonical Huffman workspace.

    Args:
        stream: Encoded bytes positioned at the first pack signature.
        max_output: Optional aggregate decoded byte allowance.
        max_memory: Optional codec workspace allowance, excluding retained decoded output.
        max_members: Optional number of member attempts, including malformed members.

    Returns:
        Validated concatenated output and each member's exact physical framing.

    Raises:
        DecodeError: If framing, integrity, supported variants, or a configured limit fails.
    """
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    while stream.tell() < len(stream):
        if max_members is not None and members >= max_members:
            raise DecodeError(
                f"UNIX pack member count exceeds {max_members}",
                status="limited",
                regions=tuple(regions),
                member_count=members,
            )
        members += 1
        try:
            regions.append(_member(stream, output, max_memory))
        except DecodeError as error:
            raise DecodeError(
                str(error),
                status=error.status,
                member_count=members,
                regions=tuple(regions) + error.regions,
            ) from error
    if not regions:
        raise DecodeError("empty input contains no UNIX pack member", member_count=0)
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser(PACK_MIME)
def parse_pack(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps UNIX pack members and recursively analyzes validated decoded content."""
    yield from parse_compressed(stream, parent, decode_pack)
