"""SCO compress -H (LZH) framing, MIME dispatch, and recursive decoding."""

from collections.abc import Iterator
from functools import partial
from pathlib import Path

from polyfile.compression import DecodeError, DecodeResult, RawRegion, parse_compressed
from polyfile.external import run_helper
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.gziphelper import find_gnu_gzip
from polyfile.magic import MagicMatcher, TestType
from polyfile.polyfile import Match, register_parser

SCO_MAGIC = b"\x1f\xa0"
SCO_MIME = "application/x-sco-compress"

with ExactNamedTempfile(
    rb"""0 string \037\240 SCO compress -H (LZH) data
!:mime application/x-sco-compress
""",
    name="SCOCompressionMimeMatcher",
) as _definition:
    MagicMatcher.DEFAULT_INSTANCE.add(Path(_definition), test_type=TestType.BINARY)


def _framing(stream: FileStream) -> tuple[RawRegion, ...]:
    start = stream.tell()
    magic = stream.read(2)
    header = RawRegion("sco_lzh_header", start, len(magic), magic)
    if len(magic) < 2:
        raise DecodeError("truncated SCO LZH signature", regions=(header,))
    if magic != SCO_MAGIC:
        raise DecodeError("invalid SCO LZH signature", regions=(header,))
    body = RawRegion("lzh_data", stream.tell(), len(stream) - stream.tell())
    if body.length < 2:
        raise DecodeError("truncated SCO LZH block header", regions=(header, body))
    return header, body


def decode_sco(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
    helper_timeout: float | None = None,
) -> DecodeResult:
    """Decodes the SCO LZH stream through the supported installed GNU gzip helper.

    Args:
        stream: Encoded bytes positioned at their signature.
        max_output: Optional decoded byte allowance.
        max_memory: Optional Linux helper address-space ceiling.
        max_members: Optional allowance for this compressed member.
        helper_timeout: Optional positive timeout for each helper invocation.

    Returns:
        Decoded bytes and physical signature/body regions.

    Raises:
        DecodeError: If framing, helper availability, integrity, or a configured limit fails.
    """
    start = stream.tell()
    regions = _framing(stream)
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "SCO LZH member exceeds the member allowance", status="limited", regions=regions
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
    return DecodeResult(data, regions)


@register_parser(SCO_MIME)
def parse_sco(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps SCO LZH framing and recursively analyzes decoded content."""
    decoder = partial(decode_sco, helper_timeout=parent.analysis_context.limits.helper_timeout)
    yield from parse_compressed(stream, parent, decoder)
