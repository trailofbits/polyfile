from io import StringIO
from typing import Any, Optional, Iterator

from fickling.analysis import check_safety
from fickling.pickle import Pickled, PickleDecodeError

from .magic import AbsoluteOffset, DynamicMagicTest, FailedTest, MagicMatcher, MagicTest, MatchedTest, Message, \
    TestResult, TestType, MatchContext


class MatchedPickle(MatchedTest):
    def __init__(
            self, test: MagicTest,
            pickled: Pickled,
            value: Any,
            offset: int,
            length: int,
            parent: Optional["TestResult"] = None,
    ):
        super().__init__(test=test, value=value, offset=offset, length=length, parent=parent)
        self.pickled: Pickled = pickled
        self._safety_log: Optional[str] = None
        self._is_likely_safe: Optional[bool] = None

    @property
    def safety_log(self) -> str:
        if self._safety_log is None:
            log_buffer = StringIO()
            self._is_likely_safe = check_safety(self.pickled, stdout=log_buffer, stderr=log_buffer)
            self._safety_log = str(log_buffer)
        return self._safety_log

    @property
    def is_likely_safe(self) -> bool:
        if self._is_likely_safe is None:
            _ = self.safety_log
            assert self._is_likely_safe is not None
        return self._is_likely_safe


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
                    log_buffer = StringIO()
                    if check_safety(pickled, stdout=log_buffer, stderr=log_buffer):
                        message = self.message
                    else:
                        log_buffer.seek(0)
                        buffer_data = log_buffer.read()
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
