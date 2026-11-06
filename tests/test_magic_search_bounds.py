import re
from unittest import TestCase

from polyfile.magic import DataTypeMatch, StringMatch


class TestBoundedSearch(TestCase):
    def test_last_start_offset_and_flagged_boundary(self):
        for flags, last in ((False, 10), (True, 9)):
            test = StringMatch("TOKEN", case_insensitive_upper=True, num_bytes=10, has_string_flags=flags)
            for offset in (0, last, last + 1):
                with self.subTest(flags=flags, offset=offset):
                    result = test.search(b"x" * offset + b"TOKEN" + b"x" * 140000)
                    self.assertEqual(bool(result), offset <= last)
                    if result:
                        self.assertEqual(result.initial_offset, offset)
                        self.assertEqual(result.raw_match, b"TOKEN")

    def test_whitespace_can_extend_past_start_range(self):
        test = StringMatch(r"A\ B", num_bytes=10, compact_whitespace=True)
        token = b"A" + b" " * 20000 + b"B"
        result = test.search(b"x" * 10 + token + b"x" * 140000)
        self.assertEqual(result.initial_offset, 10)
        self.assertEqual(result.raw_match, token)
        self.assertIs(test.search(b"x" * 11 + token + b"x" * 140000), DataTypeMatch.INVALID)

    def test_word_terminator_sees_full_buffer(self):
        test = StringMatch(r"A\ B\ ", num_bytes=10, compact_whitespace=True, full_word_match=True)
        token = b"A B" + b" " * 20000
        self.assertIs(test.search(token + b"x" * 140000), DataTypeMatch.INVALID)
        result = test.search(token + b"\0" + b"x" * 140000)
        self.assertEqual(result.raw_match, token)

    def test_replacement_pattern_keeps_lookbehind_context(self):
        test = StringMatch("TOKEN", case_insensitive_upper=True, num_bytes=10)
        test._pattern = re.compile(rb"(?<=prefix)TOKEN")
        result = test.search(b"prefixTOKEN" + b"x" * 140000)
        self.assertEqual(result.initial_offset, 6)
        self.assertEqual(result.raw_match, b"TOKEN")
