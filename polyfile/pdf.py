import codecs
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
)

from polyfile.compression import match_decoded

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
    def __init__(self, name: PSLiteral.NameType, pdf_offset: int, pdf_bytes: int):
        if isinstance(name, str) and not isinstance(name, PSStr):
            super().__init__(PSStr(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes))
        elif isinstance(name, bytes) and not isinstance(name, PSBytes):
            super().__init__(PSBytes(name, pdf_offset=pdf_offset + 1, pdf_bytes=pdf_bytes))
        else:
            super().__init__(name)

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
        return PDFLiteral(value.name, pdf_offset=pdf_offset, pdf_bytes=pdf_bytes)
    # Unfortunately, we can't convert PSKeywords to PDFKeywords here because pdfminer requires them to be singletons
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
                if not isinstance(values[index], PSLiteral):
                    values[index] = str.__str__(str(values[index]))
        return pos, values

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
                length = self._curtokenpos + 1 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFDict(obj[1], pdf_offset=obj[0], pdf_bytes=length + 2)))
            elif len(obj) == 2 and isinstance(obj[1], list):
                length = self._curtokenpos + 1 - obj[0]
                assert length > 0
                transformed.append((obj[0], PDFList(obj[1], pdf_offset=obj[0], pdf_bytes=length)))
            elif len(obj) == 2 and isinstance(obj[1], PDFStream):
                stream: PDFStream = obj[1]
                assert stream.rawdata is not None
                pos = obj[0]
                transformed.append((pos, PDFObjectStream(stream, pdf_offset=pos, pdf_bytes=len(stream.rawdata))))
            elif len(obj) == 2 and isinstance(obj[1], PSObject) and not isinstance(obj[1], PDFLiteral):
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

    def _add_token(self, obj: PSBaseParserToken):
        if has_provenance(obj):
            pos = obj.pdf_offset
        else:
            pos = self._curtokenpos
        if has_provenance(obj):
            length = obj.pdf_bytes
        elif isinstance(obj, PSLiteral):
            length = len(self._curtoken)
        else:
            length = len(self._curtoken)
        token = make_ps_object(obj, pdf_offset=pos, pdf_bytes=length)
        return super()._add_token(cast(PSBaseParserToken, token))

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
        length=obj.pdf_bytes - 1,
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


def parse_object(
    obj: object, matcher: Matcher, parent: Match | None = None, pdf_header_offset: int = 0,
) -> Iterator[Match]:
    if parent is None:
        if isinstance(obj, (PDFStreamFilter, PDFList, PDFDict, PDFDeciphered, PSBytes)) \
                or has_provenance(obj):
            raise ValueError("Mapping an instrumented PDF value requires a parent match")
        return
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
            yield from match_decoded(filter_obj, bytes(obj))
        else:
            stream = Submatch(
                "DecodingError",
                obj.error.message,
                relative_offset=0,
                length=obj.pdf_bytes,
                parent=filter_obj
            )
            yield stream
        yield from parse_object(obj.original_bytes, matcher=matcher, parent=filter_obj,
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
        yield from parse_dict(obj, matcher=matcher, parent=parent, pdf_header_offset=pdf_header_offset)
    elif isinstance(obj, PDFDeciphered):
        deciphered = Submatch(
            "PDFDeciphered",
            obj.original_bytes,
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )
        yield deciphered
        yield from match_decoded(deciphered, bytes(obj))
    elif isinstance(obj, PSBytes):
        if isinstance(obj, PNGPredictor):
            match = Submatch(
                "PNGPredictor",
                bytes(obj.original_bytes),
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
        if hasattr(obj, "original_bytes"):
            yield from match_decoded(match, bytes(obj))
        else:
            with Tempfile(obj) as f:
                yield from matcher.match(f, parent=match)
    elif has_provenance(obj):
        yield Submatch(
            obj.__class__.__name__,
            obj,
            relative_offset=obj.pdf_offset - (parent.offset - pdf_header_offset),
            length=obj.pdf_bytes,
            parent=parent
        )


class InstrumentedPDFDocument(AdapterPDFDocument):
    xref_class = InstrumentedPDFXRef
    fallback_xref_class = InstrumentedPDFXRefFallback

    def __init__(self, *args, **kwargs):
        self._decipher: DecipherCallable | None = None
        try:
            super().__init__(*args, **kwargs)
        except PDFSyntaxError as error:
            if "No /Root object" not in str(error):
                raise
            log.debug("Mapping a malformed PDF without a /Root object")

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


def pdf_obj_parser(
    file_stream: FileStream, obj, objid: int, parent: Match, pdf_header_offset: int = 0,
) -> Iterator[Match]:
    assert parent.matcher is not None
    data: bytes | None = None
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
        file_stream.seek(relative_offset)
        reverse_skip_whitespace(file_stream)
        if reverse_expect(file_stream, b"obj") and reverse_skip_whitespace(file_stream):
            version = reverse_expect(file_stream, lambda _, b: ord('0') <= b[0] <= ord('9'))
            if version and reverse_skip_whitespace(file_stream):
                obj_id = reverse_expect(file_stream, lambda _, b: ord('0') <= b[0] <= ord('9'))
                if obj_id:
                    obj_offset = relative_offset - file_stream.tell()
                    relative_offset -= obj_offset
                    obj_length += obj_offset
        file_stream.seek(relative_offset + obj_length)
        skip_whitespace(file_stream)
        if file_stream.read(6) == b"endobj":
            skip_whitespace(file_stream)
            obj_length = file_stream.tell() - relative_offset
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


def parse_trailer(
    trailer, matcher: Matcher, parent: Match, pdf_header_offset: int,
) -> Iterator[Match]:
    """Yields the submatches that map a cross-reference section's trailer dictionary.

    `InstrumentedPDFDocument` recovers from a missing `/Root` by patching `PDFXRef.get_trailer`,
    and a PDF damaged enough to need that recovery usually reaches here with a trailer that is
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
                if objid in yielded or not has_provenance(obj):
                    continue
                yielded.add(objid)
            yield from pdf_obj_parser(file_stream, obj, objid, parent, pdf_header_offset=pdf_header_offset)

        trailer = xref.get_trailer()
        if trailer is not None:
            yield from parse_trailer(trailer, matcher=parent.matcher, parent=parent,
                                     pdf_header_offset=pdf_header_offset)

        if isinstance(xref, PDFXRef):
            yield from parse_xref(xref, matcher=parent.matcher, parent=parent,
                                  pdf_header_offset=pdf_header_offset)
