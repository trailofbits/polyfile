"""Identify ICO directories whose first image does not satisfy libmagic's offset heuristic."""

import struct

from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)


def _png_header(data: bytes, start: int, length: int, dimensions: tuple[int, int]) -> bool:
    if length < 33:
        return False
    end = start + 24
    header = data[start:end]
    return (
        header[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        and struct.unpack(">II", header[16:24]) == dimensions
    )


def _dib_header(data: bytes, start: int, length: int, dimensions: tuple[int, int]) -> bool:
    if length < 40:
        return False
    end = start + 16
    size, width, height, planes, bpp = struct.unpack("<IiiHH", data[start:end])
    return (
        size in (40, 52, 56, 108, 124)
        and size <= length
        and (width, height) == (dimensions[0], dimensions[1] * 2)
        and planes == 1
        and bpp in (1, 4, 8, 16, 24, 32)
    )


def _image_entry(data: bytes, entry: int, directory_end: int) -> bool:
    end = entry + 16
    width, height, _, reserved, _, _, length, start = struct.unpack("<BBBBHHII", data[entry:end])
    if reserved != 0 or length == 0 or start < directory_end or start + length > len(data):
        return False
    dimensions = (width or 256, height or 256)
    return _png_header(data, start, length, dimensions) or _dib_header(
        data, start, length, dimensions
    )


class IcoMatcher(MagicTest):
    """Recognize validated ICO directories outside the bundled first-image offset heuristic."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="image/vnd.microsoft.icon",
            extensions=("ico",),
            message="MS Windows icon resource",
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        """Identify an ICO after checking every directory entry and its bounded image header.

        Args:
            data: Input file bytes.
            absolute_offset: Offset resolved by the magic matcher.
            parent_match: Result of a containing magic test, if any.

        Returns:
            An ICO classification, or a failed test with the rejected condition.
        """
        failure = "ICO header or image directory is invalid"
        if len(data) < 22 or data[:4] != b"\x00\x00\x01\x00":
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message=failure)
        count = int.from_bytes(data[4:6], "little")
        directory_end = 6 + count * 16
        if count == 0 or directory_end > len(data):
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message=failure)
        if int.from_bytes(data[18:22], "little") & 6 == 6:
            return FailedTest(
                self,
                offset=absolute_offset,
                parent=parent_match,
                message="first image offset is covered by the bundled ICO rule",
            )
        for entry in range(6, directory_end, 16):
            if not _image_entry(data, entry, directory_end):
                return FailedTest(
                    self, offset=absolute_offset, parent=parent_match, message=failure
                )
        return MatchedTest(self, value=data, offset=0, length=len(data), parent=parent_match)


MagicMatcher.DEFAULT_INSTANCE.add(IcoMatcher())
