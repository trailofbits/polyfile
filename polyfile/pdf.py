import sys
from typing import Callable, Dict, Iterator, List, Optional, Type, TypeVar, Union
import zlib

from pdfminer.ascii85 import ascii85decode, asciihexdecode
from pdfminer.ccitt import ccittfaxdecode
from pdfminer.lzw import lzwdecode
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdftypes import PDFNotImplementedError
from pdfminer.runlength import rldecode
from pdfminer.pdfparser import PDFParser as PDFMinerParser, PDFStream, PDFObjRef
from pdfminer.psparser import ExtraT, PSBaseParserToken, PSKeyword, PSObject, PSLiteral, PSStackEntry, PSSyntaxError
from pdfminer.pdfdocument import (
    PDFDocument, PDFXRef, KWD, PDFNoValidXRef, PSEOF, dict_value, LITERAL_XREF, LITERAL_OBJSTM, LITERAL_CATALOG,
    DecipherCallable, PDFObjectNotFound
)
from pdfminer.pdftypes import (
    LIT, LITERALS_FLATE_DECODE, LITERALS_ASCIIHEX_DECODE, LITERALS_CCITTFAX_DECODE, LITERALS_RUNLENGTH_DECODE,
    LITERAL_CRYPT, LITERALS_LZW_DECODE, LITERALS_DCT_DECODE, LITERALS_JBIG2_DECODE, LITERALS_ASCII85_DECODE,
    int_value, apply_png_predictor
)

from .fileutils import FileStream
from .fileutils import Tempfile
from .logger import getStatusLogger
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType
from .polyfile import Match, Matcher, Submatch, register_parser

log = getStatusLogger("PDF")


def load_trailer(self, parser: "PDFParser") -> None:
    try:
        (_, kwd) = parser.nexttoken()
        assert kwd == KWD(b'trailer'), f"{kwd!s} != {KWD(b'trailer')!s}"
        flush_before = parser.auto_flush
        try:
            # This might be a bug in pdfminer, or it's just that we are using it wrong, but we need to
            # flush our entire token stack to the results list in order to parse the trailer dict:
            parser.auto_flush = True
            (_, dic) = parser.nextobject()
        finally:
            parser.auto_flush = flush_before
    except PSEOF:
        x = parser.pop(1)
        if not x:
            raise PDFNoValidXRef('Unexpected EOF - file corrupted')
        (_, dic) = x[0]
    self.trailer.update(dict_value(dic))
    log.debug('trailer=%r', self.trailer)
    return


def load_xref(self: PDFXRef, parser: "PDFParser"):
    while True:
        try:
            (pos, line) = parser.nextline()
            line = line.strip()
            if not line:
                continue
        except PSEOF:
            raise PDFNoValidXRef("Unexpected EOF - file corrupted?")
        if line.startswith(b"trailer"):
            parser.seek(pos)
            break
        f = line.split(b" ")
        if len(f) != 2:
            error_msg = "Trailer not found: {!r}: line={!r}".format(parser, line)
            raise PDFNoValidXRef(error_msg)
        try:
            (start, nobjs) = map(int, f)
        except ValueError:
            error_msg = "Invalid line: {!r}: line={!r}".format(parser, line)
            raise PDFNoValidXRef(error_msg)
        for objid in range(start, start + nobjs):
            try:
                (_, line) = parser.nextline()
                line = line.strip()
            except PSEOF:
                raise PDFNoValidXRef("Unexpected EOF - file corrupted?")
            f = line.split(b" ")
            if len(f) != 3:
                error_msg = "Invalid XRef format: {!r}, line={!r}".format(
                    parser, line
                )
                raise PDFNoValidXRef(error_msg)
            (pos_b, genno_b, use_b) = f
            if use_b != b"n":
                continue
            self.offsets[objid] = (None, pos_b.__int__(), genno_b.__int__())
    log.debug("xref objects: %r", self.offsets)
    self.load_trailer(parser)


PDFXRef.load_trailer = load_trailer
PDFXRef.load = load_xref


