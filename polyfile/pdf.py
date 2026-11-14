import codecs
from dataclasses import dataclass
from encodings.utf_8 import decode as decode_utf8
from typing import (
    TYPE_CHECKING,
    BinaryIO,
    Generic,
    Protocol,
    Self,
    SupportsIndex,
    TypeGuard,
    TypeVar,
    cast,
    overload,
)
from collections.abc import Callable, Iterator
from collections.abc import Container, Iterable, Sized
from operator import contains
import zlib
import operator
import sys

from polyfile._pdfminer_adapter import (
    ascii85decode,
    asciihexdecode,
    ccittfaxdecode,
    lzwdecode,
    PDFSyntaxError,
    PDFNotImplementedError,
    rldecode,
    PDFMinerParser,
    PDFStream,
    PDFObjRef,
    PSBaseParserToken,
    PSKeyword,
    PSObject,
    PSLiteral,
    PSStackEntry,
    PSSyntaxError,
    PDFXRef,
    PDFXRefFallback,
    KWD,
    PDFNoValidXRef,
    PSEOF,
    dict_value,
    LITERAL_XREF,
    LITERAL_OBJSTM,
    LITERAL_CATALOG,
    DecipherCallable,
    PDFObjectNotFound,
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
    AdapterPDFDocument,
    settings,
    safe_int,
)

from polyfile.compression import match_decoded
from polyfile.analysis import AnalysisContext, AnalysisLimits

from polyfile.fileutils import FileStream
from polyfile.fileutils import Tempfile
from polyfile.logger import getStatusLogger
from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)
from polyfile.polyfile import Match, Matcher, Submatch

log = getStatusLogger("PDF")


@dataclass
class _DecodedPDFSource:
    source: str
    data: bytes
    match: Match | None = None


_PDFSources = dict[int, _DecodedPDFSource]


def load_trailer(self: PDFXRef, parser: PDFMinerParser) -> None:
    assert isinstance(parser, PDFParser)
    try:
        (_, kwd) = parser.nexttoken()
        assert kwd == KWD(b"trailer"), f"{kwd!s} != {KWD(b'trailer')!s}"
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
            raise PDFNoValidXRef("Unexpected EOF - file corrupted")
        (_, dic) = x[0]
    self.trailer.update(dict_value(dic))
    log.debug("trailer=%r", self.trailer)
    return


def load_xref(self: PDFXRef, parser: PDFMinerParser) -> None:
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
            error_msg = f"Trailer not found: {parser!r}: line={line!r}"
            raise PDFNoValidXRef(error_msg)
        try:
            (start, nobjs) = map(int, f)
        except ValueError:
            error_msg = f"Invalid line: {parser!r}: line={line!r}"
            raise PDFNoValidXRef(error_msg)
        for objid in range(start, start + nobjs):
            try:
                (_, line) = parser.nextline()
                line = line.strip()
            except PSEOF:
                raise PDFNoValidXRef("Unexpected EOF - file corrupted?")
            f = line.split(b" ")
            if len(f) != 3:
                error_msg = f"Invalid XRef format: {parser!r}, line={line!r}"
                raise PDFNoValidXRef(error_msg)
            (pos_b, genno_b, use_b) = f
            if use_b != b"n":
                continue
            assert isinstance(pos_b, PSBytes) and isinstance(genno_b, PSBytes)
            self.offsets[objid] = (None, pos_b.as_int(), genno_b.as_int())
    log.debug("xref objects: %r", self.offsets)
    self.load_trailer(parser)


class InstrumentedPDFXRef(PDFXRef):
    load_trailer = load_trailer
    load = load_xref


class InstrumentedPDFXRefFallback(PDFXRefFallback):
    load_trailer = load_trailer


class Provenance(Protocol):
    """The byte span carried by instrumented PDF values."""

    @property
    def pdf_offset(self) -> int: ...

    @property
    def pdf_bytes(self) -> int: ...


def _restore_pdf_token(token_class: type[object], value: object) -> object:
    """Allocate a primitive wrapper before pickle restores its metadata and entries."""
    for base in (int, float, str, bytes, list, dict):
        if issubclass(token_class, base):
            allocate = cast(Callable[..., object], base.__new__)
            if base in (list, dict):
                return allocate(token_class)
            return allocate(token_class, value)
    raise TypeError(f"Unsupported PDF token class: {token_class.__name__}")


