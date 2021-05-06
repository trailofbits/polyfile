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
                    # self.assertEqual(expected, actual)
