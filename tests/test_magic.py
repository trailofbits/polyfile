import base64
import gzip
import os
import subprocess
import sys
import time
import zlib
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple
from unittest import TestCase
from uuid import UUID

# from polyfile import logger
import polyfile.der
import polyfile.magic
from polyfile.magic import (
    DataType, MagicMatcher, MAGIC_DEFS, Match, MatchContext, RegexType, SearchType, StringType,
    TestResult
)


# logger.setLevel(logger.TRACE)

FILE_TEST_DIR: Path = Path(__file__).parent.parent / "file" / "tests"

KNOWN_FAILURES: Dict[str, int] = {
    # Empty, and worth keeping that way: every stem of the libmagic corpus now matches what
    # libmagic reports. `test_file_corpus` asserts that a stem listed here still FAILS, so an entry
    # is a deliberate record of a filed bug rather than a way to quiet the suite. Add one only
    # alongside the issue that explains it, mapped to that issue number, and delete it in the
    # change that fixes it. Issue #3480 tracks how the previous fourteen were retired.
}
"""Corpus stems that cannot pass yet, each mapped to the issue that has to be fixed first."""

DER_CERTIFICATE: Path = Path(__file__).absolute().parent / "msjdbc.cer.gz"

ISSUE_3374_PDF: bytes = base64.b64decode(
    "eNptUsFO4zAQvVvyPwyHSnAgtpukpRJCKtBuJbqkanxZbRAy1C2BkqDYRbv79YydRGm7WLJlv3me9zzj"
    "3uJ2ei4CQYkADuXTKyWXl0AJMPn3QwO7UVZty40DFmqjDfSRtqTk6ooSXaz8BUr6R3fv8pWB3xA6Ljw4"
    "5KbcFRbEXuY63XGmsMt0SK2TFFYX1kBUmwA2HoMnAkuaDbApnGY4xKgfiMFF0I8DkWVWG5tl63yrz2rW"
    "LfrjSM6tN4hICuxHKcuJOzlT9YLiFWq27wa21KbcVc/ovVGeoqtOXLTb1rwLN0C6e7IecxHRgNfKaJ+C"
    "zfT2U9v8WfmIV++MHJYpOir4XBcb+wKC85pJibGVVu+UXEtKmBSPHIsv19hmdxUPEZIDzjkM4zAYDQcg"
    "kYwItLPCpp8mSbJIT+AXvhju5fwnzMbpDF6UgdedsTDX6k2vggDOQKKZifQeW+nO7p9KozSHGJduwCCO"
    "wxjWe6BAbR8q9sDhN6CIov/BKBx1ICW2Utjvqv1Ly7J0P7BpY5r/0xDV1TJWVbb2OBCI9XqTZPoFx5+0"
    "nw=="
)
"""The payload from issue #3374, which reads as a PDF once it is decompressed."""


def tag_length_value(tag: int, value: bytes) -> bytes:
    """Encodes a DER tag-length-value triple using the short form of the length."""
    assert len(value) < 128
    return bytes((tag, len(value))) + value


def corpus_matcher(test: str) -> MagicMatcher:
    """Builds the matcher for one libmagic corpus test.

    Upstream's runner loads every `<stem>*.magic` sidecar, joined with the path separator, and
    falls back to the compiled definitions when a test ships none (`file/tests/Makefile.am`).

    Args:
        test: The stem shared by the test's `.testfile`, `.result` and sidecar files.

    Returns:
        A matcher parsed from the test's sidecars, or the default matcher when it has none.
    """
    sidecars = sorted(FILE_TEST_DIR.glob(f"{test}*.magic"))
    if not sidecars:
        return MagicMatcher.DEFAULT_INSTANCE
    print(f"\tParsing custom match scripts: {', '.join(s.name for s in sidecars)}")
    return MagicMatcher.parse(*sidecars)


def corpus_flags(test: str) -> str:
    """Reads the libmagic flags that produced a corpus test's expected result.

    Upstream's runner appends the contents of `<stem>.flags` to the flags it hands to
    `magic_open` (`file/tests/Makefile.am` and `file/tests/test.c`). `k` is `MAGIC_CONTINUE`,
    which makes `file` report every match instead of only the strongest one, joining them with
    `\\012- `. PolyFile always reports every match, so `check_corpus_test` renders that join with
    `polyfile.magic.join_matches` for the tests whose flags ask for it.

    Args:
        test: The stem shared by the test's `.testfile`, `.result` and `.flags` files.

    Returns:
        The flag letters, or the empty string when the test ships no `.flags` file.
    """
    flags = FILE_TEST_DIR / f"{test}.flags"
    if not flags.exists():
        return ""
    return flags.read_text().strip()


