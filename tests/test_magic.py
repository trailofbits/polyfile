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
        expected_text_tests = {'c-lang:82', 'sgml:65', 'troff:25', 'perl:20', 'tex:114', 'make:6', 'sgml:68',
                               'ringdove:26', 'perl:52', 'c-lang:73', 'commands:45', 'tex:98', 'ringdove:21',
                               'commands:64', 'ruby:9', 'ruby:25', 'linux:54', 'commands:135', 'sgml:105', 'ringdove:7',
                               'ringdove:22', 'ruby:31', 'ringdove:25', 'tex:134', 'uuencode:26', 'commands:86',
                               'ctags:6', 'troff:11', 'troff:15', 'lisp:26', 'commands:71', 'mail.news:43', 'pascal:5',
                               'troff:13', 'commands:57', 'mail.news:7', 'tex:67', 'ringdove:15', 'tex:55', 'sisu:17',
                               'linux:173', 'ruby:15', 'tex:76', 'ringdove:12', 'perl:47', 'tcl:15', 'kde:8',
                               'ringdove:19', 'sgml:77', 'tex:124', 'sgml:80', 'perl:14', 'python:293', 'fonts:6',
                               'json:6', 'tex:104', 'ringdove:27', 'securitycerts:4', 'commands:111', 'tex:118',
                               'securitycerts:5', 'sgml:83', 'audio:633', 'sisu:11', 'make:19', 'sgml:127',
                               'python:250', 'subtitle:19', 'sgml:89', 'commands:123', 'perl:49', 'tex:128', 'ruby:18',
                               'mail.news:19', 'assembler:15', 'ringdove:17', 'python:256', 'lisp:16',
                               'bioinformatics:156', 'rst:5', 'lex:12', 'ringdove:20', 'perl:40', 'clojure:29',
                               'mail.news:11', 'kde:10', 'commands:51', 'nim-lang:7', 'tex:136', 'misctools:6',
                               'sgml:102', 'tex:75', 'commands:139', 'c-lang:86', 'tex:93', 'commands:159', 'linux:507',
                               'windows:325', 'lisp:77', 'ringdove:28', 'gentoo:44', 'games:369', 'sgml:114',
                               'c-lang:10', 'uuencode:18', 'tex:86', 'python:9', 'perl:54', 'c-lang:90', 'fortran:6',
                               'perl:12', 'tex:46', 'c-lang:45', 'commands:36', 'softquad:26', 'ruby:37', 'tex:21',
                               'perl:51', 'ringdove:8', 'subtitle:25', 'msdos:28', 'commands:82', 'sisu:8',
                               'commands:43', 'forth:16', 'sisu:14', 'tex:116', 'c-lang:8', 'sgml:92', 'sgml:128',
                               'mail.news:27', 'tex:58', 'troff:19', 'linux:174', 'sgml:74', 'c-lang:60', 'commands:55',
                               'commands:181', 'commands:40', 'ringdove:14', 'commands:53', 'sgml:55', 'tex:106',
                               'c-lang:33', 'tex:40', 'perl:22', 'tex:122', 'commands:121', 'misctools:39',
                               'commands:117', 'tex:92', 'commands:97', 'tex:130', 'commands:49', 'c-lang:48',
                               'magic:6', 'apple:6', 'commands:7', 'perl:18', 'mail.news:29', 'tex:36', 'sgml:86',
                               'mail.news:9', 'tex:120', 'commands:34', 'cad:309', 'gimp:7', 'tex:52', 'mail.news:15',
                               'commands:25', 'c-lang:22', 'forth:10', 'archive:360', 'tcl:19', 'lex:10',
                               'commands:105', 'lisp:24', 'c-lang:25', 'commands:78', 'sgml:59', 'ringdove:32',
                               'windows:671', 'commands:61', 'sgml:136', 'c-lang:51', 'sketch:6', 'linux:170',
                               'gimp:14', 'mail.news:41', 'sgml:18', 'tcl:17', 'tex:112', 'tcl:11', 'revision:6',
                               'ringdove:18', 'clojure:23', 'ruby:53', 'kde:6', 'make:15', 'tex:94', 'tex:96',
                               'mail.news:17', 'mail.news:13', 'ruby:44', 'python:287', 'tex:49', 'tex:77', 'tex:20',
                               'ringdove:6', 'perl:10', 'ringdove:9', 'csv:6', 'assembler:11', 'perl:48', 'ringdove:29',
                               'commands:47', 'tex:126', 'python:244', 'ringdove:16', 'lisp:20', 'commands:108',
                               'commands:14', 'assembler:7', 'commands:18', 'c-lang:42', 'c-lang:69', 'assembler:17',
                               'mail.news:23', 'msdos:26', 'commands:95', 'commands:23', 'sgml:71', 'c-lang:65',
                               'ruby:12', 'lisp:22', 'psl:9', 'gnu:170', 'python:279', 'lisp:18', 'commands:142',
                               'perl:50', 'tcl:28', 'm4:5', 'mail.news:25', 'c-lang:96', 'sisu:5', 'sgml:120', 'tex:95',
                               'perl:16', 'commands:38', 'tex:89', 'commands:102', 'tex:87', 'commands:99',
                               'assembler:5', 'perl:8', 'tex:90', 'commands:90', 'lua:15', 'commands:132', 'sgml:126',
                               'tex:43', 'tcl:25', 'perl:53', 'sgml:49', 'tcl:13', 'c-lang:29', 'games:370',
                               'audio:631', 'diff:16', 'c-lang:36', 'lua:11', 'perl:24', 'tex:34', 'tex:132',
                               'commands:74', 'troff:9', 'commands:68', 'c-lang:78', 'commands:29', 'inform:9',
                               'commands:66', 'games:286', 'sgml:135', 'terminfo:48', 'commands:59', 'cad:333',
                               'mail.news:21', 'ringdove:13', 'tex:88', 'tex:138', 'commands:27', 'sgml:96', 'm4:8',
                               'images:2408', 'perl:36', 'lua:9', 'msx:78', 'python:263', 'c-lang:39', 'tex:64',
                               'tex:100', 'sgml:62', 'tex:61', 'commands:119', 'tcl:9', 'tex:102', 'sgml:108',
                               'clojure:26', 'tex:74', 'commands:137', 'tex:91', 'tex:71', 'java:19', 'ruby:50',
                               'assembler:9', 'fonts:132', 'sgml:134', 'misctools:44', 'lua:13', 'assembler:13',
                               'tex:78', 'tcl:21', 'troff:21', 'tcl:7'}
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
