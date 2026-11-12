"""Search ranges bound candidate starts while comparisons keep their full context."""

import subprocess
import sys
from unittest import TestCase

from polyfile.magic import DataTypeMatch, StringMatch


class TestBoundedSearch(TestCase):
    def test_last_start_offset_and_flagged_boundary(self):
        for flags, last in ((False, 10), (True, 9)):
            test = StringMatch("TOKEN", case_insensitive_upper=True, num_bytes=10,
                               has_string_flags=flags)
            for offset in (0, last, last + 1):
                with self.subTest(flags=flags, offset=offset):
                    result = test.search(b"x" * offset + b"TOKEN" + b"x" * 140000)
                    self.assertEqual(bool(result), offset <= last)
                    if result:
                        self.assertEqual(result.initial_offset, offset)
                        self.assertEqual(result.raw_match, b"TOKEN")

    def test_whitespace_can_extend_past_start_range(self):
        test = StringMatch(r"A\ B", num_bytes=10, compact_whitespace=True,
                           case_insensitive_upper=True)
        token = b"A" + b" " * 20000 + b"B"
        result = test.search(b"x" * 10 + token + b"x" * 140000)
        self.assertEqual(result.initial_offset, 10)
        self.assertEqual(result.raw_match, token)
        self.assertIs(test.search(b"x" * 11 + token + b"x" * 140000), DataTypeMatch.INVALID)

    def test_word_terminator_sees_full_buffer(self):
        test = StringMatch(r"A\ B\ ", num_bytes=10, compact_whitespace=True,
                           full_word_match=True, case_insensitive_lower=True,
                           case_insensitive_upper=True)
        token = b"A B" + b" " * 20000
        self.assertIs(test.search(token + b"x" * 140000), DataTypeMatch.INVALID)
        self.assertEqual(token, test.search(token + b"\0" + b"x" * 140000).raw_match)

    def test_search_continues_after_a_rejected_full_word(self):
        for fold_case in (False, True):
            test = StringMatch("TOKEN", full_word_match=True,
                               case_insensitive_upper=fold_case)
            result = test.search(b"TOKENx TOKEN\0")
            self.assertEqual(7, result.initial_offset)
            self.assertEqual(b"TOKEN", result.raw_match)

    def test_each_case_flag_applies_to_the_declared_letters(self):
        lower = StringMatch("aB", case_insensitive_lower=True)
        upper = StringMatch("aB", case_insensitive_upper=True)
        self.assertTrue(lower.search(b"AB"))
        self.assertFalse(lower.search(b"Ab"))
        self.assertTrue(upper.search(b"ab"))
        self.assertFalse(upper.search(b"Ab"))

    def test_regular_expression_metacharacters_remain_literal(self):
        value = StringMatch(r"a.*[b]\\c+")
        self.assertEqual(b"a.*[b]\\c+", value.search(b"xxa.*[b]\\c+").raw_match)
        self.assertFalse(value.search(b"aZZbc"))

    def test_blank_runs_are_not_revisited_after_failure(self):
        code = r'''
from polyfile.magic import StringMatch
payload = b' ' * 262144 + b'x'
for compact in (False, True):
    test = StringMatch(r'\ \ A', compact_whitespace=compact, optional_blanks=not compact)
    assert not test.search(payload)
    test = StringMatch(r'\ ', compact_whitespace=compact, optional_blanks=not compact,
                       full_word_match=True)
    assert not test.search(payload)
'''
        subprocess.run([sys.executable, "-c", code], check=True, timeout=5)

    def test_whitespace_only_value_returns_the_whole_run(self):
        test = StringMatch(r"\ \ ", compact_whitespace=True)
        result = test.search(b"x" + b" " * 10000)
        self.assertEqual(1, result.initial_offset)
        self.assertEqual(b" " * 10000, result.raw_match)

    def test_empty_full_word_value_can_match_a_later_boundary(self):
        for options in ({}, {"optional_blanks": True}, {"compact_whitespace": True},
                        {"case_insensitive_lower": True}):
            with self.subTest(options=options):
                result = StringMatch("", full_word_match=True, **options).search(b"xx ")
                self.assertEqual(2, result.initial_offset)
                self.assertEqual(b"", result.raw_match)
