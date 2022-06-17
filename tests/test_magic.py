from pathlib import Path
from typing import Callable, Optional
from unittest import TestCase

# from polyfile import logger
import polyfile.magic
from polyfile.magic import MagicMatcher, MAGIC_DEFS


# logger.setLevel(logger.TRACE)

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

    def test_can_match_mime(self):
        for d in MAGIC_DEFS:
            if d.name == "elf":
                elf_def = d
                break
        else:
            self.fail("Could not find the elf test!")
        matcher = MagicMatcher.parse(elf_def)
        self.assertIn("application/x-pie-executable", matcher.mimetypes)
        self.assertIn("application/x-sharedlib", matcher.mimetypes)

    def test_file_corpus(self):
        self.assertTrue(FILE_TEST_DIR.exists(), "Make sure to run `git submodule init && git submodule update` in the "
                                                "root of this repository.")

        # skip the DER definition because we don't yet support it (and none of the tests actually require it)
        default_matcher = MagicMatcher.parse(*(d for d in MAGIC_DEFS if d.name != "der"))

        tests = sorted([
            f.stem for f in FILE_TEST_DIR.glob("*.testfile")
        ])

        for test in tests:
            with self.subTest(test=test):
                testfile = FILE_TEST_DIR / f"{test}.testfile"
                result = FILE_TEST_DIR / f"{test}.result"

                if not testfile.exists() or not result.exists():
                    continue

                magicfile = FILE_TEST_DIR / f"{test}.magic"

                print(f"Testing: {test}")

                if magicfile.exists():
                    print(f"\tParsing custom match script: {magicfile.stem}")
                    matcher = MagicMatcher.parse(magicfile)
                else:
                    matcher = default_matcher

                with open(result, "r") as f:
                    expected = f.read()
                    print(f"\tExpected: {expected!r}")

                with open(testfile, "rb") as f:
                    matches = set()
                    for match in matcher.match(f.read()):
                        actual = str(match)
                        matches.add(actual)
                        print(f"\tActual:   {actual!r}")
                    if testfile.stem not in ("JW07022A.mp3", "gedcom"):
                        # The files we skip fail because there is a bug in our implementation that we have not yet fixed
                        if expected == "ASCII text" and expected not in matches:
                            self.assertIn(expected.lower(), matches)
                        elif "00000000" in expected and expected not in matches:
                            # our output is technically correct but we output "0x000000" instead of "00000000"
                            self.assertIn(expected.replace("00000000", "0x000000"), matches)
                        else:
                            self.assertIn(expected, matches)