class PSToken:
    """A parsed value whose wrappers carry its original PDF byte span.

    Python's numeric conversion protocols return native values without provenance. Use
    ``as_int()`` or ``as_float()`` when the converted value must retain ``pdf_offset`` and
    ``pdf_bytes`` for subsequent structure mapping.

    These attributes describe a token's source span. Inherited numeric arithmetic can return
    native values and does not combine the provenance of its operands.
    """

    pdf_offset: int
    pdf_bytes: int
    _pdf_byte_aligned: bool

    def __new__(cls, *args, **kwargs) -> Self:
        ret = super().__new__(cls, *args)
        ret.pdf_offset = kwargs["pdf_offset"]
        ret.pdf_bytes = kwargs["pdf_bytes"]
        if args and isinstance(args[0], PSToken):
            source = args[0]
            ret._pdf_byte_aligned = isinstance(source, PSSequence) and source._is_byte_aligned()
        return ret

    def __int__(self):
        if isinstance(self, int):
            return int.__int__(self)
        if isinstance(self, float):
            return float.__int__(self)
        if isinstance(self, (str, bytes, bytearray)):
            return int(self, base=10)
        raise TypeError("int() can't convert non-string with explicit base")

    def as_int(self):
        """Converts a numeric token to an integer while retaining its byte provenance."""
        return PSInt(int(self), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def as_float(self) -> "PSFloat":
        """Convert a numeric token to a float while preserving its original source span.

        Returns:
            A PSFloat carrying this token's pdf_offset and pdf_bytes.

        Raises:
            ValueError: If a text or byte token does not represent a floating-point number.
            OverflowError: If an integer token is too large to convert to a float.
        """
        return PSFloat(float(self), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)

    def __float__(self) -> float:
        """Return a native float; use as_float() to retain PDF byte provenance.

        Python's float() strips float-subclass metadata and warns when this method returns
        a strict subclass. The explicit conversion method preserves a tagged result.
        """
        if isinstance(self, float):
            return float.__float__(self)
        elif isinstance(self, int):
            return float(int(self))
        elif isinstance(self, bytes):
            return float(bytes.__getitem__(self, slice(None)))
        elif isinstance(self, PSStr):
            return float(str.__str__(self))
        else:
            raise NotImplementedError()

    def __bytes__(self):
        if isinstance(self, PSBytes):
            return self
        if isinstance(self, str):
            raise TypeError("string argument without an encoding")
        if isinstance(self, int):
            result = PSBytes(bytes(int(self)), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
            result._pdf_byte_aligned = False
            return result
        raise TypeError(f"cannot convert '{type(self).__name__}' object to bytes")

    def __getnewargs_ex__(self) -> tuple[tuple[object, ...], dict[str, object]]:
        """Supply constructor arguments before copy and pickle restore token state."""
        if isinstance(self, int):
            value = int.__int__(self)
        elif isinstance(self, float):
            value = float.__float__(self)
        elif isinstance(self, str):
            value = str.__str__(self)
        elif isinstance(self, bytes):
            value = bytes.__getitem__(self, slice(None))
        else:
            return (), dict(self.__dict__)
        return (value,), dict(self.__dict__)

    def __reduce_ex__(self, protocol: SupportsIndex, /):
        protocol = operator.index(protocol)
        if protocol >= 2:
            return super().__reduce_ex__(protocol)
        args, _ = self.__getnewargs_ex__()
        items = iter(self) if isinstance(self, list) else None
        return (
            _restore_pdf_token, (type(self), args[0] if args else None), self.__dict__, items,
        )

    def __str__(self):
        raise NotImplementedError()

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({super().__repr__()}, pdf_offset={self.pdf_offset!r}, "
            f"pdf_bytes={self.pdf_bytes!r})"
        )


class PSInt(PSToken, int):
    def __index__(self):
        return int.__index__(self)

    def __str__(self):
        result = PSStr(str(int(self)), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        result._pdf_byte_aligned = False
        return result


ElementT = TypeVar("ElementT")
SequenceT = TypeVar("SequenceT")
BaseT_co = TypeVar("BaseT_co", covariant=True)


class PrimitiveSequence(Protocol[BaseT_co]):
    def __add__(self, other: object, /) -> BaseT_co: ...

    @overload
    def __getitem__(self, index: SupportsIndex, /) -> object: ...

    @overload
    def __getitem__(self, index: slice, /) -> BaseT_co: ...


class PSSequence(PSToken, Generic[ElementT, SequenceT]):
    """Preserve provenance while retaining the underlying builtin sequence contracts."""

    if TYPE_CHECKING:

        def __len__(self) -> int: ...

    def _slice(self, start: int | None, stop: int | None) -> "PSSequence[ElementT, SequenceT]":
        return cast("PSSequence[ElementT, SequenceT]", self[slice(start, stop)])

    def _is_byte_aligned(self) -> bool:
        """Whether value positions still correspond to ascending individual source bytes.

        Unmarked text and byte values are initially aligned when their value length equals
        their source span. Transformed wrappers and explicitly nonlinear derived values stay
        nonlinear even when their lengths happen to match again. This marker is internal;
        it does not extend the output schema or provide a per-byte source map.

        Codec conversions certify alignment only for native ASCII, ASCII-only UTF-8, and
        representable Latin-1 values. Other conversions retain the original whole span.
        Native codec identities come from immutable dispatch entries rather than mutable
        codec attributes or overridden indexing.
        """
        return (
            isinstance(self, (str, bytes))
            and self.pdf_bytes == len(self)
            and bool(getattr(self, "_pdf_byte_aligned", True))
            and not hasattr(self, "original_bytes")
        )

    def _slice_span(self, selection: slice) -> tuple[int, int, bool]:
        """Return an enclosing aligned interval, or the original whole nonlinear span.

        Structured sequences do not have a byte-per-element map. Their slices conservatively
        retain the whole source span; integer selection separately preserves an element's own
        recorded provenance when it is available.
        """
        if not self._is_byte_aligned():
            return self.pdf_offset, self.pdf_bytes, False
        positions = range(*selection.indices(len(self)))
        if not positions:
            boundary = min(max(positions.start, 0), len(self))
            return self.pdf_offset + boundary, 0, True
        start = min(positions[0], positions[-1])
        end = max(positions[0], positions[-1]) + 1
        aligned = len(positions) == 1 or positions.step == 1
        return self.pdf_offset + start, end - start, aligned

    @staticmethod
    def _byte_separator(separator) -> bytes:
        """Validate a contiguous buffer and expose its raw bytes as a separator."""
        if type(separator) is bytes:
            return separator
        with memoryview(separator) as buffer:
            if not buffer.c_contiguous:
                raise BufferError("split separator must be a C-contiguous buffer")
            return buffer.tobytes()

    def split(self, sep: object | None = None, maxsplit: SupportsIndex = -1) -> list[SequenceT]:
        """Split token values while retaining their slice wrappers.

        Args:
            sep: Separator sequence, or None to use the token's whitespace rules. Text values
                require str separators; byte values accept contiguous buffer providers.
            maxsplit: Maximum splits; negative values split every separator. Values supporting
                Python's integer index protocol are accepted, like builtin str and bytes.

        Returns:
            Token slices, retaining empty fields for explicit separators and respecting maxsplit.

        Raises:
            ValueError: If the separator is empty.
            TypeError: If the separator has an incompatible type or maxsplit is not an index.
            OverflowError: If maxsplit exceeds the platform's index-sized integer range.
            BufferError: If a byte separator's buffer is not C-contiguous.
        """
        maximum = operator.index(maxsplit)
        if not -sys.maxsize - 1 <= maximum <= sys.maxsize:
            raise OverflowError("Python int too large to convert to C ssize_t")
        if sep is None:
            return self._split_whitespace(maximum)
        if isinstance(self, str):
            if not isinstance(sep, str):
                raise TypeError(f"must be str or None, not {type(sep).__name__}")
        elif isinstance(self, bytes):
            sep = self._byte_separator(sep)
        if not sep:
            raise ValueError("empty separator")
        return self._split_separator(sep, maximum)

    def _split_whitespace(self, maximum: int) -> list[SequenceT]:
        result: list[SequenceT] = []
        start = 0
        while start < len(self):
            while start < len(self) and not self._slice(start, start + 1).strip():
                start += 1
            if start == len(self):
                break
            if maximum == 0:
                result.append(self[start:])
                break
            stop = start
            while stop < len(self) and self._slice(stop, stop + 1).strip():
                stop += 1
            result.append(self[start:stop])
            start = stop
            maximum -= 1
        return result

    def _split_separator(self, separator: object, maximum: int) -> list[SequenceT]:
        result: list[SequenceT] = []
        start = 0
        offset = 0
        width = len(cast(Sized, separator))
        while offset <= len(self) - width and maximum != 0:
            if self[offset : offset + width] == separator:
                result.append(self[start:offset])
                start = offset + width
                offset = start
                maximum -= 1
            else:
                offset += 1
        result.append(self[start:])
        return result

    def __add__(self, other: object) -> SequenceT:
        value = cast(PrimitiveSequence[SequenceT], super()).__add__(other)
        length = self.pdf_bytes
        aligned = self._is_byte_aligned() and not other
        if (
            isinstance(other, self.__class__)
            and other.pdf_offset == self.pdf_offset + self.pdf_bytes
        ):
            length += other.pdf_bytes
            aligned = self._is_byte_aligned() and other._is_byte_aligned()
        result = self.__class__(value, pdf_offset=self.pdf_offset, pdf_bytes=length)
        result._pdf_byte_aligned = aligned
        return cast(SequenceT, result)

    def __radd__(self, other: object) -> SequenceT:
        base = cast(PrimitiveSequence[SequenceT], super())
        value = cast(PrimitiveSequence[SequenceT], other) + base.__getitem__(slice(None))
        offset, length = self.pdf_offset, self.pdf_bytes
        aligned = False
        if (
            isinstance(other, self.__class__)
            and other.pdf_offset + other.pdf_bytes == offset
        ):
            offset = other.pdf_offset
            length += other.pdf_bytes
            aligned = other._is_byte_aligned() and self._is_byte_aligned()
        elif not isinstance(other, PSSequence) and self._is_byte_aligned():
            offset -= len(cast(Sized, other))
            length += len(cast(Sized, other))
            aligned = True
        result = self.__class__(value, pdf_offset=offset, pdf_bytes=length)
        result._pdf_byte_aligned = aligned
        return cast(SequenceT, result)

    def lstrip(self, chars: object | None = None) -> SequenceT:
        if chars is None:
            chars = " \t\n\r" if isinstance(self, str) else b" \t\n\r"
        ret: PSSequence[ElementT, SequenceT] = self
        while ret and contains(cast(Container[object], chars), ret[0]):
            ret = ret._slice(1, None)
        return cast(SequenceT, ret)

    def rstrip(self, chars: object | None = None) -> SequenceT:
        if chars is None:
            chars = " \t\n\r" if isinstance(self, str) else b" \t\n\r"
        ret: PSSequence[ElementT, SequenceT] = self
        while ret and contains(cast(Container[object], chars), ret[-1]):
            ret = ret._slice(None, -1)
        return cast(SequenceT, ret)

    def strip(self, chars: object | None = None) -> SequenceT:
        stripped = cast(PSSequence[ElementT, SequenceT], self.lstrip(chars))
        return stripped.rstrip(chars)

    @overload
    def __getitem__(self, item: SupportsIndex) -> ElementT: ...

    @overload
    def __getitem__(self, item: slice) -> SequenceT: ...

    def __getitem__(self, item):
        base = cast(PrimitiveSequence[SequenceT], super())
        if not isinstance(item, (int, slice)) and hasattr(type(item), "__index__"):
            item = operator.index(item)
        if isinstance(item, int):
            value = base.__getitem__(item)
            if has_provenance(value):
                return cast(ElementT, value)
            index = item if item >= 0 else len(self) + item
            offset, length, aligned = self._slice_span(slice(index, index + 1))
            result = make_ps_object(value, pdf_offset=offset, pdf_bytes=length)
            if isinstance(result, PSSequence):
                result._pdf_byte_aligned = aligned
            return cast(ElementT, result)
        elif isinstance(item, slice):
            value = base.__getitem__(item)
            offset, length, aligned = self._slice_span(item)
            try:
                result = self.__class__(value, pdf_offset=offset, pdf_bytes=length)
            except ValueError:
                if isinstance(self, PSBytes):
                    result = PSBytes(value, pdf_offset=offset, pdf_bytes=length)
                else:
                    raise
            result._pdf_byte_aligned = aligned
            return cast(SequenceT, result)
        else:
            return base.__getitem__(item)


class PSStr(PSSequence[str, str], str):
    pdf_raw_name: bytes | None = None

    def __getitem__(self, item: SupportsIndex | slice) -> str:
        return super().__getitem__(item)

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> "PSBytes":
        if (
            not isinstance(encoding, str) or not isinstance(errors, str)
            or str.__contains__(encoding, "\x00") or str.__contains__(errors, "\x00")
        ):
            super().encode(encoding, errors)
        encoder: object = tuple.__getitem__(codecs.lookup(encoding), 0)
        result = PSBytes(
            super().encode(encoding, errors), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes
        )
        ascii_encoding = encoder is codecs.ascii_encode or encoder is codecs.utf_8_encode
        one_byte_mapping = (
            ascii_encoding and str.isascii(self)
            or encoder is codecs.latin_1_encode
            and all(ord(char) <= 0xFF for char in str.__iter__(self))
        )
        result._pdf_byte_aligned = (
            self._is_byte_aligned() and one_byte_mapping and len(result) == len(self)
        )
        return result

    def __str__(self):
        return self


class PSBytes(PSSequence[int, bytes], bytes):
    def __new__(cls, *args, **kwargs) -> Self:
        kwargs = dict(kwargs)
        if "pdf_bytes" not in kwargs:
            kwargs["pdf_bytes"] = len(args[0])
        return super().__new__(cls, *args, **kwargs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            value = bytes.__getitem__(self, item)
            offset, length, aligned = self._slice_span(item)
            result = PSBytes(value, pdf_offset=offset, pdf_bytes=length)
            result._pdf_byte_aligned = aligned
            return result
        else:
            ret = super().__getitem__(item)
            if isinstance(ret, PSInt):
                return ret
            else:
                return PSInt(ret, pdf_offset=self.pdf_offset + item)

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> PSStr:
        if (
            not isinstance(encoding, str) or not isinstance(errors, str)
            or str.__contains__(encoding, "\x00") or str.__contains__(errors, "\x00")
        ):
            super().decode(encoding, errors)
        decoder: object = tuple.__getitem__(codecs.lookup(encoding), 1)
        result = PSStr(
            super().decode(encoding, errors), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes
        )
        ascii_decoding = decoder is codecs.ascii_decode or decoder is decode_utf8
        one_byte_mapping = (
            ascii_decoding and bytes.isascii(self)
            or decoder is codecs.latin_1_decode
        )
        result._pdf_byte_aligned = (
            self._is_byte_aligned() and one_byte_mapping and len(result) == len(self)
        )
        return result


    def __str__(self):
        result = PSStr(bytes.__repr__(self), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        result._pdf_byte_aligned = False
        return result


class PDFDeciphered(PSBytes):
    original_bytes: bytes

    def __new__(cls, *args, **kwargs) -> Self:
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
        result = PSStr(float.__repr__(self), pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        result._pdf_byte_aligned = False
        return result


class PSBool:
    def __init__(self, value: bool, pdf_offset: int, pdf_bytes: int):
        self.value: bool = value
        self.pdf_offset: int = pdf_offset
        self.pdf_bytes: int = pdf_bytes

    def __bool__(self):
        return self.value

    def __int__(self):
        return int(self.value)

    def __eq__(self, other):
        return self.value == bool(other)

    def __ne__(self, other):
        return self.value != bool(other)

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        result = PSStr(self.value, pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        result._pdf_byte_aligned = False
        return result

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r}, pdf_offset={self.pdf_offset!r}, "\
               f"pdf_bytes={self.pdf_bytes!r})"


class PDFLiteral(PSLiteral):
    def __init__(
        self, name: PSLiteral.NameType, pdf_offset: int, pdf_bytes: int,
        *, raw_name: bytes | None = None,
    ):
        """Wrap a name with its full lexical span, including the leading slash."""
        self.raw_name = raw_name
        if isinstance(name, str):
            wrapped = PSStr(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes - 1)
            if raw_name is not None:
                wrapped._pdf_byte_aligned = str.isascii(name) and str.encode(name) == raw_name
            wrapped.pdf_raw_name = raw_name
        else:
            wrapped = PSBytes(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes - 1)
            if raw_name is not None:
                wrapped._pdf_byte_aligned = name == raw_name
        super().__init__(wrapped)

    @property
    def pdf_bytes(self) -> int:
        name = self.name
        assert has_provenance(name)
        return name.pdf_bytes + 1

    @property
    def pdf_offset(self) -> int:
        name = self.name
        assert has_provenance(name)
        return name.pdf_offset - 1

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


PDFBaseParserToken = PSFloat | PSBool | PDFLiteral | PSKeyword | PSBytes | PSInt


"""
pdfminer.pdfdocument unfortunately tests for equality with these literals using `is` rather than `==`, so we must
return their singletons from a dict rather than our instrumented PDFLiteral objects:
"""
PROTECTED_LITERALS: dict[str | bytes, PSLiteral] = {
    LITERAL_OBJSTM.name: LITERAL_OBJSTM,
    LITERAL_XREF.name: LITERAL_XREF,
    LITERAL_CATALOG.name: LITERAL_CATALOG
}


class PDFDict(dict[str, object]):
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

    def __new__(cls, *args, pdf_offset: int, pdf_bytes: int, **kwargs) -> Self:
        ret = super().__new__(cls, *args, **kwargs)
        ret.pdf_offset = pdf_offset
        ret.pdf_bytes = pdf_bytes
        return ret

    def __str__(self):
        return dict.__str__(self)

    def __getnewargs_ex__(self) -> tuple[tuple[object, ...], dict[str, object]]:
        """Reconstruct an empty mapping before restoring entries and provenance."""
        return (), dict(self.__dict__)

    def __reduce_ex__(self, protocol: SupportsIndex, /):
        protocol = operator.index(protocol)
        if protocol >= 2:
            return super().__reduce_ex__(protocol)
        return _restore_pdf_token, (type(self), None), self.__dict__, None, iter(self.items())



class PDFList(PSSequence[object, list[object]], list[object]):
    def __init__(self, items: Iterable[object] = (), *, pdf_offset: int, pdf_bytes: int):
        list.__init__(self, items)

    @classmethod
    def load(cls, items: Iterable[object]) -> Self:
        """Load a PDFList from an iterable of items.

        Handles edge cases:
        - Empty lists: returns zero-length wrapper at offset 0
        - Items without offsets: filters them out, warns if all lack offsets

        Args:
            items: An iterable of PDF objects to load into a list

        Returns:
            A PDFList with calculated offset and byte length based on contained items
        """
        if not cast(object, items):
            # Empty list case: return zero-length wrapper
            return cls([], pdf_offset=0, pdf_bytes=0)

        items_list = list(items)

        # Filter to items that have position information
        items_with_offsets = [
            x for x in items_list
            if has_provenance(x)
        ]

        if not items_with_offsets:
            # No items have offset information - log warning and return safe default
            log.warning(
                f"PDFList with {len(items_list)} items but none have offset information"
            )
            return cls(items_list, pdf_offset=0, pdf_bytes=0)

        # Calculate bounds from items with position data
        start_offset = min(x.pdf_offset for x in items_with_offsets)
        end_offset = max(x.pdf_offset + x.pdf_bytes for x in items_with_offsets)

        return cls(items_list, pdf_offset=start_offset, pdf_bytes=end_offset - start_offset)

    def __str__(self):
        return list.__str__(self)



def make_ps_object(
    value: object, pdf_offset: int, pdf_bytes: int,
) -> PDFBaseParserToken | PSStr | PDFDict | PSObject:
    if isinstance(value, PSLiteral):
        return PDFLiteral(
            value.name, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes,
            raw_name=value.raw_name if isinstance(value, PDFLiteral) else None,
        )
    # Unfortunately, we can't convert PSKeywords to PDFKeywords here because pdfminer requires them to be singletons
    elif isinstance(value, PDFDict):
        value.pdf_offset = pdf_offset
        value.pdf_bytes = pdf_bytes
        return value
    elif isinstance(value, dict):
        return PDFDict(value, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)
    elif isinstance(value, PSKeyword):
        return value
    elif isinstance(value, PSObject):
        setattr(value, "pdf_offset", pdf_offset)
        setattr(value, "pdf_bytes", pdf_bytes)
        return value
    elif isinstance(value, int):
        supertype = PSInt
    elif isinstance(value, float):
        supertype = PSFloat
    elif isinstance(value, bytes):
        supertype = PSBytes
    elif isinstance(value, str):
        supertype = PSStr
    else:
        raise NotImplementedError(f"Add suppport for PSSequences containing elements of type {type(value)}")
    return supertype(value, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)


class DecodingError(bytes):
    message: str | None

    def __new__(cls, *args, **kwargs) -> Self:
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
    error: DecodingError | None

    def __new__(cls, *args, **kwargs) -> Self:
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

    def __new__(cls, *args, **kwargs) -> Self:
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
    def data(self) -> PSBytes | None:
        return self._data

    @data.setter
    def data(self, new_value: bytes | None):
        if new_value is not None and not isinstance(new_value, PSBytes):
            self._data = PSBytes(new_value, pdf_offset=self.pdf_offset, pdf_bytes=self.pdf_bytes)
        else:
            self._data = new_value

    @property
    def data_value(self) -> PSBytes:
        if self.data is not None:
            return self.data
        elif self.rawdata is not None:
            assert isinstance(self.rawdata, PSBytes)
            return self.rawdata
        else:
            raise ValueError(f"PDFObjectStream {self!r} does not have any data")

    def decode(self):
        assert self.data is None \
               and self.rawdata is not None, str((self.data, self.rawdata))
        assert isinstance(self.rawdata, PSBytes)
        data = self.rawdata
        if self.decipher:
            # Handle encryption
            assert self.objid is not None
            assert self.genno is not None
            deciphered = self.decipher(self.objid, self.genno, data, self.attrs)
            assert isinstance(deciphered, PSBytes)
            data = deciphered
        filters = self.get_filters()
        if not filters:
            self.data = data
            self.rawdata = None
            return
        for (f, params) in filters:
            decoded: bytes | None = None
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
                raise PDFNotImplementedError(f"Unsupported filter: {f!r}")
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
                    error_msg = f"Unsupported predictor: {pred!r}"
                    raise PDFNotImplementedError(error_msg)
        self.data = data
        self.rawdata = None
        return


class PDFParser(PDFMinerParser):
    auto_flush: bool = False

    def end_type(self, type):
        """Finalize a composite while leaving nonliteral recovery keys unpositioned."""
        pos, values = super().end_type(type)
        if type == "d":
            for index in range(0, len(values), 2):
                key = values[index]
                if isinstance(key, PDFLiteral) and isinstance(key.name, bytes):
                    try:
                        text = bytes.decode(key.name, "utf-8")
                    except UnicodeDecodeError:
                        text = bytes.__repr__(key.name)
                    name = PSStr(text, pdf_offset=key.pdf_offset + 1, pdf_bytes=key.pdf_bytes - 1)
                    name._pdf_byte_aligned = False
                    name.pdf_raw_name = key.raw_name
                    key.name = name
                elif not isinstance(key, PSLiteral):
                    values[index] = str.__str__(str(values[index]))
        return pos, values

    def _lexical_bytes(self, start: int, end: int) -> bytes:
        position = self.fp.tell()
        try:
            self.fp.seek(start)
            return self.fp.read(end - start)
        finally:
            self.fp.seek(position)

    def nexttoken(self) -> tuple[int, PSBaseParserToken]:
        """Attach raw extents after the lexer advances past a complete token."""
        position, value = super().nexttoken()
        if isinstance(value, PSKeyword):
            return position, value
        end = self.bufpos + self.charpos
        if isinstance(value, PSLiteral):
            raw_name = self._lexical_bytes(position + 1, end)
            return position, PDFLiteral(
                value.name, position, end - position, raw_name=raw_name,
            )
        if isinstance(value, bytes):
            raw = self._lexical_bytes(position, end)
            body = raw[1:-1] if raw.startswith(b"(") else raw[1:]
            token = PSBytes(value, pdf_offset=position + 1, pdf_bytes=len(body))
            token._pdf_byte_aligned = body == value
        else:
            token = make_ps_object(value, pdf_offset=position, pdf_bytes=end - position)
        return position, cast(PSBaseParserToken, token)

    @staticmethod
    def string_escape(data: bytes | int) -> str:
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

    def token_context(self, token: Provenance, padding_bytes: int = 10) -> str:
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

    def push(self, *objs: PSStackEntry[PSKeyword | PDFStream | PDFObjRef | None]):
        transformed: list[PSStackEntry[PSKeyword | PDFStream | PDFObjRef | None]] = []
        for obj in objs:
            if len(obj) == 2 and isinstance(obj[1], dict):
                length = self._curtokenpos + 2 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFDict(obj[1], pdf_offset=obj[0], pdf_bytes=length)))
            elif len(obj) == 2 and isinstance(obj[1], list):
                length = self._curtokenpos + 1 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFList(obj[1], pdf_offset=obj[0], pdf_bytes=length)))
            elif len(obj) == 2 and isinstance(obj[1], PDFStream):
                stream: PDFStream = obj[1]
                assert stream.rawdata is not None
                pos = obj[0]
                transformed.append((pos, PDFObjectStream(stream, pdf_offset=pos, pdf_bytes=len(stream.rawdata))))
            elif len(obj) == 2 and isinstance(obj[1], PSObject) \
                    and not isinstance(obj[1], (PDFLiteral, PSKeyword)):
                pos = obj[0]
                psobj = obj[1]
                length = self._curtokenpos + 1 - obj[0]
                if isinstance(psobj, PDFObjRef):
                    orig_pos = pos
                    reference_id = psobj.objid
                    assert has_provenance(reference_id)
                    pos = min(pos, reference_id.pdf_offset)
                    length += orig_pos - pos
                setattr(psobj, "pdf_offset", pos) 
                setattr(psobj, "pdf_bytes", length)
                transformed.append((pos, psobj))
            else:
                transformed.append(obj)
        return super().push(*transformed)

    def flush(self):
        if self.auto_flush:
            self.add_results(*self.popall())
        else:
            super().flush()

    def do_keyword(self, pos: int, token: PSKeyword):
        if token is self.KEYWORD_R:
            # reference to indirect object
            try:
                ((_, objid), _) = self.pop(2)
                assert isinstance(objid, int)
                obj = PDFObjRef(self.doc, objid)
                self.push((pos, obj))
            except PSSyntaxError:
                pass
        else:
            super().do_keyword(pos, token)



class RawPDFStream:
    """Delegate binary I/O while attaching view-relative provenance to bytes read."""

    def __init__(self, file_stream: FileStream):
        self._file_stream = file_stream

    def read(self, *args, **kwargs) -> PSBytes:
        offset_before = self._file_stream.tell()
        ret = self._file_stream.read(*args, **kwargs)
        return PSBytes(ret, pdf_offset=offset_before)

    def __getattr__(self, item):
        return getattr(self._file_stream, item)


class _ObjectStreamParser(PDFParser):
    auto_flush = True
    KEYWORD_OBJ = KWD(b"obj")

    def flush(self):
        """Retain the last two numbers until a reference marker can consume them."""
        while len(self.curstack) > 2:
            self.add_results(self.curstack.pop(0))
        if any(not isinstance(value, (int, float)) for _, value in self.curstack):
            self.add_results(*self.popall())

    def nextobject(self):
        try:
            return super().nextobject()
        except PSEOF:
            if self.context or not self.curstack:
                raise
            self.add_results(*self.popall())
            return self.results.pop(0)

    def do_keyword(self, pos: int, token: PSKeyword):
        if token is self.KEYWORD_R:
            (_, value), _ = self.pop(2)
            object_id = safe_int(value)
            if object_id is not None:
                if has_provenance(value):
                    object_id = PSInt(
                        object_id, pdf_offset=value.pdf_offset, pdf_bytes=value.pdf_bytes,
                    )
                self.push((pos, PDFObjRef(self.doc, object_id)))
        elif token in (self.KEYWORD_OBJ, self.KEYWORD_ENDOBJ):
            if settings.STRICT:
                raise PDFSyntaxError("Keyword obj/endobj found in object stream")
        else:
            self.push((pos, token))


def has_provenance(obj: object) -> TypeGuard[Provenance]:
    """Reports whether a parsed object records where it came from in the file.

    Every submatch PolyFile emits is positioned from the `pdf_offset` and `pdf_bytes` that this
    module's instrumented token types carry. pdfminer hands back plain `int`, `str`, `list` and
    `dict` objects on several of its recovery paths, and those cannot be mapped.

    Args:
        obj: Any object pdfminer produced while parsing.

    Returns:
        True if `obj` carries both byte-provenance attributes.
    """
    return hasattr(obj, "pdf_offset") and hasattr(obj, "pdf_bytes")


def _set_pdf_source(value: object, source: str) -> None:
    if has_provenance(value):
        setattr(value, "pdf_source", source)
    if isinstance(value, PDFLiteral):
        _set_pdf_source(value.name, source)
    elif isinstance(value, dict):
        for key, item in value.items():
            _set_pdf_source(key, source)
            _set_pdf_source(item, source)
    elif isinstance(value, list):
        for item in value:
            _set_pdf_source(item, source)
    elif isinstance(value, PDFObjRef):
        _set_pdf_source(value.objid, source)


def _match_pdf_decoded(
    parent: Match, data: bytes, sources: _PDFSources | None,
) -> Iterator[Match]:
    record = sources.get(id(data)) if sources is not None else None
    if record is not None and record.match is not None:
        return
    matches = match_decoded(parent, data, source=record.source if record is not None else None)
    decoded = next(matches)
    if record is not None:
        record.match = decoded
    yield decoded
    yield from matches


def dict_value_with_provenance(
    dict_obj: PDFDict, key: str, value: object,
) -> Provenance | None:
    """Resolves one PDF dictionary value to something that can be positioned in the file.

    A value pdfminer returned as a plain list is reloaded as a `PDFList`, which recovers the
    provenance of its members, and the dictionary is updated so that it stays self-consistent.

    Args:
        dict_obj: The dictionary that `key` belongs to.
        key: The key whose value is being resolved, used only for logging.
        value: The value to resolve.

    Returns:
        The value with byte provenance, or None when it has to be skipped.
    """
    if has_provenance(value):
        return value
    if not isinstance(value, list):
        log.warning(f"Skipping unexpected PDF dictionary value {value!r} for key {key}")
        return None
    if not value:
        log.debug(f"Skipping empty list value for key {key}")
        return None
    try:
        value = PDFList.load(value)
    except ValueError as e:
        log.warning(f"Skipping malformed list value for key {key}: {e}")
        return None
    dict_obj[key] = value
    return value


def parse_dict(
    obj: PDFDict, matcher: Matcher, parent: Match, pdf_header_offset: int,
    *, sources: _PDFSources | None = None,
) -> Iterator[Match]:
    """Yields the submatches that map a PDF dictionary and each of its key/value pairs.

    Keys and values that carry no byte provenance are logged and skipped, so one unmappable
    entry costs that entry rather than the rest of the match tree.

    Args:
        obj: The dictionary to map.
        matcher: The matcher to use when recursing into values.
        parent: The match that the dictionary is nested in.
        pdf_header_offset: The offset of `%PDF` within the file being parsed.
    """
    dict_obj = Submatch(
        "PDFDictionary",
        '',
        relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
        length=obj.pdf_bytes,
        parent=parent
    )
    yield dict_obj
    for key, value in obj.items():
        value = dict_value_with_provenance(obj, key, value)
        if value is None:
            continue
        if not has_provenance(key):
            log.warning(f"Skipping PDF dictionary key {key!r} because it has no byte provenance")
            continue
        pair = Submatch(
            "KeyValuePair",
            '',
            relative_offset=key.pdf_offset - (dict_obj.offset - pdf_header_offset) - 1,
            length=value.pdf_offset + value.pdf_bytes - (key.pdf_offset - 1),
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
            relative_offset=value.pdf_offset - (key.pdf_offset - 1),
            length=value.pdf_bytes,
            parent=pair
        )
        yield value_match
        yield from parse_object(
            value, matcher, value_match, pdf_header_offset, sources=sources,
        )


def _pdf_submatch(
    name: str, value: object, provenance: Provenance, parent: Match, source_base: int,
) -> Submatch:
    return Submatch(
        name, value, relative_offset=provenance.pdf_offset - (parent.offset - source_base),
        length=provenance.pdf_bytes, parent=parent,
    )


def _parse_pdf_filter(
    obj: PDFStreamFilter, matcher: Matcher, parent: Match, source_base: int,
    *, sources: _PDFSources | None,
) -> Iterator[Match]:
    node = _pdf_submatch(obj.name, bytes(obj.original_bytes), obj, parent, source_base)
    yield node
    if obj.error is None:
        yield from _match_pdf_decoded(node, bytes(obj), sources)
    else:
        yield Submatch("DecodingError", obj.error.message, length=obj.pdf_bytes, parent=node)
    yield from parse_object(
        obj.original_bytes, matcher, node, source_base, sources=sources,
    )


def _parse_pdf_bytes(
    obj: PSBytes, matcher: Matcher, parent: Match, source_base: int,
    *, sources: _PDFSources | None,
) -> Iterator[Match]:
    if isinstance(obj, PNGPredictor):
        node = _pdf_submatch("PNGPredictor", bytes(obj.original_bytes), obj, parent, source_base)
        yield from parse_object(obj.params, matcher, node, source_base, sources=sources)
        yield from parse_object(obj.original_bytes, matcher, node, source_base, sources=sources)
    else:
        node = _pdf_submatch(type(obj).__name__, bytes(obj), obj, parent, source_base)
    if hasattr(obj, "original_bytes"):
        yield from parse_object(obj.original_bytes, matcher, node, source_base, sources=sources)
    if hasattr(obj, "original_bytes") or sources is not None and id(obj) in sources:
        yield from _match_pdf_decoded(node, bytes(obj), sources)
    else:
        with Tempfile(obj) as stream:
            yield from matcher.match(stream, parent=node)


def parse_object(
    obj: object, matcher: Matcher, parent: Match | None = None, pdf_header_offset: int = 0,
    *, sources: _PDFSources | None = None,
) -> Iterator[Match]:
    if parent is None:
        if isinstance(obj, (PDFStreamFilter, PDFList, PDFDict, PDFDeciphered, PSBytes)) \
                or has_provenance(obj):
            raise ValueError("Mapping an instrumented PDF value requires a parent match")
        return
    if isinstance(obj, PDFStreamFilter):
        yield from _parse_pdf_filter(obj, matcher, parent, pdf_header_offset, sources=sources)
    elif isinstance(obj, PDFList):
        node = _pdf_submatch("PDFList", "", obj, parent, pdf_header_offset)
        yield node
        for item in obj:
            yield from parse_object(item, matcher, node, pdf_header_offset, sources=sources)
    elif isinstance(obj, PDFDict):
        yield from parse_dict(obj, matcher, parent, pdf_header_offset, sources=sources)
    elif isinstance(obj, PDFDeciphered):
        node = _pdf_submatch("PDFDeciphered", obj.original_bytes, obj, parent, pdf_header_offset)
        yield node
        yield from _match_pdf_decoded(node, bytes(obj), sources)
    elif isinstance(obj, PSBytes):
        yield from _parse_pdf_bytes(obj, matcher, parent, pdf_header_offset, sources=sources)
    elif has_provenance(obj):
        yield _pdf_submatch(type(obj).__name__, obj, obj, parent, pdf_header_offset)


class InstrumentedPDFDocument(AdapterPDFDocument):
    xref_class = InstrumentedPDFXRef
    fallback_xref_class = InstrumentedPDFXRefFallback

    def __init__(self, *args, analysis_context: AnalysisContext | None = None, **kwargs):
        self._decipher: DecipherCallable | None = None
        self._analysis_context = analysis_context or AnalysisContext(AnalysisLimits())
        self._decoded_sources: _PDFSources = {}
        self._decoded_streams: dict[tuple[int, int | None], _DecodedPDFSource] = {}
        try:
            super().__init__(*args, **kwargs)
        except PDFSyntaxError as error:
            if "No /Root object" not in str(error):
                raise
            log.debug("Mapping a malformed PDF without a /Root object")

    def _object_stream_source(self, stream: PDFStream, data: bytes) -> _DecodedPDFSource:
        if not hasattr(self, "_decoded_sources"):
            self._decoded_sources = {}
            self._decoded_streams = {}
            self._analysis_context = AnalysisContext(AnalysisLimits())
        key = (stream.objid, stream.genno) if stream.objid is not None else (id(stream), None)
        record = self._decoded_streams.get(key)
        if record is None:
            record = _DecodedPDFSource(self._analysis_context.next_source(), data)
            self._decoded_sources[id(data)] = record
            self._decoded_streams[key] = record
        return record

    def _bind_object_stream(self, stream: PDFObjectStream) -> None:
        if stream.objid is not None:
            record = self._decoded_streams.get((stream.objid, stream.genno))
            if record is not None:
                stream.data = record.data

    def _get_objects(self, stream: PDFStream) -> tuple[list[object], int]:
        if stream.get("Type") is not LITERAL_OBJSTM and settings.STRICT:
            raise PDFSyntaxError(f"Not an object stream: {stream.objid}")
        try:
            count = cast(int, stream["N"])
        except KeyError:
            if settings.STRICT:
                raise PDFSyntaxError(f"Missing /N in object stream {stream.objid}") from None
            count = 0
        data = stream.get_data()
        source = self._object_stream_source(stream, data)
        data = source.data
        objects: list[object] = []
        with FileStream(data) as view:
            parser = _ObjectStreamParser(cast(BinaryIO, RawPDFStream(view)))
            parser.set_document(self)
            try:
                while True:
                    _, value = parser.nextobject()
                    _set_pdf_source(value, source.source)
                    objects.append(value)
            except PSEOF:
                pass
        return objects, count

    @property
    def decipher(self) -> DecipherCallable | None:
        if self._decipher is None:
            return None
        else:
            return self.do_decipher

    @decipher.setter
    def decipher(self, new_value: DecipherCallable | None):
        self._decipher = new_value

    def do_decipher(self, *args, **kwargs) -> bytes:
        assert self._decipher is not None
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

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None,
    ) -> TestResult:
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


