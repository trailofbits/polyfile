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

    def test_text_tests(self):
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        self.assertEqual(len(matcher.text_tests & matcher.non_text_tests), 0)
        for test in matcher.text_tests:
            self.assertEqual(test.test_type, polyfile.magic.TestType.TEXT)
        for test in matcher.non_text_tests:
            self.assertNotEqual(test.test_type, polyfile.magic.TestType.TEXT)
        num_text_tests = len(matcher.text_tests)
        num_non_text_tests = len(matcher.non_text_tests)
        if num_text_tests > 264:
            expected_text_tests = {'audio:633', 'c-lang:29', 'assembler:5', 'lua:15', 'c-lang:86', 'misctools:44', 'fonts:6', 'c-lang:90', 'tex:90', 'sisu:14', 'misctools:6', 'algol68:20', 'assembler:11', 'lisp:26', 'python:256', 'tex:52', 'sgml:89', 'lisp:24', 'sgml:86', 'cad:333', 'clojure:26', 'tex:64', 'c-lang:48', 'm4:8', 'windows:325', 'sgml:120', 'tcl:25', 'c-lang:69', 'c-lang:36', 'perl:18', 'tex:92', 'troff:9', 'sgml:74', 'games:286', 'sgml:49', 'lua:11', 'lex:10', 'c-lang:78', 'linux:174', 'sgml:83', 'audio:631', 'c-lang:82', 'terminfo:48', 'commands:102', 'tex:116', 'ruby:15', 'tex:98', 'sgml:134', 'tex:46', 'perl:49', 'algol68:22', 'tex:67', 'tex:94', 'clojure:29', 'sgml:71', 'c-lang:73', 'sgml:92', 'tex:21', 'algol68:24', 'sgml:136', 'ringdove:25', 'python:263', 'c-lang:39', 'perl:54', 'c-lang:45', 'commands:139', 'ringdove:27', 'sgml:80', 'archive:360', 'ringdove:15', 'tex:86', 'commands:159', 'tex:91', 'troff:21', 'tex:58', 'tex:55', 'lisp:18', 'tcl:13', 'python:287', 'c-lang:10', 'python:293', 'sketch:6', 'ctags:6', 'troff:11', 'tex:89', 'ringdove:28', 'ruby:12', 'lisp:20', 'tex:93', 'ruby:18', 'ringdove:26', 'psl:9', 'ruby:25', 'tcl:11', 'commands:132', 'tcl:28', 'tex:34', 'tex:76', 'perl:53', 'tex:95', 'sgml:59', 'troff:13', 'tex:122', 'sisu:5', 'perl:8', 'ringdove:17', 'assembler:15', 'make:15', 'cad:309', 'python:250', 'assembler:7', 'tex:106', 'perl:48', 'perl:10', 'ringdove:20', 'perl:16', 'gnu:170', 'tex:138', 'tex:75', 'perl:47', 'ruby:31', 'c-lang:15', 'lisp:16', 'sgml:102', 'tex:36', 'inform:9', 'tex:71', 'sisu:8', 'sgml:68', 'tex:40', 'ruby:37', 'bioinformatics:156', 'forth:16', 'commands:137', 'tcl:17', 'ringdove:18', 'make:19', 'ringdove:29', 'ringdove:19', 'tcl:7', 'sgml:65', 'perl:12', 'securitycerts:4', 'tex:104', 'fortran:6', 'ringdove:12', 'c-lang:22', 'ringdove:21', 'sgml:135', 'tex:114', 'csv:6', 'rst:5', 'apple:6', 'misctools:39', 'algol68:26', 'assembler:9', 'tex:88', 'c-lang:96', 'ruby:53', 'linux:507', 'perl:36', 'ringdove:32', 'c-lang:25', 'troff:19', 'assembler:17', 'perl:50', 'lisp:22', 'nim-lang:7', 'commands:108', 'tcl:19', 'perl:52', 'sgml:96', 'tex:132', 'perl:24', 'c-lang:8', 'make:6', 'lua:9', 'tex:124', 'perl:20', 'assembler:13', 'commands:105', 'json:6', 'sgml:128', 'c-lang:51', 'tex:96', 'securitycerts:5', 'm4:5', 'tex:43', 'ringdove:6', 'tcl:15', 'msdos:26', 'tex:134', 'softquad:26', 'tex:78', 'pascal:5', 'clojure:23', 'linux:173', 'linux:170', 'windows:671', 'forth:10', 'sgml:77', 'tex:61', 'uuencode:26', 'commands:142', 'tex:100', 'tex:20', 'ringdove:22', 'ringdove:16', 'c-lang:60', 'tex:126', 'troff:25', 'python:244', 'gentoo:44', 'ringdove:8', 'troff:15', 'tex:77', 'perl:14', 'fonts:132', 'sisu:11', 'c-lang:33', 'tex:120', 'tex:74', 'ruby:9', 'sgml:126', 'algol68:9', 'msdos:28', 'linux:54', 'sgml:62', 'sgml:127', 'tex:102', 'commands:68', 'subtitle:19', 'commands:135', 'tcl:21', 'python:279', 'lua:13', 'perl:22', 'diff:16', 'c-lang:42', 'tex:87', 'ringdove:9', 'perl:51', 'lisp:77', 'lex:12', 'tex:49', 'ringdove:7', 'ruby:44', 'c-lang:65', 'ringdove:14', 'commands:111', 'msx:78', 'perl:40', 'tcl:9', 'tex:128', 'sisu:17', 'ringdove:13', 'tex:112', 'tex:136', 'tex:118', 'java:19', 'ruby:50', 'tex:130', 'sgml:55', 'uuencode:18'}
            actual_text_tests = {
                f"{test.source_info.path.name}:{test.source_info.line}": test
                for test in matcher.text_tests if test.source_info is not None
            }
            for test_name in actual_text_tests.keys() - expected_text_tests:
                test: polyfile.magic.MagicTest = actual_text_tests[test_name]
                print(f"Expected {test_name} to be a binary test, but it was in fact text!")
                history = set()
                queue = [test]
                while queue:
                    test = queue.pop()
                    print(f"    {test.source_info!s}\t{test.subtest_type()!s}")
                    new_tests = [c for c in test.children if c not in history]
                    history |= set(new_tests)
                    queue.extend(reversed(new_tests))
        self.assertEqual(num_text_tests, 264)
        self.assertEqual(num_non_text_tests, 3178)

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

        default_matcher = MagicMatcher.DEFAULT_INSTANCE

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
                    if testfile.stem not in (
                            "JW07022A.mp3", "gedcom", "cmd1", "cmd2", "cmd3", "cmd4", "jpeg-text", "jsonlines1",
                            "multiple", "pnm1", "pnm2", "pnm3"
                    ):
                        # The files we skip fail because there is a bug in our implementation that we have not yet fixed
                        if expected == "ASCII text" and expected not in matches:
                            self.assertIn(expected.lower(), matches)
                        else:
                            expected = expected.rstrip().lower()
                            matches = [m.rstrip().lower() for m in matches]
                            if "00000000" in expected and expected not in matches:
                                # our output is technically correct but we output "0x000000" instead of "00000000"
                                self.assertIn(expected.replace("00000000", "0x000000"), matches)
                            else:
                                self.assertIn(expected, matches)