def corpus_result_matches(expected: str, matches: Set[str]) -> bool:
    """Reports whether PolyFile's matches include libmagic's expected description.

    The comparison ignores case and trailing whitespace, and it works around two known
    formatting differences between PolyFile and libmagic.

    Args:
        expected: The contents of the test's `.result` file.
        matches: The description of every match PolyFile reported for the test file.

    Returns:
        True if one of `matches` corresponds to `expected`.
    """
    expected = expected.rstrip().lower()
    lowered = {match.rstrip().lower() for match in matches}
    if "00000000" in expected and expected not in lowered:
        # Technically correct, but PolyFile formats a `%#8.8x` zero as "0x000000".
        return expected.replace("00000000", "0x000000") in lowered
    if expected.startswith("hancom hwp"):
        return any(match.endswith(expected) for match in lowered)
    return expected in lowered


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

    def test_guid_data_types(self):
        """libmagic 5.48 added `leguid` and `beguid` beside `guid`, differing only in byte order."""
        data = bytes(range(16))
        mixed_endian = UUID("03020100-0504-0706-0809-0a0b0c0d0e0f")
        file_order = UUID("00010203-0405-0607-0809-0a0b0c0d0e0f")
        for name, expected in (("guid", mixed_endian), ("leguid", mixed_endian),
                               ("beguid", file_order)):
            with self.subTest(data_type=name):
                data_type = polyfile.magic.DataType.parse(name)
                match = data_type.match(data, polyfile.magic.UUIDWildcard())
                self.assertEqual(expected, match.value)
                self.assertEqual(expected, data_type.match(data, expected).value)
                self.assertIs(polyfile.magic.DataTypeMatch.INVALID,
                              data_type.match(data, UUID(int=0)))

    def test_id3_synchsafe_decode(self):
        """Tests that `decode_id3_synchsafe` drops bit 7 of every byte and repacks the rest.

        This is a regression test for trailofbits/polyfile#3485. An ID3v2 tag stores its size
        with seven significant bits per byte, so a plain four-byte read overstates it: the size
        field `00 00 10 24` is 2084, not 0x1024.
        """
        self.assertEqual(2084, polyfile.magic.decode_id3_synchsafe(0x00001024))
        self.assertEqual(0x0FFFFFFF, polyfile.magic.decode_id3_synchsafe(0x7F7F7F7F))
        self.assertEqual(0, polyfile.magic.decode_id3_synchsafe(0x80808080))
        for shift, expected in ((0, 1), (8, 1 << 7), (16, 1 << 14), (24, 1 << 21)):
            with self.subTest(shift=shift):
                self.assertEqual(expected, polyfile.magic.decode_id3_synchsafe(1 << shift))

    def test_id3_indirect_offset_byte_orders(self):
        """Tests that `.i` and `.I` indirect offsets read their field as an ID3 synchsafe integer.

        This is a regression test for trailofbits/polyfile#3485. libmagic maps the `i` and `I`
        indirect types to FILE_LEID3 and FILE_BEID3 and applies `cvt_id3` before the offset
        arithmetic, so `>(6.I+10)` in `magic_defs/audio` resolves to 2094 and not to 4142. The
        `10 7a` case pins the decode ahead of the `+10`: decoding afterwards carries `0x7a + 10`
        into bit 7 and yields 2052 instead of 2180.
        """
        for spec, size_field, endianness, expected in (
                ("(6.I+10)", b"\x00\x00\x10\x24", polyfile.magic.Endianness.BIG, 2094),
                ("(6.i+10)", b"\x24\x10\x00\x00", polyfile.magic.Endianness.LITTLE, 2094),
                ("(6.I+10)", b"\x00\x00\x10\x7a", polyfile.magic.Endianness.BIG, 2180)):
            with self.subTest(offset=spec, size_field=size_field):
                offset = polyfile.magic.IndirectOffset.parse(spec)
                self.assertTrue(offset.is_id3)
                self.assertEqual(endianness, offset.endianness)
                header = b"ID3\x02\x00\x00" + size_field
                self.assertEqual(expected, offset.to_absolute(header, None))
        for spec in ("(6.l+10)", "(6.L+10)", "(6+10)"):
            with self.subTest(offset=spec):
                self.assertFalse(polyfile.magic.IndirectOffset.parse(spec).is_id3)

    def test_id3v2_tag_locates_its_audio_frames(self):
        """Tests that an ID3v2 tag's indirect offset lands on the MPEG frame that follows it.

        This is a regression test for trailofbits/polyfile#3485. `magic_defs/audio` reaches the
        audio frames with `>(6.I+10) indirect`; without the synchsafe decode PolyFile read the
        2084-byte tag size as 4132 and reported `contains: data`.
        """
        tag = b"ID3\x02\x00\x00\x00\x00\x10\x24"
        data = tag + b"A" * (2094 - len(tag)) + b"\xff\xfb\x70\xc0" + b"\x55" * 380
        matches = {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
        self.assertIn("Audio file with ID3 version 2.2.0, contains: MPEG ADTS, layer III, v1, "
                      "96 kbps, 44.1 kHz, Monaural", matches)

    def test_text_tests(self):
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        for test in matcher.text_tests:
            self.assertTrue(test.test_type & polyfile.magic.TestType.TEXT)
        for test in matcher.non_text_tests:
            self.assertTrue(test.test_type & polyfile.magic.TestType.BINARY
                            or test.test_type == polyfile.magic.TestType.UNKNOWN)
        # the three entries in both passes declare both the `b` and the `t` flag; see
        # PassSelectionTest.test_the_shipped_both_flag_entries_are_in_both_passes
        self.assertEqual(3, len(set(matcher.text_tests) & set(matcher.non_text_tests)))
        num_text_tests = len(matcher.text_tests)
        # expected_text_tests = repr({
        #         f"{test.source_info.path.name}:{test.source_info.line}"
        #         for test in matcher.text_tests if test.source_info is not None
        # })
        expected_text_tests = {
            'a2ml:38', 'a2ml:44', 'algol68:12', 'algol68:14', 'algol68:16', 'algol68:18', 'algol68:9',
            'andrew:30', 'android:221', 'apple:6', 'archive:583', 'assembler:11', 'assembler:13',
            'assembler:15', 'assembler:17', 'assembler:5', 'assembler:7', 'assembler:9', 'audio:645',
            'audio:648', 'bioinformatics:113', 'bioinformatics:156', 'c-lang:10', 'c-lang:103', 'c-lang:107',
            'c-lang:111', 'c-lang:15', 'c-lang:22', 'c-lang:25', 'c-lang:29', 'c-lang:32', 'c-lang:35',
            'c-lang:38', 'c-lang:41', 'c-lang:44', 'c-lang:47', 'c-lang:50', 'c-lang:59', 'c-lang:64',
            'c-lang:68', 'c-lang:72', 'c-lang:77', 'c-lang:8', 'c-lang:81', 'c-lang:85', 'c-lang:89',
            'c-lang:95', 'cddb:12', 'clojure:23', 'clojure:26', 'clojure:29', 'commands:101', 'commands:104',
            'commands:106', 'commands:111', 'commands:113', 'commands:115', 'commands:118', 'commands:121',
            'commands:123', 'commands:125', 'commands:128', 'commands:131', 'commands:133', 'commands:138',
            'commands:14', 'commands:140', 'commands:146', 'commands:148', 'commands:150', 'commands:152',
            'commands:164', 'commands:167', 'commands:169', 'commands:171', 'commands:174', 'commands:18',
            'commands:191', 'commands:213', 'commands:23', 'commands:231', 'commands:232', 'commands:233',
            'commands:25', 'commands:27', 'commands:29', 'commands:34', 'commands:36', 'commands:38',
            'commands:40', 'commands:43', 'commands:45', 'commands:47', 'commands:49', 'commands:51',
            'commands:53', 'commands:55', 'commands:57', 'commands:59', 'commands:61', 'commands:64',
            'commands:66', 'commands:68', 'commands:7', 'commands:70', 'commands:72', 'commands:74',
            'commands:76', 'commands:80', 'commands:83', 'commands:87', 'commands:91', 'commands:95',
            'commands:99', 'csv:6', 'ctags:6', 'database:900', 'diff:114', 'diff:13', 'diff:25', 'diff:35',
            'diff:41', 'diff:48', 'fonts:132', 'fonts:6', 'forth:10', 'forth:16', 'fortran:6', 'frame:71',
            'games:180', 'games:248', 'games:411', 'games:412', 'gentoo:44', 'gentoo:49', 'gimp:14', 'gimp:7',
            'gnu:170', 'images:196', 'images:210', 'images:219', 'images:2364', 'images:2657', 'images:666',
            'inform:9', 'java:19', 'java:49', 'java:51', 'javascript:10', 'javascript:12', 'javascript:14',
            'javascript:16', 'javascript:22', 'javascript:26', 'javascript:30', 'javascript:34',
            'javascript:38', 'javascript:42', 'javascript:46', 'javascript:50', 'javascript:54', 'javascript:6',
            'javascript:60', 'javascript:8', 'json:12', 'json:6', 'k9:28', 'kde:10', 'kde:6', 'kde:8', 'kml:9',
            'lex:10', 'lex:12', 'lex:7', 'linux:366', 'linux:369', 'linux:370', 'linux:54', 'linux:938',
            'lisp:16', 'lisp:18', 'lisp:20', 'lisp:22', 'lisp:24', 'lisp:26', 'lisp:77', 'lua:11', 'lua:13',
            'lua:15', 'lua:17', 'lua:9', 'm4:5', 'm4:8', 'macintosh:14', 'magic:8', 'mail.news:11',
            'mail.news:13', 'mail.news:15', 'mail.news:17', 'mail.news:19', 'mail.news:21', 'mail.news:23',
            'mail.news:25', 'mail.news:27', 'mail.news:29', 'mail.news:31', 'mail.news:33', 'mail.news:35',
            'mail.news:49', 'mail.news:7', 'mail.news:9', 'make:15', 'make:19', 'make:6', 'mathematica:21',
            'mime:6', 'mime:8', 'misctools:104', 'misctools:6', 'misctools:99', 'msdos:26', 'msdos:28',
            'msdos:9', 'msx:79', 'mup:13', 'nim-lang:7', 'os2:204', 'os2:9', 'pascal:5', 'pdf:45', 'perl:10',
            'perl:12', 'perl:14', 'perl:16', 'perl:18', 'perl:20', 'perl:22', 'perl:24', 'perl:36', 'perl:40',
            'perl:47', 'perl:48', 'perl:49', 'perl:50', 'perl:51', 'perl:52', 'perl:53', 'perl:54', 'perl:8',
            'psl:9', 'python:250', 'python:253', 'python:256', 'python:262', 'python:271', 'python:277',
            'python:295', 'python:303', 'python:309', 'python:9', 'qt:13', 'revision:7', 'ringdove:12',
            'ringdove:13', 'ringdove:14', 'ringdove:15', 'ringdove:16', 'ringdove:17', 'ringdove:18',
            'ringdove:19', 'ringdove:20', 'ringdove:21', 'ringdove:22', 'ringdove:25', 'ringdove:26',
            'ringdove:27', 'ringdove:28', 'ringdove:29', 'ringdove:32', 'ringdove:6', 'ringdove:7',
            'ringdove:8', 'ringdove:9', 'rst:5', 'ruby:12', 'ruby:15', 'ruby:18', 'ruby:25', 'ruby:31',
            'ruby:37', 'ruby:44', 'ruby:50', 'ruby:9', 'scientific:71', 'securitycerts:4', 'securitycerts:5',
            'sgi:137', 'sgml:102', 'sgml:105', 'sgml:108', 'sgml:111', 'sgml:115', 'sgml:121', 'sgml:128',
            'sgml:131', 'sgml:134', 'sgml:140', 'sgml:146', 'sgml:152', 'sgml:153', 'sgml:154', 'sgml:160',
            'sgml:161', 'sgml:162', 'sgml:17', 'sgml:21', 'sgml:57', 'sgml:6', 'sgml:62', 'sgml:64', 'sgml:66',
            'sgml:74', 'sgml:78', 'sgml:81', 'sgml:84', 'sgml:87', 'sgml:90', 'sgml:93', 'sgml:96', 'sgml:99',
            'sisu:11', 'sisu:14', 'sisu:17', 'sisu:5', 'sisu:8', 'sketch:6', 'softquad:26', 'sosi:30',
            'subtitle:19', 'subtitle:25', 'subtitle:32', 'tcl:11', 'tcl:13', 'tcl:15', 'tcl:17', 'tcl:19',
            'tcl:21', 'tcl:25', 'tcl:28', 'tcl:7', 'tcl:9', 'terminfo:49', 'tex:107', 'tex:108', 'tex:109',
            'tex:110', 'tex:111', 'tex:112', 'tex:113', 'tex:114', 'tex:115', 'tex:116', 'tex:117', 'tex:119',
            'tex:121', 'tex:123', 'tex:125', 'tex:127', 'tex:133', 'tex:135', 'tex:137', 'tex:139', 'tex:141',
            'tex:143', 'tex:145', 'tex:147', 'tex:149', 'tex:151', 'tex:153', 'tex:155', 'tex:157', 'tex:159',
            'tex:22', 'tex:23', 'tex:24', 'tex:25', 'tex:26', 'tex:27', 'tex:28', 'tex:29', 'tex:30', 'tex:31',
            'tex:32', 'tex:33', 'tex:34', 'tex:61', 'tex:64', 'tex:67', 'tex:70', 'tex:73', 'tex:76', 'tex:79',
            'tex:82', 'tex:85', 'tex:88', 'tex:92', 'tex:95', 'tex:96', 'tex:97', 'tex:98', 'tex:99',
            'troff:12', 'troff:15', 'troff:18', 'troff:23', 'troff:26', 'troff:31', 'troff:9', 'uuencode:11',
            'uuencode:18', 'uuencode:22', 'uuencode:26', 'varied.script:18', 'varied.script:27',
            'varied.script:8', 'windows:1313', 'windows:650', 'xwindows:39',
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
        self.assertEqual(expected_text_tests, {
            f"{test.source_info.path.name}:{test.source_info.line}"
            for test in matcher.text_tests if test.source_info is not None
        })

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

    def test_text_char_class_boundaries(self):
        """Tests the corners of the character class table against libmagic's `text_chars`."""
        classes = polyfile.magic.TEXT_CHAR_CLASSES
        self.assertEqual(256, len(classes))
        for byte in (0x00, 0x06, 0x0E, 0x19, 0x1C, 0x7F):
            self.assertEqual(polyfile.magic.TEXT_CHAR_NONE, classes[byte], f"byte {byte:#04x}")
        for byte in (0x07, 0x0B, 0x0D, 0x1A, 0x1B, 0x20, 0x7E, 0x85):
            self.assertEqual(polyfile.magic.TEXT_CHAR_ASCII, classes[byte], f"byte {byte:#04x}")
        for byte in (0x80, 0x84, 0x86, 0x9F):
            self.assertEqual(polyfile.magic.TEXT_CHAR_EXTENDED, classes[byte], f"byte {byte:#04x}")
        for byte in (0xA0, 0xE9, 0xEA, 0xFF):
            self.assertEqual(polyfile.magic.TEXT_CHAR_ISO_8859, classes[byte], f"byte {byte:#04x}")

    def test_text_character_classes(self):
        """Tests that text membership follows libmagic's character classes, not chardet's guess."""
        self.assertEqual("ascii", polyfile.magic.detect_text_encoding(b"plain ASCII\n"))
        self.assertEqual("utf-8", polyfile.magic.detect_text_encoding("héllo wörld".encode()))
        utf16 = b"\xff\xfe" + "hi".encode("utf-16-le")
        self.assertEqual("utf-16le", polyfile.magic.detect_text_encoding(utf16))
        self.assertEqual("unknown-8bit", polyfile.magic.detect_text_encoding(b"text\x80\x9f"))
        self.assertIsNone(polyfile.magic.detect_text_encoding(b"text\x00\x01\x02"))
        self.assertIsNone(polyfile.magic.detect_text_encoding(b"a"))

    def test_iso_8859_text_is_not_binary(self):
        """Tests that mostly-ASCII data with a handful of ISO-8859-1 high bytes matches text/plain.

        This is a regression test for trailofbits/polyfile#3468. chardet scores this data at a
        confidence of 0.07 because five high bytes cannot distinguish ISO-8859-1 from its
        siblings, so PolyFile used to report application/octet-stream where `file` reports
        text/plain.
        """
        data = (
            b"; imports with IAT inside descriptors\r\n"
            b"; Ange Albertini, BSD LICENCE 2011-2013\r\n"
            b"%include 'consts.inc'\r\n"
            b"        ; Mais elle n'a pas r\xe9ussi a laminer tes rancoeurs dialectiques\r\n"
            b"        ; et \xe9radiquer les tentacules de la d\xe9r\xe9liction...\r\n"
            b"        ; ok, j'arr\xeate de boire...\r\n"
        )
        self.assertEqual("iso-8859-1", polyfile.magic.detect_text_encoding(data))
        mimetypes = {
            mimetype
            for match in MagicMatcher.DEFAULT_INSTANCE.match(data)
            for mimetype in match.mimetypes
        }
        self.assertIn("text/plain", mimetypes)

    @staticmethod
    def messages(matcher: MagicMatcher, data: bytes) -> Set[str]:
        return {str(match) for match in matcher.match(data)}

    def only_match(self, data: bytes, message: str):
        matches = [
            match for match in MagicMatcher.DEFAULT_INSTANCE.match(data) if str(match) == message
        ]
        self.assertEqual(
            1, len(matches),
            f"expected {message!r}, but got {self.messages(MagicMatcher.DEFAULT_INSTANCE, data)!r}"
        )
        return matches[0]

    def test_newline_delimited_json(self):
        """Tests that a buffer holding more than one top-level JSON value matches NDJSON.

        This is a regression test for trailofbits/polyfile#3486. `JSONTest` parsed the whole
        buffer with a single `json.loads` call, which rejects `{}\\n{}\\n` as extra data, so
        PolyFile reported `ascii text` where `file` reports `New Line Delimited JSON text data`.
        """
        match = self.only_match(b"{}\n{}\n", "New Line Delimited JSON text data")
        self.assertEqual(["application/x-ndjson"], list(match.mimetypes))

    def test_single_json_value(self):
        """Tests that a single top-level JSON value still matches plain JSON rather than NDJSON."""
        match = self.only_match(b'{"a": [1, 2]}\n', "JSON text data")
        self.assertEqual(["application/json"], list(match.mimetypes))

    def test_json_messages_are_not_shared(self):
        """Tests that matching NDJSON does not change what a later plain JSON match reports.

        A `MagicMatcher` reuses its test objects across calls to `match`, so deriving the NDJSON
        message by assigning to `MagicTest.message` made every JSON file matched after the first
        NDJSON file report `New Line Delimited JSON text data`.
        """
        matcher = MagicMatcher.DEFAULT_INSTANCE
        self.assertIn("New Line Delimited JSON text data", self.messages(matcher, b"{}\n{}\n"))
        plain = self.messages(matcher, b"{}")
        self.assertIn("JSON text data", plain)
        self.assertNotIn("New Line Delimited JSON text data", plain)

    def test_json_values_must_share_a_first_byte(self):
        """Tests that top-level JSON values with different first bytes are not NDJSON.

        libmagic only continues past the first value if the next byte equals the first byte of
        that value (`*ouc == *uc` in `file/src/is_json.c`), so `{}\\n[]\\n` is plain text.
        """
        messages = self.messages(MagicMatcher.DEFAULT_INSTANCE, b"{}\n[]\n")
        self.assertNotIn("New Line Delimited JSON text data", messages)
        self.assertNotIn("JSON text data", messages)
        self.assertIn("ASCII text", messages)

    def test_bare_json_scalar_is_not_json(self):
        """Tests that a bare top-level scalar is not JSON.

        libmagic only reports JSON when it saw an object or an array (`st[JSON_OBJECT]` or
        `st[JSON_ARRAYN]` in `file/src/is_json.c`), so `42` is plain text even though
        `json.loads` accepts it.
        """
        messages = self.messages(MagicMatcher.DEFAULT_INSTANCE, b"42")
        self.assertNotIn("JSON text data", messages)

    def test_der_certificate(self):
        with gzip.open(DER_CERTIFICATE, "rb") as f:
            certificate = f.read()
        match = self.only_match(certificate, "Certificate, Version=3")
        self.assertEqual(["application/pkix-cert"], list(match.mimetypes))

    def test_der_certificate_request(self):
        request = tag_length_value(
            0x30, tag_length_value(0x30, tag_length_value(0x02, b"\x00"))
        ) + b"\x00"
        match = self.only_match(request, "DER Encoded Certificate request")
        self.assertEqual(["application/pkcs10"], list(match.mimetypes))

    def test_der_pkcs7_signed_data(self):
        signed_data = tag_length_value(
            0x30, tag_length_value(0x06, bytes.fromhex("2a864886f70d010702"))
        ) + b"\x00"
        match = self.only_match(signed_data, "DER Encoded PKCS#7 Signed Data")
        self.assertEqual(["application/pkcs7-mime"], list(match.mimetypes))

    def test_der_mime_types_are_reachable(self):
        # If an upstream update to polyfile/magic_defs/der rewords a message, the prefixes in
        # polyfile.der.MIME_TYPES stop matching and PolyFile silently drops the type. Fail here
        # instead, so that whoever syncs the definitions sees it.
        for mime in dict.fromkeys(mime for _, mime in polyfile.der.MIME_TYPES):
            self.assertIn(mime, MagicMatcher.DEFAULT_INSTANCE.mimetypes)

    def test_der_walks_sibling_objects(self):
        # The "DER Encoded Key Pair" tests are three sibling `der` tests that each read the
        # object after the one their predecessor matched. A trailing byte is needed because
        # libmagic rejects a short form length whose value ends on the final byte of the input.
        key_pair = tag_length_value(0x30, b"".join((
            tag_length_value(0x02, b"\x00"),
            tag_length_value(0x02, b"\x00" + b"\xab" * 64),
            tag_length_value(0x02, bytes.fromhex("010001")),
        ))) + b"\x00"
        match = self.only_match(key_pair, "DER Encoded Key Pair, 512 bits")
        # A raw PKCS#1 key pair has no registered media type, so PolyFile assigns none.
        self.assertEqual([], list(match.mimetypes))

    def test_der_does_not_break_other_matches(self):
        # Regression test for issue #3374: the der tests used to raise NotImplementedError
        # out of match(), which aborted the search before it could report the PDF.
        for matcher in (MagicMatcher.DEFAULT_INSTANCE, MagicMatcher.parse(*MAGIC_DEFS)):
            data = zlib.decompress(ISSUE_3374_PDF)
            types = [next(iter(match.mimetypes)) for match in matcher.match(data)]
            self.assertIn("application/pdf", types)

    def test_unimplemented_test_does_not_raise(self):
        class UnimplementedTest(polyfile.magic.MagicTest):
            AUTO_REGISTER_TEST = False

            def subtest_type(self) -> polyfile.magic.TestType:
                return polyfile.magic.TestType.BINARY

            def test(self, data, absolute_offset, parent_match):
                raise NotImplementedError("this test is deliberately unimplemented")

        test = UnimplementedTest(offset=polyfile.magic.AbsoluteOffset(0), message="unimplemented")
        self.assertEqual([], list(test.match(b"any data at all")))

    def test_file_corpus(self):
        self.assertTrue(FILE_TEST_DIR.exists(), "Make sure to run `git submodule init && git submodule update` in the "
                                                "root of this repository.")

        for test in sorted(f.stem for f in FILE_TEST_DIR.glob("*.testfile")):
            with self.subTest(test=test):
                self.check_corpus_test(test)

    def check_corpus_test(self, test: str):
        """Runs one libmagic corpus test and asserts the verdict `KNOWN_FAILURES` calls for.

        Args:
            test: The stem shared by the test's `.testfile`, `.result` and sidecar files.
        """
        testfile = FILE_TEST_DIR / f"{test}.testfile"
        result = FILE_TEST_DIR / f"{test}.result"

        if not testfile.exists() or not result.exists():
            return

        print(f"Testing: {test}")
        matcher = corpus_matcher(test)
        flags = corpus_flags(test)
        if flags:
            print(f"\tlibmagic flags: -{flags}")

        expected = result.read_text()
        print(f"\tExpected: {expected!r}")

        with open(testfile, "rb") as f:
            reported = list(matcher.match(f.read()))
        matches = {str(match) for match in reported}
        if "k" in flags:
            matches.add(polyfile.magic.join_matches(reported))
        for actual in sorted(matches):
            print(f"\tActual:   {actual!r}")

        self.assert_corpus_verdict(test, expected, matches, flags)

    def assert_corpus_verdict(self, test: str, expected: str, matches: Set[str], flags: str):
        """Asserts that a corpus test passes, or that it still fails if `KNOWN_FAILURES` maps it.

        Args:
            test: The stem of the corpus test.
            expected: The contents of the test's `.result` file.
            matches: The description of every match PolyFile reported for the test file.
            flags: The libmagic flag letters from the test's `.flags` file, if it ships one.
        """
        matched = corpus_result_matches(expected, matches)
        issue = KNOWN_FAILURES.get(test)
        context = f" (libmagic ran with -{flags})" if flags else ""
        if issue is None:
            self.assertTrue(matched, (
                f"{test} does not match libmagic{context}: expected {expected!r}, but PolyFile "
                f"reported {sorted(matches)!r}. If this is a bug we have filed, add {test!r} to "
                f"KNOWN_FAILURES in tests/test_magic.py, mapped to that issue number."
            ))
        else:
            self.assertFalse(matched, (
                f"{test} now matches libmagic{context}, so issue #{issue} looks fixed. Delete "
                f"{test!r} from KNOWN_FAILURES in tests/test_magic.py so that this test keeps "
                f"checking it, and close issue #{issue} if nothing else blocks it."
            ))


MATCH_TIMEOUT_SECONDS: int = 60

MATCH_SCRIPT: str = """
import sys
from polyfile.magic import MagicMatcher
with open(sys.argv[1], "rb") as f:
    data = f.read()
for match in MagicMatcher.DEFAULT_INSTANCE.match(data):
    _ = set(match.mimetypes)
"""


class MagicMatchingRegressionTest(TestCase):
    """Regression tests for the matching hang reported in issue #3411."""

    # This header uses CRLF line endings, so the `}` that closes the class is never the last
    # character on a line and the `c-lang` C++ class test can never succeed. Reduced from the
    # file attached to issue #3411.
    CRLF_CPP_HEADER: bytes = b"\r\n".join((
        b"#ifndef MEMBLOCK_HDR",
        b"#define MEMBLOCK_HDR",
        b"",
        b"class MemBlock",
        b"{",
        b"public :",
        b"\tint len;",
        b"\tconst char *data;",
        b"\tMemBlock() : len(0), data(0) {}",
        b"\tchar operator[](int i) const { return data[i]; }",
        b"};",
        b"",
        b"#endif",
        b"",
    ))

    @staticmethod
    def mimetypes(matcher: MagicMatcher, data: bytes) -> Set[str]:
        """Collects every MIME type that `matcher` reports for `data`.

        Args:
            matcher: The matcher to run.
            data: The bytes to classify.

        Returns:
            The union of the MIME types of every match.
        """
        found: Set[str] = set()
        for match in matcher.match(data):
            found |= set(match.mimetypes)
        return found

    @staticmethod
    def counting_match(result: TestResult, count: int) -> Tuple[Match, List[TestResult]]:
        """Builds a `Match` that records each result its iterator yields.

        Args:
            result: The test result to yield repeatedly.
            count: The number of results the iterator yields before it is exhausted.

        Returns:
            The match, and the list that grows by one entry per result the match consumes.
        """
        produced: List[TestResult] = []

        def results() -> Iterator[TestResult]:
            for _ in range(count):
                produced.append(result)
                yield result

        return Match(MagicMatcher.DEFAULT_INSTANCE, MatchContext(b""), results()), produced

    def match_in_subprocess(self, data: bytes, timeout: int = MATCH_TIMEOUT_SECONDS) -> float:
        """Matches `data` in a subprocess, so that a hang fails the test instead of stalling CI.

        Args:
            data: The bytes to hand to the default matcher.
            timeout: The number of seconds to wait before failing the test.

        Returns:
            The wall-clock seconds the subprocess took.
        """
        with TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input"
            input_path.write_bytes(data)
            command = [sys.executable, "-c", MATCH_SCRIPT, str(input_path)]
            started = time.monotonic()
            try:
                subprocess.run(command, capture_output=True, check=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                self.fail(f"Matching {len(data)} bytes took longer than {timeout} seconds")
            except subprocess.CalledProcessError as e:
                error = e.stderr.decode("utf-8", "replace")
                self.fail(f"Matching {len(data)} bytes failed: {error}")
            return time.monotonic() - started

    def test_cpp_class_test_terminates(self):
        """Matching a C++ header used to backtrack exponentially in the `c-lang` class test."""
        elapsed = self.match_in_subprocess(self.CRLF_CPP_HEADER)
        print(f"Matched {len(self.CRLF_CPP_HEADER)} bytes in {elapsed:.3f} seconds")

    def test_cpp_class_test_semantics(self):
        """The rewritten `c-lang` class test accepts and rejects the same sources as before."""
        for magic_def in MAGIC_DEFS:
            if magic_def.name == "c-lang":
                break
        else:
            self.fail("Could not find the c-lang definitions")
        matcher = MagicMatcher.parse(magic_def)
        source = b"class Foo {\n\tint x;\n};\n"
        self.assertIn("text/x-c++", self.mimetypes(matcher, source))
        self.assertNotIn("text/x-c++", self.mimetypes(matcher, source.replace(b"\n", b"\r\n")))

    def test_match_results_are_lazy(self):
        """Reading one result used to drain the whole result iterator."""
        data = b"#!/bin/sh\nexec cat \"$@\"\n"
        result = next(iter(MagicMatcher.DEFAULT_INSTANCE.match(data)))[0]
        match, produced = self.counting_match(result, 8)
        self.assertIs(result, match[0])
        self.assertEqual(1, len(produced))
        self.assertIs(result, match[3])
        self.assertEqual(4, len(produced))
        self.assertEqual(8, len(match))
        self.assertEqual(8, len(produced))

    def test_match_truthiness_is_lazy(self):
        """`bool(match)` used to match the whole subtree before it could answer."""
        result = next(iter(MagicMatcher.DEFAULT_INSTANCE.match(b"plain ASCII text\n")))[0]
        self.assertIsNotNone(result.test.mime, "bool() stops at the first result of a MIME match")
        match, produced = self.counting_match(result, 8)
        self.assertTrue(match)
        self.assertEqual(1, len(produced))

    def test_search_honors_its_repetition_limit(self):
        """libmagic's `search/N` tries `N` start offsets; PolyFile used to scan the whole buffer."""
        search = SearchType.parse("search/8192")
        self.assertEqual(8192, search.repetitions)
        expected = search.parse_expected("needle")
        self.assertEqual(8192, expected.num_bytes)
        self.assertTrue(search.match(b"." * 8000 + b"needle", expected))
        self.assertFalse(search.match(b"." * 9000 + b"needle", expected))


class RegexSemanticsTest(TestCase):
    """Regression tests for the `regex` data type reported in issue #3482."""

    DATA: bytes = b"aa123bb"
    """Test data whose only run of digits starts at offset 2 and ends at offset 5."""

    @staticmethod
    def relative_offset_definition(flags: str, follow_up: str) -> str:
        """Builds a definition whose second test reads at `&0` after a regex match.

        Args:
            flags: The flags to append to the `regex` type, such as `/s`.
            follow_up: The string that the second test expects to find at `&0`.

        Returns:
            The contents of a libmagic definition file.
        """
        return f"0\tregex{flags}\t=[0-9]{{1,3}}\tdigits\n>&0\tstring\t{follow_up}\tthen\n"

    @staticmethod
    def messages(definition: str, data: bytes) -> Set[str]:
        """Classifies `data` with a matcher built from a single magic definition.

        Args:
            definition: The contents of a libmagic definition file.
            data: The bytes to classify.

        Returns:
            The message of every match. A level 0 `regex` is a text test, so each message carries
            the text-encoding description that `TextEncodingDescription` appends, exactly as
            `file -b -m <definition>` prints it.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "regex_semantics"
            path.write_text(definition)
            matcher = MagicMatcher.parse(path)
        return {str(match) for match in matcher.match(data)}

    def test_regex_strips_the_equality_operator(self):
        """A leading `=` used to compile into the pattern, so such a test could never match.

        libmagic consumes the relation operator before it compiles the pattern
        (`file/src/apprentice.c:2383-2384`). 40 `=`-prefixed regex tests ship in the definitions,
        among them the `netpbm` chain that `file/tests/pnm2.testfile` exercises.
        """
        regex = RegexType.parse("regex")
        self.assertEqual(b"^[0-9]{1,50}", regex.parse_expected("=\\^[0-9]{1,50}").pattern)
        self.assertTrue(regex.match(self.DATA, regex.parse_expected("=[0-9]{1,3}")))

    def test_regex_strips_and_applies_the_negation_operator(self):
        """A leading `!` is a relation, so a non-matching regex is the successful test."""
        regex = RegexType.parse("regex/100l")
        expected = regex.parse_expected(r"!\^[^Cc\ \t].*$")

        self.assertEqual(b"^[^Cc \t].*$", expected.pattern)
        self.assertEqual("!", regex.relation(expected))
        self.assertFalse(regex.match(b"program\n", expected))
        self.assertTrue(regex.match(b"C comment\n", expected))
        self.assertEqual({"FORTRAN program, ASCII text"},
                         self.messages("0\tregex/100l\t!\\^[^Cc\\ \\t].*$\tFORTRAN program\n",
                                       b"C comment\n"))

    def test_regex_reads_only_one_relational_operator(self):
        """`!=foo` is the `!` relation over the pattern `=foo`, not a negated `foo`.

        libmagic reads one operator off the front of the value and compiles the rest
        (`file/src/apprentice.c:2383-2393`), so the `=` of a `!=` is a literal character of the
        pattern. Stripping both made `!=abc` reject an input that libmagic accepts. The expected
        column below is what `file -b` reports for each definition and input.
        """
        for specification, expected_pattern, accepted, rejected in (
                ("abc", b"abc", (b"abc\n", b"=abc\n"), (b"zzz\n",)),
                ("=abc", b"abc", (b"abc\n", b"=abc\n"), (b"zzz\n",)),
                ("!abc", b"abc", (b"zzz\n",), (b"abc\n", b"=abc\n")),
                ("!=abc", b"=abc", (b"abc\n", b"zzz\n"), (b"=abc\n",)),
        ):
            with self.subTest(specification=specification):
                regex = RegexType.parse("regex")
                self.assertEqual(expected_pattern, regex.parse_expected(specification).pattern)
                definition = f"0\tregex\t{specification}\tHIT\n"
                for data in accepted:
                    self.assertIn("HIT", " ".join(self.messages(definition, data)), repr(data))
                for data in rejected:
                    self.assertNotIn("HIT", " ".join(self.messages(definition, data)), repr(data))

    def test_regex_reports_only_the_matched_extent(self):
        """`%s` used to report every byte from offset 0 through the end of the match.

        libmagic reports only the bytes between `rm_so` and `rm_eo`
        (`file/src/softmagic.c:2413-2416`), and positions the match at `rm_so` rather than at the
        offset the test ran at.
        """
        regex = RegexType.parse("regex")
        match = regex.match(self.DATA, regex.parse_expected("=[0-9]{1,3}"))
        self.assertEqual(b"123", match.raw_match)
        self.assertEqual("123", match.value)
        self.assertEqual(2, match.initial_offset)
        self.assertEqual({"digits 123, ASCII text, with no line terminators"},
                         self.messages("0\tregex\t=[0-9]{1,3}\tdigits %s\n", self.DATA))

    def test_regex_relative_offset_resolves_from_the_match_end(self):
        """A `&` offset after a plain `regex` reads from the end of the match, at offset 5."""
        self.assertEqual({"digits then, ASCII text, with no line terminators"},
                         self.messages(self.relative_offset_definition("", "bb"), self.DATA))
        self.assertEqual({"digits, ASCII text, with no line terminators"},
                         self.messages(self.relative_offset_definition("", "123"), self.DATA))

    def test_regex_s_relative_offset_resolves_from_the_match_start(self):
        """The `s` flag was parsed and then never read, so `&` resolved from the match end.

        `CHAR_REGEX_OFFSET_START` (`file/src/file.h:419`) makes a following relative offset
        resolve from the start of the match, at offset 2 rather than offset 5
        (`file/src/softmagic.c:959-963`).
        """
        self.assertEqual({"digits then, ASCII text, with no line terminators"},
                         self.messages(self.relative_offset_definition("/s", "123"), self.DATA))
        self.assertEqual({"digits, ASCII text, with no line terminators"},
                         self.messages(self.relative_offset_definition("/s", "bb"), self.DATA))


class StringDataTypeTest(TestCase):
    """Regression tests for the `string` data type defects reported in issue #3483."""

    @staticmethod
    def messages(definition: str, data: bytes) -> Set[str]:
        """Runs a single magic definition against `data`.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match.
        """
        with TemporaryDirectory() as tmp_dir:
            magic_file = Path(tmp_dir) / "test.magic"
            magic_file.write_text(definition)
            matcher = MagicMatcher.parse(magic_file)
            return {str(match) for match in matcher.match(data)}

    def test_optional_blanks_reach_the_matcher(self):
        """`StringType.parse_expected` dropped the `w` flag, so `#!\\ ` needed a literal space.

        This is what `magic_defs/varied.script` relies on to report both `#!/usr/bin/cmd` and
        `#! /usr/bin/cmd`.
        """
        shebang = StringType.parse("string/wt")
        self.assertTrue(shebang.optional_blanks)
        expected = shebang.parse_expected("#!\\ ")
        self.assertTrue(expected.optional_blanks)
        for data in (b"#!/usr/bin/x", b"#! /usr/bin/x", b"#!\t/usr/bin/x", b"#!  \t/usr/bin/x"):
            self.assertTrue(shebang.match(data, expected), repr(data))
        self.assertFalse(shebang.match(b"#x/usr/bin/x", expected))

    def test_optional_blanks_accept_any_whitespace(self):
        """`w` was rendered as one optional literal space, so a tab or a run of blanks failed.

        libmagic consumes a run of any whitespace, of any length including none, wherever the magic
        value holds a blank (`file/src/softmagic.c:2116-2120`).
        """
        blanks = StringType.parse("string/w")
        space_in_value = blanks.parse_expected("A\\ B")
        for data in (b"AB", b"A B", b"A  B", b"A\tB", b"A \t B"):
            self.assertTrue(blanks.match(data, space_in_value), repr(data))
        self.assertFalse(blanks.match(b"AxB", space_in_value))
        self.assertTrue(blanks.match(b"AB", blanks.parse_expected("A\\tB")))

    def test_compact_whitespace_wins_over_optional_blanks(self):
        """`StringMatch` raised when a definition set both `W` and `w`, as `magic_defs/sgml` does.

        libmagic keeps both bits and lets `W` win, because `file_strncmp` tests it first
        (`file/src/softmagic.c:2103-2120`).
        """
        both = StringType.parse("string/Ww")
        self.assertTrue(both.compact_whitespace)
        self.assertTrue(both.optional_blanks)
        expected = both.parse_expected("A\\ B")
        self.assertTrue(both.match(b"A  B", expected))
        self.assertFalse(both.match(b"AB", expected))

    def test_search_b_flag_is_not_optional_blanks(self):
        """`search/…b…` was read as optional blanks; `b` selects the binary pass.

        `CHAR_BINTEST` is `b` and `CHAR_COMPACT_OPTIONAL_WHITESPACE` is `w`
        (`file/src/file.h:416` and `423`).
        """
        binary_test = SearchType.parse("search/100/b")
        self.assertFalse(binary_test.optional_blanks)
        self.assertFalse(binary_test.compact_whitespace)
        sgml = SearchType.parse("search/4096/cWbt")
        self.assertTrue(sgml.compact_whitespace)
        self.assertFalse(sgml.optional_blanks)

    def test_string_relative_base_is_the_declared_length(self):
        """`>&-1` under a `string/w` read one byte early when `w` matched no blanks.

        libmagic's `moffset` adds the declared length of the magic value, not the number of bytes
        the match consumed (`file/src/softmagic.c:904-905`), which is what lets one definition
        cover both `#!/bin/x` and `#! /bin/x`.
        """
        definition = "0\tstring/w\t#!\\ \tshebang\n>&-1\tstring\tx\t%s\n"
        self.assertEqual({"shebang /bin/x"}, self.messages(definition, b"#!/bin/x\n"))
        self.assertEqual({"shebang  /bin/x"}, self.messages(definition, b"#! /bin/x\n"))
        self.assertEqual({"shebang \t/bin/x"}, self.messages(definition, b"#!\t/bin/x\n"))

    def test_search_relative_base_starts_where_it_found_its_value(self):
        """A `search` resolves a relative offset from where it found its value, not from where it
        started looking (`file/src/softmagic.c:966-968`).

        Measuring from the start of the search instead turned `gedcom.testfile`'s message into
        `GEDCOM genealogy text version 2 VERS 2.x`.
        """
        definition = "0\tsearch/16\tVERS\tversion\n>&1\tstring\tx\t%s\n"
        self.assertEqual({"version 5.5, ASCII text"},
                         self.messages(definition, b"xxx VERS 5.5\nnext line\n"))

    def test_wildcard_string_stops_at_a_line_break(self):
        """A wildcard value ran to the first null byte, so a `%s` leaked the rest of the file.

        libmagic cuts it at the first carriage return or line feed
        (`file/src/softmagic.c:683-684`) and reads at most `MAXstring` bytes
        (`file/src/file.h:179`).
        """
        wildcard = StringType.parse("string").parse_expected("x")
        self.assertEqual(b"first", wildcard.matches(b"first\nsecond").raw_match)
        self.assertEqual(b"first", wildcard.matches(b"first\r\nsecond").raw_match)
        self.assertEqual(b"first", wildcard.matches(b"first\0second").raw_match)
        self.assertEqual(b"a" * 128, wildcard.matches(b"a" * 300).raw_match)

    def test_gedcom_reports_one_version_and_not_four_lines(self):
        """`magic_defs/scientific`'s `%s` reported four lines of `gedcom.testfile`."""
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        data = (FILE_TEST_DIR / "gedcom.testfile").read_bytes()
        messages = {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
        self.assertEqual({"GEDCOM genealogy text version 5.5, ASCII text"}, messages)

    def test_pstring_forwards_its_string_flags(self):
        """`PascalStringType` dropped every string flag, and rejected a declaration carrying one.

        libmagic accepts the string modifiers on `pstring` (`file/src/apprentice.c:1943-2020`).
        """
        trimming = DataType.parse("pstring/BT")
        self.assertEqual("hi", trimming.match(b"\x06  hi  ", trimming.parse_expected("x")).value)
        verbatim = DataType.parse("pstring/B")
        untrimmed = verbatim.match(b"\x06  hi  ", verbatim.parse_expected("x"))
        self.assertEqual("  hi  ", untrimmed.value)


class SearchTextClassificationTest(TestCase):
    r"""Regression tests for the pass classification defect reported in issue #3511.

    `StringMatch.is_always_text` looked for the two-character sequences `\x` and `\0` in the raw,
    still-escaped value, so a `search` that escapes a space as `\040` was classified binary and ran
    in PolyFile's binary pass. libmagic decides from `file_looks_utf8` over the value it unescaped
    while parsing (`file/src/apprentice.c:1277-1283`), and `file -l` lists every definition named
    here under `Text patterns`.
    """

    @staticmethod
    def runs_in_text_pass(definition: str) -> bool:
        """Whether PolyFile runs the one level-0 test of `definition` in its text pass.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.

        Returns:
            True if the test landed in the text pass, False if it landed in the binary pass.
        """
        with TemporaryDirectory() as tmp_dir:
            magic_file = Path(tmp_dir) / "test.magic"
            magic_file.write_text(definition)
            matcher = MagicMatcher.parse(magic_file)
            text, binary = matcher.text_tests, matcher.non_text_tests
        assert len(text) + len(binary) == 1, f"expected one test, got {len(text) + len(binary)}"
        return bool(text)

    def test_an_escaped_space_is_a_space(self):
        r"""Tests that `\040` no longer reads as an escaped null byte.

        This is the defect itself: the raw value `diff\040` contains the two characters `\0`, so
        the old rule called it binary even though the byte it stands for is a space.
        """
        self.assertTrue(self.runs_in_text_pass("0\tsearch/1\tdiff\\040\tdiff output text\n"))

    def test_an_escaped_line_feed_is_a_text_character(self):
        r"""Tests that `\012` is text, which is what moves `uuencode:22` into the text pass.

        A line feed is `T` in libmagic's `text_chars` table (`file/src/encoding.c:246-266`), so a
        value that contains one still looks like text.
        """
        self.assertTrue(self.runs_in_text_pass("0\tsearch/1\t$\\012ship\tship'd binary text\n"))

    def test_a_hexadecimal_space_is_a_space(self):
        r"""Tests that `\x20` is text, which is what moves `javascript:22` into the text pass."""
        definition = "0\tsearch\t\"use\\x20strict\"\tJavaScript source\n"
        self.assertTrue(self.runs_in_text_pass(definition))

    def test_utf8_is_text(self):
        r"""Tests that a value of valid multi-byte UTF-8 is text.

        `file_looks_utf8` returns 2 rather than 1 for such a value, and `set_test_type` compares
        its result against 0, so both count as text.
        """
        self.assertTrue(self.runs_in_text_pass("0\tsearch/1\tcaf\\xc3\\xa9\tcafe\n"))

    def test_a_null_byte_is_not_text(self):
        r"""Tests that a genuine null byte still classifies a value as binary.

        A null byte is `F` in libmagic's `text_chars` table, so `file_looks_utf8` returns 0 for a
        value that contains one, whichever escape the definition spelled it with.
        """
        self.assertFalse(self.runs_in_text_pass("0\tsearch/1\ta\\x00b\tnull byte\n"))
        self.assertFalse(self.runs_in_text_pass("0\tsearch/1\ta\\0b\tnull byte\n"))

    def test_a_control_character_is_not_text(self):
        r"""Tests that a control character outside libmagic's text class is binary.

        `\001` is `F` in the `text_chars` table, unlike the `\012` above, so a value carrying it
        must stay in the binary pass even though the escape spells no null byte.
        """
        self.assertFalse(self.runs_in_text_pass("0\tsearch/1\ta\\001b\tcontrol character\n"))

    def test_a_high_byte_that_is_not_utf8_is_not_text(self):
        r"""Tests that a high byte which cannot begin a UTF-8 sequence is binary.

        `file_looks_utf8` returns -1 for `\xff`, which never appears in valid UTF-8.
        """
        self.assertFalse(self.runs_in_text_pass("0\tsearch/1\ta\\xffb\thigh byte\n"))

    def test_the_shipped_python_and_diff_definitions_are_text_tests(self):
        """Tests that the two shipped definitions the issue names land in the text pass.

        `python:256` matches a `#!/usr/bin/env python` shebang and `diff:13` matches `diff`
        output; both escape a space, so both ran in the binary pass and were never described.
        """
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        text_tests = {
            (test.source_info.path.name, test.source_info.line)
            for test in matcher.text_tests if test.source_info is not None
        }
        self.assertIn(("python", 256), text_tests)
        self.assertIn(("diff", 13), text_tests)

    def test_a_binary_flagged_search_is_not_text(self):
        r"""Tests that an explicit `b` flag outranks a value that looks like text.

        `set_test_type` sets `BINTEST` from the declared string flags and breaks out of the case
        before it reaches `file_looks_utf8` (`file/src/apprentice.c:1258-1283`), so `gimp:67`,
        whose value is the text-looking `\040ncells:`, is listed under `Binary patterns` by
        `file -l`. Honoring the value alone moved it into the text pass, where it never ran for
        the binary files it exists to identify.
        """
        self.assertFalse(self.runs_in_text_pass("0\tsearch/21/b\t\\040ncells:\tbrush\n"))
        self.assertTrue(self.runs_in_text_pass("0\tsearch/21\t\\040ncells:\tbrush\n"))

    def test_the_binary_flag_is_part_of_a_search_type_s_name(self):
        """Tests that a `b`-flagged search does not share a cached type with a plain one.

        `DataType.parse` keys `TYPES_BY_NAME` on the type's name, so a flag missing from the name
        makes whichever declaration is parsed second reuse the first one's instance and silently
        adopt its flags.
        """
        flagged = DataType.parse("search/21/b")
        self.assertTrue(flagged.force_binary)
        self.assertFalse(DataType.parse("search/21").force_binary)
        self.assertIs(flagged, DataType.parse("search/b/21"))

    def test_a_gimp_animated_brush_is_still_detected(self):
        """Tests that a `.gih`-shaped buffer keeps its match once the value rule changed.

        A GIMP animated brush is a name line and a parameter line followed by binary brush data,
        so the buffer is not text and PolyFile's text pass never runs for it. With `gimp:67` in
        the text pass the format went undetected. `file -b` reports the string asserted here.
        """
        brush = b"confetti\n ncells:4 rank0:4\n" + bytes(range(256)) * 4
        messages = {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(brush)}
        self.assertIn("GIMP animated brush data", messages)

    def test_an_env_python_script_is_described(self):
        """Tests that a `#!/usr/bin/env python` script gains libmagic's encoding description.

        `file -b` reports `Python script, ASCII text executable` for this input. PolyFile reported
        the undescribed `Python script text executable`, because the test that matched ran in the
        binary pass and `file_ascmagic` never sees a binary match (`file/src/funcs.c:479-503`).
        """
        script = b'#!/usr/bin/env python\nimport sys\nprint("hi")\n'
        messages = {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(script)}
        self.assertIn("Python script, ASCII text executable", messages)
        self.assertNotIn("Python script text executable", messages)


class UseTestSemanticsTest(TestCase):
    """Regression tests for the `use` test truth value reported in issue #3484."""

    DESCRIBED_NAMED_LIST: str = "\n".join((
        "0\tname\ttrailer",
        ">4\tstring\tOK\t\\b, named list matched",
        "",
        "0\tstring\tHEAD",
        ">0\tuse\ttrailer",
        ">>0\tstring\tx\t\\b, continuation ran",
        "",
    ))
    """A `use` whose named list prints a message when the input ends in `OK`."""

    UNDESCRIBED_NAMED_LIST: str = "\n".join((
        "0\tname\ttrailer",
        ">4\tstring\tOK",
        "",
        "0\tstring\tHEAD",
        ">0\tuse\ttrailer",
        ">>0\tstring\tx\t\\b, continuation ran",
        "",
    ))
    """The same definitions, with the named list's only entry left undescribed."""

    @staticmethod
    def messages(definitions: str, data: bytes) -> Set[str]:
        """Matches `data` against ad-hoc definitions and collects the resulting messages.

        Args:
            definitions: The contents of a libmagic definition file, with tab separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match the definitions produce.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "use_semantics"
            path.write_text(definitions)
            matcher = MagicMatcher.parse(path)
            return {str(match) for match in matcher.match(data)}

    def test_use_matches_when_the_named_list_matches(self):
        """A `use` succeeds when its named list prints something, and its children then run.

        `file -b -k -m <definitions>` reports both `, named list matched` and
        `, continuation ran` for this input.
        """
        self.assertIn(
            ", named list matched, continuation ran", self.messages(self.DESCRIBED_NAMED_LIST, b"HEADOK")
        )

    def test_use_fails_when_the_named_list_does_not_match(self):
        """A `use` used to succeed even when its named list matched nothing.

        The named list's only entry needs the input to end in `OK`, so nothing in it matches
        `HEADNO`. libmagic returns the list's match count as the `use`'s truth value
        (`file/src/softmagic.c:2429-2430`) and reports no match for this input, but PolyFile used
        to run the `use`'s continuation lines anyway.
        """
        for message in self.messages(self.DESCRIBED_NAMED_LIST, b"HEADNO"):
            self.assertNotIn("named list matched", message)
            self.assertNotIn("continuation ran", message)

    def test_use_fails_when_the_named_list_prints_nothing(self):
        """An undescribed named test cannot on its own satisfy the `use` that referenced it.

        libmagic raises `found_match` only for an entry with a non-empty description
        (`file/src/softmagic.c:323` and `:439`), so neither the bare `0 name trailer` line nor the
        undescribed entry beneath it counts. `file` reports no match for `HEADOK` against these
        definitions, even though the same input matches once that entry carries a message.
        """
        for message in self.messages(self.UNDESCRIBED_NAMED_LIST, b"HEADOK"):
            self.assertNotIn("continuation ran", message)

    def test_efi_signature_list_is_not_a_false_positive(self):
        """The `efi_sig_list` `use` used to report EFI matches for UTF-16 text.

        `polyfile/magic_defs/efi:41-53` guards two `use efi_sig_list` entries behind zero-byte
        tests that any UTF-16LE ASCII text passes, and relies on the named list's 19 `guid`
        comparisons to reject. None of them match this file, and
        `file -m file/magic/Magdir/efi` reports no EFI match for it.
        """
        testfile = FILE_TEST_DIR / "utf16xmlsvg.testfile"
        self.assertTrue(testfile.exists(), "Make sure to run `git submodule init && git submodule update`")
        for match in MagicMatcher.DEFAULT_INSTANCE.match(testfile.read_bytes()):
            self.assertNotIn("EFI variable", str(match))
            self.assertNotIn("total size", str(match))


class TestStrengthTest(TestCase):
    """Regression tests for the strength computation reported in issue #3477.

    `MagicTest.base_strength` used to return a constant 20, so 96% of the shipped tests tied and
    the sort that orders them by specificity had almost no key to work with. Each test here pins
    one term of libmagic's `apprentice_magic_strength_1` and `file_magic_strength`
    (`file/src/apprentice.c:925-1120`), checked against what `file -l` prints.
    """

    @staticmethod
    def only_test(definition: str) -> polyfile.magic.MagicTest:
        """Parses `definition` and returns its single level-0 test.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.

        Returns:
            The one test the definition declares at level 0.
        """
        with TemporaryDirectory() as tmp_dir:
            magic_file = Path(tmp_dir) / "test.magic"
            magic_file.write_text(definition)
            matcher = MagicMatcher.parse(magic_file)
            tests = matcher.text_tests | matcher.non_text_tests
        assert len(tests) == 1, f"expected one test, got {len(tests)}"
        return next(iter(tests))

    def strength(self, definition: str) -> int:
        """The strength of the single level-0 test that `definition` declares."""
        return self.only_test(definition).compute_strength()

    def test_numeric_types_score_by_their_width(self):
        """Every test scored 20, so a `bequad` sorted level with a `byte`.

        libmagic adds `typesize(type) * MULT` for a numeric, date, or GUID type
        (`file/src/apprentice.c:975-996`), on top of the 20 baseline and the 10 an `=` earns. The
        expected values are what `file -l` reports for these definitions.
        """
        for data_type, expected in (
                ("byte", 40), ("leshort", 50), ("lelong", 70), ("lequad", 110),
                ("float", 70), ("double", 110), ("date", 70), ("qdate", 110),
                ("msdosdate", 50), ("msdostime", 50),
        ):
            self.assertEqual(expected, self.strength(f"0\t{data_type}\t1\tdesc\n"), data_type)

    def test_guid_scores_as_sixteen_bytes(self):
        """A `guid` is the widest type libmagic sizes, at 16 bytes."""
        self.assertEqual(
            190, self.strength("0\tguid\t00000000-0000-0000-0000-000000000000\tdesc\n"))

    def test_der_scores_one_flat_unit(self):
        """`der` adds a single unit whatever its specification (`file/src/apprentice.c:1024`)."""
        self.assertEqual(40, self.strength("0\tder\tseq\tdesc\n"))

    def test_string_scores_one_unit_per_byte(self):
        """A constant 20 made a one-byte `string` as strong as an eight-byte one.

        libmagic adds `vallen * MULT`, counting the value after unescaping
        (`file/src/apprentice.c:998-1000`), which is the dominant term for most definitions.
        """
        self.assertEqual(40, self.strength("0\tstring\tA\tdesc\n"))
        self.assertEqual(110, self.strength("0\tstring\tbplist00\tdesc\n"))
        self.assertEqual(70, self.strength("0\tstring\t\\x02\\x01\\x13\\x13\tdesc\n"))

    def test_pstring_counts_its_length_prefix(self):
        """`getstr` folds the prefix width into `vallen` (`file/src/apprentice.c:3181-3188`)."""
        self.assertEqual(80, self.strength("0\tpstring\tabcd\tdesc\n"))
        self.assertEqual(90, self.strength("0\tpstring/H\tabcd\tdesc\n"))
        self.assertEqual(110, self.strength("0\tpstring/l\tabcd\tdesc\n"))

    def test_string16_scores_half_of_a_string(self):
        """libmagic halves the term for a sixteen-bit string (`file/src/apprentice.c:1003`)."""
        self.assertEqual(50, self.strength("0\tlestring16\tabcd\tdesc\n"))

    def test_search_credits_at_most_one_unit_per_value(self):
        """A `search` roams the buffer, so libmagic caps its credit.

        `vallen * MAX(MULT / vallen, 1)` (`file/src/apprentice.c:1008-1012`) is a full unit for a
        one-byte value and then flattens to one point per byte, which is why an eight-byte
        `search` scores 38 where the same `string` scores 110.
        """
        self.assertEqual(40, self.strength("0\tsearch/8192\tA\tdesc\n"))
        self.assertEqual(40, self.strength("0\tsearch/8192\tAB\tdesc\n"))
        self.assertEqual(38, self.strength("0\tsearch/8192\t#include\tdesc\n"))
        self.assertEqual(43, self.strength("0\tsearch/512\t@opaque(lang=\tdesc\n"))

    def test_search_range_does_not_change_its_strength(self):
        """The `search/N` range is not part of the term, contrary to a plausible reading of it."""
        for repetitions in ("1", "100", "8192"):
            self.assertEqual(38, self.strength(f"0\tsearch/{repetitions}\t#include\tdesc\n"))

    def test_regex_counts_only_its_literal_characters(self):
        """A regular expression earns nothing for its metacharacters.

        `nonmagic` (`file/src/apprentice.c:813-849`) counts escapes and literals but not `?*.+^$`,
        counts a bracketed class as the one closing bracket, and a braced repetition as nothing.
        The term is then capped the way a `search`'s is.
        """
        self.assertEqual(39, self.strength("0\tregex\tabc.*\tdesc\n"))
        self.assertEqual(38, self.strength("0\tregex\tabcd\\ efg\tdesc\n"))
        self.assertEqual(40, self.strength("0\tregex\t\\^[a-z]+\tdesc\n"))

    def test_regex_literals_are_counted_before_the_posix_rewrite(self):
        """PolyFile rewrites POSIX classes to Python ones, which used to lose a literal each.

        libmagic scans `[[:space:]]` and stops its bracket scan at the inner `:]`, so the trailing
        `]` counts as a second literal; the rewritten `[ \\t\\n\\r\\f\\v]` offers only one. Thirteen
        shipped definitions differed by up to four points before the count moved ahead of the
        rewrite. `file -l` reports 36 for the `clojure` entry below.
        """
        self.assertEqual(36, self.strength(
            "0\tregex\t\\^\\\\\\(ns[[:space:]]+[a-z]\tClojure module source text\n"))
        self.assertEqual(41, self.strength(
            "0\tregex/4006\t\\^PROC[[:space:]][a-zA-Z0-9_[:space:]]*[[:space:]]=\tdesc\n"))

    def test_regex_literal_count_ends_at_an_escaped_null(self):
        """`nonmagic` walks a C string, so a `\\000` in the value ends the count.

        `magic_defs/cad:317` is the shipped case: everything after its `\\000` is invisible to
        libmagic's count, which is why `file -l` reports 40 rather than 39.
        """
        self.assertEqual(40, self.strength("0\tregex\t\\^[\\ \\t]*0\\r?\\000$\n"))
        self.assertEqual(self.strength("0\tregex\tab\\000cdefgh\tdesc\n"),
                         self.strength("0\tregex\tab\tdesc\n"))

    def test_regex_escaped_dot_counts_nothing(self):
        """libmagic unescapes before counting, so `\\.` arrives as a bare `.` and scores zero.

        This is what its "escaped dot found, use \\\\. instead" warning is about.
        """
        self.assertEqual(self.strength("0\tregex\tab.\tdesc\n"),
                         self.strength("0\tregex\tab\\.\tdesc\n"))

    def test_relational_operators_adjust_the_strength(self):
        """Every relation scored the same 20, so a wildcard tied with an exact match.

        libmagic prefers an exact match by a unit, penalizes an inequality by two, penalizes a bit
        mask by one, and zeroes anything matching (almost) everything
        (`file/src/apprentice.c:1034-1051`). A zero is then clamped up to one.
        """
        self.assertEqual(50, self.strength("0\tleshort\t=1\tdesc\n"))
        self.assertEqual(20, self.strength("0\tleshort\t>1\tdesc\n"))
        self.assertEqual(20, self.strength("0\tleshort\t<1\tdesc\n"))
        self.assertEqual(30, self.strength("0\tleshort\t&1\tdesc\n"))
        self.assertEqual(30, self.strength("0\tleshort\t^1\tdesc\n"))
        self.assertEqual(1, self.strength("0\tleshort\t!1\tdesc\n"))
        self.assertEqual(1, self.strength("0\tleshort\tx\tdesc\n"))

    def test_string_relations_adjust_the_strength(self):
        """The string family carries its relation in the parsed value, not in a numeric operator."""
        self.assertEqual(70, self.strength("0\tstring\t=abcd\tdesc\n"))
        self.assertEqual(40, self.strength("0\tstring\t>abcd\tdesc\n"))
        self.assertEqual(40, self.strength("0\tstring\t<abcd\tdesc\n"))
        self.assertEqual(1, self.strength("0\tstring\t!abcd\tdesc\n"))
        self.assertEqual(1, self.strength("0\tstring\tx\tdesc\n"))

    def test_undescribed_test_gains_a_point(self):
        """A test with no description depends on its children to print, so libmagic favors it.

        See `file/src/apprentice.c:1111-1117`. A description of nothing but blanks counts as
        absent, because libmagic skips them before copying what remains.
        """
        self.assertEqual(70, self.strength("0\tstring\tabcd\tdesc\n"))
        self.assertEqual(71, self.strength("0\tstring\tabcd\n"))
        self.assertEqual(71, self.strength("0\tstring\tabcd\t\t\n"))

    def test_strength_modifier_applies_on_top_of_the_computed_value(self):
        """`!:strength` used to be the only thing that moved a strength off 20.

        libmagic applies the factor after the type and relation terms
        (`file/src/apprentice.c:1085-1105`), and clamps the result to at least one.
        """
        self.assertEqual(70, self.strength("0\tstring\tabcd\tdesc\n"))
        self.assertEqual(85, self.strength("0\tstring\tabcd\tdesc\n!:strength + 15\n"))
        self.assertEqual(60, self.strength("0\tstring\tabcd\tdesc\n!:strength -10\n"))
        self.assertEqual(140, self.strength("0\tstring\tabcd\tdesc\n!:strength *2\n"))
        self.assertEqual(23, self.strength("0\tstring\tabcd\tdesc\n!:strength / 3\n"))
        self.assertEqual(1, self.strength("0\tstring\tabcd\tdesc\n!:strength -200\n"))

    def test_strength_modifier_applies_to_the_entry_not_the_last_test(self):
        """A `!:strength` under a continuation line used to score the continuation instead.

        libmagic always assigns the factor to `me->mp[0]`, the level-0 test of the entry, whatever
        depth the directive appears at (`file/src/apprentice.c:2470-2478`). 55 shipped entries put
        the directive after at least one continuation, `varied.script:8` among them, where `file
        -l` reports 20 for a term that would otherwise be 60.
        """
        definition = "0\tstring/wt\t#!\\ \ta\n>&-1\tstring/T\tx\t%s script text executable\n!:strength / 3\n"
        self.assertEqual(20, self.strength(definition))

    def test_multiple_magic_sidecars_match_libmagic(self):
        """`file/tests/multiple.testfile` needs its four matches in descending strength order.

        `file -l` reports 40, 40, 38, 38 for these four `search` tests. The stem stays in
        `KNOWN_FAILURES` for unrelated reasons, so this pins the strengths on their own.
        """
        strengths = []
        for sidecar in ("multiple-A.magic", "multiple-B.magic"):
            path = FILE_TEST_DIR / sidecar
            self.assertTrue(path.exists(), "Make sure to run `git submodule init && git submodule update`")
            matcher = MagicMatcher.parse(path)
            tests = matcher.text_tests | matcher.non_text_tests
            strengths.extend(sorted((t.compute_strength() for t in tests), reverse=True))
        self.assertEqual([40, 40, 38, 38], strengths)

    def test_shipped_definitions_span_libmagic_s_range_of_strengths(self):
        """96.5% of the shipped tests used to score exactly 20, over just 29 distinct values.

        `file -l` reports 133 distinct strengths over the same definitions, from 2 to 670. This
        asserts the distribution stays in that neighborhood, so a regression to a near-constant
        key is caught even if every individual term still looks right.
        """
        tests = MagicMatcher.DEFAULT_INSTANCE.text_tests | MagicMatcher.DEFAULT_INSTANCE.non_text_tests
        strengths = [test.compute_strength() for test in tests]
        self.assertGreater(len(set(strengths)), 120)
        self.assertGreater(max(strengths), 600)
        self.assertLess(sum(1 for s in strengths if s == 20) / len(strengths), 0.05)


class TextEncodingDescriptionTest(TestCase):
    """Tests for the text description libmagic appends, reported in issue #3488.

    Every string these tests expect is what `file -b` prints for the same input, checked against
    libmagic 5.48 built from the `file` submodule.
    """

    TEXT_SUFFIX_DEFINITION: str = "0\tstring/t\tMARK\tMarked file text\n"
    """A text test whose message ends in the ` text` that libmagic splices out."""

    EXECUTABLE_DEFINITION: str = "0\tstring/t\tMARK\tMarked file text executable\n"
    """A text test whose message ends in the ` text executable` that libmagic splices out."""

    BINARY_DEFINITION: str = "0\tstring\tMARK\tMarked file text\n"
    """The same test without `t`, which libmagic runs in its binary pass and never describes."""

    @staticmethod
    def messages(definition: str, data: bytes) -> Set[str]:
        """Runs a single magic definition against `data`.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "text_encoding"
            path.write_text(definition)
            matcher = MagicMatcher.parse(path)
        return {str(match) for match in matcher.match(data)}

    def describe(self, data: bytes, message: str = "") -> str:
        """Describes `data` the way libmagic describes a match on it.

        Args:
            data: The bytes to classify.
            message: The message soft magic produced for `data`.

        Returns:
            The description libmagic reports.
        """
        description = polyfile.magic.TextEncodingDescription.detect(data)
        self.assertIsNotNone(description, f"{data!r} was not classified as text")
        return description.describe(message)

    def test_a_text_suffix_is_replaced_by_the_encoding(self):
        """Tests that a message ending in ` text` loses it before the encoding is appended.

        libmagic rewrites its output buffer with `file_replace(ms, " text$", ", ")`
        (`file/src/ascmagic.c:238`), so `Marked file text` becomes `Marked file, ASCII text` and
        not `Marked file text, ASCII text`.
        """
        self.assertEqual({"Marked file, ASCII text"},
                         self.messages(self.TEXT_SUFFIX_DEFINITION, b"MARKED\n"))

    def test_a_text_executable_suffix_keeps_its_executable(self):
        """Tests that ` text executable` is spliced out and the `executable` printed again.

        libmagic falls back to `file_replace(ms, " text executable$", ", ")` and remembers to
        print ` executable` after the encoding (`file/src/ascmagic.c:240-268`), so
        `POSIX shell script text executable` becomes `POSIX shell script, ASCII text executable`.
        """
        self.assertEqual({"Marked file, ASCII text executable"},
                         self.messages(self.EXECUTABLE_DEFINITION, b"MARKED\n"))

    def test_a_message_with_no_text_suffix_gets_a_separator(self):
        """Tests that a message that ends in neither suffix is joined with `, `.

        This is the `file_printf(ms, ", ")` fallback at `file/src/ascmagic.c:243`, which is what
        turns `OpenStreetMap XML data` into `OpenStreetMap XML data, ASCII text`.
        """
        self.assertEqual("Netpbm image data, greymap, ASCII text",
                         self.describe(b"MARKED\n", "Netpbm image data, greymap"))

    def test_a_binary_test_is_not_described(self):
        """Tests that a definition libmagic runs in its binary pass gets no description.

        `file_buffer` reaches `file_ascmagic` only when the binary soft magic pass printed nothing
        (`file/src/funcs.c:479-503`), and `set_test_type` puts a `string` with no `t` flag in that
        pass (`file/src/apprentice.c:1255-1275`). `file -b` reports `Marked file text` for this
        input, with no encoding appended.
        """
        self.assertEqual({"Marked file text"}, self.messages(self.BINARY_DEFINITION, b"MARKED\n"))

    def test_json_is_not_described(self):
        """Tests that PolyFile's JSON test keeps libmagic's undecorated verdict.

        `file_is_json` runs ahead of soft magic in `file_buffer` and its match ends the run
        (`file/src/funcs.c:410-418`), so `file` reports `JSON text data` rather than
        `JSON text data, ASCII text`.
        """
        messages = {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(b'{"a": 1}\n')}
        self.assertIn("JSON text data", messages)

    def test_encoding_names_match_libmagics_spelling(self):
        """Tests that the encoding is named as libmagic names it, in libmagic's case.

        PolyFile used to report `ascii text`, and reported chardet's guess rather than the
        character class verdict, so a UTF-16 file came out as `UTF-16 text` instead of
        `Unicode text, UTF-16, little-endian text`. The names are the `code` strings of
        `file_encoding` (`file/src/encoding.c:107-172`).
        """
        for data, expected in (
                (b"hello\n", "ASCII text"),
                ("héllo wörld\n".encode(), "Unicode text, UTF-8 text"),
                (b"\xff\xfe" + "hi\n".encode("utf-16-le"),
                 "Unicode text, UTF-16, little-endian text"),
                (b"\xfe\xff" + "hi\n".encode("utf-16-be"), "Unicode text, UTF-16, big-endian text"),
                (b"caf\xe9\n", "ISO-8859 text"),
                (b"text\x80\x9f\n", "Non-ISO extended-ASCII text")):
            with self.subTest(data=data):
                self.assertEqual(expected, self.describe(data))

    def test_line_terminators_are_named(self):
        """Tests the line-terminator clause, including the LF-only case that has none.

        libmagic reports terminators only when it finds one that is not LF, or none at all
        (`file/src/ascmagic.c:284-317`), so `a\\nb\\n` is plain `ASCII text` while `hello world`
        is `ASCII text, with no line terminators`.
        """
        for data, expected in (
                (b"hello world", "ASCII text, with no line terminators"),
                (b"a\nb\n", "ASCII text"),
                (b"a\r\nb\r\n", "ASCII text, with CRLF line terminators"),
                (b"a\rb\r", "ASCII text, with CR line terminators"),
                (b"a\x85b\x85", "ASCII text, with NEL line terminators"),
                (b"a\rb\nc\n", "ASCII text, with CR, LF line terminators"),
                (b"a\x85b\n", "ASCII text, with LF, NEL line terminators"),
                (b"a\r\nb\rc\nd\x85", "ASCII text, with CRLF, CR, LF, NEL line terminators")):
            with self.subTest(data=data):
                self.assertEqual(expected, self.describe(data))

    def test_a_trailing_cr_counts_only_when_nothing_else_does(self):
        """Tests that a CR at the end of the buffer is counted the way libmagic counts it.

        libmagic raises `n_cr` when it reads the character after a CR, so a CR that ends the
        buffer is counted only by the `seen_cr && n_cr == 0 && n_crlf == 0` fixup at
        `file/src/ascmagic.c:208-209`. `a\\r\\nb\\r` therefore reports CRLF alone, while
        `a\\nb\\r` reports both CR and LF.
        """
        self.assertEqual("ASCII text, with CRLF line terminators", self.describe(b"a\r\nb\r"))
        self.assertEqual("ASCII text, with CR, LF line terminators", self.describe(b"a\nb\r"))
        self.assertEqual("ASCII text, with CR line terminators", self.describe(b"abc\r"))

    def test_very_long_lines_are_measured(self):
        """Tests the long-line clause and the length libmagic reports for it.

        A line counts as long once it exceeds `MAXLINELEN`, which is 300 characters
        (`file/src/ascmagic.c:49` and `:198-203`), and libmagic reports the length of the longest
        one rather than the number of long lines.
        """
        self.assertEqual("ASCII text", self.describe(b"x" * 300 + b"\n"))
        self.assertEqual("ASCII text, with very long lines (301)",
                         self.describe(b"x" * 301 + b"\n"))
        self.assertEqual("ASCII text, with very long lines (350)",
                         self.describe(b"x" * 310 + b"\n" + b"y" * 350 + b"\n"))
        self.assertEqual("ASCII text, with very long lines (400), with no line terminators",
                         self.describe(b"x" * 400))

    def test_only_the_first_64_kilobytes_are_measured(self):
        """Tests that the description stops at libmagic's encoding limit.

        libmagic decodes at most `FILE_ENCODING_MAX`, 64KiB, into the buffer it scans
        (`file/src/file.h:525` and `src/encoding.c:98-99`), so a file whose first line runs past
        that point reports a 65536 character line and no line terminators at all.
        """
        self.assertEqual("ASCII text, with very long lines (65536), with no line terminators",
                         self.describe(b"a" * 70000 + b"\n" + b"b" * 400 + b"\n"))

    def test_escape_sequences_and_overstriking_are_reported(self):
        """Tests the escape and backspace clauses, and the order every clause appears in.

        `file/src/ascmagic.c:274-324` prints the long-line clause, then the line terminators, then
        `, with escape sequences` and `, with overstriking`.
        """
        self.assertEqual("ASCII text, with no line terminators, with escape sequences",
                         self.describe(b"hello \x1b[31mworld"))
        self.assertEqual("ASCII text, with overstriking", self.describe(b"he\bello\n"))
        self.assertEqual("ASCII text, with very long lines (402), with CRLF line terminators, "
                         "with escape sequences, with overstriking",
                         self.describe(b"x" * 400 + b"\x1b\b\r\n"))

    def test_a_description_belongs_to_one_match_only(self):
        """Tests that one matcher describes each buffer on its own terms.

        Test objects are shared across calls to `MagicMatcher.match`, so a description stored on a
        test would leak into every later match. PolyFile used to assign `PlainTextTest.message`
        during a match for exactly this reason, and only got away with it because
        `MagicMatcher.match` built a fresh instance every call.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "text_encoding"
            path.write_text(self.TEXT_SUFFIX_DEFINITION)
            matcher = MagicMatcher.parse(path)
        crlf = "Marked file, ASCII text, with CRLF line terminators"
        for data, expected in ((b"MARKED\r\n", crlf),
                               (b"MARKED\n", "Marked file, ASCII text"),
                               (b"MARKED\r\n", crlf),
                               (b"MARKED", "Marked file, ASCII text, with no line terminators")):
            with self.subTest(data=data):
                self.assertEqual({expected}, {str(match) for match in matcher.match(data)})

    def test_only_match_mime_reports_the_same_types(self):
        """Tests that the description does not disturb which MIME types a match reports.

        `MagicTest._match` prunes subtrees that cannot report a MIME type when
        `MatchContext.only_match_mime` is set, and the description is appended to a match's
        message rather than to its results, so both modes report the types they did before.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        for stem, expected in (("osm", {"text/xml"}),
                               ("gedcom", {"text/vnd.familysearch.gedcom"}),
                               ("pnm1", {"image/x-portable-graymap"}),
                               ("json1", {"application/json"}),
                               ("jpeg-text", {"text/plain"})):
            data = (FILE_TEST_DIR / f"{stem}.testfile").read_bytes()
            for only_match_mime in (False, True):
                with self.subTest(test=stem, only_match_mime=only_match_mime):
                    context = MatchContext(data, only_match_mime=only_match_mime)
                    self.assertEqual(expected, {
                        mimetype
                        for match in MagicMatcher.DEFAULT_INSTANCE.match(context)
                        for mimetype in match.mimetypes
                        if mimetype is not None
                    })


ORDER_SCRIPT: str = """
import sys
from polyfile.magic import MagicMatcher
for path in sys.argv[1:]:
    with open(path, "rb") as f:
        data = f.read()
    print(path, "\t".join(str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(data)))
"""

HASH_SEEDS: Tuple[str, ...] = ("0", "1", "12345")


class MatchOrderTest(TestCase):
    """Regression tests for the match order reported in issue #3509.

    `MagicMatcher` used to hold its level 0 tests in sets, so `MagicMatcher.match` reported them
    in set-iteration order and threw away the sort `MagicMatcher.parse` had applied. `MagicTest`
    inherits identity hashing, which ties that order to allocation order and therefore to
    Python's per-process hash seed, so the same input could name a different primary type on a
    later run.
    """

    MULTI_MATCH_STEMS: Tuple[str, ...] = (
        "HWP2016.hwpx.zip", "keyman-2", "escapevel", "issue311docx", "issue359xlsx", "osm",
    )
    """Corpus stems that PolyFile reports more than one match for, so their order is observable."""

    def assert_strongest_first(self, tests: Iterable[polyfile.magic.MagicTest], label: str):
        """Asserts that `tests` arrive in non-increasing order of strength.

        Args:
            tests: The level 0 tests to check, in the order something reported them.
            label: What is being checked, for the failure message.
        """
        previous: Optional[polyfile.magic.MagicTest] = None
        for test in tests:
            if previous is not None:
                self.assertLessEqual(
                    test.compute_strength(), previous.compute_strength(),
                    f"{label}: {test.source_info} has strength {test.compute_strength()}, above "
                    f"the {previous.compute_strength()} of the {previous.source_info} before it"
                )
            previous = test

    def test_each_pass_runs_its_tests_strongest_first(self):
        """Tests that both of `MagicMatcher.match`'s passes are ordered, not just the test list.

        This is the assertion a set cannot satisfy: over thousands of tests, an order that came
        from hashing is not going to be non-increasing by accident.
        """
        matcher = MagicMatcher.DEFAULT_INSTANCE
        self.assert_strongest_first(matcher, "the level 0 tests")
        self.assert_strongest_first(matcher.non_text_tests, "the binary pass")
        self.assert_strongest_first(matcher.text_tests, "the text pass")

    def test_only_match_orders_the_tests_it_keeps(self):
        """Tests that a matcher `MagicMatcher.only_match` narrowed is ordered too.

        `only_match` collects its tests out of `MagicMatcher.tests_by_mime`, which holds sets, so
        the order has to be established where the matcher stores the tests rather than where
        `MagicMatcher.parse` reads them.
        """
        matcher = MagicMatcher.DEFAULT_INSTANCE.only_match(
            mimetypes=["application/zip", "application/pdf", "image/jpeg", "text/plain"])
        self.assert_strongest_first(matcher, "only_match")
        self.assert_strongest_first(matcher.non_text_tests, "only_match's binary pass")
        self.assert_strongest_first(matcher.text_tests, "only_match's text pass")

    def test_matches_follow_the_order_of_the_tests_that_produced_them(self):
        """Tests that a file's matches arrive in the order the matcher runs the tests.

        The binary pass runs before the text pass, so the reported matches are not globally
        ordered by strength; what has to hold is that they are a subsequence of the two passes.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        matcher = MagicMatcher.DEFAULT_INSTANCE
        position = {
            test: index
            for index, test in enumerate(chain(matcher.non_text_tests, matcher.text_tests))
        }
        for stem in self.MULTI_MATCH_STEMS:
            with self.subTest(test=stem):
                data = (FILE_TEST_DIR / f"{stem}.testfile").read_bytes()
                tests = [match[0].test for match in matcher.match(data)]
                self.assertGreater(len(tests), 1, f"{stem} no longer reports several matches")
                missing = [test for test in tests if test not in position]
                self.assertEqual([], missing, f"{stem} matched a test the matcher does not hold")
                indices = [position[test] for test in tests]
                self.assertEqual(sorted(indices), indices)

    def test_equal_strengths_break_the_way_libmagic_breaks_them(self):
        """Tests the tie-break `apprentice_sort` applies, over `file/tests/multiple`'s sidecars.

        Those two definition files declare two tests of strength 40 and two of 38, and
        `file/tests/multiple.result` requires `Viva File 2.0`, `RTF1.0`, `Test File 1.0`,
        `ABCD File`. Strength does not decide either pair. libmagic compares the two entries'
        `struct magic` bytes and takes the greater one first
        (`file/src/apprentice.c:1132-1149`), and for both pairs the first field that differs is
        `offset`, so the test that reads further into the file wins.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        matcher = MagicMatcher.parse(FILE_TEST_DIR / "multiple-A.magic",
                                     FILE_TEST_DIR / "multiple-B.magic")
        self.assertEqual([40, 40, 38, 38], [test.compute_strength() for test in matcher])
        self.assertEqual(["Viva File 2.0", "RTF1.0", "Test File 1.0", "ABCD File"],
                         [str(test.message) for test in matcher])

    def test_match_order_does_not_depend_on_the_hash_seed(self):
        """Tests that separate processes report a file's matches in the same order.

        Python randomizes the hash seed per process unless `PYTHONHASHSEED` is set, so this is
        what made the old behavior reach users rather than only showing up under a debugger.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        paths = [str(FILE_TEST_DIR / f"{stem}.testfile") for stem in self.MULTI_MATCH_STEMS]
        command = [sys.executable, "-c", ORDER_SCRIPT, *paths]
        reported: Dict[str, str] = {}
        for seed in HASH_SEEDS:
            environment = dict(os.environ, PYTHONHASHSEED=seed)
            try:
                result = subprocess.run(command, capture_output=True, check=True,
                                        env=environment, timeout=MATCH_TIMEOUT_SECONDS)
            except subprocess.CalledProcessError as e:
                self.fail(f"PYTHONHASHSEED={seed} failed: {e.stderr.decode('utf-8', 'replace')}")
            reported[seed] = result.stdout.decode("utf-8")
        detail = "".join(f"PYTHONHASHSEED={seed}:\n{output}"
                         for seed, output in reported.items())
        self.assertEqual(1, len(set(reported.values())),
                         f"the match order differs between hash seeds:\n{detail}")


class MatchJoinTest(TestCase):
    """Tests for the joined description reported in issue #3491.

    `file -k` renders every match into one description rather than reporting only the strongest,
    and `file/tests/multiple.result` is the corpus expectation that records the format. Every
    string these tests expect is what `file -b -k` prints for the same input, checked against
    libmagic 5.48 built from the `file` submodule.
    """

    TWO_TEXT_TESTS: str = "0\tstring/t\tMARKED\tFirst file text\n0\tstring/t\tMARK\tSecond\n"
    """Two text tests that both match `MARKED`.

    Their strings are 6 and 4 bytes long, so their strengths differ and the order of the join
    does not rest on the tie-break issue #3509 settled. The first message ends in the ` text`
    that libmagic splices out, which it must keep because the splice lands on the last part.
    """

    ONE_TEXT_TEST: str = "0\tstring/t\tMARK\tOnly file text\n"
    """A single text test, so there is nothing to separate."""

    CONTROL_CHARACTER_TEST: str = "0\tstring\tMARK\tMarked\n>4\tbyte\tx\t, code %c\n"
    """A binary test that prints a byte of the file as a character, as libmagic's tar check does
    for `file/tests/JW07022A.mp3.testfile`."""

    @staticmethod
    def matcher(definition: str) -> MagicMatcher:
        """Parses a single magic definition.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.

        Returns:
            A matcher holding just that definition's tests.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "match_join"
            path.write_text(definition)
            return MagicMatcher.parse(path)

    def join(self, definition: str, data: bytes, raw: bool = False) -> str:
        """Describes every match one definition reports for `data`, in one string.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.
            data: The bytes to classify.
            raw: Whether to skip the escaping, as libmagic's `MAGIC_RAW` does.

        Returns:
            The joined description.
        """
        return polyfile.magic.join_matches(self.matcher(definition).match(data), raw=raw)

    def test_two_matches_are_joined_with_an_escaped_separator(self):
        """Tests that the join uses libmagic's separator, escaped the way `file` escapes it.

        `FILE_SEPARATOR` is `\\n- ` (`file/src/funcs.c:276`), and `file_getbuffer` octal-escapes
        the line feed unless `MAGIC_RAW` is set, which is why `file/tests/multiple.result` holds
        `\\012- `.
        """
        self.assertEqual("First file text\\012- Second, ASCII text, with no line terminators",
                         self.join(self.TWO_TEXT_TESTS, b"MARKED"))

    def test_the_raw_form_keeps_the_separator_unescaped(self):
        """Tests that `raw` reports the line feed itself, as `file -r` does."""
        self.assertEqual("First file text\n- Second, ASCII text, with no line terminators",
                         self.join(self.TWO_TEXT_TESTS, b"MARKED", raw=True))

    def test_the_encoding_description_is_appended_once(self):
        """Tests that only the last part carries the text-encoding description.

        libmagic keeps one output buffer, so `file_ascmagic` rewrites the tail of the whole join
        rather than each part (`file/src/ascmagic.c:235-258`). Issue #3488 attaches the
        description to every match, which is right for one description per line, so joining those
        strings directly would report the encoding once per part. That the first part still ends
        in ` text` is the other half of the evidence: the splice reached only the last part.
        """
        joined = self.join(self.TWO_TEXT_TESTS, b"MARKED", raw=True)
        self.assertEqual(1, joined.count("ASCII text"))
        self.assertEqual(["First file text", "Second, ASCII text, with no line terminators"],
                         joined.split(polyfile.magic.MATCH_SEPARATOR))

    def test_joining_does_not_change_what_each_match_reports(self):
        """Tests that the join leaves the per-match descriptions issue #3488 produces alone.

        `--format file` prints one match per line, and each of those lines has to stand on its
        own, so the join must not reach into the matches to move the description.
        """
        matches = list(self.matcher(self.TWO_TEXT_TESTS).match(b"MARKED"))
        polyfile.magic.join_matches(matches)
        self.assertEqual({"First file, ASCII text, with no line terminators",
                          "Second, ASCII text, with no line terminators"},
                         {str(match) for match in matches})

    def test_a_single_match_is_its_own_description(self):
        """Tests that one match joins to just its description, with no separator.

        `trim_separator` (`file/src/funcs.c:284`) takes the trailing separator back off, so a
        lone match reads exactly as it does without `-k`.
        """
        self.assertEqual("Only file, ASCII text, with no line terminators",
                         self.join(self.ONE_TEXT_TEST, b"MARK"))

    def test_the_parts_follow_the_order_of_the_matches(self):
        """Tests the join against `file/tests/multiple.result`, the corpus expectation.

        The four parts come out in the order `MagicMatcher.match` reports them, which issue #3509
        made libmagic's own order. Reordering them here would hide a regression in that.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        matcher = MagicMatcher.parse(FILE_TEST_DIR / "multiple-A.magic",
                                     FILE_TEST_DIR / "multiple-B.magic")
        data = (FILE_TEST_DIR / "multiple.testfile").read_bytes()
        self.assertEqual(
            "Viva File 2.0\\012- RTF1.0\\012- Test File 1.0\\012- ABCD File, ASCII text, "
            "with no line terminators",
            polyfile.magic.join_matches(matcher.match(data))
        )

    def test_an_unprintable_character_is_octal_escaped(self):
        """Tests that the escaping covers more than the separator's line feed.

        `file_getbuffer` escapes every character it cannot print, not just the one the separator
        contributes, which is how the `-k` description of `file/tests/JW07022A.mp3.testfile`
        reports the byte 2 in an ID3 field as `\\002`.
        """
        self.assertEqual("Marked , code \\002",
                         self.join(self.CONTROL_CHARACTER_TEST, b"MARK\x02\x00\x00\x00rest"))
        self.assertEqual("Marked , code \x02",
                         self.join(self.CONTROL_CHARACTER_TEST, b"MARK\x02\x00\x00\x00rest",
                                   raw=True))


class UCSTextBufferTest(TestCase):
    """Regression tests for the buffer the text tests read, reported in issue #3489.

    libmagic decodes its input into a UCS-4 buffer, drops the byte order mark, re-encodes that
    buffer as UTF-8, and runs its text tests against the result rather than against the file's
    bytes (`file_ascmagic_with_encoding` in `file/src/ascmagic.c`, `looks_ucs16` and `looks_ucs32`
    in `file/src/encoding.c`). PolyFile ran its text tests against the raw bytes, so no text
    definition could match a UTF-16 or UTF-32 file.

    Every string these tests expect is what `file -b -k` prints for the same input, checked against
    libmagic 5.48 built from the `file` submodule. libmagic joins its `-k` output into one string
    and appends a single text-encoding description to the end of the join, which is issue #3491, so
    these tests read the description off each match instead.
    """

    SVG: str = ('<?xml version="1.0"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>\n')
    """A document `polyfile/magic_defs/sgml` reports as SVG, XML 1.0 and XML."""

    ENCODINGS: Tuple[Tuple[str, str, bytes], ...] = (
        ("utf-16le", "UTF-16, little-endian", b"\xff\xfe"),
        ("utf-16be", "UTF-16, big-endian", b"\xfe\xff"),
        ("utf-32le", "UTF-32, little-endian", b"\xff\xfe\x00\x00"),
        ("utf-32be", "UTF-32, big-endian", b"\x00\x00\xfe\xff"),
    )
    """Each UCS encoding libmagic names, with the name it gives it and its byte order mark."""

    @staticmethod
    def encode(text: str, encoding: str) -> bytes:
        """Encodes `text` the way a file in `encoding` holds it, byte order mark included.

        Args:
            text: The characters to encode.
            encoding: One of the encoding names in `ENCODINGS`.

        Returns:
            The encoded bytes.
        """
        bom = next(mark for name, _, mark in UCSTextBufferTest.ENCODINGS if name == encoding)
        return bom + text.encode(encoding)

    @staticmethod
    def text_buffer(data: bytes) -> Optional[bytes]:
        """Returns the buffer `MagicMatcher.match` would hand the text tests for `data`.

        Args:
            data: The bytes to classify.

        Returns:
            The buffer, or None if `data` is not text.
        """
        encoding = polyfile.magic.detect_text_encoding(data)
        if encoding is None:
            return None
        return MatchContext(data).text_test_context(encoding).data

    def test_a_utf16_document_matches_the_text_tests(self):
        """Tests that the SVG and XML definitions match a UTF-16 document of either endianness.

        `polyfile/magic_defs/sgml:6` anchors `\\<?xml\\ version=` at offset 0, which no UTF-16 file
        can satisfy in its own bytes: `file/tests/utf16xmlsvg.testfile` begins
        `ff fe 3c 00 3f 00 78 00`.
        """
        for encoding, name, _ in self.ENCODINGS[:2]:
            with self.subTest(encoding=encoding):
                data = self.encode(self.SVG, encoding)
                self.assertEqual(
                    {f"SVG Scalable Vector Graphics image, Unicode text, {name} text",
                     f"XML 1.0 document, Unicode text, {name} text",
                     f"XML document, Unicode text, {name} text"},
                    {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
                )

    def test_a_utf32_document_matches_the_text_tests(self):
        """Tests that a UTF-32 document matches the same text tests, plus its byte order mark.

        `looks_ucs32` runs ahead of `looks_ucs16` in `file_encoding`, and `polyfile/magic_defs/
        unicode:13` matches the UTF-32 mark in the binary pass, which is why `file -b` stops at
        `Unicode text, UTF-32, little-endian` and only `file -b -k` shows the text matches.
        """
        for encoding, name, _ in self.ENCODINGS[2:]:
            with self.subTest(encoding=encoding):
                data = self.encode(self.SVG, encoding)
                self.assertEqual(
                    {f"Unicode text, {name}",
                     f"SVG Scalable Vector Graphics image, Unicode text, {name} text",
                     f"XML 1.0 document, Unicode text, {name} text",
                     f"XML document, Unicode text, {name} text"},
                    {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
                )

    def test_the_byte_order_mark_is_not_in_the_text_buffer(self):
        """Tests that the decoded buffer starts at the first character, not at the mark.

        `looks_ucs16` starts its loop at `i = 2` and `looks_ucs32` at `i = 4`
        (`file/src/encoding.c`), so the mark never reaches the buffer the text tests read. Keeping
        it as U+FEFF pushes every offset forward by the length of its UTF-8 form and costs the SVG
        match, whose first test is anchored at offset 0.
        """
        for encoding, _, _ in self.ENCODINGS:
            with self.subTest(encoding=encoding):
                buffer = self.text_buffer(self.encode(self.SVG, encoding))
                self.assertEqual(self.SVG.encode("utf-8"), buffer)

    def test_an_eight_bit_input_is_not_decoded(self):
        """Tests that only a UCS input gets a second buffer, so every other offset stays honest.

        A buffer that differs from the file's bytes costs the offsets its tests report, and
        decoding costs time on every input, so an encoding whose characters libmagic copies
        straight into its UCS-4 buffer keeps the context it already had.
        """
        inputs = ((b"plain ascii text\n", "ascii"),
                  ("café naïve\n".encode("utf-8"), "utf-8"),
                  ("café naïve\n".encode("latin-1"), "iso-8859-1"),
                  (b"caf\x85 na\x8bve\n", "unknown-8bit"))
        for data, expected_encoding in inputs:
            with self.subTest(encoding=expected_encoding):
                self.assertEqual(expected_encoding, polyfile.magic.detect_text_encoding(data))
                context = MatchContext(data)
                self.assertIs(context, context.text_test_context(expected_encoding))
                self.assertIsNone(context.decoded_from)

    def test_the_decoded_buffer_stops_at_the_encoding_byte_limit(self):
        """Tests that decoding reads at most `FILE_ENCODING_MAX` bytes of the file.

        `file_encoding` clamps its input to `ms->encoding_max`, which `apprentice.c` sets to
        `FILE_ENCODING_MAX`, 64 kibibytes (`file/src/file.h:525`). Without the clamp a UTF-16 file
        of any size gets decoded in full on every call to `MagicMatcher.match`.
        """
        limit = polyfile.magic.TEXT_ENCODING_MAX_BYTES
        data = self.encode("a" * (limit // 2), "utf-16le")
        self.assertGreater(len(data), limit)
        self.assertEqual(b"a" * (limit // 2 - 1), self.text_buffer(data))

    def test_a_decoded_match_reports_offsets_into_the_buffer_it_read(self):
        """Tests that a match against a decoded buffer says so rather than claiming file offsets.

        There is no map from an offset in the decoded buffer back to the byte in the file that
        produced it, so a match on a UCS file carries the encoding it was decoded from and
        `Match.explain` explains it against the buffer its tests read. This is the limitation the
        transcoding introduces, pinned so it cannot start reporting decoded offsets as file
        offsets.
        """
        data = self.encode(self.SVG, "utf-16le")
        matches = {str(match): match for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
        match = matches["XML document, Unicode text, UTF-16, little-endian text"]
        self.assertEqual("utf-16le", match.context.decoded_from)
        result = match[0]
        self.assertEqual(b"<?xml", match.context.data[result.offset:result.offset + result.length])
        self.assertEqual(b"\xff\xfe<\x00?", data[result.offset:result.offset + result.length])
        explanation = match.explain(file=data, ansi_color=False)
        self.assertIn("decoded from this file as utf-16le, not into the file itself", explanation)

    def test_a_match_on_the_files_own_bytes_claims_no_decoding(self):
        """Tests that an ASCII match keeps reporting file offsets, with no note in `explain`.

        The note and the switch to the decoded buffer belong to `MatchContext.decoded_from`, so a
        match that read the file's bytes has to be explained exactly as it was before.
        """
        data = self.SVG.encode("utf-8")
        matches = {str(match): match for match in MagicMatcher.DEFAULT_INSTANCE.match(data)}
        match = matches["XML document, ASCII text"]
        self.assertIsNone(match.context.decoded_from)
        result = match[0]
        self.assertEqual(b"<?xml", data[result.offset:result.offset + result.length])
        self.assertNotIn("decoded from this file", match.explain(file=data, ansi_color=False))

    def test_the_json_and_csv_checks_read_the_files_own_bytes(self):
        """Tests that the checks `file_buffer` runs before soft magic never see decoded text.

        `file_buffer` runs `file_is_json` and `file_is_csv` against the buffer it was handed
        (`file/src/funcs.c:412-429`), so `file -b -k` reports only `Unicode text, UTF-16,
        little-endian text` for a UTF-16 JSON document. PolyFile models both as text soft magic
        tests, so decoding the text buffer would have handed them the decoded text and reported a
        CSV match libmagic does not report.

        The `JSON text data` this expects for the UTF-16 document is a separate divergence that
        predates the decoding: `parse_json` reads the bytes through `json.detect_encoding`, which
        sniffs a UTF-16 byte order mark, and `file_is_json` does not. PolyFile reports the encoding
        description alongside it, which is the decision recorded in trailofbits/polyfile#3500.
        """
        document = '{"a": 1, "b": 2}\n'
        self.assertIn("CSV text (excel dialect)", {
            str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(document.encode("utf-8"))
        })
        self.assertEqual(
            {"JSON text data", "Unicode text, UTF-16, little-endian text"},
            {str(match) for match in
             MagicMatcher.DEFAULT_INSTANCE.match(self.encode(document, "utf-16le"))}
        )


class DataTypeNameTest(TestCase):
    """Regression tests for the interning collision reported in issue #3515.

    `DataType.parse` interns every type it builds in `polyfile.magic.TYPES_BY_NAME`, keyed on the
    name the type builds for itself. A flag the name leaves out makes two declarations that differ
    only by that flag share one instance, and whichever declaration parses first decides the flags
    for both. `RegexType` left out `t` and `b`, and `StringType`'s no-flag shortcut left out `f`.
    """

    def test_every_flag_reaches_the_name(self):
        """Tests that each flag letter of each type appears in the parsed type's name.

        A missing letter is what makes two declarations collide, so this asserts the property the
        collision violated rather than the pairs that happened to collide.
        """
        for declaration, flags in (("string", "WwCcTftb"), ("search/8", "WwCcTftbs"),
                                   ("regex/8", "cslTtb")):
            for flag in flags:
                spec = f"{declaration}/{flag}"
                with self.subTest(declaration=spec):
                    self.assertIn(flag, DataType.parse(spec).name)

    def test_declarations_that_differ_by_one_flag_are_distinct(self):
        """Tests that adding a flag to a declaration yields a different interned type."""
        for declaration, flags in (("string", "WwCcTftb"), ("search/8", "WwCcTftbs"),
                                   ("regex/8", "cslTtb")):
            plain = DataType.parse(declaration)
            for flag in flags:
                spec = f"{declaration}/{flag}"
                with self.subTest(declaration=spec):
                    self.assertIsNot(plain, DataType.parse(spec))

    def test_a_name_that_drops_a_flag_is_rejected(self):
        """Tests that a type whose name loses a flag raises instead of interning silently.

        The failure this prevents is silent: no exception and no warning, just a type behaving as
        though its flag were absent. `DataType.parse` now reparses the name it built and compares
        the result, which is the check that would have caught both halves of issue #3515.
        """
        class ForgetfulStringType(StringType):
            def declaration(self) -> str:
                return "string"

        DataType.parse("string")
        try:
            polyfile.magic.StringType = ForgetfulStringType
            polyfile.magic.TYPES_BY_NAME.pop("string/f", None)
            with self.assertRaises(ValueError):
                DataType.parse("string/f")
        finally:
            polyfile.magic.StringType = StringType
            polyfile.magic.TYPES_BY_NAME.pop("string/f", None)

    def test_whole_word_match_survives_parsing(self):
        """Tests that `string/f` is its own type and matches whole words only.

        `StringType.__init__` left `full_word_match` out of the tuple that decides whether a
        declaration carries any flag, so a declaration whose only flag was `f` took the bare name
        `string` and shared the unflagged type's instance.
        """
        whole_word = DataType.parse("string/f")
        self.assertIsNot(whole_word, DataType.parse("string"))
        self.assertTrue(whole_word.full_word_match)
        self.assertFalse(DataType.parse("string").full_word_match)
        expected = whole_word.parse_expected("if")
        self.assertTrue(whole_word.match(b"if x then", expected))
        self.assertFalse(whole_word.match(b"iffy", expected))


class SearchFlagTableTest(TestCase):
    """Regression tests for the `search` flag table reported in issue #3478.

    libmagic reads the string flags of a `search` in one loop shared with `string`, `pstring` and
    `regex` (`file/src/apprentice.c:1940-2028`), and the letters are defined in
    `file/src/file.h:415-431`. `SearchType.parse` read `B` as compact whitespace, read `b` as
    optional blanks, and dropped `t` altogether.
    """

    FLAGS: Tuple[Tuple[str, str], ...] = (
        ("W", "compact_whitespace"),
        ("w", "optional_blanks"),
        ("c", "case_insensitive_lower"),
        ("C", "case_insensitive_upper"),
        ("T", "trim"),
        ("f", "full_word_match"),
        ("s", "match_to_start"),
        ("t", "force_text"),
        ("b", "force_binary"),
    )
    """Each flag a `search` accepts, paired with the behavior libmagic gives it."""

    def test_each_flag_sets_only_its_own_behavior(self):
        """Tests that every letter maps to the one behavior libmagic gives it.

        `b` set `optional_blanks`, which made a `search` tolerate whitespace libmagic requires to
        match exactly, so PolyFile reported matches libmagic does not.
        """
        for letter, attribute in self.FLAGS:
            with self.subTest(flag=letter):
                flagged = SearchType.parse(f"search/8/{letter}")
                for _, other in self.FLAGS:
                    self.assertEqual(other == attribute, getattr(flagged, other), other)

    def test_the_pascal_string_length_flag_is_rejected(self):
        """Tests that `B` raises rather than passing for compact whitespace.

        `B` is `CHAR_PSTRING_1_BE`, and libmagic's flag loop jumps to its error label for any type
        but `pstring` (`file/src/apprentice.c:1983-1986`). Reading it as `W` would have let a
        `search/B` silently compact the whitespace of its value.
        """
        for declaration in ("search/8/B", "string/B"):
            with self.subTest(declaration=declaration):
                with self.assertRaises(ValueError):
                    DataType.parse(declaration)
        self.assertEqual(1, DataType.parse("pstring/B").byte_length)

    def test_flags_may_precede_an_undocumented_repetition_count(self):
        """Tests that `ber`'s `search/b64` is `search/64` with the binary flag set.

        libmagic reads the digits of a string declaration as the repetition count and each letter
        as a flag, in one loop, so the two orders mean the same thing.
        """
        self.assertIs(DataType.parse("search/b64"), DataType.parse("search/64/b"))
        self.assertEqual(64, DataType.parse("search/b64").repetitions)


class PassSelectionTest(TestCase):
    """Regression tests for the pass selection defect reported in issue #3490.

    libmagic decides which of its two soft magic passes a definition belongs to in
    `set_test_type`, from the type and the `b`/`t` string flags of the entry's level 0 line alone
    (`file/src/apprentice.c:1200-1284`). `set_text_binary` hands it one entry per top-level test
    (`file/src/apprentice.c:1423-1453`), so a subtest never changes the answer. PolyFile derived
    the classification from a test's children instead, which put both halves of a text/binary
    definition pair in the binary pass.
    """

    @staticmethod
    def passes(definition: str) -> polyfile.magic.TestType:
        """The passes PolyFile runs the one level 0 test of `definition` in.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.

        Returns:
            The passes the test landed in.
        """
        with TemporaryDirectory() as tmp_dir:
            magic_file = Path(tmp_dir) / "test.magic"
            magic_file.write_text(definition)
            matcher = MagicMatcher.parse(magic_file)
            text, binary = list(matcher.text_tests), list(matcher.non_text_tests)
        assert len(set(text) | set(binary)) == 1, "expected exactly one level 0 test"
        found = polyfile.magic.TestType.UNKNOWN
        if text:
            found |= polyfile.magic.TestType.TEXT
        if binary:
            found |= polyfile.magic.TestType.BINARY
        return found

    def test_a_text_flag_outranks_a_binary_subtest(self):
        """Tests that `t` on the level 0 line wins over a binary subtest under it.

        `magic_defs/varied.script:8` is `string/wt` with a `string/T` subtest, and its `string/wb`
        twin sits four lines below. PolyFile put both in the binary pass, so
        `file/tests/cmd1.testfile` reported the binary variant as well as the text one.
        """
        definition = "0\tstring/wt\t#!\\ \ta\n>&-1\tstring/T\tx\t%s script text executable\n"
        self.assertEqual(polyfile.magic.TestType.TEXT, self.passes(definition))

    def test_a_binary_flag_outranks_a_text_subtest(self):
        """Tests that `b` on the level 0 line wins over an all-text group.

        `magic_defs/varied.script:12` is the binary half of the same pair.
        """
        definition = "0\tstring/wb\t#!\\ \ta\n>&-1\tstring/T\tx\t%s script executable\n"
        self.assertEqual(polyfile.magic.TestType.BINARY, self.passes(definition))

    def test_a_subtest_never_adds_a_pass(self):
        """Tests that a numeric subtest does not drag a text entry into the binary pass.

        `file -l -m` over a definition of `0 string/t XY` with a `>2 belong 0` subtest lists it
        under `Text patterns` only, because `set_text_binary` calls `set_test_type` once per
        top-level entry and never for a continuation line.
        """
        definition = "0\tstring/t\tXY\tflagged text\n>2\tbelong\t0\t\\b, zero\n"
        self.assertEqual(polyfile.magic.TestType.TEXT, self.passes(definition))
        definition = "0\tsearch/1\tPQ\tunflagged search\n>2\tbelong\t0\t\\b, zero\n"
        self.assertEqual(polyfile.magic.TestType.TEXT, self.passes(definition))

    def test_an_unflagged_entry_belongs_to_exactly_one_pass(self):
        """Tests the fallbacks `set_test_type` reaches when no flag names a pass.

        A `string` takes the binary pass whatever its value, which the comment there calls a
        compatibility choice; a `search` or a `regex` takes the pass its own value looks like,
        by `file_looks_utf8`.
        """
        for definition, expected in (
                ("0\tstring\tTU\tplain string\n", polyfile.magic.TestType.BINARY),
                ("0\tregex/1024\tab+c\tunflagged regex\n", polyfile.magic.TestType.TEXT),
                ("0\tsearch/1\ta\\x00b\tnull byte\n", polyfile.magic.TestType.BINARY),
                ("0\tlestring16\tVersion=\tsixteen bit\n", polyfile.magic.TestType.BINARY),
        ):
            with self.subTest(definition=definition):
                self.assertEqual(expected, self.passes(definition))

    def test_both_flags_belong_to_both_passes(self):
        """Tests that an entry carrying `b` and `t` runs in both passes.

        `softmagic` skips an entry only when exactly one of the two bits is set and it is the
        wrong one (`file/src/softmagic.c:249-253`), and `set_test_type` sets both bits from both
        flags, so `magic_defs/sgml:6`, `sgml:17` and `sgml:74` are listed under `Binary patterns`
        and under `Text patterns` by `file -l`. `TestType` could not express that.
        """
        self.assertEqual(polyfile.magic.TestType.BOTH,
                         self.passes("0\tstring/bt\tRS\tboth flags\n"))
        self.assertEqual(polyfile.magic.TestType.BOTH,
                         self.passes("0\tsearch/4096/cWbt\t\\<!doctype\\ svg\tSVG XML document\n"))

    def test_the_shipped_both_flag_entries_are_in_both_passes(self):
        """Tests that the three shipped `b`-and-`t` entries reach both passes."""
        matcher = MagicMatcher.parse(*MAGIC_DEFS)
        in_both = {
            f"{test.source_info.path.name}:{test.source_info.line}"
            for test in set(matcher.text_tests) & set(matcher.non_text_tests)
            if test.source_info is not None
        }
        self.assertEqual({"sgml:6", "sgml:17", "sgml:74"}, in_both)


class PassGateTest(TestCase):
    """Regression tests for the missing pass gate reported in issue #3490.

    `softmagic` skips an entry when the buffer looks like text and the entry declares only
    `STRING_BINTEST`, and when it does not and the entry declares only `STRING_TEXTTEST`
    (`file/src/softmagic.c:249-253`). PolyFile ran every non-text test against every input, so a
    definition that spells one shebang twice reported both spellings.
    """

    @staticmethod
    def messages(definition: str, data: bytes) -> Set[str]:
        """Runs a single magic definition against `data`.

        Args:
            definition: The text of a magic definition file, with tab-separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match.
        """
        with TemporaryDirectory() as tmp_dir:
            magic_file = Path(tmp_dir) / "test.magic"
            magic_file.write_text(definition)
            return {str(match) for match in MagicMatcher.parse(magic_file).match(data)}

    def test_a_binary_flagged_entry_skips_a_text_buffer(self):
        """Tests that `b` keeps an entry from running against a buffer that looks like text."""
        definition = "0\tstring/b\tMARK\tbinary only\n"
        self.assertNotIn("binary only", self.messages(definition, b"MARK and then some text\n"))
        self.assertIn("binary only", self.messages(definition, b"MARK\x00\x01\x02\xff"))

    def test_a_text_flagged_entry_skips_a_binary_buffer(self):
        """Tests that `t` keeps an entry from running against a buffer that is not text.

        The entry never reaches the text pass, because `file_buffer` runs `file_ascmagic` only for
        a buffer `file_encoding` recognized (`file/src/funcs.c:495-503`).
        """
        definition = "0\tstring/t\tMARK\ttext only\n"
        self.assertNotIn("text only", self.messages(definition, b"MARK\x00\x01\x02\xff"))
        self.assertIn("text only, ASCII text",
                      self.messages(definition, b"MARK and then some text\n"))

    def test_an_unflagged_entry_runs_against_both_kinds_of_buffer(self):
        """Tests that an entry naming no pass is never skipped for the pass it landed in.

        The gate reads the declared flags, not the pass the entry was sorted into, because
        `softmagic` tests `m->str_flags` rather than `m->flag`.
        """
        definition = "0\tstring\tMARK\tno flags\n"
        self.assertIn("no flags", self.messages(definition, b"MARK\x00\x01\x02\xff"))
        self.assertIn("no flags", self.messages(definition, b"MARK and then some text\n"))

    def test_a_both_flagged_entry_runs_against_both_kinds_of_buffer(self):
        """Tests that `b` and `t` together survive the gate in either direction.

        `softmagic`'s skip fires only when exactly one of the two bits is set, so an entry that
        sets both is never skipped. It must still report one match per buffer and not two, because
        libmagic stops after its binary pass prints something.
        """
        definition = "0\tstring/bt\tMARK\tboth flags\n"
        for data in (b"MARK\x00\x01\x02\xff", b"MARK and then some text\n"):
            with self.subTest(data=data):
                self.assertEqual({"both flags"}, self.messages(definition, data))

    def test_a_script_reports_only_libmagics_variant(self):
        """Tests that `file/tests/cmd1.testfile` no longer reports a binary variant.

        `magic_defs/varied.script` spells one shebang twice, `string/wt` at line 8 and
        `string/wb` at line 12. PolyFile reported `a /usr/bin/cmd1 script executable (binary
        data)` alongside the correct message; `file -b` reports only the one asserted here.
        """
        self.assertTrue(FILE_TEST_DIR.exists(),
                        "Run `git submodule init && git submodule update` in the repository root.")
        for stem in ("cmd1", "cmd2"):
            with self.subTest(stem=stem):
                data = (FILE_TEST_DIR / f"{stem}.testfile").read_bytes()
                messages = {str(m) for m in MagicMatcher.DEFAULT_INSTANCE.match(data)}
                self.assertEqual({f"a /usr/bin/{stem} script, ASCII text executable"}, messages)

    def test_an_ascii_svg_is_not_described(self):
        """Tests that an SVG matched on the file's own bytes gains no encoding description.

        `magic_defs/sgml:6` declares both flags, so it runs in both passes. libmagic's binary pass
        matches it on the file's bytes and `checkdone` stops before `file_ascmagic`
        (`file/src/funcs.c:479-503`), so `file -b` reports a bare `SVG Scalable Vector Graphics
        image`. The same definition matched on the decoded buffer does gain the description, which
        is what `file/tests/utf16xmlsvg.testfile` expects.
        """
        svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>\n'
        messages = {str(m) for m in MagicMatcher.DEFAULT_INSTANCE.match(svg)}
        self.assertIn("SVG Scalable Vector Graphics image", messages)
        self.assertNotIn("SVG Scalable Vector Graphics image, ASCII text", messages)
        utf16 = b"\xff\xfe" + svg.decode("utf-8").encode("utf-16le")
        self.assertIn("SVG Scalable Vector Graphics image, Unicode text, UTF-16, little-endian text",
                      {str(m) for m in MagicMatcher.DEFAULT_INSTANCE.match(utf16)})


class DefaultTestSemanticsTest(TestCase):
    """Regression tests for when a `default` test fires, reported in issue #3517.

    libmagic keeps one `got_match` flag per continuation level and zeroes it whenever it descends
    into a level (`file/src/funcs.c:640-660`, called from `file/src/softmagic.c:346` and `:487`).
    A `default` fires only while that flag is unset, a `clear` unsets it, and every other test that
    passes `magiccheck` sets it (`file/src/softmagic.c:418-428`).

    Every string these tests expect is what `file -b -k` reports for the same definitions and
    input, checked against libmagic 5.48 built from the `file` submodule.
    """

    @staticmethod
    def messages(definitions: str, data: bytes) -> Set[str]:
        """Matches `data` against ad-hoc definitions and collects the resulting messages.

        Args:
            definitions: The contents of a libmagic definition file, with tab separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match the definitions produce.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "default_semantics"
            path.write_text(definitions)
            matcher = MagicMatcher.parse(path)
            return {str(match) for match in matcher.match(data)}

    def fired(self, definitions: str, data: bytes = b"HEADB") -> bool:
        """Reports whether the `fallback` message of a `default` test appears in the output.

        Args:
            definitions: The contents of a libmagic definition file.
            data: The bytes to classify, defaulting to one whose fifth byte is `B`.

        Returns:
            True if some match carries the `fallback` message.
        """
        return any("fallback" in message for message in self.messages(definitions, data))

    HEAD: str = "0\tstring\tHEAD\thead\n"
    """A level 0 test that matches the first four bytes of this class's test data."""

    NAMED_LIST: str = "0\tname\tnlist\n>0\tstring\tB\tnamed list matched\n\n"
    """A named list that prints a message when the byte it is invoked at is `B`."""

    def test_a_default_fires_when_no_earlier_test_at_its_level_matched(self):
        """A `default` is the fallback for its level, so a failed sibling must not stop it."""
        self.assertTrue(self.fired(
            self.HEAD + ">4\tstring\tZ\tsibling\n>4\tdefault\tx\tfallback\n"
        ))

    def test_a_default_does_not_fire_when_an_earlier_test_at_its_level_matched(self):
        """A matched sibling sets `got_match` for the level, which suppresses the `default`."""
        self.assertFalse(self.fired(
            self.HEAD + ">4\tstring\tB\tsibling\n>4\tdefault\tx\tfallback\n"
        ))

    def test_an_undescribed_sibling_suppresses_a_default(self):
        """An earlier sibling counts even with no description, which #3517 predicted otherwise.

        libmagic gates `found_match` and printing on a non-empty description
        (`file/src/softmagic.c:432-440`) but sets `got_match` for any test that passes
        `magiccheck` (`file/src/softmagic.c:424-428`), so the two are not the same condition.
        `file -b -k` reports only `head` for these definitions.
        """
        self.assertFalse(self.fired(
            self.HEAD + ">4\tstring\tB\n>4\tdefault\tx\tfallback\n"
        ))

    def test_a_use_that_matched_suppresses_a_default(self):
        """A `use` whose named list printed something sets `got_match` for its level."""
        self.assertFalse(self.fired(
            self.NAMED_LIST + self.HEAD + ">4\tuse\tnlist\n>4\tdefault\tx\tfallback\n"
        ))

    def test_a_use_that_printed_nothing_does_not_suppress_a_default(self):
        """A `use` used to suppress a following `default` whenever its named list matched at all.

        `FILE_USE`'s `magiccheck` is the number of entries in the named list that printed
        (`file/src/softmagic.c:2429-2430`), so a list whose only entry is undescribed leaves the
        `use` failing and the level's `got_match` unset. `file -b -k` reports `head fallback` for
        these definitions.
        """
        self.assertTrue(self.fired(
            "0\tname\tnlist\n>0\tstring\tB\n\n" + self.HEAD
            + ">4\tuse\tnlist\n>4\tdefault\tx\tfallback\n"
        ))

    def test_a_named_list_does_not_suppress_a_default_under_its_use(self):
        """What a named list matches used to leak into the level of the `use`'s own children.

        libmagic saves the whole level array before running a named list and restores it afterwards
        (`file/src/softmagic.c:2013` and `:2033`), so the list cannot touch the `got_match` of any
        level outside itself. `file -b -k` reports `head named list matched fallback` here.
        """
        self.assertTrue(self.fired(
            self.NAMED_LIST + self.HEAD + ">4\tuse\tnlist\n>>4\tstring\tZ\tsibling\n"
            ">>4\tdefault\tx\tfallback\n"
        ))

    def test_clear_lets_a_later_default_fire_again(self):
        """A `clear` used to set the condition it is supposed to reset.

        `ClearTest.test` unset the parent's flag and then built a `MatchedTest` against that same
        parent, which raised the flag straight back. libmagic's `FILE_CLEAR` arm zeroes
        `got_match` instead of taking the arm that raises it (`file/src/softmagic.c:422-424`).
        `file -b -k` reports `head sibling` and `fallback` for these definitions.
        """
        self.assertTrue(self.fired(
            self.HEAD + ">4\tstring\tB\tsibling\n>4\tclear\tx\n>4\tdefault\tx\tfallback\n"
        ))

    def test_a_plain_png_is_reported_as_a_png(self):
        """The broken `clear` cost every non-animated PNG its match.

        `polyfile/magic_defs/images:524` clears the level so that the `>8 default x` at `:533` can
        supply the standard PNG branch once the animated branch above it has failed. With the flag
        stuck set, that `default` never fired and `MagicMatcher.match` fell through to
        `OctetStreamTest`, reporting `data` for an ordinary PNG file.
        """
        ihdr = b"\x00\x00\x00\x0DIHDR" + (8).to_bytes(4, "big") * 2 + bytes((8, 6, 0, 0, 0))
        png = b"\x89PNG\r\n\x1a\n" + ihdr
        self.assertIn("PNG image data, 8 x 8, 8-bit/color RGBA, non-interlaced",
                      {str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(png)})


class RegexSubjectTest(TestCase):
    """Regression tests for the bytes a `regex` test matches against, reported in issue #3517.

    libmagic copies the region a `regex` runs over and NUL-terminates the copy by overwriting its
    last byte (`file/src/softmagic.c:2393-2405`), then passes it to `regexec` as a C string. The
    pattern therefore never sees the region's last byte, and never sees anything past a NUL that
    was already in the region. PolyFile handed the pattern the whole region, so a `regex` matched
    bytes libmagic cannot reach.

    Every string these tests expect is what `file -b -k` reports for the same definitions and
    input, checked against libmagic 5.48 built from the `file` submodule.
    """

    DEFINITION: str = "0\tstring\tHEAD\thead\n>4\tregex\tTARGET\tfound\n"
    """A level 0 test on `HEAD`, whose continuation looks for `TARGET` in the rest of the file."""

    @staticmethod
    def messages(definitions: str, data: bytes) -> Set[str]:
        """Matches `data` against ad-hoc definitions and collects the resulting messages.

        Args:
            definitions: The contents of a libmagic definition file, with tab separated columns.
            data: The bytes to classify.

        Returns:
            The message of every match the definitions produce.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "regex_subject"
            path.write_text(definitions)
            matcher = MagicMatcher.parse(path)
            return {str(match) for match in matcher.match(data)}

    def found(self, definitions: str, data: bytes) -> bool:
        """Reports whether the `found` message of the `regex` test appears in the output.

        Args:
            definitions: The contents of a libmagic definition file.
            data: The bytes to classify.

        Returns:
            True if some match carries the `found` message.
        """
        return any("found" in message for message in self.messages(definitions, data))

    def test_a_regex_does_not_see_past_a_nul_in_its_region(self):
        """A pattern used to match bytes that libmagic's C string cannot reach."""
        self.assertTrue(self.found(self.DEFINITION, b"HEADTARGETxx\n"))
        self.assertFalse(self.found(self.DEFINITION, b"HEADxx\x00TARGETxx\n"))

    def test_a_regex_does_not_see_the_last_byte_of_its_region(self):
        """The NUL that terminates libmagic's copy overwrites the region's final byte."""
        self.assertFalse(self.found(self.DEFINITION, b"HEADTARGET"))
        self.assertTrue(self.found(self.DEFINITION, b"HEADTARGETx"))

    def test_an_explicit_range_is_trimmed_after_it_is_applied(self):
        """`regex/N` reads N bytes and then loses the last of them, so N must exceed the pattern.

        `bytecnt` is the declared range clamped to what is left of the buffer
        (`file/src/softmagic.c:1417-1422`), and the trim happens afterwards, in `magiccheck`.
        """
        self.assertFalse(self.found("0\tstring\tHEAD\thead\n>4\tregex/6\tTARGET\tfound\n",
                                    b"HEADTARGETxxxx"))
        self.assertTrue(self.found("0\tstring\tHEAD\thead\n>4\tregex/7\tTARGET\tfound\n",
                                   b"HEADTARGETxxxx"))

    def test_hwpx_is_not_reported_as_microsoft_ooxml(self):
        """A Hancom HWPX file used to report as `Microsoft OOXML`, and to report it first.

        `polyfile/magic_defs/msooxml:38` looks for an OOXML part name at offset 0x1E, which in this
        file holds `mimetypeapplication/hwp+zip` followed by the next local file header. libmagic
        stops at the NUL inside that header and finds no part name, so it never reaches the
        `default x  Microsoft OOXML` ladder at `:63-69`. PolyFile read on to the end of the file,
        found `.png` in a later member name, and took the whole ladder down to `:66`, whose level 0
        entry scores 81 and so sorted the wrong type to the front of the output.
        """
        testfile = FILE_TEST_DIR / "HWP2016.hwpx.zip.testfile"
        self.assertTrue(testfile.exists(), "Make sure to run `git submodule init && git submodule update`")
        matches = [str(match) for match in MagicMatcher.DEFAULT_INSTANCE.match(testfile.read_bytes())]
        self.assertNotIn("Microsoft OOXML", matches)
        self.assertEqual("Hancom HWP (Hangul Word Processor) file, HWPX", matches[0])


class RegexLineLimitTest(TestCase):
    """Regression tests for the `l` flag on a `regex` test, reported in issue #3525.

    `l` bounds how much buffer the test may scan, expressed in lines. `mcopy` narrows the region
    to whole lines and clamps it to `FILE_REGEX_MAX` (`file/src/softmagic.c:1411-1440`), and
    `magiccheck` then runs one `regexec` over the whole region. The compile is
    `REG_EXTENDED | REG_NEWLINE | REGEX_ICASE(m)` (`file/src/softmagic.c:2160`), where
    `REG_NEWLINE` does not depend on the flag, so `^` and `$` match at line boundaries and `.`
    stops at one whether or not `l` is set.

    PolyFile split the region on newlines and called `Pattern.match` on each line instead, which
    anchored every pattern to a line start, and which reached `regexec`'s subject through neither
    `RegexType.subject` nor the byte clamp, so neither the NUL rule that issue #3517 fixed nor
    `FILE_REGEX_MAX` applied under `l`.

    Every verdict these tests assert is what `file -b -k` reports for the same definition and
    input, checked against libmagic 5.48 built from the `file` submodule.
    """

    UNANCHORED: str = "0\tregex/4l\t=beta\tfound\n"
    """Looks for `beta` anywhere within the first four lines."""

    @staticmethod
    def found(definitions: str, data: bytes) -> bool:
        """Reports whether the `found` message of the definition's `regex` test appears.

        Args:
            definitions: The contents of a libmagic definition file, with tab separated columns.
            data: The bytes to classify.

        Returns:
            True if some match carries the `found` message.
        """
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "regex_line_limit"
            path.write_text(definitions)
            return any("found" in str(match) for match in MagicMatcher.parse(path).match(data))

    def test_a_pattern_matches_part_way_into_a_line(self):
        """`beta` three characters into line two used to be missed, because `l` anchored.

        This is the reproducer from issue #3525. 31 of the 40 shipped `regex/...l` tests carry a
        pattern that does not begin with `^`, so each of them could only match at a line start.
        """
        self.assertTrue(self.found(self.UNANCHORED, b"alpha\nxxbeta\ngamma\n"))

    def test_the_line_count_still_bounds_the_scan(self):
        """Widening the scan must not reach past the declared number of lines."""
        self.assertTrue(self.found(self.UNANCHORED, b"a\nb\nc\nxxbeta\ne\n"))
        self.assertFalse(self.found(self.UNANCHORED, b"a\nb\nc\nd\nxxbeta\n"))

    def test_a_crlf_pair_counts_as_one_line_break(self):
        """Counting the `\\r` of a `\\r\\n` pair as a line of its own would halve the budget.

        `mcopy` finds the `\\n` and steps past it (`file/src/softmagic.c:1433-1436`), so the four
        lines this input is allowed reach the one that holds `beta`.
        """
        self.assertTrue(self.found(self.UNANCHORED, b"a\r\nb\r\nc\r\nxxbeta\r\ne\r\n"))

    def test_a_caret_still_anchors_at_a_line_start(self):
        """`REG_NEWLINE` makes `^` match at a line start and nowhere else."""
        anchored = "0\tregex/4l\t=^beta\tfound\n"
        self.assertTrue(self.found(anchored, b"alpha\nbeta\ngamma\n"))
        self.assertFalse(self.found(anchored, b"alpha\nxxbeta\ngamma\n"))

    def test_a_dollar_still_matches_at_a_line_end(self):
        """`REG_NEWLINE` makes `$` match before a newline, not only at the end of the region."""
        at_line_end = "0\tregex/4l\t=beta$\tfound\n"
        self.assertTrue(self.found(at_line_end, b"alphabeta\nxx\nyy\nzz\n"))
        self.assertFalse(self.found(at_line_end, b"alpha\nbetaxx\nyy\nzz\n"))

    def test_a_dot_does_not_cross_a_newline(self):
        """One `regexec` over a multi-line region must still not let `.` span the lines."""
        spanning = "0\tregex/4l\t=beta.gamma\tfound\n"
        self.assertFalse(self.found(spanning, b"beta\ngamma\nzz\nyy\n"))
        self.assertTrue(self.found(spanning, b"betaXgamma\nzz\nyy\nww\n"))

    def test_the_region_still_stops_at_a_nul(self):
        """Issue #3517's NUL rule never applied under `l`, because `l` skipped `subject`.

        Both inputs hold a NUL, so both are binary and the `b` flag puts the test in the pass that
        runs on them (`file/src/softmagic.c:249-253`). Only the NUL that precedes `beta` hides it.
        """
        binary = "0\tregex/4lb\t=beta\tfound\n"
        self.assertTrue(self.found(binary, b"xxbeta\nzz\x00\nyy\nww\n"))
        self.assertFalse(self.found(binary, b"xx\x00beta\nzz\nyy\nww\n"))

    def test_the_region_still_loses_its_last_byte(self):
        """A file with no line terminator at all is scanned whole, and so loses its last byte.

        `magiccheck` overwrites the region's last byte with the NUL that terminates its copy, so
        `beta` at the very end of the file is out of reach and `betaZ` is not. PolyFile used to
        report no match either way, because its per-line loop gave up on finding no newline.
        """
        self.assertFalse(self.found(self.UNANCHORED, b"xxbeta"))
        self.assertTrue(self.found(self.UNANCHORED, b"xxbetaZ"))

    def test_the_walk_passes_over_a_terminator_it_lands_on(self):
        """The line walk resumes one byte past the line it just took, skipping a blank line.

        `mcopy` steps past the terminator and then the `for` increment steps again
        (`file/src/softmagic.c:1433-1437`), so a terminator sitting in that second position is not
        counted. Four blank-separated lines therefore cost three of the four the budget allows,
        and `beta` is still in reach; a budget of two runs out before it.
        """
        self.assertTrue(self.found(self.UNANCHORED, b"a\n\n\n\nxxbeta\n"))
        self.assertFalse(self.found("0\tregex/2l\t=beta\tfound\n", b"a\n\n\n\nxxbeta\n"))

    def test_running_out_of_lines_widens_the_region(self):
        """An unterminated last line is searched, rather than dropped.

        Running out of terminators before the line count is reached puts the region back to the
        whole byte budget (`file/src/softmagic.c:1438-1439`). With a budget of three lines this
        input runs out and its unterminated tail is searched; with a budget of two the budget is
        spent on the two terminated lines and the tail is left out.
        """
        self.assertTrue(self.found("0\tregex/3l\t=beta\tfound\n", b"a\nb\nxxbetaZ"))
        self.assertFalse(self.found("0\tregex/2l\t=beta\tfound\n", b"a\nb\nxxbetaZ"))

    def test_a_line_budget_over_8_kib_is_clamped(self):
        """`regex/128l` asks for 10240 bytes and gets 8192, which PolyFile did not model.

        `bytecnt` is `linecnt * 80` clamped to `ms->regex_max`, which `apprentice.c:573` seeds
        with `FILE_REGEX_MAX` (`file/src/softmagic.c:1417-1422`). 19 shipped definitions declare
        `regex/128l`, so a long first line used to let them match bytes libmagic cannot reach.
        """
        clamped = "0\tregex/128l\t=beta\tfound\n"
        self.assertTrue(self.found(clamped, b"a" * 8000 + b"beta" + b"a" * 2000))
        self.assertFalse(self.found(clamped, b"a" * 9000 + b"beta" + b"a" * 2000))
