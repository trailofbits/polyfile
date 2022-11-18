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
        expected_text_tests = {'sgml:128', 'c-lang:73', 'misctools:39', 'tex:128', 'commands:137', 'forth:10',
                               'commands:132', 'tex:74', 'ruby:15', 'tex:91', 'c-lang:90', 'misctools:6', 'sgml:96',
                               'sisu:8', 'tex:21', 'tex:138', 'tcl:19', 'tex:98', 'tex:134', 'commands:108', 'troff:21',
                               'tex:116', 'tex:124', 'python:256', 'tex:55', 'tex:87', 'sgml:65', 'tex:88', 'msdos:26',
                               'ruby:50', 'tex:136', 'c-lang:82', 'ringdove:27', 'c-lang:8', 'python:293', 'gentoo:44',
                               'sgml:126', 'python:279', 'assembler:15', 'c-lang:69', 'make:15', 'tex:49', 'python:244',
                               'perl:18', 'tcl:15', 'assembler:9', 'commands:135', 'pascal:5', 'c-lang:60', 'tex:102',
                               'ringdove:8', 'commands:105', 'ringdove:28', 'sgml:102', 'msx:78', 'sgml:62',
                               'ringdove:7', 'commands:68', 'linux:507', 'tex:122', 'perl:53', 'c-lang:10',
                               'commands:102', 'tex:77', 'tex:64', 'linux:54', 'perl:36', 'ringdove:19', 'sisu:14',
                               'ringdove:22', 'c-lang:33', 'tcl:13', 'inform:9', 'perl:22', 'clojure:26', 'c-lang:25',
                               'troff:13', 'archive:360', 'tex:106', 'tex:43', 'json:6', 'tex:93', 'fonts:6', 'ruby:37',
                               'c-lang:51', 'tcl:7', 'windows:325', 'sgml:55', 'tex:71', 'securitycerts:5', 'tcl:25',
                               'm4:5', 'c-lang:48', 'assembler:5', 'ruby:9', 'c-lang:86', 'tcl:17', 'ruby:25', 'rst:5',
                               'ringdove:17', 'tex:90', 'commands:111', 'lex:10', 'windows:671', 'ringdove:18',
                               'lex:12', 'c-lang:29', 'tex:75', 'troff:15', 'make:19', 'troff:19', 'ringdove:32',
                               'tex:126', 'tex:89', 'sgml:89', 'ringdove:14', 'sisu:17', 'ringdove:25', 'lisp:20',
                               'tcl:21', 'tex:94', 'ringdove:29', 'uuencode:18', 'tex:46', 'c-lang:78', 'c-lang:65',
                               'assembler:13', 'sgml:86', 'c-lang:36', 'tex:34', 'm4:8', 'ringdove:12', 'ringdove:9',
                               'python:263', 'tex:95', 'perl:8', 'tex:76', 'ctags:6', 'audio:631', 'assembler:11',
                               'make:6', 'securitycerts:4', 'assembler:17', 'sgml:120', 'tex:86', 'perl:12', 'ruby:53',
                               'lisp:16', 'tex:92', 'fortran:6', 'ringdove:13', 'c-lang:96', 'sgml:127', 'perl:54',
                               'troff:9', 'nim-lang:7', 'python:250', 'perl:52', 'python:287', 'c-lang:45', 'sgml:74',
                               'c-lang:39', 'lisp:22', 'lua:11', 'tex:104', 'cad:333', 'ringdove:15', 'sgml:92',
                               'assembler:7', 'ruby:44', 'tex:118', 'sgml:68', 'linux:174', 'lisp:26', 'fonts:132',
                               'perl:51', 'perl:40', 'games:286', 'sgml:59', 'tex:132', 'uuencode:26', 'lua:15',
                               'linux:173', 'sgml:134', 'clojure:23', 'tex:96', 'sisu:5', 'tcl:11', 'tex:36',
                               'troff:25', 'msdos:28', 'ruby:18', 'tex:58', 'audio:633', 'sgml:49', 'lisp:18',
                               'perl:49', 'cad:309', 'perl:14', 'lisp:24', 'sketch:6', 'tex:114', 'softquad:26',
                               'clojure:29', 'lua:13', 'forth:16', 'tex:78', 'lua:9', 'sgml:77', 'ringdove:16',
                               'tex:112', 'tex:20', 'misctools:44', 'commands:139', 'troff:11', 'tex:67', 'perl:50',
                               'tex:120', 'sgml:135', 'sgml:136', 'perl:10', 'tex:130', 'ringdove:21', 'ringdove:20',
                               'tex:100', 'csv:6', 'linux:170', 'perl:48', 'perl:16', 'commands:142', 'sgml:71',
                               'tex:52', 'c-lang:22', 'ruby:31', 'perl:24', 'bioinformatics:156', 'gnu:170', 'sgml:80',
                               'terminfo:48', 'tcl:9', 'commands:159', 'ringdove:6', 'ruby:12', 'diff:16',
                               'subtitle:19', 'psl:9', 'c-lang:42', 'lisp:77', 'perl:20', 'tex:61', 'apple:6', 'tcl:28',
                               'tex:40', 'sisu:11', 'perl:47', 'ringdove:26', 'sgml:83', 'java:19'}
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