def reverse_expect(
    file_stream: FileStream, expected: bytes | Callable[[int, bytes], bool],
) -> bytes:
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


def _pdf_object_start(stream: FileStream, position: int) -> int:
    stream.seek(position)
    reverse_skip_whitespace(stream)
    if not reverse_expect(stream, b"obj") or not reverse_skip_whitespace(stream):
        return position
    version = reverse_expect(stream, lambda _, byte: ord("0") <= byte[0] <= ord("9"))
    if not version or not reverse_skip_whitespace(stream):
        return position
    number = reverse_expect(stream, lambda _, byte: ord("0") <= byte[0] <= ord("9"))
    return stream.tell() if number else position


def _pdf_object_extent(stream: FileStream, obj: Provenance) -> tuple[int, int]:
    if isinstance(obj, PDFObjectStream):
        attributes = obj.attrs
        if not has_provenance(attributes):
            raise ValueError("PDF stream attributes have no lexical source span")
        position = attributes.pdf_offset
        end = obj.data_value.pdf_offset + obj.data_value.pdf_bytes
    else:
        position, end = obj.pdf_offset, obj.pdf_offset + obj.pdf_bytes
    with stream.save_pos():
        start = _pdf_object_start(stream, position)
        stream.seek(end)
        skip_whitespace(stream)
        if isinstance(obj, PDFObjectStream) and stream.read(9) != b"endstream":
            return start, end - start
        skip_whitespace(stream)
        if stream.read(6) == b"endobj":
            skip_whitespace(stream)
            end = stream.tell()
    return start, end - start


