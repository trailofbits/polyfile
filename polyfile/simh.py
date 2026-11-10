"""Identify and map SIMH tape records without assuming tape records are files."""

from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)

MIME_TYPE = "application/SIMH-tape-data"
END_OF_MEDIUM = 0xFFFFFFFF
LENGTH_MASK = 0x00FFFFFF


def _length(word: int) -> int:
    if word == END_OF_MEDIUM:
        return word
    if word & 0x0F000000:
        raise ValueError("SIMH record length uses reserved bits 24 through 27")
    length = word & LENGTH_MASK
    return length + (length & 1)


def _accepts(data: bytes) -> bool:
    """Apply the native libmagic probe, including its ten-tape-mark stopping point."""
    offset = records = marks = 0
    while offset + 4 <= len(data):
        word = int.from_bytes(data[offset : offset + 4], "little")
        offset += 4
        try:
            length = _length(word)
        except ValueError:
            return False
        if length == END_OF_MEDIUM:
            break
        if length == 0:
            marks += 1
            if marks == 10:
                break
            continue
        offset += length
        if offset + 4 > len(data):
            break
        try:
            trailer = _length(int.from_bytes(data[offset : offset + 4], "little"))
        except ValueError:
            return False
        offset += 4
        if length != trailer:
            return False
        records += 1
    return records > 0


class SIMHTest(MagicTest):
    """Recognize native SIMH record framing ahead of soft magic."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime=MIME_TYPE,
            extensions=("tap",),
            message="SIMH tape data",
        )

    @property
    def precedes_soft_magic(self) -> bool:
        return True

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        if _accepts(data[absolute_offset:]):
            return MatchedTest(
                self,
                value=None,
                offset=absolute_offset,
                length=len(data) - absolute_offset,
                parent=parent_match,
            )
        return FailedTest(
            self,
            offset=absolute_offset,
            parent=parent_match,
            message="no complete SIMH record sequence",
        )


MagicMatcher.DEFAULT_INSTANCE.add(SIMHTest())
