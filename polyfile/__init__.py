from polyfile import (
    nes,
    jpeg,
    zipmatcher,
    zlibmatcher,
    simh,
    gzipmatcher,
    lzipmatcher,
    lz4matcher,
    zstdmatcher,
    compressmatcher,
    scomatcher,
    packmatcher,
    nitf,
    http,
    kaitaimatcher,
    languagematcher,
    pickles,
    polyfile
)

from polyfile import bzip2matcher, freezematcher, lrzipmatcher, lzmamatcher, tarmatcher, xzmatcher
from polyfile.analysis import AnalysisLimits
from polyfile.provenance import SourceSpan
from polyfile.__main__ import main
from polyfile.polyfile import __version__, InvalidMatch, Match, Matcher, Parser, PARSERS, register_parser, Submatch


# Lazy PDF parser registration
# This registers immediately but defers importing pdf.py (and pdfminer) until first use
class _LazyPDFParser(Parser):
    """Lazy wrapper that imports the actual PDF parser on first use."""

    _actual_parser = None

    def parse(self, stream, match):
        from polyfile.pdf_compat import pdfminer_compatibility_error

        error = pdfminer_compatibility_error()
        if error is not None:
            match.analysis_status = "unsupported"
            match.analysis_message = error
            return
        if _LazyPDFParser._actual_parser is None:
            try:
                from polyfile import pdf
            except ImportError as error:
                match.analysis_status = "unsupported"
                match.analysis_message = f"PDFminer adapter API is unavailable: {error}"
                return
            _LazyPDFParser._actual_parser = pdf.pdf_parser
        yield from _LazyPDFParser._actual_parser(stream, match)


PARSERS["application/pdf"].add(_LazyPDFParser())
