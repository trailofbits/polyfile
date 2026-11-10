"""Recursive decoding of modern LZ4 frames with optional resource controls."""

import importlib
import struct
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

LZ4_MAGIC = b"\x04\x22\x4d\x18"
LEGACY_MAGICS = frozenset((b"\x02\x21\x4c\x18", b"\x03\x21\x4c\x18"))
SKIPPABLE_BASE = 0x184D2A50
FRAME_SIGNATURES = frozenset(
    int.from_bytes(magic, "little") for magic in LEGACY_MAGICS | {LZ4_MAGIC}
)


class SkippableLz4Matcher(MagicTest):
    """Recognizes LZ4 streams that begin with complete skippable frames."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-lz4",
            extensions=("lz4",),
            message="LZ4 compressed data with skippable frames",
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        offset = 0
        while offset + 8 <= len(data):
            signature, size = struct.unpack_from("<II", data, offset)
            if signature & 0xFFFFFFF0 != SKIPPABLE_BASE:
                break
            if size > len(data) - offset - 8:
                return FailedTest(
                    self, offset=absolute_offset, message="truncated skippable frame"
                )
            offset += size + 8
        if (
            offset
            and len(data) - offset >= 4
            and struct.unpack_from("<I", data, offset)[0] in FRAME_SIGNATURES
        ):
            return MatchedTest(
                self, value=data, offset=absolute_offset, length=len(data)
            )
        return FailedTest(
            self, offset=absolute_offset, message="no LZ4 frame follows metadata"
        )


MagicMatcher.DEFAULT_INSTANCE.add(SkippableLz4Matcher())


def _backend() -> ModuleType:
    try:
        return importlib.import_module("lz4.frame")
    except ImportError as error:
        raise DecodeError(
            "LZ4 decoder is unavailable; reinstall the required lz4 dependency",
            status="unsupported",
            member_count=0,
        ) from error


def _skippable(stream: FileStream) -> RawRegion:
    start = stream.tell()
    header = stream.read(8)
    if len(header) != 8:
        raise DecodeError(f"truncated LZ4 skippable header at offset {start}")
    size = int.from_bytes(header[4:], "little")
    if size > len(stream) - stream.tell():
        raise DecodeError(f"truncated LZ4 skippable payload at offset {start}")
    stream.seek(stream.tell() + size)
    return RawRegion("skippable_frame", start, size + 8)


def _frame_info(stream: FileStream, backend: ModuleType) -> tuple[dict, bytes]:
    with stream.save_pos():
        header = stream.read(19)
    try:
        info = backend.get_frame_info(header)
    except RuntimeError as error:
        raise DecodeError(
            f"invalid LZ4 frame header at offset {stream.tell()}: {error}"
        ) from error
    if header[4] & 1:
        offset = 6 + (8 if header[4] & 8 else 0)
        dictionary = struct.unpack_from("<I", header, offset)[0]
        if dictionary:
            raise DecodeError(
                f"LZ4 frame requires external dictionary {dictionary}",
                status="unsupported",
            )
    return info, header


def _codec_memory(info: dict) -> int:
    """Returns a conservative allowance for LZ4's native buffers and frame context.

    Args:
        info: Validated frame information returned by lz4.frame.get_frame_info.

    Returns:
        Two maximum blocks, optional linked-block history, and 4 KiB of context allowance.
    """
    return 2 * info["block_size"] + (128 * 1024 if info["block_linked"] else 0) + 4096


def _frame(
    stream: FileStream,
    output: OutputBuffer,
    backend: ModuleType,
    max_memory: int | None,
) -> RawRegion:
    start = stream.tell()
    info, header = _frame_info(stream, backend)
    memory = _codec_memory(info)
    if max_memory is not None and memory > max_memory:
        raise DecodeError(
            f"LZ4 frame needs a {memory}-byte codec allowance, exceeding "
            f"--max-codec-memory={max_memory}",
            status="limited",
        )
    if (
        header[4] & 8
        and output.remaining is not None
        and info["content_size"] > output.remaining
    ):
        raise DecodeError(
            "LZ4 decoded size exceeds the remaining output allowance", status="limited"
        )
    decoder = backend.LZ4FrameDecompressor()
    while not decoder.eof:
        chunk = stream.read(CHUNK_SIZE) if decoder.needs_input else b""
        if decoder.needs_input and not chunk:
            raise DecodeError(f"truncated LZ4 frame at offset {start}")
        try:
            data = decoder.decompress(chunk, output.next_size)
        except RuntimeError as error:
            raise DecodeError(
                f"invalid LZ4 frame at offset {start}: {error}"
            ) from error
        output.append(data)
    end = stream.tell() - len(decoder.unused_data or b"")
    stream.seek(end)
    return RawRegion("lz4_frame", start, end - start)


def _next_region(
    stream: FileStream,
    output: OutputBuffer,
    backend: ModuleType,
    max_memory: int | None,
) -> RawRegion:
    with stream.save_pos():
        magic = stream.read(4)
    if (
        len(magic) == 4
        and int.from_bytes(magic, "little") & 0xFFFFFFF0 == SKIPPABLE_BASE
    ):
        return _skippable(stream)
    if magic == LZ4_MAGIC:
        return _frame(stream, output, backend, max_memory)
    if magic in LEGACY_MAGICS:
        raise DecodeError("legacy LZ4 frames are unsupported", status="unsupported")
    raise DecodeError(f"invalid LZ4 frame signature at offset {stream.tell()}")


def decode_lz4(
    stream: FileStream,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    """Decodes complete modern LZ4 frames and skips metadata frames.

    Args:
        stream: The encoded input.
        max_output: Optional concatenated-output allowance.
        max_memory: Optional native codec-buffer allowance, in bytes.
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
                    f"LZ4 frame count exceeds {max_members}", status="limited"
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
        raise DecodeError("empty input contains no LZ4 frame", member_count=0)
    return DecodeResult(output.finish(), tuple(regions), members)


@register_parser("application/x-lz4")
def parse_lz4(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Maps LZ4 frames and recursively analyzes validated decoded bytes."""
    yield from parse_compressed(stream, parent, decode_lz4)
