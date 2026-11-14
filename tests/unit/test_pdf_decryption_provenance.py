"""Real encrypted PDFs retain container extents and isolate decrypted byte sources."""

from typing import BinaryIO, cast
from collections.abc import Iterator

from pdfminer.pdfdocument import PDFPasswordIncorrect
import pytest

from polyfile.fileutils import FileStream
from polyfile.pdf import (
    InstrumentedPDFDocument, PDFList, PDFParser, RawPDFStream, has_provenance, pdf_parser,
)
from polyfile.polyfile import Match, Matcher
from pdf_fixtures import CATALOG, encrypted_pdf, pdf_fixture

ARRAYS = [
    (b"[1 2]", 1, 0),
    (b"[]", 1, 0),
    (b"[[] []]", 3, 0),
    (b"[1.25 {secret} [] [2 {secret}]]", 3, 2),
    (b"<< /Nested [1 {secret} []] >>", 2, 1),
]


def descendants(node: Match) -> Iterator[Match]:
    """Yield an emitted subtree in document order."""
    yield node
    for child in node.children:
        yield from descendants(child)


@pytest.mark.parametrize("case", ARRAYS)
@pytest.mark.parametrize("encrypted", [False, True])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("source_base", [0, 117])
def test_decrypted_containers_and_children_reach_serialized_structure(
    case: tuple[bytes, int, int], encrypted: bool, source: str, source_base: int,
) -> None:
    body, array_count, secret_count = case
    data = encrypted_pdf(body) if encrypted else pdf_fixture(
        [*CATALOG, body.replace(b"{secret}", b"(abc)")],
    )
    if not encrypted:
        secret_count = 0
    parent = Match(
        "PDF", None, relative_offset=source_base, length=len(data),
        matcher=Matcher(parse=False), source=source,
    )
    with FileStream(b"prefix" + data, start=6) as stream:
        nodes = list(pdf_parser(stream, parent))
    obj = next(node for node in nodes if node.name == "PDFObject" and node.match == 3)
    subtree = list(descendants(obj))
    arrays = [node for node in subtree if node.name == "PDFList"]
    assert len(arrays) == array_count
    for array in arrays:
        output = array.to_obj()
        start, end = array.offset - source_base, array.offset - source_base + array.length
        assert data[start:start + 1] == b"["
        assert data[end - 1:end] == b"]"
        assert output["source"] == source
    decoded = [node for node in subtree if node.name == "decoded_content"]
    assert len(decoded) == secret_count
    assert len({node.source for node in decoded}) == secret_count
    for buffer in decoded:
        assert buffer.decoded == b"a\nb"
        assert (buffer.offset, buffer.length) == (0, 3)
        assert buffer.source != source
        assert buffer.parent is not None and buffer.parent.name == "PDFDeciphered"
        assert buffer.parent.source == source
        assert buffer.parent.length == 6


@pytest.mark.parametrize("caching", [False, True])
def test_document_lookup_retains_original_array_delimiters(caching: bool) -> None:
    data = encrypted_pdf(b"[1 {secret} []]")
    start = data.index(b"[1 ")
    end = data.index(b"\nendobj", start)
    with FileStream(data) as stream:
        document = InstrumentedPDFDocument(
            PDFParser(cast(BinaryIO, RawPDFStream(stream))), caching=caching,
        )
        value = document.getobj(3)
        assert isinstance(value, PDFList)
        assert (value.pdf_offset, value.pdf_bytes) == (start, end - start)
        assert all(has_provenance(item) for item in value)
        empty = value[2]
        assert isinstance(empty, PDFList)
        assert empty.pdf_bytes == 2
        assert document.getobj(3) == value


def test_bad_password_preserves_the_native_authentication_error() -> None:
    data = encrypted_pdf(b"[]")
    with FileStream(data) as stream:
        with pytest.raises(PDFPasswordIncorrect):
            InstrumentedPDFDocument(
                PDFParser(cast(BinaryIO, RawPDFStream(stream))), password="wrong",
            )