def pdf_obj_parser(
    file_stream: FileStream, obj, objid: int, parent: Match, pdf_header_offset: int = 0,
    *, sources: _PDFSources | None = None,
) -> Iterator[Match]:
    """Map one physical indirect object and its instrumented body."""
    assert parent.matcher is not None
    assert has_provenance(obj)
    log.status(f"Parsing PDF obj {objid}")
    values = [obj]
    display_name, value = f"PDFObject{objid}", objid
    if isinstance(obj, PDFObjectStream):
        display_name, value = f"PDFObject{obj.objid}.{obj.genno}", (obj.objid, obj.genno)
        values = [obj.attrs]
        try:
            values.append(obj.get_data())
        except PDFNotImplementedError as error:
            log.error(f"Unsupported PDF stream filter in object {obj.objid}: {error}")
    position, size = _pdf_object_extent(file_stream, obj)
    node = Submatch(
        "PDFObject", value, display_name=display_name, relative_offset=position,
        length=size, parent=parent,
    )
    yield node
    try:
        for item in values:
            yield from parse_object(
                item, parent.matcher, node, pdf_header_offset, sources=sources,
            )
    finally:
        log.clear_status()


def parse_trailer(
    trailer, matcher: Matcher, parent: Match, pdf_header_offset: int,
) -> Iterator[Match]:
    """Yields the submatches that map a cross-reference section's trailer dictionary.

    `InstrumentedPDFDocument` retains a missing-root document's local state. A damaged
    PDF usually reaches here with a trailer that is
    empty or whose entries pdfminer rebuilt without byte provenance. Those entries are logged and
    skipped so that the cross-reference table after them is still mapped.

    Args:
        trailer: The dictionary returned by `PDFBaseXRef.get_trailer`.
        matcher: The matcher to use when recursing into values.
        parent: The match that the trailer is nested in.
        pdf_header_offset: The offset of `%PDF` within the file being parsed.
    """
    pairs = [(k, v) for k, v in trailer.items() if has_provenance(k) and has_provenance(v)]
    if len(pairs) < len(trailer):
        log.warning(f"Skipping {len(trailer) - len(pairs)} PDF trailer entries that have no byte provenance")
    if not pairs:
        log.debug("Skipping a PDF trailer that maps to no bytes in the file")
        return
    trailer_start = min(k.pdf_offset for k, _ in pairs)
    trailer_end = max(v.pdf_offset + v.pdf_bytes for _, v in pairs)
    t = Submatch(
        "Trailer",
        b"",
        relative_offset=trailer_start,
        length=trailer_end - trailer_start,
        parent=parent
    )
    yield t
    for k, v in pairs:
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
        yield from parse_object(v, matcher=matcher, parent=value_match, pdf_header_offset=pdf_header_offset)


