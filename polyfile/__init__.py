from . import (
    nes,
    jpeg,
    zipmatcher,
    nitf,
    http,
    kaitaimatcher,
    languagematcher,
    pickles,
    polyfile
)

from .__main__ import main
from .polyfile import __version__, InvalidMatch, Match, Matcher, Parser, PARSERS, register_parser, Submatch


# Lazy PDF parser registration
# This registers immediately but defers importing pdf.py (and pdfminer) until first use
class _LazyPDFParser(Parser):
    """Lazy wrapper that imports the actual PDF parser on first use."""

    _actual_parser = None

    def parse(self, stream, match):
        if _LazyPDFParser._actual_parser is None:
            from . import pdf
            _LazyPDFParser._actual_parser = pdf.pdf_parser
        yield from _LazyPDFParser._actual_parser(stream, match)


PARSERS["application/pdf"].add(_LazyPDFParser())
