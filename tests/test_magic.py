import base64
import gzip
import subprocess
import sys
import time
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterator, List, Optional, Set, Tuple
from unittest import TestCase
from uuid import UUID

# from polyfile import logger
import polyfile.der
import polyfile.magic
from polyfile.magic import MagicMatcher, MAGIC_DEFS, Match, MatchContext, SearchType, TestResult


# logger.setLevel(logger.TRACE)

FILE_TEST_DIR: Path = Path(__file__).parent.parent / "file" / "tests"

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
            'javascript:6', 'javascript:60', 'javascript:8', 'json:6', 'k9:28', 'kde:10', 'kde:6',
            'kde:8', 'lex:10', 'lex:12', 'linux:366', 'linux:369', 'linux:370', 'linux:54',
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
                            "gedcom", "cmd1", "cmd2", "cmd3", "cmd4", "jpeg-text", "jsonlines1",
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
        data = b"#!/bin/sh\nexec cat \"$@\"\n"
        result = next(iter(MagicMatcher.DEFAULT_INSTANCE.match(data)))[0]
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
