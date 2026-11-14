"""Identify PDF signatures without importing the structural parser or PDFminer."""

from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)


class RelaxedPDFMatcher(MagicTest):
    """Recognize PDF headers after preambles that the libmagic rules exclude."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/pdf",
            extensions=("pdf",),
            message="Malformed PDF",
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None,
    ) -> TestResult:
        if b"%PDF-" in data:
            return MatchedTest(self, value=data, offset=0, length=len(data))
        return FailedTest(self, offset=0, message='data did not contain "%PDF-"')


MagicMatcher.DEFAULT_INSTANCE.add(RelaxedPDFMatcher())
