import re
from unittest import TestCase

from polyfile.magic import DataTypeMatch, StringMatch


class SearchForbidden:
    """Wraps a compiled pattern and fails if `StringMatch.search` scans the whole buffer.

    The bounded path calls `match` at each permitted start and never `search`, so a test that
    installs this wrapper fails unless it reaches that path.
    """

    def __init__(self, pattern: re.Pattern):
        self.wrapped = pattern
        self.pattern = pattern.pattern
        self.flags = pattern.flags

    def match(self, *args):
        return self.wrapped.match(*args)

    def search(self, *args):
        raise AssertionError("searched the whole buffer instead of only the permitted starts")


def bounded(test: StringMatch) -> StringMatch:
    test._pattern = SearchForbidden(test.pattern)
    return test


class TestBoundedSearch(TestCase):
    def test_last_start_offset_and_flagged_boundary(self):
        # `C` turns each letter into a character class, so the pattern starts with one.
        for flags, last in ((False, 10), (True, 9)):
            test = bounded(StringMatch("TOKEN", case_insensitive_upper=True, num_bytes=10, has_string_flags=flags))
            for offset in (0, last, last + 1):
                with self.subTest(flags=flags, offset=offset):
                    result = test.search(b"x" * offset + b"TOKEN" + b"x" * 140000)
                    self.assertEqual(bool(result), offset <= last)
                    if result:
                        self.assertEqual(result.initial_offset, offset)
                        self.assertEqual(result.raw_match, b"TOKEN")

    def test_whitespace_can_extend_past_start_range(self):
        test = bounded(StringMatch(r"A\ B", num_bytes=10, compact_whitespace=True, case_insensitive_upper=True))
        token = b"A" + b" " * 20000 + b"B"
        result = test.search(b"x" * 10 + token + b"x" * 140000)
        self.assertEqual(result.initial_offset, 10)
        self.assertEqual(result.raw_match, token)
        self.assertIs(test.search(b"x" * 11 + token + b"x" * 140000), DataTypeMatch.INVALID)

    def test_word_terminator_sees_full_buffer(self):
        # `c` and `C` together compile with re.IGNORECASE, the path's other trigger.
        test = bounded(StringMatch(r"A\ B\ ", num_bytes=10, compact_whitespace=True, full_word_match=True,
                                   case_insensitive_lower=True, case_insensitive_upper=True))
        self.assertTrue(test.pattern.flags & re.IGNORECASE)
        token = b"A B" + b" " * 20000
        self.assertIs(test.search(token + b"x" * 140000), DataTypeMatch.INVALID)
        result = test.search(token + b"\0" + b"x" * 140000)
        self.assertEqual(result.raw_match, token)

    def test_replacement_pattern_keeps_lookbehind_context(self):
        test = StringMatch("TOKEN", case_insensitive_upper=True, num_bytes=10)
        test._pattern = SearchForbidden(re.compile(rb"(?<=prefix)TOKEN", re.IGNORECASE))
        result = test.search(b"prefixTOKEN" + b"x" * 140000)
        self.assertEqual(result.initial_offset, 6)
        self.assertEqual(result.raw_match, b"TOKEN")

    def test_unbounded_shapes_keep_the_native_search(self):
        # A literal prefix gains nothing from the bounded path, so it must still use `search`.
        test = bounded(StringMatch("TOKEN", num_bytes=10))
        with self.assertRaises(AssertionError):
            test.search(b"x" * 140000)
