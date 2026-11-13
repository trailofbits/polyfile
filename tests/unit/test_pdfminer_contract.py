"""Qualify the PDFminer APIs used by PolyFile's structural adapter."""

from io import BytesIO
import builtins
from typing import BinaryIO, cast

from pdfminer.pdfdocument import PDFDocument, PDFXRef
from pdfminer.pdfparser import PDFParser as NativePDFParser
import pytest

from polyfile.pdf import InstrumentedPDFDocument, PDFParser, RawPDFStream
from polyfile.fileutils import FileStream
from polyfile import _LazyPDFParser
from polyfile.polyfile import Match, Matcher
from polyfile import pdf_compat
from pdf_fixtures import CATALOG, pdf_fixture


def test_instrumentation_does_not_replace_native_xref_methods() -> None:
    assert PDFXRef.load.__module__ == "pdfminer.pdfdocument"
    assert PDFXRef.load_trailer.__module__ == "pdfminer.pdfdocument"
    document = PDFDocument(NativePDFParser(BytesIO(pdf_fixture(CATALOG))))
    assert document.catalog["Pages"].objid == 2


@pytest.mark.parametrize("data", [pdf_fixture(CATALOG), pdf_fixture(CATALOG, b"")])
def test_document_local_xrefs_and_root_recovery(data: bytes) -> None:
    native_trailer = PDFXRef.get_trailer
    with FileStream(data) as stream:
        document = InstrumentedPDFDocument(PDFParser(cast(BinaryIO, RawPDFStream(stream))))
        assert list(document.xrefs[0].get_objids()) == [1, 2]
        catalog = document.getobj(1)
        assert isinstance(catalog, dict)
        assert catalog["Pages"].objid == 2
    assert PDFXRef.get_trailer is native_trailer


@pytest.mark.parametrize("suffix", [b"junk\n", b"0\n", b"stream\n"])
def test_fallback_preserves_trailers_with_trailing_tokens(suffix: bytes) -> None:
    data = pdf_fixture(CATALOG)
    data = data[:data.index(b"startxref")] + b"%%EOF\n" + suffix
    with FileStream(data) as stream:
        document = InstrumentedPDFDocument(PDFParser(cast(BinaryIO, RawPDFStream(stream))))
        assert document.xrefs[0].get_trailer()["Root"].objid == 1
        assert document.catalog["Pages"].objid == 2


@pytest.mark.parametrize("installed", ["20251230", "20990101"])
def test_unqualified_version_preserves_classification_and_reports_status(
    monkeypatch: pytest.MonkeyPatch, installed: str,
) -> None:
    monkeypatch.setattr(pdf_compat, "version", lambda _: installed)
    parent = Match("PDF", None, length=4, matcher=Matcher(parse=False))
    assert list(_LazyPDFParser().parse(FileStream(b"%PDF"), parent)) == []
    result = parent.to_obj()
    assert result["analysis_status"] == "unsupported"
    assert installed in result["analysis_message"]
    assert pdf_compat.SUPPORTED_PDFMINER in result["analysis_message"]


def test_missing_pdfminer_has_an_actionable_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_: str) -> str:
        raise pdf_compat.PackageNotFoundError("pdfminer.six")

    monkeypatch.setattr(pdf_compat, "version", missing)
    assert "not installed" in str(pdf_compat.pdfminer_compatibility_error())


def test_unavailable_adapter_api_reports_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    original = builtins.__import__

    def import_module(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "polyfile" and "pdf" in fromlist:
            raise ImportError("missing PDFminer parser interface")
        return original(name, globals, locals, fromlist, level)

    monkeypatch.setattr(_LazyPDFParser, "_actual_parser", None)
    monkeypatch.setattr(builtins, "__import__", import_module)
    parent = Match("PDF", None, length=4, matcher=Matcher(parse=False))
    assert list(_LazyPDFParser().parse(FileStream(b"%PDF"), parent)) == []
    assert parent.analysis_status == "unsupported"
    assert "missing PDFminer parser interface" in str(parent.analysis_message)
