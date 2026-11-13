"""Instrumented PDF values keep truthful primitive and provenance interfaces."""

from io import BytesIO

from pdfminer.pdfdocument import LITERAL_CATALOG
import pytest

from polyfile.fileutils import FileStream
from polyfile.pdf import (
    PDFDeciphered,
    PDFDict,
    PDFList,
    PDFLiteral,
    PDFParser,
    PSBytes,
    PSInt,
    RawPDFStream,
    has_provenance,
    parse_object,
)
from polyfile.polyfile import Matcher


def test_provenance_detection_accepts_falsy_instrumented_values() -> None:
    token = PSInt(0, pdf_offset=7, pdf_bytes=1)
    assert not has_provenance(0)
    assert has_provenance(token)
    assert (token.pdf_offset, token.pdf_bytes) == (7, 1)


def test_list_loading_preserves_a_user_subclass() -> None:
    class Values(PDFList):
        pass

    token = PSInt(3, pdf_offset=7, pdf_bytes=1)
    values = Values.load([token])
    assert type(values) is Values
    assert values == [3]
    assert (values.pdf_offset, values.pdf_bytes) == (7, 1)


def test_deciphered_slices_use_the_base_byte_wrapper() -> None:
    value = PDFDeciphered(b"abc", original_bytes=b"encoded", pdf_offset=7, pdf_bytes=7)
    part = value[1:2]
    assert type(part) is PSBytes
    assert part == b"b"
    assert (part.pdf_offset, part.pdf_bytes) == (7, 7)


def test_dictionary_lookup_retains_pdfminer_singletons() -> None:
    literal = PDFLiteral("Catalog", pdf_offset=7, pdf_bytes=7)
    value = PDFDict({"Type": literal}, pdf_offset=0, pdf_bytes=20)
    assert value.get("Type") is LITERAL_CATALOG
    assert (value.pdf_offset, value.pdf_bytes) == (0, 20)


def test_pdf_parser_stack_accepts_null_values() -> None:
    parser = PDFParser(BytesIO(b""))
    parser.push((3, None))
    assert parser.pop(1) == [(3, None)]


def test_raw_pdf_reads_report_positions_within_the_selected_view() -> None:
    backing = FileStream(b"prefixabc", start=6)
    stream = RawPDFStream(FileStream(backing, start=1, length=2))
    first = stream.read(1)
    second = stream.read()
    assert (first, first.pdf_offset, first.pdf_bytes) == (b"b", 0, 1)
    assert (second, second.pdf_offset, second.pdf_bytes) == (b"c", 1, 1)


def test_unmappable_values_do_not_require_a_parent_match() -> None:
    assert list(parse_object(None, Matcher())) == []


def test_instrumented_values_report_a_missing_parent_match() -> None:
    token = PSInt(0, pdf_offset=7, pdf_bytes=1)
    with pytest.raises(ValueError, match="requires a parent match"):
        list(parse_object(token, Matcher()))
