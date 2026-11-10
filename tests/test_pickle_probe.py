"""Malformed pickle probes must not emit warnings during arbitrary-byte analysis."""

from polyfile.magic import FailedTest
from polyfile.pickles import DEFAULT_PICKLE_MATCHER


def test_invalid_pickle_escape_is_rejected_without_a_warning() -> None:
    data = b"P\\\xd1\n.\x80\x04"
    result = DEFAULT_PICKLE_MATCHER.test(data, 0, None)
    assert isinstance(result, FailedTest)
    assert "invalid escape sequence" in result.message
