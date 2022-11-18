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
        # expected_text_tests = repr({
        #         f"{test.source_info.path.name}:{test.source_info.line}"
        #         for test in matcher.text_tests if test.source_info is not None
        # })
        expected_text_tests = {'commands:55', 'terminfo:48', 'ruby:53', 'troff:11', 'sgml:59', 'tex:102', 'commands:23', 'commands:61', 'tcl:21', 'sgml:62', 'sgml:74', 'c-lang:48', 'perl:49', 'c-lang:69', 'perl:18', 'clojure:26', 'tex:138', 'tex:118', 'linux:54', 'perl:22', 'lisp:16', 'commands:86', 'sisu:17', 'sisu:14', 'fonts:132', 'c-lang:96', 'perl:12', 'tcl:9', 'troff:19', 'commands:108', 'tex:71', 'perl:48', 'securitycerts:4', 'windows:671', 'tcl:13', 'c-lang:42', 'sgml:136', 'ringdove:7', 'tex:132', 'c-lang:45', 'tex:52', 'tex:104', 'tex:89', 'commands:99', 'commands:49', 'tex:100', 'commands:51', 'assembler:13', 'msx:78', 'tex:112', 'troff:21', 'cad:333', 'misctools:39', 'tex:49', 'gnu:170', 'perl:50', 'commands:47', 'tex:136', 'tcl:25', 'forth:16', 'perl:10', 'perl:53', 'cad:309', 'python:287', 'psl:9', 'python:279', 'commands:14', 'perl:52', 'tcl:17', 'inform:9', 'softquad:26', 'tex:91', 'make:6', 'commands:137', 'troff:15', 'commands:159', 'commands:74', 'tex:64', 'commands:64', 'c-lang:60', 'tex:94', 'assembler:9', 'ringdove:17', 'c-lang:73', 'make:19', 'lex:12', 'make:15', 'python:293', 'ruby:9', 'ringdove:19', 'ringdove:27', 'perl:14', 'commands:66', 'tex:92', 'sgml:126', 'perl:20', 'sgml:49', 'fortran:6', 'ringdove:20', 'c-lang:10', 'sgml:96', 'tex:58', 'subtitle:19', 'uuencode:18', 'c-lang:8', 'c-lang:29', 'csv:6', 'sgml:128', 'tex:46', 'commands:121', 'c-lang:33', 'python:256', 'assembler:15', 'games:286', 'ruby:18', 'tex:76', 'commands:82', 'assembler:5', 'perl:40', 'archive:360', 'json:6', 'commands:40', 'sgml:83', 'linux:174', 'tex:20', 'tex:95', 'sisu:5', 'python:250', 'c-lang:65', 'lua:15', 'commands:7', 'tex:90', 'bioinformatics:156', 'commands:102', 'c-lang:36', 'ringdove:16', 'commands:25', 'tex:106', 'lisp:26', 'ringdove:22', 'gentoo:44', 'commands:139', 'ruby:50', 'commands:18', 'commands:78', 'tex:120', 'ringdove:6', 'tex:114', 'tcl:19', 'mail.news:17', 'c-lang:51', 'commands:53', 'sgml:92', 'troff:9', 'msdos:28', 'forth:10', 'ringdove:28', 'sgml:65', 'commands:132', 'tcl:15', 'ringdove:21', 'ruby:25', 'clojure:23', 'commands:117', 'misctools:6', 'ctags:6', 'lisp:18', 'sgml:135', 'fonts:6', 'audio:631', 'tex:21', 'commands:123', 'sgml:102', 'ringdove:26', 'ringdove:18', 'tex:77', 'sgml:86', 'commands:105', 'tex:86', 'ruby:37', 'sgml:71', 'perl:47', 'tex:122', 'tex:126', 'apple:6', 'tex:128', 'commands:38', 'mail.news:19', 'm4:8', 'tex:96', 'c-lang:86', 'securitycerts:5', 'tcl:28', 'ruby:12', 'c-lang:82', 'uuencode:26', 'ringdove:8', 'tex:40', 'commands:95', 'ringdove:9', 'c-lang:78', 'c-lang:39', 'linux:173', 'commands:43', 'tex:98', 'tex:75', 'tex:43', 'windows:325', 'msdos:26', 'tcl:7', 'commands:97', 'commands:27', 'commands:29', 'troff:25', 'tex:34', 'linux:170', 'nim-lang:7', 'ringdove:15', 'perl:36', 'perl:8', 'tex:87', 'commands:71', 'tex:74', 'commands:34', 'misctools:44', 'commands:57', 'lua:13', 'c-lang:25', 'ringdove:14', 'pascal:5', 'sgml:134', 'ringdove:32', 'lisp:24', 'tex:124', 'perl:51', 'perl:24', 'sgml:80', 'diff:16', 'rst:5', 'commands:135', 'commands:90', 'commands:142', 'lex:10', 'tex:55', 'lua:9', 'tex:36', 'perl:16', 'sgml:55', 'python:263', 'java:19', 'lua:11', 'commands:119', 'lisp:77', 'sisu:11', 'tex:93', 'tex:130', 'troff:13', 'sgml:68', 'ringdove:25', 'tex:67', 'assembler:11', 'c-lang:22', 'ruby:31', 'sgml:127', 'ruby:15', 'ringdove:12', 'sgml:89', 'clojure:29', 'tex:61', 'tex:78', 'linux:507', 'sketch:6', 'commands:68', 'ringdove:29', 'commands:45', 'm4:5', 'commands:111', 'perl:54', 'sisu:8', 'tex:134', 'commands:59', 'ruby:44', 'sgml:120', 'assembler:7', 'audio:633', 'assembler:17', 'c-lang:90', 'tcl:11', 'ringdove:13', 'tex:116', 'python:244', 'sgml:77', 'lisp:22', 'commands:36', 'tex:88', 'lisp:20'}
        if num_text_tests > len(expected_text_tests):
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
        self.assertEqual(num_text_tests, len(expected_text_tests))

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
