from unittest import TestCase

from polyfile.der import (
    DERHeader, DERMismatch, DERSpecification, InvalidDER, format_value, read_length, read_tag,
    tag_name
)


def tlv(tag: int, value: bytes) -> bytes:
    """Encodes a tag-length-value triple using the short form of the length."""
    assert len(value) < 128
    return bytes((tag, len(value))) + value


class ReadTagTest(TestCase):
    def test_low_tag_number(self):
        self.assertEqual((0x10, 1), read_tag(b"\x30\x03\x02\x01\x00", 0))

    def test_class_and_constructed_bits_are_ignored(self):
        self.assertEqual(read_tag(b"\x02\x00\x00", 0), read_tag(b"\xc2\x00\x00", 0))

    def test_context_specific_zero_reads_as_eoc(self):
        tag, _ = read_tag(b"\xa0\x03\x02\x01\x02", 0)
        self.assertEqual("eoc", tag_name(tag))

    def test_high_tag_number(self):
        # `gettag` in der.c accumulates only the octets that have their most significant bit
        # set, and leaves the last octet of the tag for `getlength` to read. PolyFile keeps
        # that behavior so that it reports what `file` reports.
        self.assertEqual((31 * 128 + 1, 2), read_tag(b"\x1f\x81\x00\x00\x00", 0))

    def test_empty_data(self):
        with self.assertRaises(InvalidDER):
            read_tag(b"", 0)

    def test_truncated_high_tag_number(self):
        with self.assertRaises(InvalidDER):
            read_tag(b"\x1f", 0)


class ReadLengthTest(TestCase):
    def test_short_form(self):
        self.assertEqual((3, 2), read_length(b"\x30\x03\x02\x01\x00\x00", 1))

    def test_long_form(self):
        self.assertEqual((0x0A72, 4), read_length(b"\x30\x82\x0a\x72" + b"\x00" * 0x0A72, 1))

    def test_value_past_the_end_of_the_data(self):
        with self.assertRaises(InvalidDER):
            read_length(b"\x30\x82\xff\xff\x00\x00", 1)

    def test_short_form_value_ending_at_the_end_of_the_data(self):
        # `getlength` in der.c rejects a short form length whose value ends on the final byte of the
        # input. PolyFile keeps that behavior so that it reports what `file` reports.
        with self.assertRaises(InvalidDER):
            read_length(b"\x30\x03\x02\x01\x00", 1)
        self.assertEqual((3, 2), read_length(b"\x30\x03\x02\x01\x00\x00", 1))


class FormatValueTest(TestCase):
    def test_printable_string(self):
        self.assertEqual("US", format_value(0x13, b"US"))

    def test_utf8_string(self):
        self.assertEqual("Trail of Bits", format_value(0x0C, b"Trail of Bits"))

    def test_utc_time(self):
        self.assertEqual("2023-01-11 23:59:49 GMT", format_value(0x17, b"230111235949Z"))

    def test_short_utc_time_falls_back_to_hex(self):
        self.assertEqual("323330313131", format_value(0x17, b"230111"))

    def test_object_identifier_is_hex(self):
        self.assertEqual("550406", format_value(0x06, bytes.fromhex("550406")))

    def test_hex_is_truncated_to_the_libmagic_buffer(self):
        # der.c formats into a 128 byte buffer, so it emits at most 63 bytes as 126 hex digits.
        self.assertEqual("ab" * 63, format_value(0x02, b"\xab" * 100))

    def test_text_is_truncated_to_the_libmagic_buffer(self):
        self.assertEqual("a" * 127, format_value(0x13, b"a" * 200))


class DERHeaderTest(TestCase):
    def test_parse(self):
        data = tlv(0x30, tlv(0x02, b"\x00")) + b"\x00"
        header = DERHeader.parse(data, 0)
        self.assertEqual("seq", header.name)
        self.assertEqual(0, header.start)
        self.assertEqual(2, header.header_length)
        self.assertEqual(3, header.length)
        self.assertEqual(5, header.end)

    def test_parse_at_an_offset(self):
        data = b"\xff\xff" + tlv(0x02, b"\x2a") + b"\x00"
        header = DERHeader.parse(data, 2)
        self.assertEqual("int", header.name)
        self.assertEqual("2a", header.formatted_value(data))


class DERSpecificationTest(TestCase):
    def setUp(self):
        self.data = tlv(0x02, bytes.fromhex("010001")) + b"\x00"
        self.header = DERHeader.parse(self.data, 0)

    def match(self, specification: str):
        return DERSpecification(specification).match(self.header, self.data)

    def test_tag_only(self):
        self.assertIsNone(self.match("int"))

    def test_wrong_tag(self):
        with self.assertRaises(DERMismatch):
            self.match("seq")

    def test_tag_and_length(self):
        self.assertIsNone(self.match("int3"))

    def test_wrong_length(self):
        with self.assertRaises(DERMismatch):
            self.match("int2")

    def test_tag_length_and_value(self):
        self.assertEqual("010001", self.match("int3=010001"))

    def test_wrong_value(self):
        with self.assertRaises(DERMismatch):
            self.match("int3=010002")

    def test_wildcard_value(self):
        self.assertEqual("010001", self.match("int3=x"))

    def test_value_without_a_length(self):
        self.assertEqual("010001", self.match("int=x"))

    def test_a_tag_name_is_not_matched_by_a_prefix_of_another(self):
        # "int" must not satisfy a test for a tag whose name merely starts the same way.
        with self.assertRaises(DERMismatch):
            self.match("int_str=x")

    def test_trailing_garbage(self):
        with self.assertRaises(DERMismatch):
            self.match("int!3")
