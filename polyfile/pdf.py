from io import BytesIO

from . import pdfparser
from .logger import getStatusLogger
from .polyfile import Match, Submatch, submatcher

log = getStatusLogger("PDF")


def token_length(tok):
    if hasattr(tok, 'token'):
        return len(tok.token)
    else:
        return len(tok[1])


def content_length(content):
    return content[-1].offset.offset - content[0].offset.offset + token_length(content[-1])


def parse_object(object, parent=None):
    log.status('Parsing PDF obj %d %d' % (object.id, object.version))
    objtoken, objid, objversion, endobj = object.objtokens
    pdf_length=endobj.offset.offset - object.content[0].offset.offset + 1 + len(endobj.token)
    if parent is None or isinstance(parent, PDF):
        parent_offset = 0
    else:
        parent_offset = parent.offset
    obj = Submatch(
        name="PDFObject",
        display_name=f"PDFObject{object.id}.{object.version}",
        match_obj=(object.id, object.version),
        relative_offset=objid.offset.offset - parent_offset,
        length=pdf_length + object.content[0].offset.offset - objid.offset.offset,
        parent=parent
    )
    yield obj
    yield Submatch(
        "PDFObjectID",
        object.id,
        relative_offset=0,
        length=len(objid.token),
        parent=obj
    )
    yield Submatch(
        "PDFObjectVersion",
        object.version,
        relative_offset=objversion.offset.offset - objid.offset.offset,
        length=len(objversion.token),
        parent=obj
    )
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
    dict_offset = oPDFParseDictionary.content[0].offset.offset - objid.offset.offset
    dict_length = content_length(oPDFParseDictionary.content)
    yield Submatch(
        "PDFDictionary",
        dict_content,
        relative_offset=dict_offset,
        length=dict_length,
        parent=obj
    )
    log.debug('')
    log.debug('')
    content_start = dict_offset + dict_length
    content_len = endobj.offset.offset - content_start - objid.offset.offset
    if content_len > 0:
        yield Submatch(
            "PDFObjectContent",
            (),
            relative_offset=content_start,
            length=content_len,
            parent=obj
        )
    log.clear_status()


def parse_pdf(file_stream, parent=None):
    if parent is None or isinstance(parent, PDF):
        parent_offset = 0
    else:
        parent_offset = parent.offset
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
                    relative_offset=object.offset.offset - parent_offset,
                    length=len(object.comment),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_XREF:
                log.debug('PDF xref')
                yield Submatch(
                    name='PDFXref',
                    match_obj=object,
                    relative_offset=object.content[0].offset.offset - parent_offset,
                    length=content_length(object.content),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_TRAILER:
                pdfparser.cPDFParseDictionary(object.content[1:], False)
                yield Submatch(
                    name='PDFTrailer',
                    match_obj=object,
                    relative_offset=object.content[0].offset.offset - parent_offset,
                    length=content_length(object.content),
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_STARTXREF:
                yield Submatch(
                    name='PDFStartXRef',
                    match_obj=object.index,
                    relative_offset=object.offset.offset - parent_offset,
                    length=object.length,
                    parent=parent
                )
            elif object.type == pdfparser.PDF_ELEMENT_INDIRECT_OBJECT:
                yield from parse_object(object, parent=parent)


@submatcher('adobe_pdf.trid.xml', 'adobe_pdf-utf8.trid.xml')
class PDF(Match):
    def submatch(self, file_stream):
        yield from parse_pdf(file_stream, parent=self)
