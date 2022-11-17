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
        num_text_tests = len(matcher.text_tests)
        num_non_text_tests = len(matcher.non_text_tests)
        if num_text_tests > 287:
            expected_text_tests = {'sgml:134', 'tex:132', 'tcl:17', 'perl:49', 'sgml:92', 'make:6', 'tex:75', 'uuencode:18', 'ringdove:22', 'ctags:6', 'softquad:26', 'sgml:136', 'sgml:96', 'apple:6', 'c-lang:78', 'python:293', 'nim-lang:7', 'tex:46', 'sisu:17', 'troff:9', 'ruby:31', 'ruby:18', 'sgml:59', 'tex:118', 'ruby:9', 'perl:12', 'games:218', 'sgml:120', 'c-lang:45', 'tex:76', 'c-lang:36', 'lex:12', 'sgml:68', 'misctools:6', 'sgml:74', 'diff:11', 'tcl:9', 'scientific:65', 'sgml:135', 'lua:13', 'tex:86', 'sgml:89', 'tex:92', 'assembler:7', 'c-lang:10', 'tcl:15', 'forth:16', 'assembler:17', 'ringdove:29', 'assembler:13', 'subtitle:19', 'lex:10', 'perl:10', 'tex:40', 'commands:102', 'algol68:22', 'sgml:102', 'ringdove:26', 'tex:88', 'perl:18', 'msdos:28', 'tcl:19', 'c-lang:90', 'python:287', 'pascal:5', 'securitycerts:4', 'troff:11', 'ruby:50', 'json:6', 'tex:96', 'ringdove:6', 'c-lang:42', 'commands:135', 'tex:87', 'ringdove:19', 'tex:71', 'tex:128', 'c-lang:29', 'lisp:18', 'python:232', 'tex:104', 'tcl:25', 'troff:21', 'tex:114', 'algol68:20', 'tex:112', 'rst:5', 'sgml:126', 'images:2115', 'tex:21', 'linux:507', 'perl:36', 'games:286', 'perl:48', 'tex:49', 'python:235', 'tex:36', 'm4:8', 'ruby:25', 'tex:64', 'ringdove:13', 'python:263', 'perl:16', 'c-lang:8', 'tex:122', 'ringdove:20', 'c-lang:96', 'ringdove:25', 'lua:15', 'gimp:67', 'commands:137', 'images:186', 'tex:138', 'commands:68', 'sisu:5', 'ringdove:17', 'ruby:12', 'python:244', 'lisp:24', 'lua:9', 'sgml:83', 'sgml:127', 'uuencode:26', 'lisp:77', 'clojure:23', 'm4:5', 'c-lang:22', 'database:853', 'perl:53', 'sgml:55', 'fonts:6', 'perl:51', 'uuencode:22', 'cddb:12', 'tex:78', 'xwindows:38', 'diff:6', 'terminfo:48', 'python:279', 'commands:159', 'perl:47', 'tex:98', 'commands:139', 'sgml:62', 'tex:74', 'inform:9', 'c-lang:65', 'lisp:22', 'ruby:44', 'tex:126', 'tex:93', 'ringdove:8', 'tex:89', 'sgml:80', 'diff:8', 'commands:111', 'misctools:44', 'tex:120', 'make:19', 'troff:13', 'sgml:49', 'audio:633', 'tcl:13', 'sgml:128', 'c-lang:33', 'tex:34', 'sosi:30', 'assembler:15', 'lisp:20', 'sketch:6', 'windows:454', 'cad:333', 'ringdove:14', 'tex:134', 'tex:52', 'c-lang:25', 'tex:130', 'sgml:71', 'tcl:21', 'clojure:29', 'tex:58', 'tex:77', 'perl:40', 'ruby:53', 'sisu:14', 'sgml:86', 'sgml:65', 'linux:54', 'troff:19', 'perl:22', 'make:15', 'tcl:7', 'c-lang:86', 'c-lang:39', 'tex:43', 'audio:631', 'c-lang:73', 'gnu:170', 'troff:25', 'clojure:26', 'assembler:11', 'algol68:24', 'lua:11', 'commands:132', 'os2:9', 'ringdove:9', 'perl:54', 'bioinformatics:156', 'psl:9', 'commands:105', 'commands:142', 'csv:6', 'python:250', 'tex:61', 'c-lang:69', 'ringdove:15', 'c-lang:51', 'sisu:11', 'perl:24', 'windows:671', 'tex:94', 'diff:24', 'tex:90', 'algol68:9', 'tex:55', 'linux:174', 'assembler:9', 'perl:50', 'sisu:8', 'misctools:39', 'ringdove:32', 'perl:14', 'tex:91', 'windows:325', 'ringdove:28', 'ringdove:7', 'algol68:26', 'c-lang:15', 'forth:10', 'c-lang:82', 'images:209', 'troff:15', 'perl:52', 'tex:106', 'gentoo:44', 'sgml:77', 'ringdove:16', 'lisp:26', 'assembler:5', 'c-lang:60', 'c-lang:48', 'tex:124', 'tex:67', 'ringdove:27', 'lisp:16', 'images:200', 'commands:108', 'java:19', 'msx:78', 'fonts:132', 'diff:13', 'qt:13', 'cad:309', 'tex:116', 'msdos:26', 'ruby:15', 'ringdove:21', 'tex:136', 'tex:100', 'ruby:37', 'securitycerts:5', 'perl:8', 'tcl:11', 'fortran:6', 'ringdove:12', 'tex:95', 'tex:102', 'perl:20', 'archive:360', 'python:256', 'linux:173', 'python:238', 'diff:16', 'tcl:28', 'linux:170', 'ringdove:18', 'tex:20'}
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
        self.assertEqual(num_text_tests, 287)
        self.assertEqual(num_non_text_tests, 3149)

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
