import base64
import zlib

from . import pdfparser
from . import kaitai
from .kaitaimatcher import ast_to_matches
from .logger import getStatusLogger
from .polyfile import Match, Matcher, Submatch, submatcher

log = getStatusLogger("PDF")


def token_length(tok):
    if hasattr(tok, 'token'):
        return len(tok.token)
    else:
        return len(tok[1])


def content_length(content):
    return content[-1].offset.offset - content[0].offset.offset + token_length(content[-1])


def _emit_dict(parsed, parent, pdf_offset):
    dict_obj = Submatch(
        "PDFDictionary",
        '',
        relative_offset=parsed.start.offset.offset - parent.offset + pdf_offset,
        length=parsed.end.offset.offset - parsed.start.offset.offset + len(parsed.end.token),
        parent=parent
    )
    yield dict_obj
    for key, value in parsed:
        if isinstance(value, pdfparser.ParsedDictionary):
            value_end = value.end.offset.offset + len(value.end.token)
        else:
            value_end = value[-1].offset.offset + len(value[-1].token)
        pair_offset = key.offset.offset - dict_obj.offset
        pair = Submatch(
            "KeyValuePair",
            '',
            relative_offset=pair_offset + pdf_offset,
            length=value_end - key.offset.offset,
            parent=dict_obj
        )
        yield pair
        yield Submatch(
            "Key",
            key.token,
            relative_offset=0,
            length=len(key.token),
            parent=pair
        )
        if isinstance(value, pdfparser.ParsedDictionary):
            yield from _emit_dict(value, pair, pdf_offset)
        else:
            value_length = value[-1].offset.offset + len(value[-1].token) - value[0].offset.offset
            yield Submatch(
                "Value",
                ''.join(v.token for v in value),
                relative_offset=value[0].offset.offset - key.offset.offset,
                length=value_length,
                parent=pair
            )


def parse_object(file_stream, object, matcher: Matcher, parent=None):
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
    #log.debug('')
    #pp = BytesIO()
    #oPDFParseDictionary.PrettyPrint('  ', stream=pp)
    #pp.flush()
    #dict_content = pp.read()
    #log.debug(dict_content)
    dict_offset = oPDFParseDictionary.content[0].offset.offset - objid.offset.offset
    dict_length = content_length(oPDFParseDictionary.content)
    if oPDFParseDictionary.parsed is not None:
        yield from _emit_dict(oPDFParseDictionary.parsed, obj, parent.offset)
    #log.debug('')
    #log.debug('')
    content_start = dict_offset + dict_length
    content_len = endobj.offset.offset - content_start - objid.offset.offset
    is_dct_decode = False
    is_flate_decode = False
    if content_len > 0:
        content = Submatch(
            "PDFObjectContent",
            (),
            relative_offset=content_start,
            length=content_len,
            parent=obj
        )
        yield content
        stream_len = None
        if oPDFParseDictionary.parsed is not None:
            is_dct_decode = '/Filter' in oPDFParseDictionary.parsed \
                and oPDFParseDictionary.parsed['/Filter'].strip() == '/DCTDecode'
            is_flate_decode = '/Filter' in oPDFParseDictionary.parsed \
                and oPDFParseDictionary.parsed['/Filter'].strip() == '/FlateDecode'
            if '/Length' in oPDFParseDictionary.parsed:
                try:
                    stream_len = int(oPDFParseDictionary.parsed['/Length'])
                except ValueError:
                    pass
        old_pos = file_stream.tell()
        try:
            file_stream.seek(content.root_offset)
            raw_content = file_stream.read(content_len)
        finally:
            file_stream.seek(old_pos)
        streamtoken = b'stream'
        if raw_content.startswith(streamtoken):
            raw_content = raw_content[len(streamtoken):]
            if raw_content.startswith(b'\r'):
                streamtoken += b'\r'
                raw_content = raw_content[1:]
            if raw_content.startswith(b'\n'):
                streamtoken += b'\n'
                raw_content = raw_content[1:]
                if raw_content.endswith(b'\n'):
                    endtoken = b'endstream'
                    if raw_content.endswith(b'\r\n'):
                        endtoken += b'\r\n'
                    else:
                        endtoken += b'\n'
                    if raw_content.endswith(endtoken):
                        raw_content = raw_content[:-len(endtoken)]
                        if raw_content.endswith(b'\n') and stream_len is not None and len(raw_content) > stream_len:
                            endtoken = b'\n' + endtoken
                            raw_content = raw_content[:-1]
                        yield Submatch(
                            "StartStream",
                            streamtoken,
                            relative_offset=0,
                            length=len(streamtoken),
                            parent=content
                        )
                        streamcontent = Submatch(
                            "StreamContent",
                            raw_content,
                            relative_offset=len(streamtoken),
                            length=len(raw_content),
                            parent=content
                        )
                        yield streamcontent
                        # Temporarily disabled this until we figure out how to handle incorrect matches:
                        # with file_stream.save_pos() as fs:
                        #     with fs[streamcontent.offset:streamcontent.offset + streamcontent.length] as f:
                        #         f.seek(0)
                        #         yield from matcher.match(
                        #             f,
                        #             streamcontent
                        #         )
                        if is_dct_decode and raw_content[:1] == b'\xff':
                            # This is most likely a JPEG image
                            try:
                                ast = kaitai.parse('jpeg', raw_content)
                            except Exception as e:
                                log.error(str(e))
                                ast = None
                            if ast is not None:
                                iterator = ast_to_matches(ast, parent=streamcontent)
                                try:
                                    jpeg_match = next(iterator)
                                    jpeg_match.img_data = f"data:image/jpeg;base64,{base64.b64encode(raw_content).decode('utf-8')}"
                                    yield jpeg_match
                                    yield from iterator
                                except StopIteration:
                                    pass
                        elif is_flate_decode:
                            try:
                                decoded = zlib.decompress(raw_content)
                                yield Submatch(
                                    "FlateEncoded",
                                    raw_content,
                                    relative_offset=0,
                                    length=len(raw_content),
                                    parent=streamcontent,
                                    decoded=decoded
                                )
                            except zlib.error:
                                log.warn(f"DEFLATE decoding error at near offset {streamcontent.offset}")

                        yield Submatch(
                           "EndStream",
                            endtoken,
                            relative_offset=len(streamtoken) + len(raw_content),
                            length=len(endtoken),
                            parent=content
                        )
    log.clear_status()


def parse_pdf(file_stream, matcher: Matcher, parent=None):
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
                yield from parse_object(file_stream, object, matcher=matcher, parent=parent)


@submatcher('adobe_pdf.trid.xml', 'adobe_pdf-utf8.trid.xml')
class PDF(Match):
    def submatch(self, file_stream):
        yield from parse_pdf(file_stream, matcher=self.matcher, parent=self)
