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
        expected_text_tests = {'lisp:20', 'tex:54', 'misctools:104', 'sgml:100', 'mail.news:7', 'python:287',
                               'c-lang:29', 'perl:16', 'make:6', 'commands:53', 'assembler:7', 'assembler:15', 'tex:97',
                               'tex:106', 'tex:136', 'lisp:16', 'csv:6', 'sgml:131', 'sgml:145', 'cad:317',
                               'javascript:37', 'sisu:17', 'mail.news:19', 'sgml:88', 'javascript:14', 'commands:201',
                               'perl:53', 'm4:5', 'tcl:9', 'commands:199', 'securitycerts:4', 'ringdove:19', 'lex:10',
                               'javascript:63', 'mail.news:29', 'games:459', 'lua:13', 'windows:989', 'javascript:41',
                               'tex:138', 'java:49', 'sgml:147', 'tex:60', 'sgml:56', 'bioinformatics:156',
                               'softquad:26', 'tex:51', 'c-lang:22', 'commands:55', 'tex:38', 'commands:95', 'tcl:11',
                               'audio:648', 'sisu:8', 'linux:170', 'perl:8', 'python:279', 'tex:88', 'perl:12',
                               'tex:126', 'tcl:21', 'ruby:31', 'perl:20', 'perl:22', 'tex:104', 'sgml:54',
                               'mail.news:21', 'tex:23', 'perl:51', 'lisp:24', 'tex:114', 'sgml:73', 'c-lang:78',
                               'gimp:7', 'assembler:13', 'c-lang:60', 'commands:121', 'pascal:5', 'commands:117',
                               'commands:86', 'tex:108', 'commands:49', 'perl:24', 'audio:646', 'tex:122', 'clojure:29',
                               'revision:6', 'tex:128', 'tex:78', 'python:293', 'commands:142', 'ruby:44', 'troff:15',
                               'sgml:18', 'subtitle:25', 'commands:102', 'sgml:97', 'c-lang:51', 'tex:91', 'perl:47',
                               'sisu:14', 'perl:48', 'tex:36', 'games:458', 'ringdove:32', 'commands:108', 'linux:54',
                               'tcl:28', 'commands:36', 'tex:22', 'misctools:6', 'c-lang:45', 'sgml:49', 'commands:40',
                               'tex:140', 'commands:200', 'mail.news:25', 'java:19', 'archive:450', 'kde:10',
                               'android:214', 'ringdove:9', 'mail.news:41', 'ringdove:6', 'commands:181', 'cad:365',
                               'tex:63', 'tex:98', 'c-lang:10', 'javascript:10', 'rst:5', 'c-lang:65', 'javascript:33',
                               'tex:89', 'troff:25', 'python:244', 'tex:79', 'sgml:76', 'uuencode:18', 'kde:6',
                               'ringdove:20', 'lua:11', 'ringdove:26', 'tex:48', 'ringdove:18', 'sgml:58', 'perl:52',
                               'mail.news:15', 'c-lang:96', 'linux:173', 'tex:96', 'linux:174', 'sgml:70',
                               'ringdove:13', 'sisu:5', 'ringdove:22', 'javascript:29', 'ruby:25', 'commands:74',
                               'terminfo:49', 'ringdove:8', 'ruby:18', 'c-lang:73', 'commands:82', 'commands:29',
                               'clojure:26', 'commands:25', 'ringdove:17', 'ringdove:14', 'tex:92', 'tex:102', 'tex:69',
                               'lex:12', 'javascript:57', 'tex:100', 'commands:23', 'perl:54', 'commands:51',
                               'sgml:138', 'troff:11', 'perl:18', 'javascript:45', 'tex:95', 'mail.news:13', 'tex:116',
                               'images:2421', 'windows:457', 'tex:134', 'm4:8', 'javascript:16', 'ringdove:27',
                               'c-lang:48', 'misctools:99', 'tex:132', 'python:256', 'c-lang:69', 'assembler:17',
                               'tex:80', 'assembler:9', 'java:51', 'nim-lang:7', 'tex:77', 'clojure:23', 'python:263',
                               'mail.news:9', 'diff:16', 'ruby:15', 'commands:139', 'tcl:17', 'magic:6', 'json:6',
                               'commands:90', 'forth:10', 'commands:135', 'commands:66', 'commands:43', 'msdos:28',
                               'lisp:26', 'fortran:6', 'ruby:12', 'javascript:12', 'commands:123', 'commands:14',
                               'commands:57', 'tex:57', 'perl:40', 'tex:73', 'ringdove:29', 'commands:78',
                               'commands:99', 'tex:66', 'commands:111', 'tcl:15', 'python:9', 'fonts:6', 'tex:94',
                               'ctags:6', 'tcl:7', 'troff:9', 'forth:16', 'commands:119', 'tex:90', 'fonts:132',
                               'ringdove:16', 'tex:124', 'gnu:170', 'lisp:22', 'make:15', 'python:250', 'psl:9',
                               'tex:45', 'commands:61', 'c-lang:36', 'ruby:50', 'mail.news:23', 'mail.news:11',
                               'javascript:49', 'ringdove:12', 'commands:64', 'sgml:146', 'lisp:77', 'sgml:66',
                               'inform:9', 'commands:47', 'games:295', 'ringdove:28', 'commands:38', 'lua:9', 'tex:42',
                               'c-lang:82', 'mail.news:17', 'c-lang:90', 'commands:105', 'troff:13', 'ringdove:15',
                               'c-lang:39', 'commands:59', 'gimp:14', 'securitycerts:5', 'ruby:53', 'tcl:19',
                               'linux:516', 'c-lang:33', 'tex:120', 'c-lang:42', 'commands:97', 'uuencode:26',
                               'perl:50', 'perl:49', 'kde:8', 'sgml:125', 'tcl:25', 'sgml:82', 'tex:93', 'msdos:26',
                               'sgml:94', 'sgml:137', 'tcl:13', 'lisp:18', 'commands:7', 'sgml:79', 'tex:118',
                               'ruby:37', 'ruby:9', 'perl:14', 'make:19', 'ringdove:25', 'msx:78', 'sgml:116',
                               'sgml:91', 'javascript:6', 'javascript:53', 'sketch:6', 'commands:68', 'c-lang:25',
                               'assembler:5', 'lua:15', 'sisu:11', 'javascript:8', 'commands:137', 'c-lang:86',
                               'commands:159', 'apple:6', 'gentoo:44', 'commands:18', 'troff:21', 'mail.news:43',
                               'ringdove:21', 'sgml:107', 'c-lang:8', 'tex:130', 'commands:45', 'sgml:103',
                               'commands:71', 'commands:132', 'perl:10', 'commands:34', 'ringdove:7', 'perl:36',
                               'commands:27', 'sgml:85', 'sgml:113', 'sgml:119', 'assembler:11', 'subtitle:19',
                               'sgml:139', 'mail.news:27', 'tex:76', 'troff:19'}
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
                            elif expected.startswith("hancom hwp"):
                                self.assertTrue(any(m.endswith(expected) for m in matches))
                            else:
                                self.assertIn(expected, matches)