def xref_row_span(row: tuple[object, object, object]) -> tuple[int, int] | None:
    """Measures the bytes that one cross-reference row occupies in the file.

    Args:
        row: An object ID, position, and generation number triple from `PDFXRef.offsets`.

    Returns:
        The row's start and end offsets, or None when any of its cells has no byte provenance.
    """
    _, pos, gen_no = row
    if not has_provenance(pos) or not has_provenance(gen_no):
        return None
    cells: list[Provenance] = []
    for cell in row:
        if cell is None:
            continue
        if not has_provenance(cell):
            return None
        cells.append(cell)
    return min(c.pdf_offset for c in cells), max(c.pdf_offset + c.pdf_bytes for c in cells)


def parse_xref(
    xref: PDFXRef, matcher: Matcher, parent: Match, pdf_header_offset: int,
) -> Iterator[Match]:
    """Yields the submatches that map a cross-reference table and each of its rows.

    `PDFXRefFallback` subclasses `PDFXRef` but reconstructs the table with its own `load`, which
    stores plain integer positions instead of the instrumented tokens that this module's
    `load_xref` produces. Its rows therefore map to nothing and are logged and skipped.

    Args:
        xref: The cross-reference table to map.
        matcher: The matcher to use when recursing into cells.
        parent: The match that the table is nested in.
        pdf_header_offset: The offset of `%PDF` within the file being parsed.
    """
    rows = [(row, span) for row in xref.offsets.values() if (span := xref_row_span(row)) is not None]
    if len(rows) < len(xref.offsets):
        log.warning(f"Skipping {len(xref.offsets) - len(rows)} rows of a {xref.__class__.__name__} "
                    "cross-reference table that have no byte provenance")
    if not rows:
        log.debug("Skipping a PDF cross-reference table that maps to no bytes in the file")
        return
    xref_start = min(start for _, (start, _) in rows)
    xref_end = max(end for _, (_, end) in rows)
    x = Submatch(
        "XRefTable",
        b"",
        relative_offset=xref_start,
        length=xref_end - xref_start,
        parent=parent
    )
    yield x
    for row, (row_start, row_end) in rows:
        row_match = Submatch(
            "XRefRow",
            b"",
            relative_offset=row_start - xref_start,
            length=row_end - row_start,
            parent=x
        )
        yield row_match
        yield from parse_xref_row(row, row_start, matcher=matcher, parent=row_match,
                                  pdf_header_offset=pdf_header_offset)


