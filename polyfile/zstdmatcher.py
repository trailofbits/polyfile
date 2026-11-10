"""Validated recursive decoding of modern Zstandard frames."""

import importlib
import struct
import sys
from collections.abc import Iterator
from types import ModuleType

from polyfile.compression import (
    CHUNK_SIZE,
    DecodeError,
    DecodeResult,
    OutputBuffer,
    RawRegion,
    parse_compressed,
)
from polyfile.fileutils import FileStream
from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)
from polyfile.polyfile import Match, register_parser

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
SKIPPABLE_BASE = 0x184D2A50
LEGACY_MAGICS = frozenset(
    bytes([version]) + ZSTD_MAGIC[1:] for version in range(0x22, 0x28)
)
ZSTD_SIGNATURES = frozenset(
    int.from_bytes(magic, "little") for magic in LEGACY_MAGICS | {ZSTD_MAGIC}
)


class SkippableZstdMatcher(MagicTest):
    """Recognizes Zstandard streams that begin with complete skippable frames."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/zstd",
            extensions=("zst",),
            message="Zstandard compressed data with skippable frames",
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        offset = 0
        while offset + 8 <= len(data):
            signature = struct.unpack_from("<I", data, offset)[0]
            if signature & 0xFFFFFFF0 != SKIPPABLE_BASE:
                break
            size = struct.unpack_from("<I", data, offset + 4)[0]
            if size > len(data) - offset - 8:
                return FailedTest(
                    self, offset=absolute_offset, message="truncated skippable frame"
                )
            offset += size + 8
        if (
            offset
            and len(data) - offset >= 4
            and struct.unpack_from("<I", data, offset)[0] in ZSTD_SIGNATURES
        ):
            return MatchedTest(
                self, value=data, offset=absolute_offset, length=len(data)
            )
        return FailedTest(
            self, offset=absolute_offset, message="no Zstandard frame follows metadata"
        )


MagicMatcher.DEFAULT_INSTANCE.add(SkippableZstdMatcher())


def _backend() -> ModuleType:
    module = "compression.zstd" if sys.version_info >= (3, 14) else "backports.zstd"
    try:
        return importlib.import_module(module)
    except ImportError as error:
        raise DecodeError(
            f"Zstandard decoder {module} is unavailable; reinstall PolyFile's dependencies",
            status="unsupported",
            member_count=0,
        ) from error


def _skippable(stream: FileStream) -> RawRegion:
    start = stream.tell()
    header = stream.read(8)
    if len(header) != 8:
        raise DecodeError(f"truncated Zstandard skippable header at offset {start}")
    size = int.from_bytes(header[4:], "little")
    if size > len(stream) - stream.tell():
        raise DecodeError(f"truncated Zstandard skippable payload at offset {start}")
    stream.seek(stream.tell() + size)
    return RawRegion("skippable_frame", start, size + 8)


def _frame_header(stream: FileStream, backend: ModuleType) -> tuple[int, int | None]:
    start = stream.tell()
    with stream.save_pos():
        header = stream.read(18)
    try:
        info = backend.get_frame_info(header)
    except backend.ZstdError as error:
        raise DecodeError(
            f"invalid Zstandard frame header at offset {start}: {error}"
        ) from error
    if info.dictionary_id:
        raise DecodeError(
            f"Zstandard frame at offset {start} requires dictionary {info.dictionary_id}",
            status="unsupported",
        )
    if header[4] & 0x20:
        return info.decompressed_size, info.decompressed_size
    descriptor = header[5]
    base = 1 << (10 + (descriptor >> 3))
    return base + (base >> 3) * (descriptor & 7), info.decompressed_size


def _decompressor(backend: ModuleType, window: int, max_memory: int | None):
    if max_memory is not None and window > max_memory:
        raise DecodeError(
            f"Zstandard frame requires a {window}-byte window, exceeding "
            f"--max-codec-memory={max_memory}",
            status="limited",
        )
    parameter = backend.DecompressionParameter.window_log_max
    lower, upper = parameter.bounds()
    if window > 1 << upper:
        raise DecodeError(
            "Zstandard frame window exceeds this runtime's supported range",
            status="unsupported",
        )
    bound = (
        upper
        if max_memory is None
        else max(lower, min(upper, (max_memory - 1).bit_length()))
    )
    return backend.ZstdDecompressor(options={parameter: bound})


def _frame(
    stream: FileStream,
    output: OutputBuffer,
    backend: ModuleType,
    max_memory: int | None,
) -> RawRegion:
    start = stream.tell()
    window, size = _frame_header(stream, backend)
    if size is not None and output.remaining is not None and size > output.remaining:
        raise DecodeError(
            "Zstandard decoded size exceeds the remaining output allowance",
            status="limited",
        )
    decoder = _decompressor(backend, window, max_memory)
    while not decoder.eof:
        chunk = stream.read(CHUNK_SIZE) if decoder.needs_input else b""
        if decoder.needs_input and not chunk:
            raise DecodeError(f"truncated Zstandard frame at offset {start}")
        try:
            data = decoder.decompress(chunk, output.next_size)
        except backend.ZstdError as error:
            raise DecodeError(
                f"invalid Zstandard frame at offset {start}: {error}"
            ) from error
        output.append(data)
    end = stream.tell() - len(decoder.unused_data)
    stream.seek(end)
    return RawRegion("zstandard_frame", start, end - start)


def _next_region(
    stream: FileStream,
    output: OutputBuffer,
    backend: ModuleType,
    max_memory: int | None,
) -> RawRegion:
    with stream.save_pos():
        magic = stream.read(4)
    signature = int.from_bytes(magic, "little")
    if len(magic) == 4 and signature & 0xFFFFFFF0 == SKIPPABLE_BASE:
        return _skippable(stream)
    if magic == ZSTD_MAGIC:
        return _frame(stream, output, backend, max_memory)
    if magic in LEGACY_MAGICS:
        raise DecodeError(
            "legacy Zstandard frames are unsupported", status="unsupported"
        )
    raise DecodeError(f"invalid Zstandard frame signature at offset {stream.tell()}")


def decode_zstd(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decodes complete modern Zstandard frames and skips metadata frames.

    Args:
        stream: The encoded input.
        max_output: Optional concatenated-output allowance.
        max_memory: Optional maximum declared decoder window, in bytes.
        max_members: Optional number of regular and skippable frames.

    Returns:
        Validated concatenated output with physical frame extents.

    Raises:
        DecodeError: If input is invalid, unsupported, or exceeds a configured limit.
    """
    backend = _backend()
    output = OutputBuffer(max_output)
    regions: list[RawRegion] = []
    members = 0
    while stream.tell() < len(stream):
        try:
            if max_members is not None and members >= max_members:
                raise DecodeError(
                    f"Zstandard frame count exceeds {max_members}", status="limited"
                )
            members += 1
            regions.append(_next_region(stream, output, backend, max_memory))
        except DecodeError as error:
            raise DecodeError(
                str(error),
                status=error.status,
                regions=tuple(regions) + error.regions,
                member_count=members,
            ) from error
    if not regions:
        raise DecodeError("empty input contains no Zstandard frame", member_count=0)
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser("application/zstd")
def parse_zstd(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps Zstandard frames and recursively analyzes validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_zstd)
