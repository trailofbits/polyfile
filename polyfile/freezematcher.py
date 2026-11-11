"""Disambiguation and recursive analysis of freeze 1.x and gzip 0.5 streams."""

from collections.abc import Iterator
from pathlib import Path

from polyfile.compression import (
    DecodeError,
    DecodeResult,
    OutputBuffer,
    RawRegion,
    parse_compressed,
)
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.freeze1 import FREEZE_MAGIC, FREEZE_MEMORY, decode_freeze1
from polyfile.gzipmatcher import GZIP_MAGIC, _member, _padding
from polyfile.magic import MagicMatcher, TestType
from polyfile.polyfile import Match, register_parser

FREEZE_MIME = "application/x-freeze"

with ExactNamedTempfile(
    rb"""0 string \037\236 frozen file 1.0 (or gzip 0.5)
!:mime application/x-freeze
""",
    name="FrozenCompressionMimeMatcher",
) as _definition:
    MagicMatcher.DEFAULT_INSTANCE.add(Path(_definition), test_type=TestType.BINARY)


class _LegacyGzipView(FileStream):
    def read(self, n: int | None = None) -> bytes:
        offset = self.tell()
        data = super().read(n)
        if offset < 2:
            replaced = min(len(data), 2 - offset)
            end = offset + replaced
            data = GZIP_MAGIC[offset:end] + data[replaced:]
        return data


def _physical_region(region: RawRegion, origin: int) -> RawRegion:
    return RawRegion(
        "gzip_0_5_member" if region.name == "gzip_member" else region.name,
        origin + region.offset,
        region.length,
        FREEZE_MAGIC if region.name == "magic" else region.value,
        tuple(_physical_region(child, origin) for child in region.children),
    )


def _legacy_member(stream: FileStream, output: OutputBuffer) -> RawRegion:
    start = stream.tell()
    with stream.save_pos():
        header = stream.read(4)
    if header[:2] != FREEZE_MAGIC:
        raise DecodeError(f"invalid gzip 0.5 signature at byte offset {start}")
    if len(header) == 4 and header[3] & 2:
        raise DecodeError(
            "gzip 0.5 multipart continuation is unsupported", status="unsupported"
        )
    view = _LegacyGzipView(stream, start=start)
    try:
        region = _member(view, output)
    except DecodeError as error:
        regions = tuple(_physical_region(item, start) for item in error.regions)
        raise DecodeError(str(error), status=error.status, regions=regions) from error
    stream.seek(start + view.tell())
    return _physical_region(region, start)


def _legacy_gzip(
    stream: FileStream, max_output: int | None, max_members: int | None
) -> DecodeResult:
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    while stream.tell() < len(stream):
        with stream.save_pos():
            magic = stream.read(2)
        try:
            if regions and magic.startswith(b"\0"):
                regions.append(_padding(stream))
            else:
                if max_members is not None and members >= max_members:
                    raise DecodeError(
                        "gzip 0.5 member allowance exhausted", status="limited"
                    )
                members += 1
                regions.append(_legacy_member(stream, output))
        except DecodeError as error:
            raise DecodeError(
                str(error),
                status=error.status,
                regions=tuple(regions) + error.regions,
                member_count=members,
            ) from error
    return DecodeResult(output.finish(), tuple(regions), members)


def _disambiguate(
    stream: FileStream, max_output: int | None, max_members: int | None
) -> DecodeResult:
    start = stream.tell()
    try:
        return _legacy_gzip(stream, max_output, max_members)
    except DecodeError as error:
        if error.status == "limited":
            raise
        gzip_error = error
        stream.seek(start)
    try:
        result = decode_freeze1(stream, max_output=max_output)
    except DecodeError as error:
        status = "unsupported" if gzip_error.status == "unsupported" else error.status
        raise DecodeError(
            f"neither gzip 0.5 ({gzip_error}) nor freeze 1.x ({error}) validates",
            status=status,
            regions=(
                RawRegion(
                    "gzip_0_5_candidate",
                    start,
                    len(stream) - start,
                    str(gzip_error),
                    gzip_error.regions,
                ),
                RawRegion(
                    "freeze_1_candidate",
                    start,
                    len(stream) - start,
                    str(error),
                    error.regions,
                ),
            ),
            member_count=max(gzip_error.member_count, error.member_count),
        ) from error
    return DecodeResult(
        result.data, result.regions, max(result.member_count, gzip_error.member_count)
    )


def decode_frozen(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Validates gzip 0.5 framing before trying the shared-signature freeze 1.x format.

    Args:
        stream: Encoded bytes positioned at their shared signature.
        max_output: Optional decoded byte allowance.
        max_memory: Optional codec-state allowance; either variant needs 64 KiB.
        max_members: Optional compressed-member allowance.

    Returns:
        Complete validated bytes with physical framing regions.

    Raises:
        DecodeError: If both formats fail validation, or a configured limit is reached.
    """
    if max_memory is not None and max_memory < FREEZE_MEMORY:
        raise DecodeError(
            "freeze/gzip requires 64 KiB codec memory", status="limited", member_count=0
        )
    if max_members is not None and max_members < 1:
        raise DecodeError(
            "freeze/gzip member allowance exhausted", status="limited", member_count=0
        )
    with stream.save_pos():
        header = stream.read(3)
    if header[:2] != FREEZE_MAGIC:
        raise DecodeError("invalid or truncated freeze/gzip 0.5 signature")
    if header[2:] == b"\x08":
        return _disambiguate(stream, max_output, max_members)
    return decode_freeze1(stream, max_output=max_output)


@register_parser(FREEZE_MIME)
def parse_frozen(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps either shared-signature format and analyzes its validated decoded content."""
    yield from parse_compressed(stream, parent, decode_frozen)