def parse_xref_row(
    row, row_start: int, matcher: Matcher, parent: Match, pdf_header_offset: int,
) -> Iterator[Match]:
    """Yields the submatches that map the cells of one cross-reference row.

    Args:
        row: An object ID, position, and generation number triple from `PDFXRef.offsets`.
        row_start: The offset of the row within the file.
        matcher: The matcher to use when recursing into cells.
        parent: The match that the row is nested in.
        pdf_header_offset: The offset of `%PDF` within the file being parsed.
    """
    obj_id, pos, gen_no = row
    if obj_id is not None:
        ret = Submatch(
            "ObjectID",
            b"",
            relative_offset=obj_id.pdf_offset - row_start,
            length=obj_id.pdf_bytes,
            parent=parent
        )
        yield ret
        yield from parse_object(obj_id, matcher=matcher, parent=ret, pdf_header_offset=pdf_header_offset)
    ret = Submatch(
        "Position",
        b"",
        relative_offset=pos.pdf_offset - row_start,
        length=pos.pdf_bytes,
        parent=parent
    )
    yield ret
    yield from parse_object(pos, matcher=matcher, parent=ret, pdf_header_offset=pdf_header_offset)
    ret = Submatch(
        "Generation",
        b"",
        relative_offset=gen_no.pdf_offset - row_start,
        length=gen_no.pdf_bytes,
        parent=parent
    )
    yield ret
    yield from parse_object(gen_no, matcher=matcher, parent=ret,
                            pdf_header_offset=pdf_header_offset)


