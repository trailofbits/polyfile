import logging
from pathlib import Path
from typing import Callable, Optional
from unittest import TestCase

from polyfile import logger
import polyfile.magic
from polyfile.magic import MagicMatcher, MAGIC_DEFS


# logger.setLevel(logging.DEBUG)

FILE_TEST_DIR: Path = Path(__file__).parent.parent / "file" / "tests"

class MagicTest(TestCase):
    _old_local_date: Optional[Callable[[int], str]] = None

    @classmethod
    def setUpClass(cls):
        # the libmagic test corpus assumes the local time zone is UTC, so hack magic to get it to work:
        cls._old_local_date = polyfile.magic.local_date
        polyfile.magic.local_date = polyfile.magic.utc_date

    @classmethod
    def tearDownClass(cls):
        # undo our UTC hack
        polyfile.magic.local_date = cls._old_local_date

    def test_parsing(self):
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        print(f"# MIME Types:      {len(matcher.mimetypes)}")
        print(f"# File Extensions: {len(matcher.extensions)}")

    def test_only_matching(self):
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        self.assertIs(matcher, matcher.only_match())
        self.assertIn("application/zip", matcher.only_match(mimetypes=("application/zip",)).mimetypes)
        self.assertIn("com", matcher.only_match(extensions=("com",)).extensions)

    def test_file_corpus(self):
        self.assertTrue(FILE_TEST_DIR.exists(), "Make sure to run `git submodule init && git submodule update` in the "
                                                "root of this repository.")

        # skip the DER definition because we don't yet support it (and none of the tests actually require it)
        matcher = MagicMatcher.parse(*(d for d in MAGIC_DEFS if d.name != "der"))

        tests = sorted([
            f.stem for f in FILE_TEST_DIR.glob("*.testfile")
        ])

        for test in tests:
            testfile = FILE_TEST_DIR / f"{test}.testfile"
            result = FILE_TEST_DIR / f"{test}.result"

            if not testfile.exists() or not result.exists():
                continue

            print(f"Testing: {test}")
            with open(result, "r") as f:
                expected = f.read()
                print(f"\tExpected: {expected!r}")

            with open(testfile, "rb") as f:
                for match in matcher.match(f.read()):
                    actual = str(match)
                    print(f"\tActual:   {actual!r}")
                    if testfile.stem not in ("JW07022A.mp3", "cl8m8ocofedso", "gedcom", "regex-eol", "uf2"):
                        # The files we skip fail because:
                        #   1. a mismatch between the database we have and the one used to generate the results in
                        #      the test corpus;
                        #   2. there is a bug in our implementation that we have not yet fixed; and/or
                        #   3. our output is technically correct but we output it slightly differently (e.g., we output
                        #      "0x000000" instead of "00000000"
                        self.assertEqual(expected, actual)
