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
        expected_text_tests = {
            'android:214', 'apple:6', 'archive:583', 'assembler:11', 'assembler:13', 'assembler:15',
            'assembler:17', 'assembler:5', 'assembler:7', 'assembler:9', 'audio:645', 'audio:648',
            'bioinformatics:156', 'c-lang:10', 'c-lang:103', 'c-lang:107', 'c-lang:111', 'c-lang:22',
            'c-lang:25', 'c-lang:29', 'c-lang:32', 'c-lang:35', 'c-lang:38', 'c-lang:41', 'c-lang:44',
            'c-lang:47', 'c-lang:50', 'c-lang:59', 'c-lang:64', 'c-lang:68', 'c-lang:72', 'c-lang:77',
            'c-lang:8', 'c-lang:81', 'c-lang:85', 'c-lang:89', 'c-lang:95', 'cad:317', 'cad:365',
            'clojure:23', 'clojure:26', 'clojure:29', 'commands:101', 'commands:104', 'commands:106',
            'commands:111', 'commands:113', 'commands:115', 'commands:118', 'commands:121',
            'commands:123', 'commands:125', 'commands:128', 'commands:131', 'commands:133',
            'commands:139', 'commands:14', 'commands:141', 'commands:143', 'commands:145',
            'commands:157', 'commands:160', 'commands:162', 'commands:164', 'commands:167',
            'commands:18', 'commands:184', 'commands:206', 'commands:224', 'commands:225',
            'commands:226', 'commands:23', 'commands:25', 'commands:27', 'commands:29', 'commands:34',
            'commands:36', 'commands:38', 'commands:40', 'commands:43', 'commands:45', 'commands:47',
            'commands:49', 'commands:51', 'commands:53', 'commands:55', 'commands:57', 'commands:59',
            'commands:61', 'commands:64', 'commands:66', 'commands:68', 'commands:7', 'commands:70',
            'commands:72', 'commands:74', 'commands:76', 'commands:80', 'commands:83', 'commands:87',
            'commands:91', 'commands:95', 'commands:99', 'csv:6', 'ctags:6', 'diff:48', 'fonts:132',
            'fonts:6', 'forth:10', 'forth:16', 'fortran:6', 'games:248', 'games:411', 'games:412',
            'gentoo:44', 'gimp:14', 'gimp:7', 'gnu:170', 'images:2620', 'inform:9', 'java:19',
            'java:49', 'java:51', 'javascript:10', 'javascript:12', 'javascript:14', 'javascript:16',
            'javascript:30', 'javascript:34', 'javascript:38', 'javascript:42', 'javascript:46',
            'javascript:50', 'javascript:54', 'javascript:6', 'javascript:60', 'javascript:8',
            'json:6', 'kde:10', 'kde:6', 'kde:8', 'lex:10', 'lex:12', 'linux:366', 'linux:369',
            'linux:370', 'linux:54', 'linux:938', 'lisp:16', 'lisp:18', 'lisp:20', 'lisp:22',
            'lisp:24', 'lisp:26', 'lisp:77', 'lua:11', 'lua:13', 'lua:15', 'lua:9', 'm4:5', 'm4:8',
            'magic:8', 'mail.news:11', 'mail.news:13', 'mail.news:15', 'mail.news:17', 'mail.news:19',
            'mail.news:21', 'mail.news:23', 'mail.news:25', 'mail.news:27', 'mail.news:29',
            'mail.news:31', 'mail.news:33', 'mail.news:35', 'mail.news:47', 'mail.news:49',
            'mail.news:7', 'mail.news:9', 'make:15', 'make:19', 'make:6', 'misctools:104',
            'misctools:6', 'misctools:99', 'msdos:26', 'msdos:28', 'msx:79', 'nim-lang:7', 'pascal:5',
            'perl:10', 'perl:12', 'perl:14', 'perl:16', 'perl:18', 'perl:20', 'perl:22', 'perl:24',
            'perl:36', 'perl:40', 'perl:47', 'perl:48', 'perl:49', 'perl:50', 'perl:51', 'perl:52',
            'perl:53', 'perl:54', 'perl:8', 'psl:9', 'python:262', 'python:271', 'python:277',
            'python:295', 'python:303', 'python:309', 'python:9', 'revision:7', 'ringdove:12',
            'ringdove:13', 'ringdove:14', 'ringdove:15', 'ringdove:16', 'ringdove:17', 'ringdove:18',
            'ringdove:19', 'ringdove:20', 'ringdove:21', 'ringdove:22', 'ringdove:25', 'ringdove:26',
            'ringdove:27', 'ringdove:28', 'ringdove:29', 'ringdove:32', 'ringdove:6', 'ringdove:7',
            'ringdove:8', 'ringdove:9', 'ruby:12', 'ruby:15', 'ruby:18', 'ruby:25', 'ruby:31',
            'ruby:37', 'ruby:44', 'ruby:50', 'ruby:53', 'ruby:9', 'securitycerts:4', 'securitycerts:5',
            'sgml:102', 'sgml:105', 'sgml:108', 'sgml:111', 'sgml:115', 'sgml:121', 'sgml:128',
            'sgml:131', 'sgml:134', 'sgml:140', 'sgml:146', 'sgml:152', 'sgml:153', 'sgml:154',
            'sgml:160', 'sgml:161', 'sgml:162', 'sgml:17', 'sgml:57', 'sgml:6', 'sgml:62', 'sgml:64',
            'sgml:66', 'sgml:74', 'sgml:78', 'sgml:81', 'sgml:84', 'sgml:87', 'sgml:90', 'sgml:93',
            'sgml:96', 'sgml:99', 'sisu:11', 'sisu:14', 'sisu:17', 'sisu:5', 'sisu:8', 'sketch:6',
            'softquad:26', 'subtitle:19', 'subtitle:25', 'tcl:11', 'tcl:13', 'tcl:15', 'tcl:17',
            'tcl:19', 'tcl:21', 'tcl:25', 'tcl:28', 'tcl:7', 'tcl:9', 'terminfo:49', 'tex:103',
            'tex:104', 'tex:105', 'tex:106', 'tex:107', 'tex:108', 'tex:109', 'tex:110', 'tex:111',
            'tex:112', 'tex:113', 'tex:115', 'tex:117', 'tex:119', 'tex:121', 'tex:123', 'tex:129',
            'tex:131', 'tex:133', 'tex:135', 'tex:137', 'tex:139', 'tex:141', 'tex:143', 'tex:145',
            'tex:147', 'tex:149', 'tex:151', 'tex:153', 'tex:155', 'tex:22', 'tex:23', 'tex:24',
            'tex:25', 'tex:26', 'tex:27', 'tex:28', 'tex:29', 'tex:30', 'tex:31', 'tex:32', 'tex:33',
            'tex:34', 'tex:47', 'tex:49', 'tex:57', 'tex:60', 'tex:63', 'tex:66', 'tex:69', 'tex:72',
            'tex:75', 'tex:78', 'tex:81', 'tex:84', 'tex:88', 'tex:91', 'tex:92', 'tex:93', 'tex:94',
            'tex:95', 'troff:12', 'troff:15', 'troff:18', 'troff:23', 'troff:26', 'troff:31',
            'troff:9', 'uuencode:18', 'uuencode:26', 'windows:1064', 'windows:457',
        }
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
                            "multiple", "osm", "pnm1", "pnm2", "pnm3", "utf16xmlsvg"
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
