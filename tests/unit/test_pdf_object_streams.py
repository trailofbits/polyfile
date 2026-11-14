"""Compressed indirect objects map their actual decoded source rather than encoded offsets."""

import base64
from typing import BinaryIO, cast

from pdfminer.pdfparser import PDFStream
from pdfminer.pdfdocument import LITERAL_OBJSTM
import pytest

from polyfile.fileutils import FileStream
from polyfile.pdf import (
    InstrumentedPDFDocument, PDFObjectStream, PDFParser, RawPDFStream,
    PDFSyntaxError, has_provenance, pdf_parser, settings,
)
from polyfile.polyfile import Match, Matcher
from polyfile.analysis import AnalysisLimits
from pdf_fixtures import CATALOG, object_stream_pdf

BODIES = [b"1.25", b"<< /\xff 42 >>", b"[1 (a\\nb)]", b"1 0 R"]


@pytest.mark.parametrize("compressed", [False, True])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("source_base", [0, 117])
def test_object_stream_values_are_emitted_under_one_decoded_buffer(
    compressed: bool, source: str, source_base: int,
) -> None:
    data, decoded = object_stream_pdf(BODIES, compressed=compressed)
    matcher = Matcher(parse=False)
    parent = Match(
        "PDF", None, relative_offset=source_base, length=len(data), matcher=matcher, source=source,
    )
    if source == "decoded:0":
        assert parent.analysis_context.next_source() == "decoded:0"
    with FileStream(b"prefix" + data + b"suffix", start=6, length=len(data)) as outer:
        with FileStream(outer) as stream:
            nodes = list(pdf_parser(stream, parent))
    objects = [node for node in nodes if node.name == "PDFObject"]
    assert len(objects) == 8
    compressed_objects = [node for node in objects if node.source != source]
    assert len(compressed_objects) == 4
    decoded_nodes = [node for node in nodes if node.name == "decoded_content"]
    buffer = next(node for node in decoded_nodes if node.decoded == decoded)
    assert len([node for node in decoded_nodes if node.source == buffer.source]) == 1
    assert base64.b64decode(buffer.to_obj()["decoded"]) == decoded
    assert buffer.offset == 0
    for body, node in zip(BODIES, compressed_objects, strict=True):
        output = node.to_obj()
        assert node.parent is buffer
        assert (output["source"], output["offset"], output["size"]) == (
            buffer.source, decoded.index(body), len(body),
        )
        assert node.children
        assert all(child.source == buffer.source for child in node.children)
    dictionary = compressed_objects[1].children[0]
    assert any(child.name == "KeyValuePair" for child in dictionary.children)


@pytest.mark.parametrize("caching", [False, True])
def test_lookup_boundary_returns_tagged_values_and_reuses_the_decoded_source(caching: bool) -> None:
    data, _ = object_stream_pdf(BODIES)
    with FileStream(data) as stream:
        document = InstrumentedPDFDocument(
            PDFParser(cast(BinaryIO, RawPDFStream(stream))), caching=caching,
        )
        values = [document.getobj(number) for number in range(3, 7)]
        for number, value in enumerate(values, 3):
            assert has_provenance(value)
            assert getattr(value, "pdf_source") == "decoded:0"
            repeated = document.getobj(number)
            assert getattr(repeated, "pdf_source") == "decoded:0"
            if caching:
                assert repeated is value


@pytest.mark.parametrize("bodies", [[b"42", b"1 0 R"], [b"1", b"2", b"3"], [b"42"]])
def test_pending_numbers_and_references_keep_their_object_boundaries(bodies: list[bytes]) -> None:
    data, decoded = object_stream_pdf(bodies)
    parent = Match("PDF", None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    objects = [node for node in nodes if node.name == "PDFObject" and node.source != "file"]
    assert len(objects) == len(bodies)
    for node, body in zip(objects, bodies, strict=True):
        assert decoded[node.offset:node.offset + node.length] == body


def test_compressed_catalog_can_be_loaded_before_its_stream_is_emitted() -> None:
    data, decoded = object_stream_pdf([CATALOG[0]], root=3)
    parent = Match("PDF", None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    catalog = next(node for node in nodes if node.name == "PDFObject" and node.match == 3)
    assert catalog.source != "file"
    assert catalog.offset == decoded.index(CATALOG[0])


def test_standalone_object_stream_parser_records_decoded_positions() -> None:
    stream = PDFObjectStream(
        PDFStream({"Type": LITERAL_OBJSTM, "N": 1}, b"7 0 1.25 "),
        pdf_offset=100, pdf_bytes=9,
    )
    document = object.__new__(InstrumentedPDFDocument)
    values, count = document._get_objects(stream)
    value = values[2]
    assert count == 1
    assert value == 1.25
    assert has_provenance(value)
    assert (value.pdf_offset, value.pdf_bytes) == (4, 4)
    assert getattr(value, "pdf_source") == "decoded:0"


def test_decoded_object_emission_respects_the_analysis_depth_limit() -> None:
    data, _ = object_stream_pdf(BODIES)
    matcher = Matcher(parse=False, limits=AnalysisLimits(max_depth=0))
    parent = Match("PDF", None, length=len(data), matcher=matcher)
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    assert not any(node.name == "PDFObject" and node.source != "file" for node in nodes)
    assert any(
        node.name == "decoded_content" and node.analysis_status == "limited" for node in nodes
    )


def test_unsupported_object_stream_filter_preserves_the_remaining_physical_structure() -> None:
    data, _ = object_stream_pdf(BODIES)
    data = data.replace(b"/FlateDecode", b"/WrongDecode")
    parent = Match("PDF", None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    assert len([node for node in nodes if node.name == "PDFObject"]) == 4
    assert parent.analysis_status == "unsupported"
    assert "WrongDecode" in str(parent.analysis_message)


@pytest.mark.parametrize(
    ("attributes", "data", "message"),
    [
        ({"N": 1}, b"1", "Not an object stream"),
        ({"Type": LITERAL_OBJSTM}, b"1", "Missing /N"),
        ({"Type": LITERAL_OBJSTM, "N": 1}, b"obj ", "Keyword obj/endobj"),
    ],
)
def test_object_stream_strict_errors_remain_actionable(
    monkeypatch: pytest.MonkeyPatch, attributes: dict[str, object], data: bytes, message: str,
) -> None:
    monkeypatch.setattr(settings, "STRICT", True)
    stream = PDFObjectStream(PDFStream(attributes, data), pdf_offset=100, pdf_bytes=len(data))
    document = object.__new__(InstrumentedPDFDocument)
    with pytest.raises(PDFSyntaxError, match=message):
        document._get_objects(stream)
