from io import BytesIO

from . import pdfparser
from .logger import getStatusLogger
from .polyfile import matcher, Match, Submatch

log = getStatusLogger("PDF")


def parse_object(object, parent=None):
    log.status('Parsing PDF obj %d %d' % (object.id, object.version))
    pdf_length=object.content[-1].offset.offset - object.content[0].offset.offset + 1
    obj = Submatch(
        "PDFObject",
        (object.id, object.version),
        relative_offset=object.content[0].offset.offset,
        length=pdf_length,
        parent=parent
    )
    yield obj
    log.debug(' Type: %s' % pdfparser.ConditionalCanonicalize(object.GetType(), False))
    log.debug(' Referencing: %s' % ', '.join(map(lambda x: '%s %s %s' % x, object.GetReferences())))
    dataPrecedingStream = object.ContainsStream()
    if dataPrecedingStream:
        log.debug(' Contains stream')
        log.debug(' %s' % pdfparser.FormatOutput(dataPrecedingStream, False))
        oPDFParseDictionary = pdfparser.cPDFParseDictionary(dataPrecedingStream, False)
    else:
        log.debug(' %s' % pdfparser.FormatOutput(object.content, False))
        oPDFParseDictionary = pdfparser.cPDFParseDictionary(object.content, False)
    log.debug('')
    pp = BytesIO()
    oPDFParseDictionary.PrettyPrint('  ', stream=pp)
    pp.flush()
    dict_content = pp.read()
    log.debug(dict_content)
    dict_offset = oPDFParseDictionary.content[0].offset.offset - object.content[0].offset.offset
    dict_length = len(oPDFParseDictionary.content)
    yield Submatch(
        "PDFDictionary",
        dict_content,
        relative_offset=dict_offset,
        length=dict_length,
        parent=obj
    )
    log.debug('')
    log.debug('')
    yield Submatch(
        "PDFObjectContent",
        (),
        relative_offset=dict_offset + dict_length,
        length=len(pdfparser.FormatOutput(object.content, True)),
        parent=obj
    )
    log.clear_status()


def parse_pdf(file_stream, parent=None):
    with file_stream.tempfile(suffix='.pdf') as pdf_path:
        parser = pdfparser.cPDFParser(pdf_path, True)
        while True:
            object = parser.GetObject()
            if object is None:
                break
            elif object.type == pdfparser.PDF_ELEMENT_COMMENT:
                log.debug(f"PDF comment at {object.offset}, length {len(object.comment)}")
                yield Submatch(
                    name='PDFComment',
                    match_obj=object,
                    relative_offset=object.offset.offset,
                    length=len(object.comment),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_XREF:
                log.debug('PDF xref')
                yield Submatch(
                    name='PDFXref',
                    match_obj=object,
                    relative_offset=object.content[0].offset.offset,
                    length=len(object.content),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_TRAILER:
                pdfparser.cPDFParseDictionary(object.content[1:], False)
                yield Submatch(
                    name='PDFTrailer',
                    match_obj=object,
                    relative_offset=object.content[0].offset.offset,
                    length=len(object.content),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_STARTXREF:
                yield Submatch(
                    name='PDFStartXRef',
                    match_obj=object.index,
                    relative_offset=object.offset.offset,
                    length=object.length,
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_INDIRECT_OBJECT:
                yield from parse_object(object, parent=parent)


@matcher('adobe_pdf.trid.xml', 'adobe_pdf-utf8.trid.xml')
class PdfMatcher(Match):
    def submatch(self, file_stream):
        yield from parse_pdf(file_stream, parent=self)
