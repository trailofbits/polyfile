"""UNIX pack Huffman-tree framing, signature dispatch, and recursive decoding."""

from collections.abc import Iterator
from functools import partial
from pathlib import Path

from polyfile.compression import DecodeError, DecodeResult, RawRegion, parse_compressed
from polyfile.external import run_helper
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.gziphelper import find_gnu_gzip
from polyfile.magic import MagicMatcher, TestType
from polyfile.polyfile import Match, register_parser

PACK_MAGIC = b"\x1f\x1e"
OLD_PACK_MAGIC = b"\x1f\x1f"
PACK_MIME = "application/x-unix-pack"

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
            "old UNIX pack (1f 1f) is unsupported by GNU gzip", start, fields, status="unsupported"
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
            f"UNIX pack maximum code length {width} exceeds GNU gzip support",
            start,
            fields,
            status="unsupported",
        )
    return start, declared_size, width, fields


def _validate_tree(counts: bytes, start: int, fields: list[RawRegion]) -> None:
    available = 1
    for index, count in enumerate(counts):
        available = available * 2 - count - (2 if index == len(counts) - 1 else 0)
        if available < 0:
            raise _failure("oversubscribed UNIX pack Huffman tree", start, fields)
    if available:
        raise _failure("incomplete UNIX pack Huffman tree", start, fields)


def _framing(stream: FileStream) -> tuple[tuple[RawRegion, ...], int]:
    start, declared_size, width, fields = _header(stream)
    counts = stream.read(width)
    fields.append(RawRegion("leaves_per_length", start + 7, len(counts), counts))
    if len(counts) != width:
        raise _failure("truncated UNIX pack Huffman counts", start, fields)
    literals_count = sum(counts) + 1
    if literals_count > 256:
        raise _failure("UNIX pack Huffman tree has too many literals", start, fields)
    _validate_tree(counts, start, fields)
    offset = stream.tell()
    literals = stream.read(literals_count)
    fields.append(RawRegion("literals", offset, len(literals), literals))
    if len(literals) != literals_count:
        raise _failure("truncated UNIX pack Huffman literals", start, fields)
    body = RawRegion("huffman_data", stream.tell(), len(stream) - stream.tell())
    return (_region(start, fields), body), declared_size


def decode_pack(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
    helper_timeout: float | None = None,
) -> DecodeResult:
    """Decodes a modern UNIX pack stream through the supported GNU gzip helper.

    Args:
        stream: Encoded bytes positioned at the pack signature.
        max_output: Optional decoded byte allowance.
        max_memory: Optional Linux helper address-space ceiling.
        max_members: Optional allowance for this compressed member.
        helper_timeout: Optional positive timeout for each helper invocation.

    Returns:
        Decoded bytes with physical framing and tree regions.

    Raises:
        DecodeError: If framing, helper availability, integrity, or a configured limit fails.
    """
    start = stream.tell()
    regions, declared_size = _framing(stream)
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "UNIX pack member exceeds the member allowance", status="limited", regions=regions
        )
    if max_output is not None and declared_size > max_output:
        raise DecodeError(
            f"declared UNIX pack size {declared_size} exceeds the output allowance",
            status="limited",
            regions=regions,
        )
    try:
        executable = find_gnu_gzip(helper_timeout=helper_timeout)
        stream.seek(start)
        data = run_helper(
            stream,
            (executable, "-d", "-c"),
            max_output=max_output,
            max_memory=max_memory,
            helper_timeout=helper_timeout,
        )
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=regions) from error
    if len(data) != declared_size:
        raise DecodeError(
            "UNIX pack decoded length does not match its declared size", regions=regions
        )
    return DecodeResult(data, regions)


@register_parser(PACK_MIME)
def parse_pack(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps UNIX pack fields and recursively analyzes decoded content."""
    decoder = partial(decode_pack, helper_timeout=parent.analysis_context.limits.helper_timeout)
    yield from parse_compressed(stream, parent, decoder)
