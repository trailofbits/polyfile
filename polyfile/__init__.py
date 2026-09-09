# Auto-fix for Kaitai Struct generated code using reserved keyword 'class'
import os
import re
from pathlib import Path

def _fix_class_keyword_if_needed():
    """Automatically fix the 'class' keyword issue in openpgp_message.py if needed."""
    try:
        parser_file = Path(__file__).parent / "kaitai" / "parsers" / "openpgp_message.py"
        if parser_file.exists():
            with open(parser_file, 'r') as f:
                content = f.read()
            
            # Check if the file needs fixing
            if re.search(r'\bself\.class\b', content):
                # Apply the fix
                fixed_content = re.sub(r'\bself\.class\b', 'self.class_', content)
                fixed_content = re.sub(r"\['class'\]", "['class_']", fixed_content)
                fixed_content = re.sub(r'SEQ_FIELDS = \[(.*)"class"(.*)\]', r'SEQ_FIELDS = [\1"class_"\2]', fixed_content)
                
                with open(parser_file, 'w') as f:
                    f.write(fixed_content)
    except Exception:
        # Silently ignore any errors - don't break the import
        pass

# Run the fix before importing modules
_fix_class_keyword_if_needed()

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
