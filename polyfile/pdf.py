from . import pdfparser
from .logger import getStatusLogger
from .polyfile import matcher, Match, Submatch

log = getStatusLogger("PDF")


def parse_pdf(file_stream, parent=None):
    with file_stream.tempfile(suffix='.pdf') as pdf_path:
        parser = pdfparser.cPDFParser(pdf_path, True)
        while True:
            object = parser.GetObject()
            if object is None:
                break
            elif object.type == pdfparser.PDF_ELEMENT_COMMENT:
                log.debug(f"PDF comment at {object.offset}, length {len(object.comment)}")
                yield Submatch(name='PDFComment', match_obj=object, relative_offset=object.offset.offset, parent=parent)
            elif object.type == pdfparser.PDF_ELEMENT_XREF:
                log.debug('PDF xref')
                yield Submatch(name='PDFXref', match_obj=object, relative_offset=object.content[0].offset.offset, parent=parent)


@matcher('adobe_pdf.trid.xml', 'adobe_pdf-utf8.trid.xml')
class PdfMatcher(Match):
    def submatch(self, file_stream):
        yield from parse_pdf(file_stream, parent=self)
