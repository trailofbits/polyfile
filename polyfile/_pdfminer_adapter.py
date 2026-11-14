"""PDFminer imports and document factories qualified by the PDF contract tests."""

from typing import Any

from pdfminer import settings
from pdfminer.ascii85 import ascii85decode, asciihexdecode
from pdfminer.ccitt import ccittfaxdecode
from pdfminer.lzw import lzwdecode
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdftypes import PDFNotImplementedError
from pdfminer.runlength import rldecode
from pdfminer.pdfparser import PDFParser as PDFMinerParser, PDFStream, PDFObjRef
from pdfminer.pdfparser import safe_int
from pdfminer.psparser import (
    PSBaseParserToken,
    PSKeyword,
    PSObject,
    PSLiteral,
    PSStackEntry,
    PSSyntaxError,
)
from pdfminer.pdfdocument import (
    PDFDocument,
    PDFXRef,
    KWD,
    PDFNoValidXRef,
    PSEOF,
    dict_value,
    LITERAL_XREF,
    LITERAL_OBJSTM,
    LITERAL_CATALOG,
    DecipherCallable,
    PDFObjectNotFound,
)
from pdfminer.pdftypes import (
    LIT,
    LITERALS_FLATE_DECODE,
    LITERALS_ASCIIHEX_DECODE,
    LITERALS_CCITTFAX_DECODE,
    LITERALS_RUNLENGTH_DECODE,
    LITERAL_CRYPT,
    LITERALS_LZW_DECODE,
    LITERALS_DCT_DECODE,
    LITERALS_JBIG2_DECODE,
    LITERALS_ASCII85_DECODE,
    int_value,
    apply_png_predictor,
)

from pdfminer.pdfdocument import PDFBaseXRef, PDFXRefFallback, PDFXRefStream
from pdfminer.pdftypes import list_value
from pdfminer.pdftypes import PDFException, decipher_all, stream_value