def _document_objects(document: InstrumentedPDFDocument, parent: Match) -> dict[int, object]:
    objects: dict[int, object] = {}
    for xref in document.xrefs:
        for number in xref.get_objids():
            if number in objects:
                continue
            try:
                obj = document.getobj(number)
            except PDFObjectNotFound:
                continue
            except PDFNotImplementedError as error:
                parent.analysis_status = "unsupported"
                parent.analysis_message = f"PDF object {number}: {error}"
                continue
            if has_provenance(obj):
                objects[number] = obj
    return objects


def _map_decoded_objects(
    objects: dict[int, object], sources: _PDFSources, parent: Match,
) -> Iterator[Match]:
    by_source = {record.source: record for record in sources.values()}
    assert parent.matcher is not None
    for number, obj in objects.items():
        source = getattr(obj, "pdf_source", parent.source)
        if source == parent.source:
            continue
        record = by_source.get(source)
        if record is None or record.match is None:
            parent.analysis_status = "unsupported"
            parent.analysis_message = f"PDF object {number} has no emitted decoded source {source}"
            continue
        if record.match.analysis_status == "limited":
            continue
        assert has_provenance(obj)
        node = Submatch(
            "PDFObject", number, display_name=f"PDFObject{number}",
            relative_offset=obj.pdf_offset, length=obj.pdf_bytes, parent=record.match,
        )
        yield node
        yield from parse_object(obj, parent.matcher, node, sources=sources)


