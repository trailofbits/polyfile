"""Behavior and resource bounds for the magic regular expression engine."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from polyfile.magic import MAGIC_DEFS, MagicMatcher, RegexType


class TestMagicRegexEngine(TestCase):
    def test_regex_uses_the_leftmost_longest_match(self):
        expression = RegexType.parse("regex")
        match = expression.match(b"xxab\n", expression.parse_expected("a|ab"))
        self.assertEqual(b"ab", match.raw_match)
        self.assertEqual(2, match.initial_offset)

    def test_regex_operates_on_bytes_and_keeps_ascii_case_rules(self):
        expression = RegexType.parse("regex/c")
        match = expression.match(b"\xffX\n", expression.parse_expected(r"\xffx"))
        self.assertEqual(b"\xffX", match.raw_match)
        self.assertFalse(expression.match(b"\xc9\n", expression.parse_expected(r"\xe9")))

    def test_unsupported_syntax_reports_the_definition_and_line(self):
        for pattern in (r"=(?=a)a", r"=(?<!x)a", r"=(a)\\1"):
            with self.subTest(pattern=pattern), TemporaryDirectory() as directory:
                path = Path(directory) / "unsupported.magic"
                path.write_text(f"# A custom definition\n0\tregex\t{pattern}\tfound\n")
                with self.assertRaisesRegex(ValueError, r"unsupported\.magic line 2:.*RE2"):
                    MagicMatcher.parse(path)

    def test_every_bundled_definition_loads(self):
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        self.assertTrue(list(matcher))
        self.assertTrue(matcher.named_tests)

    def test_nested_repetition_finishes_without_backtracking(self):
        code = """
from polyfile.magic import MagicRegex
expression = MagicRegex(b'^(a+)+$')
assert expression.search(b'a' * 8192 + b'!') is None
"""
        subprocess.run([sys.executable, "-c", code], check=True, timeout=5)

    def test_regex_anchors_and_negation_remain_available(self):
        expression = RegexType.parse("regex")
        self.assertEqual(b"beta", expression.match(
            b"alpha\nbeta\ngamma\n", expression.parse_expected("=^beta$")
        ).raw_match)
        self.assertTrue(expression.match(b"alpha\n", expression.parse_expected("!beta")))
        self.assertFalse(expression.match(b"beta\n", expression.parse_expected("!beta")))
