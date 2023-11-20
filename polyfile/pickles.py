from typing import Optional

from fickling.analysis import Analyzer, Severity
from fickling.fickle import Pickled, PickleDecodeError

from .magic import AbsoluteOffset, DynamicMagicTest, FailedTest, MagicMatcher, MatchedTest, TestResult, TestType


class PickleMatcher(DynamicMagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-python-pickle",
            extensions=("pickle", "pkl"),
            default_message="Python Pickle Serialization"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        prev = -1
        for i, c in enumerate(data):
            if i >= 128:
                break
            elif prev == 0x80 and c in (2, 3, 4):
                try:
                    pickled = Pickled.load(data)
                    results = Analyzer.default_instance.analyze(pickled)
                    if results.severity <= Severity.LIKELY_SAFE:
                        message = self.message
                    else:
                        buffer_data = results.to_string(verbosity=Severity.LIKELY_UNSAFE)
                        if buffer_data:
                            buffer_data = f"\n{buffer_data}".replace("%", "%%")
                        message = f"Likely Unsafe {self.default_message}{buffer_data}"
                    return MatchedTest(self.bind(message), value=str(message), offset=0, length=len(data))
                except PickleDecodeError as e:
                    return FailedTest(self, offset=0, message=f"data was not decodable as a pickle file: {e!s}")
            prev = c
        return FailedTest(self, offset=0, message="data did not start with b\"\x80[\x02\x03\x04]\"")


DEFAULT_PICKLE_MATCHER = PickleMatcher()
MagicMatcher.DEFAULT_INSTANCE.add(DEFAULT_PICKLE_MATCHER)