def _map_pdf_document(
    stream: FileStream, document: InstrumentedPDFDocument, parent: Match,
) -> Iterator[Match]:
    objects = _document_objects(document, parent)
    sources = document._decoded_sources
    assert parent.matcher is not None
    for number, obj in objects.items():
        if getattr(obj, "pdf_source", parent.source) == parent.source:
            if isinstance(obj, PDFObjectStream):
                document._bind_object_stream(obj)
            yield from pdf_obj_parser(stream, obj, number, parent, parent.offset, sources=sources)
    yield from _map_decoded_objects(objects, sources, parent)
    for xref in document.xrefs:
        trailer = xref.get_trailer()
        if trailer is not None:
            yield from parse_trailer(trailer, parent.matcher, parent, parent.offset)
        if isinstance(xref, PDFXRef):
            yield from parse_xref(xref, parent.matcher, parent, parent.offset)


# Note: PDF parser is registered lazily in __init__.py to defer pdfminer import
def pdf_parser(file_stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map a PDF view into its parent's physical or decoded analysis source.

    Args:
        file_stream: A stream view containing the PDF and any leading preamble. Stream
            positions and token provenance are relative to this view.
        parent: The match whose source position identifies byte zero of the view. Its
            source coordinates can differ from the stream's backing-file coordinates.

    Yields:
        The PDF's structure positioned within the parser parent's analysis source.
    """
    source_base = parent.offset
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
    pdf_header_offset = source_base
    assert parent.matcher is not None
    parser = PDFParser(cast(BinaryIO, RawPDFStream(file_stream)))
    doc = InstrumentedPDFDocument(parser, analysis_context=parent.analysis_context)
    yield from _map_pdf_document(file_stream, doc, parent)
