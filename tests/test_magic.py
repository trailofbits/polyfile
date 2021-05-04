from pathlib import Path
from unittest import TestCase

from polyfile.magic import MagicMatcher, MAGIC_DEFS


FILE_TEST_DIR: Path = Path(__file__).parent.parent / "file" / "tests"

class MagicTest(TestCase):
    def test_parsing(self):
        _ = MagicMatcher.parse(*MAGIC_DEFS)

    def test_file_corpus(self):
        self.assertTrue(FILE_TEST_DIR.exists(), "Make sure to run `git submodule init && git submodule update` in the "
                                                "root of this repository.")

        matcher = MagicMatcher.parse(*MAGIC_DEFS)

        tests = sorted([
            f.stem for f in FILE_TEST_DIR.glob("*.testfile")
        ])

        for test in tests:
            testfile = FILE_TEST_DIR / f"{test}.testfile"
            result = FILE_TEST_DIR / f"{test}.result"

            print(f"Testing: {test}")

            if not testfile.exists() or not result.exists():
                continue

            with open(testfile, "rb") as f:
                for match in matcher.match(f.read()):
                    print(match)