class AdapterPDFDocument(PDFDocument):
    """Use document-local xref factories without patching PDFminer classes."""

    xref_class: type[PDFXRef] = PDFXRef
    fallback_xref_class: type[PDFXRefFallback] = PDFXRefFallback

    def __init__(
        self, parser: PDFMinerParser, password: str = "", caching: bool = True,
        fallback: bool = True,
    ) -> None:
        self.caching = caching
        self.xrefs: list[PDFBaseXRef] = []
        self.info: list[dict[str, Any]] = []
        self.catalog: dict[str, Any] = {}
        self.encryption: tuple[Any, Any] | None = None
        self.decipher: DecipherCallable | None = None
        self._parser = parser
        self._cached_objs: dict[int, tuple[object, int]] = {}
        self._parsed_objs: dict[int, tuple[list[object], int]] = {}
        parser.set_document(self)
        self.is_printable = self.is_modifiable = self.is_extractable = True
        self._load_xrefs(parser, fallback)
        self._load_trailers(password)
        if self.catalog.get("Type") is not LITERAL_CATALOG and settings.STRICT:
            raise PDFSyntaxError("Catalog not found!")

    def _load_xrefs(self, parser: PDFMinerParser, fallback: bool) -> None:
        try:
            self.read_xref_from(parser, self.find_xref(parser), self.xrefs)
        except PDFNoValidXRef:
            if fallback:
                parser.fallback = True
                xref = self.fallback_xref_class()
                xref.load(parser)
                self.xrefs.append(xref)

    def _load_trailers(self, password: str) -> None:
        for xref in self.xrefs:
            trailer = xref.get_trailer()
            if not trailer:
                continue
            if "Encrypt" in trailer:
                identifiers = list_value(trailer["ID"]) if "ID" in trailer else (b"", b"")
                self.encryption = (identifiers, dict_value(trailer["Encrypt"]))
                self._initialize_password(password)
            if "Info" in trailer:
                self.info.append(dict_value(trailer["Info"]))
            if "Root" in trailer:
                self.catalog = dict_value(trailer["Root"])
                return
        raise PDFSyntaxError("No /Root object! - Is this really a PDF?")

    def read_xref_from(
        self, parser: PDFMinerParser, start: int, xrefs: list[PDFBaseXRef],
    ) -> None:
        parser.seek(start)
        parser.reset()
        try:
            pos, token = parser.nexttoken()
        except PSEOF as error:
            raise PDFNoValidXRef("Unexpected EOF while reading PDF cross references") from error
        if isinstance(token, int):
            parser.seek(pos)
            parser.reset()
            xref: PDFBaseXRef = PDFXRefStream()
        else:
            if token is parser.KEYWORD_XREF:
                parser.nextline()
            xref = self.xref_class()
        xref.load(parser)
        xrefs.append(xref)
        trailer = xref.get_trailer()
        for key in ("XRefStm", "Prev"):
            if key in trailer:
                self.read_xref_from(parser, int_value(trailer[key]), xrefs)

    def getobj(self, objid: int) -> object:
        """Return an indirect object through this document's decryption hook.

        Args:
            objid: The indirect object identifier.

        Returns:
            The parsed object, reusing it when document caching is enabled.

        Raises:
            PDFObjectNotFound: If no cross-reference entry resolves the object.
        """
        if not self.xrefs:
            raise PDFException("PDFDocument is not initialized")
        if objid in self._cached_objs:
            return self._cached_objs[objid][0]
        obj, generation = self._load_object(objid)
        if isinstance(obj, PDFStream):
            obj.set_objid(objid, generation)
        if self.caching:
            self._cached_objs[objid] = obj, generation
        return obj

    def _load_object(self, objid: int) -> tuple[object, int]:
        for xref in self.xrefs:
            try:
                stream_id, index, generation = xref.get_pos(objid)
            except KeyError:
                continue
            try:
                if stream_id is not None:
                    stream = stream_value(self.getobj(stream_id))
                    obj = self._getobj_objstm(stream, index, objid)
                else:
                    obj = self._getobj_parse(index, objid)
                    if self.decipher:
                        obj = self._decipher_object(objid, generation, obj)
                return obj, generation
            except (PSEOF, PDFSyntaxError):
                continue
        raise PDFObjectNotFound(objid)

    def _decipher_object(self, objid: int, generation: int, obj: object) -> object:
        assert self.decipher is not None
        return decipher_all(self.decipher, objid, generation, obj)


__all__ = [
    "settings",
    "safe_int",
    "ascii85decode",
    "asciihexdecode",
    "ccittfaxdecode",
    "lzwdecode",
    "PDFSyntaxError",
    "PDFNotImplementedError",
    "rldecode",
    "PDFMinerParser",
    "PDFStream",
    "PDFObjRef",
    "PSBaseParserToken",
    "PSKeyword",
    "PSObject",
    "PSLiteral",
    "PSStackEntry",
    "PSSyntaxError",
    "PDFDocument",
    "PDFXRef",
    "KWD",
    "PDFNoValidXRef",
    "PSEOF",
    "dict_value",
    "LITERAL_XREF",
    "LITERAL_OBJSTM",
    "LITERAL_CATALOG",
    "DecipherCallable",
    "PDFObjectNotFound",
    "LIT",
    "LITERALS_FLATE_DECODE",
    "LITERALS_ASCIIHEX_DECODE",
    "LITERALS_CCITTFAX_DECODE",
    "LITERALS_RUNLENGTH_DECODE",
    "LITERAL_CRYPT",
    "LITERALS_LZW_DECODE",
    "LITERALS_DCT_DECODE",
    "LITERALS_JBIG2_DECODE",
    "LITERALS_ASCII85_DECODE",
    "int_value",
    "apply_png_predictor",
    "PDFBaseXRef",
    "PDFXRefStream",
    "PDFXRefFallback",
    "AdapterPDFDocument",
]
