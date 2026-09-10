import base64
import gzip
import subprocess
import sys
import time
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple
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
    # `test_file_corpus` asserts that each of these stems still fails, so fixing one of these bugs
    # includes deleting its stems from this map in the same change. Each value is the issue that
    # has to be fixed first, and the trailing comment names what blocks the stem after that.
    # Issue #3480 tracks the whole set.
    #
    # This test ships two sidecars, which the harness loads, and a `.flags` of `k`. PolyFile
    # reports all four names as separate matches, each with its own text-encoding description, so
    # what is left is the joined form: #3491 for the `\012- ` separator and #3477 for the strength
    # order the parts appear in. Splitting the expected string on `\012- ` here instead would drop
    # #3491 from that list.
    "multiple": 3491,       # then #3477
    # Text tests run against the raw bytes, so the SVG test never matches a UTF-16 file and
    # PolyFile reports only the text-encoding description.
    "utf16xmlsvg": 3489,
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
    `\\012- `. PolyFile always reports every match and never builds that join (issue #3491), so
    the harness only reports the flags rather than emulating them.

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
            'a2ml:38', 'a2ml:44', 'andrew:30', 'android:221', 'apple:6', 'archive:583',
            'assembler:11', 'assembler:13', 'assembler:15', 'assembler:17', 'assembler:5',
            'assembler:7', 'assembler:9', 'audio:645', 'audio:648', 'bioinformatics:156',
            'c-lang:10', 'c-lang:103', 'c-lang:107', 'c-lang:111', 'c-lang:22', 'c-lang:25',
            'c-lang:29', 'c-lang:32', 'c-lang:35', 'c-lang:38', 'c-lang:41', 'c-lang:44',
            'c-lang:47', 'c-lang:50', 'c-lang:59', 'c-lang:64', 'c-lang:68', 'c-lang:72',
            'c-lang:77', 'c-lang:8', 'c-lang:81', 'c-lang:85', 'c-lang:89', 'c-lang:95', 'cad:317',
            'cad:365', 'clojure:23', 'clojure:26', 'clojure:29', 'commands:101', 'commands:104',
            'commands:106', 'commands:111', 'commands:113', 'commands:115', 'commands:118',
            'commands:121', 'commands:123', 'commands:125', 'commands:128', 'commands:131',
            'commands:133', 'commands:138', 'commands:14', 'commands:140', 'commands:146',
            'commands:148', 'commands:150', 'commands:152', 'commands:164', 'commands:167',
            'commands:169', 'commands:171', 'commands:174', 'commands:18', 'commands:191',
            'commands:213', 'commands:23', 'commands:231', 'commands:232', 'commands:233',
            'commands:25', 'commands:27', 'commands:29', 'commands:34', 'commands:36',
            'commands:38', 'commands:40', 'commands:43', 'commands:45', 'commands:47',
            'commands:49', 'commands:51', 'commands:53', 'commands:55', 'commands:57',
            'commands:59', 'commands:61', 'commands:64', 'commands:66', 'commands:68', 'commands:7',
            'commands:70', 'commands:72', 'commands:74', 'commands:76', 'commands:80',
            'commands:83', 'commands:87', 'commands:91', 'commands:95', 'commands:99', 'csv:6',
            'ctags:6', 'diff:48', 'fonts:132', 'fonts:6', 'forth:10', 'forth:16', 'fortran:6',
            'games:248', 'games:411', 'games:412', 'gentoo:44', 'gimp:14', 'gimp:7', 'gnu:170',
            'images:2657', 'inform:9', 'java:19', 'java:49', 'java:51', 'javascript:10',
            'javascript:12', 'javascript:14', 'javascript:16', 'javascript:30', 'javascript:34',
            'javascript:38', 'javascript:42', 'javascript:46', 'javascript:50', 'javascript:54',
            'javascript:6', 'javascript:60', 'javascript:8', 'json:12', 'json:6', 'k9:28', 'kde:10',
            'kde:6', 'kde:8', 'lex:10', 'lex:12', 'linux:366', 'linux:369', 'linux:370', 'linux:54',
            'linux:938', 'lisp:16', 'lisp:18', 'lisp:20', 'lisp:22', 'lisp:24', 'lisp:26',
            'lisp:77', 'lua:11', 'lua:13', 'lua:15', 'lua:17', 'lua:9', 'm4:5', 'm4:8', 'magic:8',
            'mail.news:11', 'mail.news:13', 'mail.news:15', 'mail.news:17', 'mail.news:19',
            'mail.news:21', 'mail.news:23', 'mail.news:25', 'mail.news:27', 'mail.news:29',
            'mail.news:31', 'mail.news:33', 'mail.news:35', 'mail.news:49', 'mail.news:7',
            'mail.news:9', 'make:15', 'make:19', 'make:6', 'misctools:104', 'misctools:6',
            'misctools:99', 'msdos:26', 'msdos:28', 'msx:79', 'nim-lang:7', 'pascal:5', 'perl:10',
            'perl:12', 'perl:14', 'perl:16', 'perl:18', 'perl:20', 'perl:22', 'perl:24', 'perl:36',
            'perl:40', 'perl:47', 'perl:48', 'perl:49', 'perl:50', 'perl:51', 'perl:52', 'perl:53',
            'perl:54', 'perl:8', 'psl:9', 'python:262', 'python:271', 'python:277', 'python:295',
            'python:303', 'python:309', 'python:9', 'revision:7', 'ringdove:12', 'ringdove:13',
            'ringdove:14', 'ringdove:15', 'ringdove:16', 'ringdove:17', 'ringdove:18',
            'ringdove:19', 'ringdove:20', 'ringdove:21', 'ringdove:22', 'ringdove:25',
            'ringdove:26', 'ringdove:27', 'ringdove:28', 'ringdove:29', 'ringdove:32', 'ringdove:6',
            'ringdove:7', 'ringdove:8', 'ringdove:9', 'ruby:12', 'ruby:15', 'ruby:18', 'ruby:25',
            'ruby:31', 'ruby:37', 'ruby:44', 'ruby:50', 'ruby:9', 'securitycerts:4',
            'securitycerts:5', 'sgml:102', 'sgml:105', 'sgml:108', 'sgml:111', 'sgml:115',
            'sgml:121', 'sgml:128', 'sgml:131', 'sgml:134', 'sgml:140', 'sgml:146', 'sgml:152',
            'sgml:153', 'sgml:154', 'sgml:160', 'sgml:161', 'sgml:162', 'sgml:17', 'sgml:57',
            'sgml:6', 'sgml:62', 'sgml:64', 'sgml:66', 'sgml:74', 'sgml:78', 'sgml:81', 'sgml:84',
            'sgml:87', 'sgml:90', 'sgml:93', 'sgml:96', 'sgml:99', 'sisu:11', 'sisu:14', 'sisu:17',
            'sisu:5', 'sisu:8', 'sketch:6', 'softquad:26', 'subtitle:19', 'subtitle:25', 'tcl:11',
            'tcl:13', 'tcl:15', 'tcl:17', 'tcl:19', 'tcl:21', 'tcl:25', 'tcl:28', 'tcl:7', 'tcl:9',
            'terminfo:49', 'tex:107', 'tex:108', 'tex:109', 'tex:110', 'tex:111', 'tex:112',
            'tex:113', 'tex:114', 'tex:115', 'tex:116', 'tex:117', 'tex:119', 'tex:121', 'tex:123',
            'tex:125', 'tex:127', 'tex:133', 'tex:135', 'tex:137', 'tex:139', 'tex:141', 'tex:143',
            'tex:145', 'tex:147', 'tex:149', 'tex:151', 'tex:153', 'tex:155', 'tex:157', 'tex:159',
            'tex:22', 'tex:23', 'tex:24', 'tex:25', 'tex:26', 'tex:27', 'tex:28', 'tex:29',
            'tex:30', 'tex:31', 'tex:32', 'tex:33', 'tex:34', 'tex:47', 'tex:49', 'tex:51',
            'tex:53', 'tex:61', 'tex:64', 'tex:67', 'tex:70', 'tex:73', 'tex:76', 'tex:79',
            'tex:82', 'tex:85', 'tex:88', 'tex:92', 'tex:95', 'tex:96', 'tex:97', 'tex:98',
            'tex:99', 'troff:12', 'troff:15', 'troff:18', 'troff:23', 'troff:26', 'troff:31',
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
            matches = {str(match) for match in matcher.match(f.read())}
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
