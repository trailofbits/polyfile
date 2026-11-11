"""UNIX compress framing and recursive decoding through a supported GNU gzip."""

import re
import shutil
from collections.abc import Iterator
from functools import partial
from pathlib import Path

from polyfile.compression import DecodeError, DecodeResult, RawRegion, parse_compressed
from polyfile.external import run_helper
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, register_parser

COMPRESS_MAGIC = b"\x1f\x9d"
_GNU_VERSION = re.compile(rb"^gzip (\d+)\.(\d+)(?:\r?\n|$)")


def find_gnu_gzip(*, helper_timeout: float | None = None) -> str:
    """Finds GNU gzip 1.15 or newer among the supported installed executable names.

    Args:
        helper_timeout: Optional timeout for each fixed version-query invocation.

    Returns:
        The absolute path of a supported installed GNU gzip executable.

    Raises:
        DecodeError: If no supported helper is installed or a requested limit is exceeded.
    """
    for name in ("ggzip", "gzip"):
        found = shutil.which(name)
        if found is None:
            continue
        executable = str(Path(found).resolve())
        try:
            with FileStream(b"") as stream:
                version = run_helper(
                    stream,
                    (executable, "--version"),
                    max_output=8192,
                    helper_timeout=helper_timeout,
                )
        except DecodeError as error:
            if error.status == "limited":
                raise
            continue
        matched = _GNU_VERSION.search(version)
        if (
            matched is not None
            and b"Free Software Foundation, Inc." in version
            and tuple(map(int, matched.groups())) >= (1, 15)
        ):
            return executable
    raise DecodeError(
        "UNIX compress decoding requires GNU gzip 1.15 or newer; install ggzip or gzip on PATH",
        status="unsupported",
    )


def _framing(stream: FileStream) -> tuple[RawRegion, ...]:
    start = stream.tell()
    header = stream.read(3)
    fields = [RawRegion("magic", start, min(2, len(header)), header[:2])]
    if len(header) == 3:
        fields.append(RawRegion("flags", start + 2, 1, header[2]))
    region = RawRegion("compress_header", start, len(header), children=tuple(fields))
    if len(header) < 3:
        raise DecodeError("truncated UNIX compress header", regions=(region,))
    if header[:2] != COMPRESS_MAGIC:
        raise DecodeError("invalid UNIX compress signature", regions=(region,))
    _validate_flags(header[2], region)
    if len(stream) - stream.tell() == 1:
        raise DecodeError("truncated first UNIX compress code", regions=(region,))
    return region, RawRegion("lzw_data", stream.tell(), len(stream) - stream.tell())


def _validate_flags(flags: int, region: RawRegion) -> None:
    if flags & 0x60:
        raise DecodeError("reserved UNIX compress header bits are set", regions=(region,))
    width = flags & 0x1F
    if width < 9:
        raise DecodeError(f"invalid UNIX compress code width {width}", regions=(region,))
    if width == 9:
        raise DecodeError(
            "a 9-bit UNIX compress maximum is unsupported by the GNU gzip backend",
            status="unsupported",
            regions=(region,),
        )
    if width > 16:
        raise DecodeError(
            f"unsupported UNIX compress code width {width}",
            status="unsupported",
            regions=(region,),
        )


def decode_compress(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
    helper_timeout: float | None = None,
) -> DecodeResult:
    """Decodes one UNIX compress stream using an installed, version-qualified helper.

    Args:
        stream: Encoded UNIX compress stream, positioned at its header.
        max_output: Optional maximum decoded size.
        max_memory: Optional hard helper memory ceiling, supported on Linux.
        max_members: Optional allowance for this single compressed member.
        helper_timeout: Optional timeout in seconds for each helper invocation.

    Returns:
        Complete decoded bytes and their physical header/data regions.

    Raises:
        DecodeError: If framing, helper availability, integrity, or a configured limit fails.
    """
    start = stream.tell()
    regions = _framing(stream)
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "UNIX compress member exceeds the member allowance",
            status="limited",
            regions=regions,
        )
    try:
        executable = find_gnu_gzip(helper_timeout=helper_timeout)
        stream.seek(start)
        result = run_helper(
            stream,
            (executable, "-d", "-c"),
            max_output=max_output,
            max_memory=max_memory,
            helper_timeout=helper_timeout,
        )
    except DecodeError as error:
        raise DecodeError(str(error), status=error.status, regions=regions) from error
    return DecodeResult(result, regions)


@register_parser("application/x-compress")
def parse_compress(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps UNIX compress framing and recursively analyzes its decoded bytes."""
    decoder = partial(decode_compress, helper_timeout=parent.analysis_context.limits.helper_timeout)
    yield from parse_compressed(stream, parent, decoder)