class PSToken:
    pdf_offset: int
    pdf_bytes: int

    def __new__(cls, *args, **kwargs):
        ret = super().__new__(cls, *args)
        ret.pdf_offset = kwargs["pdf_offset"]
        ret.pdf_bytes = kwargs["pdf_bytes"]
        return ret

    def __int__(self):
        if isinstance(self, PSInt):
            return self
        return PSInt(int(self, base=10), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __float__(self):
        if isinstance(self, float):
            return self
        elif isinstance(self, int):
            return PSFloat(int(self, base=10), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        elif isinstance(self, bytes):
            return PSFloat(self.decode(), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        elif isinstance(self, PSStr):
            return PSFloat(str(self), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        else:
            raise NotImplementedError()

    def __bytes__(self):
        if isinstance(self, PSBytes):
            return self
        else:
            return PSBytes(self, pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __hex__(self):
        return PSStr(super().__hex__(), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __str__(self):
        raise NotImplementedError()
        # return PSStr(super().__str__(), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()}, pdf_offset={self.pdf_offset!r}, "\
               f"pdf_bytes={self.pdf_bytes!r})"


class PSInt(PSToken, int):
    def __index__(self):
        return self

    def __str__(self):
        return str(int(self))


C = TypeVar("C")


class PSSequence(PSToken):
    def split(self: Type[C], sep: Optional[C] = None, maxsplit: int = -1) -> List[C]:
        remainder = self
        current: Optional[C] = None
        result: List[C] = []
        if sep is None:
            remainder = remainder.strip()
        while remainder and (maxsplit < 0 or len(result) <= maxsplit):
            c = remainder[0:1]
            remainder = remainder[1:]
            if sep is None:
                if not c.strip():
                    if current is not None:
                        result.append(current)
                        current = None
                else:
                    if current is None:
                        current = c
                    else:
                        current += c
            else:
                if current is None:
                    current = c
                else:
                    current += c
                if current[-len(sep):] == sep:
                    result.append(current[:-len(sep)])
                    current = None
        if current is not None:
            if not result or maxsplit < 0 or len(result) <= maxsplit:
                result.append(current)
            else:
                result[-1] += current
        return result

    def __add__(self: Type[C], other) -> C:
        if isinstance(other, self.__class__) and other.pdf_offset == self.pdf_offset + self.pdf_bytes:
            return self.__class__(super().__add__(other), pdf_offset=self.pdf_offset)
        return self.__class__(super().__add__(other), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __radd__(self: Type[C], other) -> C:
        return self.__class__(other, pdf_offset=self.pdf_offset - len(other)) + self

    def lstrip(self: Type[C], chars: bytes = b" \t\n\r") -> C:
        ret = self
        while ret and ret[0] in chars:
            ret = ret[1:]
        return ret

    def rstrip(self: Type[C], chars: bytes = b" \t\n\r") -> C:
        ret = self
        while ret and ret[-1] in chars:
            ret = ret[:-1]
        return ret

    def strip(self: Type[C], chars: bytes = b" \t\n\r") -> C:
        return self.lstrip(chars).rstrip(chars)

    def __getitem__(self, item):
        if isinstance(item, int):
            value = super().__getitem__(item)
            return make_ps_object(value, pdf_offset=self.pdf_offset+item, pdf_bytes=self.pdf_bytes-item)
        elif isinstance(item, slice):
            if item.start is None:
                start = 0
            else:
                start = item.start
            if item.stop is None:
                stop = self.pdf_bytes
            else:
                stop = item.stop
            try:
                return self.__class__(
                    super().__getitem__(item),
                    pdf_offset=self.pdf_offset+start,
                    pdf_bytes=self.pdf_bytes-(stop - start)
                )
            except ValueError:
                if isinstance(self, PSBytes):
                    return PSBytes(
                        super().__getitem__(item),
                        pdf_offset=self.pdf_offset+start,
                        pdf_bytes=self.pdf_bytes-(stop - start)
                    )
                else:
                    raise
        else:
            return super().__getitem__(item)


class PSStr(PSSequence, str):
    def encode(self, encoding: str = ..., errors: str = ...) -> bytes:
        return PSBytes(super().encode(encoding, errors), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __str__(self):
        return str.__str__(self)


class PSBytes(PSSequence, bytes):
    def __new__(cls, *args, **kwargs):
        kwargs = dict(kwargs)
        if "pdf_bytes" not in kwargs:
            kwargs["pdf_bytes"] = len(args[0])
        return super().__new__(cls, *args, **kwargs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start is None:
                start = 0
            else:
                start = item.start
            return PSBytes(super().__getitem__(item), pdf_offset=self.pdf_offset + start)
        else:
            ret = super().__getitem__(item)
            if isinstance(ret, PSInt):
                return ret
            else:
                return PSInt(ret, pdf_offset=self.pdf_offset + item)

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> PSStr:
        return PSStr(super().decode(encoding, errors), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)


    def __str__(self):
        return bytes.__str__(self)


class PDFDeciphered(PSBytes):
    original_bytes: bytes

    def __new__(cls, *args, **kwargs):
        kwargs = dict(kwargs)
        if "pdf_bytes" not in kwargs:
            kwargs["pdf_bytes"] = len(args[0])
        if "original_bytes" in kwargs:
            original_bytes = kwargs["original_bytes"]
            del kwargs["original_bytes"]
        else:
            raise ValueError(f"{cls.__name__}.__init__ requires the `original_bytes` argument")
        ret = super().__new__(cls, *args, **kwargs)
        setattr(ret, "original_bytes", original_bytes)
        return ret


class PSFloat(PSToken, float):
    def __str__(self):
        return float.__str__(self)


class PSBool:
    def __init__(self, value: bool, pdf_offset: int, pdf_bytes: int):
        self.value: bool = value
        self.pdf_offset: int = pdf_offset
        self.pdf_bytes: int = pdf_bytes

    def __bool__(self):
        return self.value

    def __int__(self):
        return PSInt(int(self.value), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __eq__(self, other):
        return self.value == bool(other)

    def __ne__(self, other):
        return self.value != bool(other)

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return PSStr(self.value, pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r}, pdf_offset={self.pdf_offset!r}, "\
               f"pdf_bytes={self.pdf_bytes!r})"


class PDFLiteral(PSLiteral):
    def __init__(self, name: PSLiteral.NameType, pdf_offset: int, pdf_bytes: int):
        if isinstance(name, str) and not isinstance(name, PSStr):
            super().__init__(PSStr(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes))
        elif isinstance(name, bytes) and not isinstance(name, PSBytes):
            super().__init__(PSBytes(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes))
        else:
            super().__init__(name)

    @property
    def pdf_bytes(self) -> int:
        return self.name.pdf_bytes + 1  # add one to account for the leading "/"

    @property
    def pdf_offset(self) -> int:
        return self.name.pdf_offset - 1

    def __eq__(self, other):
        return isinstance(other, PSLiteral) and self.name == other.name


class PDFKeyword(PSKeyword):
    def __init__(self, name: bytes, pdf_offset: int, pdf_bytes: int):
        pdf_bytes = len(name)  # sometimes we actually lose the length of the token, so rely on the keyword name
        if not isinstance(name, PSBytes):
            super().__init__(PSBytes(name, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes))
        else:
            super().__init__(name)
        self.pdf_offset: int = pdf_offset
        self.pdf_bytes: int = pdf_bytes

    def __eq__(self, other):
        return isinstance(other, PSKeyword) and self.name == other.name

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r}, pdf_offset={self.pdf_offset}, pdf_bytes={self.pdf_bytes})"

    def __str__(self):
        return f"/{self.name!s}"


PDFBaseParserToken = Union[PSFloat, PSBool, PDFLiteral, PSKeyword, PSBytes, PSInt]


"""
pdfminer.pdfdocument unfortunately tests for equality with these literals using `is` rather than `==`, so we must
return their singletons from a dict rather than our instrumented PDFLiteral objects:
"""
PROTECTED_LITERALS: Dict[str, PSLiteral] = {
    LITERAL_OBJSTM.name: LITERAL_OBJSTM,
    LITERAL_XREF.name: LITERAL_XREF,
    LITERAL_CATALOG.name: LITERAL_CATALOG
}


if sys.version_info < (3, 7):
    # Before Python 3.7, we'll get an MRO error if we extend from both dict and Dict
    PDFDict_Type = object
else:
    PDFDict_Type = Dict[PSStr, Union[PDFBaseParserToken, PSStr, "PDFDict", "PDFList"]]


class PDFDict(dict, PDFDict_Type):
    pdf_offset: int
    pdf_bytes: int

    def __init__(self, *args, **kwargs):
        kwargs = dict(kwargs)
        if "pdf_offset" in kwargs:
            del kwargs["pdf_offset"]
        if "pdf_bytes" in kwargs:
            del kwargs["pdf_bytes"]
        super().__init__(*args, **kwargs)

    def get(self, key, default = None):
        result = super().get(key, default)
        if isinstance(result, PDFLiteral) and result.name in PROTECTED_LITERALS:
            # we must return the protected literals as their singleton version:
            return PROTECTED_LITERALS[result.name]
        return result

    def __new__(cls, *args, pdf_offset: int, pdf_bytes: int, **kwargs):
        ret = super().__new__(cls, *args, **kwargs)
        ret.pdf_offset = pdf_offset
        ret.pdf_bytes = pdf_bytes
        return ret

    def __str__(self):
        return dict.__str__(self)



class PDFList(PSSequence, list):
    @staticmethod
    def load(iterable) -> "PDFList":
        start_offset: Optional[int] = None
        end_offset: Optional[int] = None
        items = []
        for item in iterable:
            if hasattr(item, "pdf_offset") and hasattr(item, "pdf_bytes"):
                if start_offset is None or start_offset > item.pdf_offset:
                    start_offset = item.pdf_offset
                if end_offset is None or end_offset < item.pdf_offset + item.pdf_bytes:
                    end_offset = item.pdf_offset + item.pdf_bytes
            items.append(item)
        if start_offset is None or end_offset is None:
            raise ValueError(f"Cannot determine PDF bounds for list {items!r}")
        return PDFList(items, pdf_offset=start_offset, pdf_bytes=end_offset - start_offset)

    def __str__(self):
        return list.__str__(self)



def make_ps_object(value, pdf_offset: int, pdf_bytes: int) -> Union[PDFBaseParserToken, PSStr, PDFDict]:
    if isinstance(value, PSLiteral):
        return PDFLiteral(value.name, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)
    # Unfortunately, we can't convert PSKeywords to PDFKeywords here because pdfminer requires them to be singletons
    # elif isinstance(value, PSKeyword):
    #     return PDFKeyword(value.name, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)
    elif isinstance(value, PDFDict):
        value.pdf_offset = pdf_offset
        value.pdf_bytes = pdf_bytes
        return value
    elif isinstance(value, dict):
        return PDFDict(value, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)
    elif isinstance(value, PSObject):
        setattr(value, "pdf_offset", pdf_offset)
        if isinstance(value, PSKeyword):
            # sometimes the byte count gets off, so set it to the name size
            pdf_bytes = len(value.name)
        setattr(value, "pdf_bytes", pdf_bytes)
        return value
    elif isinstance(value, int):
        supertype = PSInt
    elif isinstance(value, float):
        supertype = PSFloat
    elif isinstance(value, bool):
        supertype = PSBool
    elif isinstance(value, bytes):
        supertype = PSBytes
    elif isinstance(value, str):
        supertype = PSStr
    else:
        raise NotImplementedError(f"Add suppport for PSSequences containing elements of type {type(value)}")
    return supertype(value, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)


class DecodingError(bytes):
    message: Optional[str]

    def __new__(cls, *args, **kwargs):
        kwargs = dict(kwargs)
        if "message" in kwargs:
            message = kwargs["message"]
            del kwargs["message"]
        else:
            message = None
        ret = super().__new__(cls, b'')
        setattr(ret, "message", message)
        return ret


class PDFStreamFilter(PSBytes):
    name: str
    original_bytes: bytes
    error: Optional[DecodingError]

    def __new__(cls, *args, **kwargs):
        kwargs = dict(kwargs)
        if "pdf_bytes" not in kwargs:
            kwargs["pdf_bytes"] = len(args[0])
        if "original_bytes" in kwargs:
            original_bytes = kwargs["original_bytes"]
            del kwargs["original_bytes"]
        else:
            raise ValueError(f"{cls.__name__}.__init__ requires the `original_bytes` argument")
        if "name" in kwargs:
            name = kwargs["name"]
            del kwargs["name"]
        else:
            raise ValueError(f"{cls.__name__}.__init__ requires the `name` argument")
        if isinstance(args[0], DecodingError):
            error = args[0]
        else:
            error = None
        ret = super().__new__(cls, *args, **kwargs)
        setattr(ret, "original_bytes", original_bytes)
        setattr(ret, "name", name)
        setattr(ret, "error", error)
        return ret


class PNGPredictor(PSBytes):
    params: PDFDict
    original_bytes: bytes

    def __new__(cls, *args, **kwargs):
        kwargs = dict(kwargs)
        if "pdf_bytes" not in kwargs:
            kwargs["pdf_bytes"] = len(args[0])
        if "original_bytes" in kwargs:
            original_bytes = kwargs["original_bytes"]
            del kwargs["original_bytes"]
        else:
            raise ValueError(f"{cls.__name__}.__init__ requires the `original_bytes` argument")
        if "params" in kwargs:
            params = kwargs["params"]
            del kwargs["params"]
        else:
            raise ValueError(f"{cls.__name__}.__init__ requires the `params` argument")
        ret = super().__new__(cls, *args, **kwargs)
        setattr(ret, "original_bytes", original_bytes)
        setattr(ret, "params", params)
        return ret


class PDFObjectStream(PDFStream):
    def __init__(self, parent: PDFStream, pdf_offset: int, pdf_bytes: int):
        super().__init__(
            attrs=parent.attrs,
            rawdata=PSBytes(parent.rawdata, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes),
            decipher=parent.decipher
        )
        self.parent: PDFStream = parent
        self.pdf_offset: int = pdf_offset
        self.pdf_bytes: int = pdf_bytes
        self.data = parent.data
        self.objid = parent.objid
        self.genno = parent.genno

    @property
    def data(self) -> Optional[PSBytes]:
        return self._data

    @data.setter
    def data(self, new_value: Optional[bytes]):
        if new_value is not None and not isinstance(new_value, PSBytes):
            self._data = PSBytes(new_value, pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        else:
            self._data = new_value

    @property
    def data_value(self) -> PSBytes:
        if self.data is not None:
            return self.data
        elif self.rawdata is not None:
            return self.rawdata
        else:
            raise ValueError(f"PDFObjectStream {self!r} does not have any data")

    def decode(self):
        assert self.data is None \
               and self.rawdata is not None, str((self.data, self.rawdata))
        data = self.rawdata
        if self.decipher:
            # Handle encryption
            assert self.objid is not None
            assert self.genno is not None
            data = self.decipher(self.objid, self.genno, data, self.attrs)
        filters = self.get_filters()
        if not filters:
            self.data = data
            self.rawdata = None
            return
        for (f, params) in filters:
            decoded: Optional[bytes] = None
            if f in LITERALS_FLATE_DECODE:
                # will get errors if the document is encrypted.
                try:
                    decoded = zlib.decompress(data)
                except zlib.error as e:
                    decoded = DecodingError(str(e))
            elif f in LITERALS_LZW_DECODE:
                decoded = lzwdecode(data)
            elif f in LITERALS_ASCII85_DECODE:
                decoded = ascii85decode(data)
            elif f in LITERALS_ASCIIHEX_DECODE:
                decoded = asciihexdecode(data)
            elif f in LITERALS_RUNLENGTH_DECODE:
                decoded = rldecode(data)
            elif f in LITERALS_CCITTFAX_DECODE:
                decoded = ccittfaxdecode(data, params)
            elif f in LITERALS_DCT_DECODE or f == LIT("JPXDecode"):
                # This is probably a JPG stream
                # it does not need to be decoded twice.
                # Just return the stream to the user.
                pass
            elif f in LITERALS_JBIG2_DECODE:
                pass
            elif f == LITERAL_CRYPT:
                # not yet..
                raise PDFNotImplementedError('/Crypt filter is unsupported')
            else:
                raise PDFNotImplementedError('Unsupported filter: %r' % f)
            if decoded is not None:
                if isinstance(f, PDFLiteral):
                    name = f.name
                else:
                    name = f
                data = PDFStreamFilter(
                    decoded,
                    pdf_offset=data.pdf_offset,
                    pdf_bytes=data.pdf_bytes,
                    original_bytes=data,
                    name=name
                )
            # apply predictors
            if params and 'Predictor' in params:
                pred = int_value(params['Predictor'])
                if pred == 1:
                    # no predictor
                    pass
                elif 10 <= pred:
                    # PNG predictor
                    colors = int_value(params.get('Colors', 1))
                    columns = int_value(params.get('Columns', 1))
                    raw_bits_per_component = params.get('BitsPerComponent', 8)
                    bitspercomponent = int_value(raw_bits_per_component)
                    predicted = apply_png_predictor(pred, colors, columns,
                                               bitspercomponent, data)
                    data = PNGPredictor(
                        predicted,
                        pdf_offset=data.pdf_offset,
                        pdf_bytes=data.pdf_bytes,
                        original_bytes=data,
                        params=params
                    )
                else:
                    error_msg = 'Unsupported predictor: %r' % pred
                    raise PDFNotImplementedError(error_msg)
        self.data = data
        self.rawdata = None
        return


class PDFParser(PDFMinerParser):
    auto_flush: bool = False

    @staticmethod
    def string_escape(data: Union[bytes, int]) -> str:
        if not isinstance(data, int):
            return "".join(PDFParser.string_escape(d) for d in data)
        elif data == ord('\n'):
            return "\\n"
        elif data == ord('\t'):
            return "\\t"
        elif data == ord('\r'):
            return "\\r"
        elif data == 0:
            return "\\0"
        elif data == ord('\\'):
            return "\\\\"
        elif 32 <= data <= 126:
            return chr(data)
        else:
            return f"\\x{data:02X}"

    def token_context(self, token: Union[PDFBaseParserToken, PSStr], padding_bytes: int = 10) -> str:
        pos_before = self.fp.tell()
        try:
            bytes_before = min(token.pdf_offset, padding_bytes)
            self.fp.seek(token.pdf_offset - bytes_before)
            if bytes_before > 0:
                context_before = PDFParser.string_escape(self.fp.read(bytes_before))
            else:
                context_before = ""
            content = PDFParser.string_escape(self.fp.read(token.pdf_bytes))
            context_after = PDFParser.string_escape(self.fp.read(padding_bytes))
            return f"{context_before}{content}{context_after}\n" \
                   f"{' ' * len(context_before)}" \
                   f"{'^' * len(content)}" \
                   f"{' ' * len(context_after)}"
        finally:
            self.fp.seek(pos_before)

    def push(self, *objs: PSStackEntry[ExtraT]):
        transformed = []
        for obj in objs:
            if len(obj) == 2 and isinstance(obj[1], dict):
                length = self._curtokenpos + 1 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFDict(obj[1], pdf_offset=obj[0], pdf_bytes=length + 2)))
            elif len(obj) == 2 and isinstance(obj[1], list):
                length = self._curtokenpos + 1 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFList(obj[1], pdf_offset=obj[0], pdf_bytes=length)))
            elif len(obj) == 2 and isinstance(obj[1], PDFStream):
                stream: PDFStream = obj[1]
                pos = obj[0]
                transformed.append((pos, PDFObjectStream(stream, pdf_offset=pos, pdf_bytes=len(stream.rawdata))))
            elif len(obj) == 2 and isinstance(obj[1], PSObject) and not isinstance(obj[1], PDFLiteral):
                pos = obj[0]
                psobj = obj[1]
                length = self._curtokenpos + 1 - obj[0]
                if isinstance(psobj, PDFObjRef):
                    orig_pos = pos
                    pos = min(pos, psobj.objid.pdf_offset)
                    length += orig_pos - pos
                setattr(psobj, "pdf_offset", pos) 
                setattr(psobj, "pdf_bytes", length)
                transformed.append((pos, psobj))
            else:
                transformed.append(obj)
        return super().push(*transformed)

    def _add_token(self, obj: PSBaseParserToken):
        if hasattr(obj, "pdf_offset"):
            pos = obj.pdf_offset
        else:
            pos = self._curtokenpos
        if hasattr(obj, "pdf_bytes"):
            length = obj.pdf_bytes
        elif isinstance(obj, PSLiteral):
            length = len(self._curtoken)
        else:
            length = len(self._curtoken)
        obj = make_ps_object(obj, pdf_offset=pos, pdf_bytes=length)
        # log.info(f"\n{self.token_context(obj)}")
        return super()._add_token(obj)

    def flush(self):
        if self.auto_flush:
            self.add_results(*self.popall())
        else:
            super().flush()

    def do_keyword(self, pos: int, token: PSKeyword):
        if token is self.KEYWORD_R:
            # reference to indirect object
            try:
                ((_, objid), (_, genno)) = self.pop(2)
                obj = PDFObjRef(self.doc, objid, genno)
                self.push((pos, obj))
            except PSSyntaxError:
                pass
        else:
            super().do_keyword(pos, token)

    # def nexttoken(self) -> Tuple[int, PSBaseParserToken]:
    #     pos, token = super().nexttoken()
    #     if isinstance(token, PSObject):
    #         setattr(token, "pdf_offset", pos)
    #     elif isinstance(token, int):
    #         token = PSInt(token, pdf_offset=pos)
    #     elif isinstance(token, bytes):
    #         token = PSBytes(token, pdf_offset=pos)
    #     elif isinstance(token, float):
    #         token = PSFloat(token, pdf_offset=pos)
    #     elif isinstance(token, bool):
    #         token - PSBool(token, pdf_offset=pos)
    #     else:
    #         raise NotImplementedError(f"Add support for tokens of type {type(token)}")
    #     return pos, token

    # def do_keyword(self, pos: int, token: PSKeyword) -> None:


class RawPDFStream:
    def __init__(self, file_stream):
        self._file_stream = file_stream

    def read(self, *args, **kwargs):
        offset_before = self._file_stream.tell()
        ret = self._file_stream.read(*args, **kwargs)
        if isinstance(ret, bytes):
            ret = PSBytes(ret, pdf_offset=offset_before)
        return ret

    def __getattr__(self, item):
        return getattr(self._file_stream, item)


def parse_object(obj, matcher: Matcher, parent: Optional[Match] = None, pdf_header_offset: int = 0):
    if isinstance(obj, PDFStreamFilter):
        filter_obj = Submatch(
            f"{obj.name!s}",
            bytes(obj.original_bytes),
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )
        yield filter_obj
        if obj.error is None:
            stream = Submatch(
                "DecodedStream",
                bytes(obj),
                relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
                length=obj.pdf_bytes,
                parent=filter_obj,
                decoded=bytes(obj)
            )
        else:
            stream = Submatch(
                "DecodingError",
                obj.error.message,
                relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
                length=obj.pdf_bytes,
                parent=filter_obj
            )
        yield stream
        yield from parse_object(obj.original_bytes, matcher=matcher, parent=stream,
                                pdf_header_offset=pdf_header_offset)
    elif isinstance(obj, PDFList):
        list_obj = Submatch(
            "PDFList",
            '',
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )
        yield list_obj
        for item in obj:
            yield from parse_object(item, matcher=matcher, parent=list_obj, pdf_header_offset=pdf_header_offset)
    elif isinstance(obj, PDFDict):
        dict_obj = Submatch(
            "PDFDictionary",
            '',
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes - 1,
            parent=parent
        )
        yield dict_obj
        for key, value in obj.items():
            if not hasattr(value, "pdf_offset") or not hasattr(value, "pdf_bytes"):
                if isinstance(value, list):
                    value = PDFList.load(value)
                else:
                    raise ValueError(f"Unexpected PDF dictionary value {value!r}")
            pair = Submatch(
                "KeyValuePair",
                '',
                relative_offset=key.pdf_offset - (dict_obj.offset - pdf_header_offset) - 1,
                length=value.pdf_offset + value.pdf_bytes - key.pdf_offset,
                parent=dict_obj
            )
            yield pair
            yield Submatch(
                "Key",
                key,
                relative_offset=0,
                length=key.pdf_bytes + 1,
                parent=pair
            )
            value_match = Submatch(
                "Value",
                value,
                relative_offset=value.pdf_offset - key.pdf_offset,
                length=value.pdf_bytes,
                parent=pair
            )
            yield value_match
            yield from parse_object(value, matcher=matcher, parent=value_match, pdf_header_offset=pdf_header_offset)
    elif isinstance(obj, PDFDeciphered):
        deciphered = Submatch(
            "PDFDeciphered",
            obj.original_bytes,
            decoded=obj,
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )
        yield deciphered
        with Tempfile(obj) as f:
            yield from matcher.match(f, parent=deciphered)
    elif isinstance(obj, PSBytes):
        if isinstance(obj, PNGPredictor):
            match = Submatch(
                "PNGPredictor",
                bytes(obj.original_bytes),
                decoded=obj,
                relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
                length=obj.pdf_bytes,
                parent=parent
            )
            yield from parse_object(obj.params, matcher=matcher, parent=match, pdf_header_offset=pdf_header_offset)
            yield from parse_object(obj.original_bytes, matcher=matcher, parent=match,
                                    pdf_header_offset=pdf_header_offset)
        else:
            match = Submatch(
                obj.__class__.__name__,
                bytes(obj),
                relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
                length=obj.pdf_bytes,
                parent=parent
            )
        if hasattr(obj, "original_bytes"):
            yield from parse_object(obj.original_bytes, matcher=matcher, parent=match,
                                    pdf_header_offset=pdf_header_offset)
        # recursively match against the deflated contents
        with Tempfile(obj) as f:
            yield from matcher.match(f, parent=match)
    elif hasattr(obj, "pdf_offset") and hasattr(obj, "pdf_bytes"):
        yield Submatch(
            obj.__class__.__name__,
            obj,
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )


class InstrumentedPDFDocument(PDFDocument):
    def __init__(self, *args, **kwargs):
        self._xrefs = []
        self._decipher: Optional[DecipherCallable] = None
        try:
            super().__init__(*args, **kwargs)
        except PDFSyntaxError as pse:
            if "No /Root object" not in str(pse):
                raise pse
            # this is a malformed PDF without a trailer root object
            old_get_trailer = PDFXRef.get_trailer

            def get_trailer(_):
                return {"Root": {}}

            try:
                PDFXRef.get_trailer = get_trailer
                # try it again with our patched trailer loading:
                super().__init__(*args, **kwargs)
            finally:
                PDFXRef.get_trailer = old_get_trailer

    # @property
    # def xrefs(self):
    #     if not self._xrefs:
    #         pass
    #     return self._xrefs
    #
    # @xrefs.setter
    # def xrefs(self, new_value):
    #     self._xrefs = new_value

    @property
    def decipher(self) -> DecipherCallable:
        if self._decipher is None:
            return None
        else:
            return self.do_decipher

    @decipher.setter
    def decipher(self, new_value: DecipherCallable):
        self._decipher = new_value

    def do_decipher(self, *args, **kwargs) -> PSBytes:
        deciphered = self._decipher(*args, **kwargs)
        if isinstance(deciphered, bytes) and not isinstance(deciphered, PSBytes):
            for arg in args:
                if isinstance(arg, PSBytes):
                    deciphered = PDFDeciphered(
                        deciphered,
                        pdf_offset=arg.pdf_offset,
                        pdf_bytes=arg.pdf_bytes,
                        original_bytes=arg
                    )
                    break
        return deciphered


# The default libmagic test for detecting PDFs is too restrictive:
class RelaxedPDFMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/pdf",
            extensions=("pdf",),
            message="Malformed PDF"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if b"%PDF-" in data:
            return MatchedTest(self, value=data, offset=0, length=len(data))
        return FailedTest(self, offset=0, message="data did not contain \"%PDF-\"")


MagicMatcher.DEFAULT_INSTANCE.add(RelaxedPDFMatcher())


def reverse_skip_whitespace(file_stream) -> bool:
    found_whitespace = False
    while True:
        try:
            file_stream.seek(-1, from_what=1)
        except IndexError:
            break
        b = file_stream.read(1)
        if b not in (b' ', b'\t', b'\n'):
            break
        found_whitespace = True
        file_stream.seek(-1, from_what=1)
    return found_whitespace


def skip_whitespace(file_stream) -> bool:
    found_whitespace = False
    while True:
        b = file_stream.read(1)
        if b not in (b' ', b'\t', b'\n'):
            try:
                file_stream.seek(-1, from_what=1)
            except IndexError:
                pass
            break
        found_whitespace = True
    return found_whitespace


def reverse_expect(file_stream, expected: Union[bytes, Callable[[int, bytes], bool]]) -> bytes:
    skipped_bytes = 0
    start_pos = file_stream.tell()
    with file_stream.save_pos():
        if isinstance(expected, bytes):
            try:
                file_stream.seek(-len(expected), from_what=1)
            except IndexError:
                return b""
            if file_stream.read(len(expected)) != expected:
                return b""
            skipped_bytes = len(expected)
        else:
            while True:
                try:
                    file_stream.seek(start_pos - skipped_bytes - 1)
                except IndexError:
                    return b""
                b = file_stream.read(1)
                if not expected(skipped_bytes, b):
                    break
                skipped_bytes += 1
    file_stream.seek(start_pos - skipped_bytes)
    try:
        return file_stream.read(skipped_bytes)
    finally:
        file_stream.seek(start_pos - skipped_bytes)


def pdf_obj_parser(file_stream, obj, objid: int, parent: Match, pdf_header_offset: int = 0) -> Iterator[Submatch]:
    data: Optional[bytes] = None
    if isinstance(obj, PDFObjectStream):
        log.status(f"Parsing PDF obj {obj.objid!s} {obj.genno!s}")
        try:
            data = obj.get_data()
        except PDFNotImplementedError as e:
            log.error(f"Unsupported PDF stream filter in object {obj.objid!s} {obj.genno!s}: {e!s}")
        relative_offset = obj.attrs.pdf_offset
        obj_length = obj.data_value.pdf_offset - obj.attrs.pdf_offset + obj.data_value.pdf_bytes - 1
    else:
        log.status(f"Parsing PDF obj {objid!s}")
        relative_offset = obj.pdf_offset
        obj_length = obj.pdf_bytes - 1
    with file_stream.save_pos():
        file_stream.seek(parent.offset + relative_offset - pdf_header_offset)
        reverse_skip_whitespace(file_stream)
        if reverse_expect(file_stream, b"obj") and reverse_skip_whitespace(file_stream):
            version = reverse_expect(file_stream, lambda _, b: ord('0') <= b[0] <= ord('9'))
            if version and reverse_skip_whitespace(file_stream):
                obj_id = reverse_expect(file_stream, lambda _, b: ord('0') <= b[0] <= ord('9'))
                if obj_id:
                    obj_offset = parent.offset + relative_offset - pdf_header_offset - file_stream.tell()
                    relative_offset -= obj_offset
                    obj_length += obj_offset
        file_stream.seek(parent.offset + relative_offset - pdf_header_offset + obj_length)
        skip_whitespace(file_stream)
        if file_stream.read(6) == b"endobj":
            skip_whitespace(file_stream)
            obj_length = file_stream.tell() - (parent.offset + relative_offset - pdf_header_offset)
    if isinstance(obj, PDFObjectStream):
        match = Submatch(
            name="PDFObject",
            display_name=f"PDFObject{obj.objid!s}.{obj.genno!s}",
            match_obj=(obj.objid, obj.genno),
            relative_offset=relative_offset,
            length=obj_length,
            parent=parent
        )
        yield match
        yield from parse_object(obj.attrs, matcher=parent.matcher, parent=match, pdf_header_offset=pdf_header_offset)
        if data is not None:
            yield from parse_object(data, matcher=parent.matcher, parent=match, pdf_header_offset=pdf_header_offset)
    else:
        match = Submatch(
            name="PDFObject",
            display_name=f"PDFObject{objid}",
            match_obj=objid,
            relative_offset=relative_offset,
            length=obj_length,
            parent=parent
        )
        yield match
        yield from parse_object(obj, parent.matcher, match, pdf_header_offset=pdf_header_offset)
    log.clear_status()


@register_parser("application/pdf")
def pdf_parser(file_stream, parent: Match):
    # pdfminer expects %PDF to be at byte offset zero in the file
    pdf_header_offset = file_stream.first_index_of(b"%PDF")
    if pdf_header_offset > 0:
        # the PDF header does not start at byte offset zero!
        yield Submatch(
            "IgnoredPDFPreamble",
            b"",
            relative_offset=0,
            length=pdf_header_offset,
            parent=parent
        )
        pdf_content = Submatch(
            "OffsetPDFContent",
            b"",
            relative_offset=pdf_header_offset,
            parent=parent
        )
        yield pdf_content
        with FileStream(file_stream, start=pdf_header_offset) as f:
            yield from pdf_parser(f, pdf_content)
        return
    pdf_header_offset = file_stream.start
    parser = PDFParser(RawPDFStream(file_stream))
    doc = InstrumentedPDFDocument(parser)
    yielded = set()
    for xref in doc.xrefs:
        for objid in xref.get_objids():
            try:
                obj = doc.getobj(objid)
            except PDFObjectNotFound:
                continue
            if isinstance(obj, PDFObjectStream):
                if (obj.objid, obj.genno) in yielded:
                    continue
                yielded.add((obj.objid, obj.genno))
            else:
                if objid in yielded or not hasattr(obj, "pdf_offset") or not hasattr(obj, "pdf_bytes"):
                    continue
                yielded.add(objid)
            yield from pdf_obj_parser(file_stream, obj, objid, parent, pdf_header_offset=pdf_header_offset)

        trailer = xref.get_trailer()
        if trailer is not None:
            trailer_start = min(k.pdf_offset for k in trailer.keys())
            trailer_end = max(v.pdf_offset + v.pdf_bytes for v in trailer.values())
            t = Submatch(
                "Trailer",
                b"",
                relative_offset=trailer_start,
                length=trailer_end - trailer_start,
                parent=parent
            )
            yield t
            for k, v in trailer.items():
                kvp = Submatch(
                    "KeyValuePair",
                    b"",
                    relative_offset=k.pdf_offset - trailer_start,
                    length=v.pdf_offset + v.pdf_bytes - k.pdf_offset,
                    parent=t
                )
                yield kvp
                yield Submatch(
                    "Key",
                    k,
                    relative_offset=k.pdf_offset - k.pdf_offset,
                    length=k.pdf_bytes,
                    parent=kvp
                )
                value_match = Submatch(
                    "Value",
                    b"",
                    relative_offset=v.pdf_offset - k.pdf_offset,
                    length=v.pdf_bytes,
                    parent=kvp
                )
                yield value_match
                yield from parse_object(v, matcher=parent.matcher, parent=value_match,
                                        pdf_header_offset=pdf_header_offset)

        if not isinstance(xref, PDFXRef):
            continue

        xref_start = min(min(c.pdf_offset for c in row if c is not None) for row in xref.offsets.values())
        xref_end = max(max(c.pdf_offset + c.pdf_bytes for c in row if c is not None) for row in xref.offsets.values())
        x = Submatch(
            "XRefTable",
            b"",
            relative_offset=xref_start,
            length=xref_end - xref_start,
            parent=parent
        )
        yield x
        for row in xref.offsets.values():
            row_start = min(c.pdf_offset for c in row if c is not None)
            row_end = max(c.pdf_offset + c.pdf_bytes for c in row if c is not None)
            row_match = Submatch(
                "XRefRow",
                b"",
                relative_offset=row_start - xref_start,
                length=row_end - row_start,
                parent=x
            )
            yield row_match
            obj_id, pos, gen_no = row
            if obj_id is not None:
                ret = Submatch(
                    "ObjectID",
                    b"",
                    relative_offset=obj_id.pdf_offset - row_start,
                    length=obj_id.pdf_bytes,
                    parent=row_match
                )
                yield ret
                yield from parse_object(obj_id, matcher=parent.matcher, parent=ret, pdf_header_offset=pdf_header_offset)
            ret = Submatch(
                "Position",
                b"",
                relative_offset=pos.pdf_offset - row_start,
                length=pos.pdf_bytes,
                parent=row_match
            )
            yield ret
            yield from parse_object(ret, matcher=parent.matcher, parent=ret, pdf_header_offset=pdf_header_offset)
            ret = Submatch(
                "Generation",
                b"",
                relative_offset=gen_no.pdf_offset - row_start,
                length=gen_no.pdf_bytes,
                parent=row_match
            )
            yield ret
            yield from parse_object(ret, matcher=parent.matcher, parent=ret, pdf_header_offset=pdf_header_offset)
