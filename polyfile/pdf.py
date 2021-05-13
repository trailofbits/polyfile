import zlib
from typing import Dict, Iterator, List, Optional, Type

from . import pdfparser
from .kaitai.parser import KaitaiParser
from .fileutils import Tempfile
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


FILTERS_BY_NAME: Dict[str, Type["StreamFilter"]] = {}


class StreamFilter:
    name: str

    def __init__(self, next_decoder: Optional["StreamFilter"] = None):
        self.next_decoder: Optional[StreamFilter] = next_decoder

    def __init_subclass__(cls, **kwargs):
        FILTERS_BY_NAME[f"/{cls.name}Decode"] = cls

    def decode(self, matcher: Matcher, raw_content: bytes, parent: Submatch) -> Iterator[Submatch]:
        raise NotImplementedError()

    def match(self, matcher: Matcher, raw_content: bytes, parent: Submatch) -> Iterator[Submatch]:
        for submatch in self.decode(matcher, raw_content, parent):
            yield submatch
            if submatch.decoded is None:
                if self.next_decoder is not None:
                    log.warning(f"Expected submatch submatch {submatch!r} from decoded by {self.__class__.__name__} "
                                "to have a `decoded` member, but it was `None`")
                continue
            if self.next_decoder is None:
                # recursively match against the deflated contents
                with Tempfile(submatch.decoded) as f:
                    yield from matcher.match(f, parent=submatch)
            else:
                yield from self.next_decoder.match(matcher, submatch.decoded, submatch)


class FlateDecoder(StreamFilter):
    name = "Flate"

    def decode(self, matcher: Matcher, raw_content: bytes, parent: Submatch) -> Iterator[Submatch]:
        try:
            decoded = zlib.decompress(raw_content)
            yield Submatch(
                f"{self.name}Encoded",
                raw_content,
                relative_offset=0,
                length=len(raw_content),
                parent=parent,
                decoded=decoded
            )
        except zlib.error:
            log.warn(f"DEFLATE decoding error near offset {parent.offset}")


class DCTDecoder(StreamFilter):
    name = "DCT"

    def decode(self, matcher: Matcher, raw_content: bytes, parent: Submatch) -> Iterator[Submatch]:
        if raw_content[:1] != b'\xff':
            return
        # This is most likely a JPEG image
        try:
            ast = KaitaiParser.load("image/jpeg.ksy").parse(raw_content).ast
        except Exception as e:
            log.error(str(e))
            ast = None
        if ast is not None:
            yield from ast_to_matches(ast, parent=parent)


class ASCIIHexDecoder(StreamFilter):
    name = "ASCIIHex"

    def decode(self, matcher: Matcher, raw_content: bytes, parent: Submatch) -> Iterator[Submatch]:
        data = bytearray()
        for byte_str in raw_content.replace(b"\n", b" ").split(b" "):
            byte_str = byte_str.strip()
            if byte_str.endswith(b">"):
                byte_str = byte_str[:-1].strip()
            try:
                data.append(int(byte_str, 16))
            except ValueError:
                log.warning(f"Invalid byte string {byte_str!r} near offset {parent.offset}")
                return
        yield Submatch(
            f"{self.name}Encoded",
            raw_content,
            relative_offset=0,
            length=len(raw_content),
            parent=parent,
            decoded=bytes(data)
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
        filters: List[StreamFilter] = []
        if oPDFParseDictionary.parsed is not None:
            if '/Filter' in oPDFParseDictionary.parsed:
                filter_value = oPDFParseDictionary.parsed["/Filter"].strip()
                if filter_value.startswith("[") and filter_value.endswith("]"):
                   filter_value = str(filter_value[1:-1])
                for filter in filter_value.split(" "):
                    if len(filter.strip()) == 0:
                        continue
                    elif filter.strip() not in FILTERS_BY_NAME:
                        log.warn(f"Unimplemented PDF filter: {filter.strip()}")
                    else:
                        new_filter = FILTERS_BY_NAME[filter.strip()]()
                        if filters:
                            filters[-1].next_decoder = new_filter
                        filters.append(new_filter)
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
                if raw_content.endswith(b'\n') or raw_content.endswith(b'\r'):
                    endtoken = b'endstream'
                    if raw_content.endswith(b'\r\n'):
                        endtoken += b'\r\n'
                    elif raw_content.endswith(b'\r'):
                        endtoken += b'\r'
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
                        if filters:
                            yield from filters[0].match(matcher, raw_content, streamcontent)
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


@submatcher("application/pdf")
class PDF(Match):
    def submatch(self, file_stream):
        yield from parse_pdf(file_stream, matcher=self.matcher, parent=self)
