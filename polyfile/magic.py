"""
A pure Python implementation of libmagic.

This is to avoid having libmagic be a dependency, as well as to add the ability for searching for matches at arbitrary
byte offsets.

This implementation is also optimized to only test for the file's MIME types; it skips all of the tests for printing
details about the file.

"""
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import re
import struct
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union
from uuid import UUID, uuid4

DEFS_DIR: Path = Path(__file__).absolute().parent / "magic_defs"

MAGIC_DEFS: List[Path] = [
    path
    for path in DEFS_DIR.glob("*")
    if path.name not in ("COPYING", "magic.mgc") and not path.name.startswith(".")
]


def unescape(to_unescape: str) -> str:
    """Processes unicode escape sequences. Also handles libmagic's support for single digit `\\x#` hex escapes."""
    # first, process single digit hex escapes:
    b = bytearray()
    escaped = False
    byte_escape: Optional[str] = None
    for c in to_unescape:
        if escaped:
            if c == "x":
                byte_escape = ""
            escaped = False
        else:
            if byte_escape is not None:
                if not byte_escape:
                    byte_escape = c
                elif not c.isnumeric() and not ord("a") <= ord(c.lower()) <= ord("f"):
                    # the last three bytes were a single byte hex escape, like "\xD" or "\x5"
                    assert len(b) >= 3
                    b = b[:-3]
                    b.append(int(byte_escape, 16))
                    byte_escape = None
                else:
                    byte_escape = None
            if c == "\\":
                escaped = True
        b.append(ord(c))
    if byte_escape:
        # the string ended with a single byte hex escape
        assert len(b) >= 3
        b = b[:-3]
        b.append(int(byte_escape, 16))
    return b.decode("unicode_escape")


class Match:
    def __init__(self, test: "MagicTest", value: Any, offset: int, length: int, parent: Optional["Match"] = None):
        self.test: MagicTest = test
        self.value: Any = value
        self.offset: int = offset
        self.length: int = length
        self.parent: Optional[Match] = parent

    def __hash__(self):
        return hash((self.test, self.offset, self.length))

    def __eq__(self, other):
        return isinstance(other, Match) and other.test == self.test and other.offset == self.offset \
               and other.length == self.length

    def __repr__(self):
        return f"{self.__class__.__name__}(test={self.test!r}, offset={self.offset}, length={self.length}, " \
               f"parent={self.parent!r})"

    def __str__(self):
        if self.test.message is not None:
            # TODO: Fix pasting our value in
            return self.test.message
            #if self.value is not None and "%" in self.test.message:
            #    return self.test.message % (self.value,)
            #else:
            #    return self.test.message
        else:
            return f"Match[{self.offset}:{self.offset + self.length}]"


class Endianness(Enum):
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"
    PDP = "me"


def parse_numeric(text: str) -> int:
    text = text.strip()
    if text.startswith("-"):
        factor = -1
        text = text[1:]
    else:
        factor = 1
    if text.startswith("+"):
        text = text[1:]
    if text.endswith("L"):
        text = text[:-1]
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16) * factor
    elif text.startswith("0") and len(text) > 1:
        return int(text, 8) * factor
    else:
        return int(text) * factor


class Offset(ABC):
    @abstractmethod
    def to_absolute(self, data: bytes, last_match: Optional[Match]) -> int:
        raise NotImplementedError()

    @staticmethod
    def parse(offset: str) -> "Offset":
        if offset.startswith("&"):
            return RelativeOffset(Offset.parse(offset[1:]))
        elif offset.startswith("("):
            return IndirectOffset.parse(offset)
        elif offset.startswith("-"):
            return NegativeOffset(parse_numeric(offset[1:]))
        else:
            return AbsoluteOffset(parse_numeric(offset))


class AbsoluteOffset(Offset):
    def __init__(self, offset: int):
        self.offset: int = offset

    def to_absolute(self, data: bytes, last_match: Optional[Match]) -> int:
        return self.offset

    def __repr__(self):
        return f"{self.__class__.__name__}(offset={self.offset})"

    def __str__(self):
        return str(self.offset)


class NegativeOffset(Offset):
    def __init__(self, magnitude: int):
        self.magnitude: int = magnitude

    def to_absolute(self, data: bytes, last_match: Optional[Match]) -> int:
        return len(data) - self.magnitude

    def __repr__(self):
        return f"{self.__class__.__name__}(magnitude={self.magnitude})"

    def __str__(self):
        return f"{self.magnitude}"


class RelativeOffset(Offset):
    def __init__(self, relative_to: Offset):
        self.relative_to: Offset = relative_to

    def to_absolute(self, data: bytes, last_match: Optional[Match]) -> int:
        return last_match.offset + last_match.length + self.relative_to.to_absolute(data, last_match)

    def __repr__(self):
        return f"{self.__class__.__name__}(relative_to={self.relative_to})"

    def __str__(self):
        return f"&{self.relative_to}"


class IndirectOffset(Offset):
    def __init__(self, offset: Offset, num_bytes: int, endianness: Endianness, signed: bool,
                 post_process: Callable[[int], int] = lambda n: n):
        self.offset: Offset = offset
        self.num_bytes: int = num_bytes
        self.endianness: Endianness = endianness
        self.signed: bool = signed
        self.post_process: Callable[[int], int] = post_process
        if self.endianness != Endianness.LITTLE and self.endianness != endianness.BIG:
            raise ValueError(f"Invalid endianness: {endianness!r}")
        elif num_bytes not in (1, 2, 4, 8):
            raise ValueError(f"Invalid number of bytes: {num_bytes}")

    def to_absolute(self, data: bytes, last_match: Optional[Match]) -> int:
        if self.num_bytes == 1:
            fmt = "B"
        elif self.num_bytes == 2:
            fmt = "H"
        elif self.num_bytes == 8:
            fmt = "Q"
        else:
            fmt = "I"
        if self.signed:
            fmt = fmt.lower()
        if self.endianness == Endianness.LITTLE:
            fmt = f"<{fmt}"
        else:
            fmt = f">{fmt}"
        offset = self.offset.to_absolute(data, last_match)
        return self.post_process(struct.unpack(fmt, data[offset:offset + self.num_bytes])[0])

    NUMBER_PATTERN: str = r"(0[xX][\dA-Fa-f]+|\d+)L?"
    INDIRECT_OFFSET_PATTERN: re.Pattern = re.compile(
        "^\("
        rf"(?P<offset>&?-?{NUMBER_PATTERN})"
        r"((?P<signedness>[.,])(?P<type>[bBcCeEfFgGhHiILlmsSqQ]))?"
        rf"(?P<post_process>[\*&/]?[+-]?({NUMBER_PATTERN}|\(-?{NUMBER_PATTERN}\)))?"
        "\)$"
    )

    @classmethod
    def parse(cls, offset: str) -> "IndirectOffset":
        m = cls.INDIRECT_OFFSET_PATTERN.match(offset)
        if not m:
            raise ValueError(f"Invalid indirect offset: {offset!r}")
        t = m.group("type")
        if t is None:
            t = "I"
        if t == "m":
            raise NotImplementedError("TODO: Add support for middle endianness")
        elif t.islower():
            endianness = Endianness.LITTLE
        else:
            endianness = Endianness.BIG
        t = t.lower()
        if t in ("b", "c"):
            num_bytes = 1
        elif t in ("e", "f", "g", "q"):
            num_bytes = 8
        elif t in ("h", "s"):
            num_bytes = 2
        elif t in ("i", "l"):
            # TODO: Confirm that "l" should really be here
            num_bytes = 4
        else:
            raise ValueError(f"Unsupported indirect specifier type: {m.group('type')!r}")
        pp = m.group("post_process")
        if pp is None:
            post_process = lambda n: n
        else:
            multiply = pp.startswith("*")
            bitwise_and = pp.startswith("&")
            divide = pp.startswith("/")
            if multiply or bitwise_and or divide:
                pp = pp[1:]
            if pp.startswith("+"):
                pp = pp[1:]
            if pp.startswith("(") and pp.endswith(")"):
                # some definition files like `msdos` have indirect offsets of the form: >>>(&0x0f.l+(-4))
                # Handle those nested parenthesis around the `(-4)` here. This is an undocumented part of the DSL,
                # so, TODO: confirm we are handling it properly and it's not something more complex like a nested
                #           indirect offset
                pp = pp[1:-1]
            operand = parse_numeric(pp)
            if multiply:
                post_process = lambda n: n * operand
            elif bitwise_and:
                post_process = lambda n: n & operand
            elif divide:
                post_process = lambda n: n // operand
            else:
                post_process = lambda n: n + operand
        return IndirectOffset(
            offset=Offset.parse(m.group("offset")),
            num_bytes=num_bytes,
            endianness=endianness,
            signed=m.group("signedness") == ",",
            post_process=post_process
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(offset={self.offset!r}, num_bytes={self.num_bytes}, "\
               f"endianness={self.endianness!r}, signed={self.signed}, addend={self.addend})"

    def __str__(self):
        if self.addend == 0:
            addend = ""
        elif self.addend < 0:
            addend = str(self.addend)
        else:
            addend = f"+{self.addend}"
        return f"({self.offset!s}{['.', ','][self.signed]}{self.num_bytes}{self.endianness}{addend})"


class MagicTest(ABC):
    def __init__(
            self,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None
    ):
        self.offset: Offset = offset
        self.mime: Optional[str] = mime
        self.extensions: Set[str] = set(extensions)
        self.message: str = message
        self.parent: Optional[MagicTest] = parent
        self.children: List[MagicTest] = []
        if self.parent is not None:
            self.level: int = self.parent.level + 1
            self.parent.children.append(self)
        else:
            self.level = 0
        if mime is not None:
            self._can_match_mime: Optional[bool] = True
            p = self.parent
            while p is not None and p._can_match_mime is None:
                p._can_match_mime = True
                p = p.parent
        else:
            self._can_match_mime = None

    @property
    def can_match_mime(self) -> bool:
        if self._can_match_mime is None:
            self._can_match_mime = any(child.can_match_mime for child in self.children)
        return self._can_match_mime

    @abstractmethod
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        raise NotImplementedError()

    def _match(
            self,
            data: bytes,
            only_match_mime: bool = False,
            parent_match: Optional[Match] = None
    ) -> Iterator[Match]:
        if only_match_mime and not self.can_match_mime:
            return
        m = self.test(data, self.offset.to_absolute(data, parent_match), parent_match)
        if m is not None:
            if not only_match_mime or self.mime is not None:
                yield m
            for child in self.children:
                if not only_match_mime or child.can_match_mime:
                    yield from child._match(data=data, only_match_mime=only_match_mime, parent_match=m)

    def match(self, data: bytes, only_match_mime: bool = False) -> Iterator[Match]:
        """Yields all matches for the given data"""
        return self._match(data, only_match_mime=only_match_mime)

    def __str__(self):
        s = f"{'>' * self.level}{self.offset!s}\t{self.message}"
        if self.mime is not None:
            s = f"{s}\n!:mime\t{self.mime}"
        for e in self.extensions:
            s = f"{s}\n!:ext\t{e}"
        return s


TYPES_BY_NAME: Dict[str, "DataType"] = {}


T = TypeVar("T")


class DataTypeMatch:
    INVALID: "DataTypeMatch"

    def __init__(self, raw_match: Optional[bytes] = None, value: Optional[Any] = None):
        self.raw_match: Optional[bytes] = raw_match
        if value is None and raw_match is not None:
            self.value: Optional[bytes] = raw_match
        else:
            self.value = value

    def __bool__(self):
        return self.raw_match is not None

    def __repr__(self):
        return f"{self.__class__.__name__}(raw_match={self.raw_match!r}, value={self.value!r})"

    def __str__(self):
        if self.value is not None:
            return str(self.value)
        elif self.raw_match is None:
            return "DataTypeNoMatch"
        else:
            return repr(self.raw_match)


DataTypeMatch.INVALID = DataTypeMatch()


class DataType(ABC, Generic[T]):
    def __init__(self, name: str):
        self.name: str = name

    @abstractmethod
    def parse_expected(self, specification: str) -> T:
        raise NotImplementedError()

    @abstractmethod
    def match(self, data: bytes, expected: T) -> DataTypeMatch:
        raise NotImplementedError()

    @staticmethod
    def parse(fmt: str) -> "DataType":
        if fmt in TYPES_BY_NAME:
            return TYPES_BY_NAME[fmt]
        elif fmt.startswith("string") or fmt.startswith("ustring"):
            dt = StringType.parse(fmt)
        elif fmt == "lestring16":
            dt = UTF16Type(endianness=Endianness.LITTLE)
        elif fmt == "bestring16":
            dt = UTF16Type(endianness=Endianness.BIG)
        elif fmt.startswith("pstring"):
            dt = PascalStringType.parse(fmt)
        elif fmt.startswith("search"):
            dt = SearchType.parse(fmt)
        elif fmt.startswith("regex"):
            dt = RegexType.parse(fmt)
        else:
            dt = NumericDataType.parse(fmt)
        if dt.name in TYPES_BY_NAME:
            # Sometimes a data type will change its name based on modifiers.
            # For example, string and pstring will always include their modifiers after their name
            dt = TYPES_BY_NAME[dt.name]
        else:
            TYPES_BY_NAME[dt.name] = dt
        TYPES_BY_NAME[fmt] = dt
        return dt

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class UTF16Type(DataType[bytes]):
    def __init__(self, endianness: Endianness):
        if endianness == Endianness.LITTLE:
            super().__init__("lestring16")
        elif endianness == Endianness.BIG:
            super().__init__("bestring16")
        else:
            raise ValueError(f"UTF16 strings only support big and little endianness, not {endianness!r}")
        self.endianness: Endianness = endianness

    def parse_expected(self, specification: str) -> bytes:
        if self.endianness == Endianness.LITTLE:
            return specification.encode("utf-16-le")
        else:
            return specification.encode("utf-16-be")

    def match(self, data: bytes, expected: bytes) -> DataTypeMatch:
        if data.startswith(expected):
            if self.endianness == Endianness.LITTLE:
                return DataTypeMatch(expected, expected.decode("utf-16-le"))
            else:
                return DataTypeMatch(expected, expected.decode("utf-16-be"))
        else:
            return DataTypeMatch.INVALID


class StringType(DataType[bytes]):
    def __init__(
            self,
            case_insensitive_lower: bool = False,
            case_insensitive_upper: bool = False,
            compact_whitespace: bool = False,
            optional_blanks: bool = False,
            trim: bool = False
    ):
        if not all((case_insensitive_lower, case_insensitive_upper, compact_whitespace, optional_blanks, trim)):
            name = "string"
        else:
            name = f"string/{['', 'W'][compact_whitespace]}{['', 'w'][optional_blanks]}"\
                   f"{['', 'C'][case_insensitive_upper]}{['', 'c'][case_insensitive_lower]}"\
                   f"{['', 'T'][trim]}"
        super().__init__(name)
        self.case_insensitive_lower: bool = case_insensitive_lower
        self.case_insensitive_upper: bool = case_insensitive_upper
        self.compact_whitespace: bool = compact_whitespace
        self.optional_blanks: bool = optional_blanks
        self.trim: bool = trim

    def parse_expected(self, specification: str) -> bytes:
        return specification.encode("utf-8")

    def match(self, data: bytes, expected: bytes) -> DataTypeMatch:
        try:
            expected_str = expected.decode("utf-8")
        except UnicodeDecodeError:
            expected_str = expected
        matched = bytearray()
        had_whitespace = False
        last_char: Optional[int] = None
        for b in data:
            if not expected:
                break
            matched.append(b)
            is_whitespace = bytes([b]) in b" \t\n"
            if self.trim and last_char is None and is_whitespace:
                # skip leading whitespace
                continue
            elif self.compact_whitespace and is_whitespace:
                if last_char is not None and bytes([last_char]) in b" \t\n":  # type: ignore
                    # compact consecutive whitespace
                    continue
                else:
                    had_whitespace = True
            if not (
                    b == expected[0] or
                    (self.case_insensitive_lower and b == expected[0:1].lower()[0]) or
                    (self.case_insensitive_upper and b == expected[0:1].upper()[0])
            ):
                if not (self.optional_blanks and expected[0:1] in b" \t\n"):
                    return DataTypeMatch.INVALID
            expected = expected[1:]
        if self.compact_whitespace and not had_whitespace:
            return DataTypeMatch.INVALID
        return DataTypeMatch(bytes(matched), expected_str)

    STRING_TYPE_FORMAT: re.Pattern = re.compile(r"^u?string(/[BbCctTWw]*)?$")

    @classmethod
    def parse(cls, format_str: str) -> "StringType":
        m = cls.STRING_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid string type declaration: {format_str!r}")
        if m.group(1) is None:
            options: Iterable[str] = ()
        else:
            options = m.group(1)
        return StringType(
            case_insensitive_lower="c" in options,
            case_insensitive_upper="C" in options,
            compact_whitespace="B" in options or "W" in options,
            optional_blanks="b" in options or "w" in options,
            trim="T" in options
        )


class SearchType(StringType):
    def __init__(
            self,
            repetitions: Optional[int] = None,
            case_insensitive_lower: bool = False,
            case_insensitive_upper: bool = False,
            compact_whitespace: bool = False,
            optional_blanks: bool = False,
            match_to_start: bool = False,
            trim: bool = False
    ):
        if repetitions is not None and repetitions <= 0:
            raise ValueError("repetitions must be either None or a positive integer")
        super().__init__(
            case_insensitive_lower=case_insensitive_lower,
            case_insensitive_upper=case_insensitive_upper,
            compact_whitespace=compact_whitespace,
            optional_blanks=optional_blanks,
            trim=trim
        )
        self.repetitions: Optional[int] = repetitions
        if repetitions is None:
            rep_str = ""
        else:
            rep_str = f"/{repetitions}"
        assert self.name.startswith("string")
        self.name = f"search{rep_str}{self.name[6:]}"
        self.match_to_start: bool = match_to_start
        if match_to_start:
            if self.name == f"search{rep_str}":
                self.name = f"search{rep_str}/s"
            else:
                self.name = f"{self.name}s"

    def match(self, data: bytes, expected: bytes) -> DataTypeMatch:
        if self.repetitions is None:
            rep = len(data)
        else:
            rep = self.repetitions
        for i in range(rep):
            match = super().match(data[i:], expected)
            if match:
                return match
        return DataTypeMatch.INVALID

    SEARCH_TYPE_FORMAT: re.Pattern = re.compile(
        r"^search"
        r"((/(?P<repetitions1>(0[xX][\dA-Fa-f]+|\d+)))(/(?P<flags1>[BbCctTWws]*)?)?|"
        r"/((?P<flags2>[BbCctTWws]*)/?)?(?P<repetitions2>(0[xX][\dA-Fa-f]+|\d+)))$"
    )
    # NOTE: some specification files like `ber` use `search/b64`, which is undocumented. We treat that equivalent to
    #       the compliant `search/b/64`.
    # TODO: Figure out if this is correct.

    @classmethod
    def parse(cls, format_str: str) -> "SearchType":
        if format_str == "search":
            # it's undocumented, but you can apparently use the search test without an explicit repetition number
            return SearchType()
        m = cls.SEARCH_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid search type declaration: {format_str!r}")
        if m.group("repetitions1") is not None:
            repetitions = parse_numeric(m.group("repetitions1"))
            flags = m.group("flags1")
        elif m.group("repetitions2") is not None:
            repetitions = parse_numeric(m.group("repetitions2"))
            flags = m.group("flags2")
        else:
            raise ValueError(f"Invalid search type declaration: {format_str!r}")
        if flags is None:
            options: Iterable[str] = ()
        else:
            options = flags
        return SearchType(
            repetitions=repetitions,
            case_insensitive_lower="c" in options,
            case_insensitive_upper="C" in options,
            compact_whitespace="B" in options or "W" in options,
            optional_blanks="b" in options or "w" in options,
            trim="T" in options,
            match_to_start="s" in options
        )


class PascalStringType(DataType[bytes]):
    def __init__(
            self,
            byte_length: int = 1,
            endianness: Endianness = Endianness.BIG,
            count_includes_length: bool = False
    ):
        if endianness != Endianness.BIG and endianness != Endianness.LITTLE:
            raise ValueError("Endianness must be either BIG or LITTLE")
        elif byte_length == 1:
            modifier = "B"
        elif byte_length == 2:
            if endianness == Endianness.BIG:
                modifier = "H"
            else:
                modifier = "h"
        elif byte_length == 4:
            if endianness == Endianness.BIG:
                modifier = "L"
            else:
                modifier = "l"
        else:
            raise ValueError("byte_length must be either 1, 2, or 4")
        if count_includes_length:
            modifier = f"{modifier}J"
        super().__init__(f"pstring/{modifier}")
        self.byte_length: int = byte_length
        self.endianness: Endianness = endianness
        self.count_includes_length: int = count_includes_length

    def parse_expected(self, specification: str) -> bytes:
        return specification.encode("utf-8")

    def match(self, data: bytes, expected: bytes) -> DataTypeMatch:
        if len(data) < self.byte_length:
            return DataTypeMatch.INVALID
        elif self.byte_length == 1:
            length = data[0]
        elif self.byte_length == 2:
            if self.endianness == Endianness.BIG:
                length = struct.unpack(">H", data[:2])[0]
            else:
                length = struct.unpack("<H", data[:2])[0]
        elif self.endianness == Endianness.BIG:
            length = struct.unpack(">I", data[:4])[0]
        else:
            length = struct.unpack("<I", data[:4])[0]
        if self.count_includes_length:
            length -= self.byte_length
        if len(data) < self.byte_length + length:
            return DataTypeMatch.INVALID
        elif len(expected) != length:
            return DataTypeMatch.INVALID
        if data[self.byte_length:self.byte_length + length] == expected:
            try:
                return DataTypeMatch(expected, expected.decode("utf-8"))
            except UnicodeDecodeError:
                return DataTypeMatch(expected)
        else:
            return DataTypeMatch.INVALID

    PSTRING_TYPE_FORMAT: re.Pattern = re.compile(r"^pstring(/J?[BHhLl]?J?)?$")

    @classmethod
    def parse(cls, format_str: str) -> "PascalStringType":
        m = cls.PSTRING_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid pstring type declaration: {format_str!r}")
        if m.group(1) is None:
            options: Iterable[str] = ()
        else:
            options = m.group(1)
        if "H" in options:
            byte_length = 2
            endianness = Endianness.BIG
        elif "h" in options:
            byte_length = 2
            endianness = Endianness.LITTLE
        elif "L" in options:
            byte_length = 4
            endianness = Endianness.BIG
        elif "l" in options:
            byte_length = 4
            endianness = Endianness.LITTLE
        else:
            byte_length = 1
            endianness = Endianness.BIG
        return PascalStringType(
            byte_length=byte_length,
            endianness=endianness,
            count_includes_length="J" in options
        )


def posix_to_python_re(match: str) -> str:
    for match_from, replace_with in (
            ("upper", "A-Z"),
            ("lower", "a-z"),
            ("alpha", "A-Za-z"),
            ("digit", "0-9"),
            ("xdigit", "0-9A-Fa-f"),
            ("alnum", "A-Za-z0-9"),
            ("punct", ",./<>?`;':\"\\[\\]{}\|~!@#$%\\^&*()_+-="),
            ("blank", " \t"),
            ("space", " \t\n\r\f\v"),
            ("word", "\\w")
    ):
        match = match.replace(f"[:{match_from}:]", f"{replace_with}")
    return match


class RegexType(DataType[re.Pattern]):
    def __init__(
            self,
            length: Optional[int] = None,
            case_insensitive: bool = False,
            match_to_start: bool = False,
            limit_lines: bool = False,
            trim: bool = False
    ):
        if length is None:
            if limit_lines:
                length = 8 * 1024 // 80  # libmagic assumes 80 bytes per line
            else:
                length = 8 * 1024  # libmagic limits to 8KiB by default
        self.limit_lines: bool = limit_lines
        self.length: int = length
        self.case_insensitive: bool = case_insensitive
        self.match_to_start: bool = match_to_start
        self.trim: bool = trim
        super().__init__(f"regex/{self.length}{['', 'c'][case_insensitive]}{['', 's'][match_to_start]}"
                         f"{['', 'l'][self.limit_lines]}{['', 'T'][self.trim]}")

    def parse_expected(self, specification: str) -> re.Pattern:
        # regexes need to have escapes processed again:
        unescaped_spec = unescape(specification)
        # handle POSIX-style character classes:
        unescaped_spec = posix_to_python_re(unescaped_spec).encode("utf-8")
        try:
            if self.case_insensitive:
                return re.compile(unescaped_spec, re.IGNORECASE)
            else:
                return re.compile(unescaped_spec)
        except re.error as e:
            raise ValueError(str(e))

    def match(self, data: bytes, expected: re.Pattern) -> DataTypeMatch:
        if self.limit_lines:
            limit = self.length
            offset = 0
            byte_limit = 80 * self.length  # libmagic uses an implicit byte limit assuming 80 characters per line
            while limit > 0:
                limit -= 1
                line_offset = data.find(b"\n", offset, byte_limit)
                if line_offset < 0:
                    return DataTypeMatch.INVALID
                line = data[offset:line_offset]
                m = expected.search(line)
                if m:
                    match = data[:offset + m.end()]
                    try:
                        value = match.encode("utf-8")
                    except UnicodeDecodeError:
                        value = match
                    if self.trim:
                        value = value.strip()
                    return DataTypeMatch(match, value)
                offset = line_offset + 1
        else:
            m = expected.search(data[:self.length])
            if m:
                match = data[:m.end()]
                try:
                    value = match.encode("utf-8")
                except UnicodeDecodeError:
                    value = match
                if self.trim:
                    value = value.strip()
                return DataTypeMatch(match, value)
            else:
                return DataTypeMatch.INVALID

    REGEX_TYPE_FORMAT: re.Pattern = re.compile(r"^regex(/(?P<length>\d+)?(?P<flags>[cslT]*)(b\d*)?)?$")
    # NOTE: some specification files like `cad` use `regex/b`, which is undocumented, and it's unclear from the libmagic
    #       source code whether it is simply ignored or if it has a purpuse. We ignore it here.

    @classmethod
    def parse(cls, format_str: str) -> "RegexType":
        m = cls.REGEX_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid regex type declaration: {format_str!r}")
        if m.group("flags") is None:
            options: Iterable[str] = ()
        else:
            options = m.group("flags")
        if m.group("length") is None:
            length: Optional[int] = None
        else:
            length = int(m.group("length"))
        return RegexType(
            length=length,
            case_insensitive="c" in options,
            match_to_start="s" in options,
            limit_lines="l" in options,
            trim="T" in options
        )


BASE_NUMERIC_TYPES_BY_NAME: Dict[str, "BaseNumericDataType"] = {}


class BaseNumericDataType(Enum):
    BYTE = ("byte", "b", 1)
    SHORT = ("short", "h", 2)
    LONG = ("long", "l", 4)
    QUAD = ("quad", "q", 8)
    FLOAT = ("float", "f", 4)
    DOUBLE = ("double", "d", 8)
    DATE = ("date", "L", 4)
    QDATE = ("qdate", "Q", 8)
    LDATE = ("ldate", "L", 4)
    QLDATE = ("qldate", "Q", 8)
    QWDATE = ("qwdate", "Q", 8)

    def __init__(self, name: str, struct_fmt: str, num_bytes: int, post_process: Callable[[int], int] = lambda n: n):
        self.struct_fmt: str = struct_fmt
        self.num_bytes: int = num_bytes
        self.post_process: Callable[[int], int] = post_process
        BASE_NUMERIC_TYPES_BY_NAME[name] = self


NUMERIC_OPERATORS_BY_SYMBOL: Dict[str, "NumericOperator"] = {}


class NumericOperator(Enum):
    EQUALS = ("=", lambda a, b: a == b)
    LESS_THAN = ("<", lambda a, b: a < b)
    GREATER_THAN = (">", lambda a, b: a > b)
    BITWISE_AND = ("&", lambda a, b: a & b)
    BITWISE_XOR = ("^", lambda a, b: a ^ b)
    NOT = ("!", lambda a, b: not (a == b))

    def __init__(self, symbol: str, test: Union[Callable[[int, int], bool], Callable[[float, float], bool]]):
        self.symbol: str = symbol
        self.test: Union[Callable[[int, int], bool], Callable[[float, float], bool]] = test
        NUMERIC_OPERATORS_BY_SYMBOL[symbol] = self

    @staticmethod
    def get(symbol: str) -> "NumericOperator":
        return NUMERIC_OPERATORS_BY_SYMBOL[symbol]


class NumericValue(Generic[T]):
    def __init__(self, value: T, operator: NumericOperator = NumericOperator.EQUALS):
        self.value: T = value
        self.operator: NumericOperator = operator

    def test(self, to_match: T) -> bool:
        return self.operator.test(self.value, to_match)

    @staticmethod
    def parse(value: str, num_bytes: int) -> "NumericValue":
        value = value.strip()
        try:
            return IntegerValue.parse(value, num_bytes)
        except ValueError:
            pass
        try:
            return FloatValue.parse(value, num_bytes)
        except ValueError:
            pass
        raise ValueError(f"Could not parse numeric type {value!r}")


class NumericWildcard(NumericValue):
    def __init__(self):
        super().__init__(None)

    def test(self, to_match) -> bool:
        return True


class IntegerValue(NumericValue[int]):
    @staticmethod
    def parse(value: str, num_bytes: int) -> "IntegerValue":
        try:
            operator = NumericOperator.get(value[0])
            value = value[1:]
        except KeyError:
            operator = NumericOperator.EQUALS
        if value[0] == "~":
            int_value = parse_numeric(value[1:])
            int_value = (1 << (num_bytes * 8)) - 1 - int_value
        else:
            int_value = parse_numeric(value)
        return IntegerValue(value=int_value, operator=operator)


class FloatValue(NumericValue[float]):
    @staticmethod
    def parse(value: str, num_bytes: int) -> "FloatValue":
        try:
            operator = NumericOperator.get(value[0])
            value = value[1:]
        except KeyError:
            operator = NumericOperator.EQUALS
        if operator in (NumericOperator.BITWISE_AND, NumericOperator.BITWISE_XOR):
            raise ValueError(f"A floating point value cannot have the {operator.symbol} operator")
        return FloatValue(value=float(value), operator=operator)


class NumericDataType(DataType[NumericValue]):
    def __init__(
            self,
            name: str,
            base_type: BaseNumericDataType,
            unsigned: bool = False,
            endianness: Endianness = Endianness.NATIVE,
            preprocess: Callable[[int], int] = lambda x: x
    ):
        super().__init__(name)
        self.base_type: BaseNumericDataType = base_type
        self.unsigned: bool = unsigned
        self.endianness: Endianness = endianness
        self.preprocess: Callable[[int], int] = preprocess
        if self.endianness == Endianness.PDP and self.base_type.num_bytes != 4:
            raise ValueError(f"PDP endianness can only be used with four byte base types, not {self.base_type}")

    def parse_expected(self, specification: str) -> NumericValue:
        if specification == "x":
            return NumericWildcard()
        else:
            return NumericValue.parse(specification, self.base_type.num_bytes)

    def match(self, data: bytes, expected: NumericValue) -> DataTypeMatch:
        if len(data) < self.base_type.num_bytes:
            return DataTypeMatch.INVALID
        elif self.endianness == Endianness.PDP:
            assert self.base_type.num_bytes == 4
            if self.unsigned:
                value = (struct.unpack("<H", data[:2]) << 16)[0] | struct.unpack("<H", data[2:4])[0]
            else:
                be_data = bytes([data[1], data[0], data[3], data[2]])
                value = struct.unpack(">i", be_data)[0]
        else:
            if self.unsigned and self.base_type not in (BaseNumericDataType.DOUBLE, BaseNumericDataType.FLOAT):
                struct_fmt = self.base_type.struct_fmt.upper()
            else:
                struct_fmt = self.base_type.struct_fmt
            struct_fmt = f"{self.endianness.value}{struct_fmt}"
            try:
                value = struct.unpack(struct_fmt, data[:self.base_type.num_bytes])[0]
            except struct.error:
                return DataTypeMatch.INVALID
        value = self.preprocess(value)
        if expected.test(value):
            return DataTypeMatch(data[:self.base_type.num_bytes], value)
        else:
            return DataTypeMatch.INVALID

    @staticmethod
    def parse(fmt: str) -> "NumericDataType":
        name = fmt
        if fmt.startswith("u"):
            fmt = fmt[1:]
            if fmt.startswith("double") or fmt.startswith("float"):
                raise ValueError(f"{name[1:]} cannot be unsigned")
            unsigned = True
        else:
            unsigned = False
        if fmt.startswith("le"):
            endianness = Endianness.LITTLE
            fmt = fmt[2:]
        elif fmt.startswith("be"):
            endianness = Endianness.BIG
            fmt = fmt[2:]
        elif fmt.startswith("me"):
            endianness = Endianness.PDP
            fmt = fmt[2:]
        else:
            endianness = Endianness.NATIVE
        for symbol, operator in (
                ("&", lambda a, b: a & b),
                ("%", lambda a, b: a % b),
                ("+", lambda a, b: a + b),
                ("-", lambda a, b: a - b),
                ("^", lambda a, b: a ^ b),
                ("/", lambda a, b: [a // b, a / b][isinstance(a, float)]),
                ("*", lambda a, b: a * b),
                ("|", lambda a, b: a | b)
        ):
            pos = fmt.find(symbol)
            if pos > 0:
                operand = parse_numeric(fmt[pos+1:])
                preprocess = lambda n: operator(n, operand)
                fmt = fmt[:pos]
                break
        else:
            preprocess = lambda n: n
        if fmt not in BASE_NUMERIC_TYPES_BY_NAME:
            raise ValueError(f"Invalid numeric data type: {name!r}")
        return NumericDataType(
            name=name,
            base_type=BASE_NUMERIC_TYPES_BY_NAME[fmt],
            unsigned=unsigned,
            endianness=endianness,
            preprocess=preprocess
        )


class ConstantMatchTest(MagicTest, Generic[T]):
    def __init__(
            self,
            offset: Offset,
            data_type: DataType[T],
            constant: T,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.data_type: DataType[T] = data_type
        self.constant: T = constant

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        match = self.data_type.match(data[absolute_offset:], self.constant)
        if match:
            return Match(self, offset=absolute_offset, length=len(match.raw_match), value=match.value,
                         parent=parent_match)
        else:
            return None


class OffsetMatchTest(MagicTest):
    def __init__(
            self,
            offset: Offset,
            value: IntegerValue,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.value: IntegerValue = value

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        if self.value.test(absolute_offset):
            return Match(self, offset=0, length=absolute_offset, value=absolute_offset, parent=parent_match)
        else:
            return None


class IndirectTest(MagicTest):
    def __init__(
            self,
            matcher: "MagicMatcher",
            offset: Offset,
            relative: bool = False,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional[MagicTest] = None
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.matcher: MagicMatcher = matcher
        self.relative: bool = relative

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        if self.relative:
            if parent_match is None:
                return None
            absolute_offset += parent_match.offset
        for match in self.matcher.match(data[absolute_offset:]):
            match.offset += absolute_offset
            yield match


class GUIDTest(MagicTest):
    def __init__(
            self,
            offset: Offset,
            uuid: Optional[UUID] = None,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional[MagicTest] = None
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        if uuid is None:
            self.uuid: UUID = uuid4()
        else:
            self.uuid = uiid

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        return Match(self, str(self.uuid), absolute_offset, 0, parent=parent_match)


class NamedTest(MagicTest):
    def __init__(
            self,
            name: str,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = ""
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=None)
        self.name: str = name

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        if parent_match is not None:
            return Match(self, offset=parent_match.offset + parent_match.length, length=0, value=self.name,
                         parent=parent_match)
        else:
            raise ValueError("A named test must always be called from a `use` test.")

    def __str__(self):
        return self.name


class UseTest(MagicTest):
    def __init__(
            self,
            named_test: NamedTest,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None,
            flip_endianness: bool = False
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.named_test: NamedTest = named_test
        self.flip_endianness: bool = flip_endianness

    def _match(
            self,
            data: bytes,
            only_match_mime: bool = False,
            parent_match: Optional[Match] = None
    ) -> Iterator[Match]:
        if self.flip_endianness:
            raise NotImplementedError("TODO: Add support for use tests with flipped endianness")
        yield from self.named_test._match(data, only_match_mime, parent_match)
        if only_match_mime and not self.can_match_mime:
            return
        m = self.test(data, self.offset.to_absolute(parent_match), parent_match)
        if m is not None:
            if not only_match_mime or self.mime is not None:
                yield m
            for child in self.children:
                if not only_match_mime or child.can_match_mime:
                    yield from child._match(data=data, only_match_mime=only_match_mime, parent_match=m)

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        raise NotImplementedError("This function should never be called")


class DefaultTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        if parent_match is None or getattr(parent_match, "_cleared", False):
            return Match(self, offset=absolute_offset, length=0, value=True)
        else:
            return None


class ClearTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        if parent_match is None:
            return Match(self, offset=absolute_offset, length=0, value=None)
        else:
            setattr(parent_match, "_cleared", True)
            return Match(self, offset=absolute_offset, length=0, parent=parent_match, value=None)


class DERTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[Match]) -> Optional[Match]:
        raise NotImplementedError(
            "TODO: Implement support for the DER test (e.g., using the Kaitai asn1_der.py parser)"
        )


TEST_PATTERN: re.Pattern = re.compile(
    r"^(?P<level>[>]*)(?P<offset>[^\s!][^\s]*)\s+(?P<data_type>[^\s]+)\s+(?P<remainder>.+)$"
)
MIME_PATTERN: re.Pattern = re.compile(r"^!:mime\s+([^\s]+)\s*(#.*)?$")
EXTENSION_PATTERN: re.Pattern = re.compile(r"^!:ext\s+([^\s]+)\s*(#.*)?$")


def _split_with_escapes(text: str) -> Tuple[str, str]:
    first_length = 0
    escaped = False
    for c in text:
        if escaped:
            escaped = False
        elif c == "\\":
            escaped = True
        elif c == " " or c == "\t" or c == "\n":
            break
        first_length += 1
    return text[:first_length], text[first_length + 1:]


class MagicMatcher:
    def __init__(self, tests: Iterable[MagicTest]):
        self.tests: List[MagicTest] = []
        self.named_tests: Dict[str, NamedTest] = {}
        for test in tests:
            if isinstance(test, NamedTest):
                self.named_tests[test.name] = test
            else:
                self.tests.append(test)

    def match(self, data: bytes, only_match_mime: bool = False) -> Iterator[Match]:
        for test in self.tests:
            yield from test.match(data, only_match_mime=only_match_mime)

    @staticmethod
    def _parse_file(def_file: Union[str, Path], matcher: "MagicMatcher") -> Iterable[UseTest]:
        current_test: Optional[MagicTest] = None
        late_bindings: List[UseTest] = []
        with open(def_file, "rb") as f:
            for line_number, raw_line in enumerate(f.readlines()):
                line_number += 1
                raw_line = raw_line.lstrip()
                if not raw_line or raw_line.startswith(b"#"):
                    # skip empty lines and comments
                    continue
                elif raw_line.startswith(b"!:apple") or raw_line.startswith(b"!:strength"):
                    # ignore these directives for now
                    continue
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                m = TEST_PATTERN.match(line)
                if m:
                    level = len(m.group("level"))
                    while current_test is not None and current_test.level >= level:
                        current_test = current_test.parent
                    if current_test is None and level != 0:
                        raise ValueError(f"{def_file!s} line {line_number}: Invalid level for test {line!r}")
                    test_str, message = _split_with_escapes(m.group("remainder"))
                    # process any escape characters:
                    test_str = unescape(test_str)
                    message = unescape(message)
                    comment_pos = message.find("#")
                    if comment_pos >= 0:
                        message = message[:comment_pos].lstrip()
                    try:
                        offset = Offset.parse(m.group("offset"))
                    except ValueError as e:
                        raise ValueError(f"{def_file!s} line {line_number}: {e!s}")
                    data_type = m.group("data_type")
                    if data_type == "name":
                        if current_test is not None:
                            raise ValueError(f"{def_file!s} line {line_number}: A named test must be at level 0")
                        elif test_str in matcher.named_tests:
                            raise ValueError(f"{def_file!s} line {line_number}: Duplicate test named {test_str!r}")
                        test = NamedTest(name=test_str, offset=offset, message=message)
                        matcher.named_tests[test_str] = test
                    else:
                        if data_type == "default":
                            if current_test is None:
                                raise NotImplementedError("TODO: Add support for default tests at level 0")
                            test = DefaultTest(offset=offset, message=message, parent=current_test)
                        elif data_type == "clear":
                            if current_test is None:
                                raise NotImplementedError("TODO: Add support for clear tests at level 0")
                            test = ClearTest(offset=offset, message=message, parent=current_test)
                        elif data_type == "offset":
                            expected_value = IntegerValue.parse(test_str, num_bytes=8)
                            test = OffsetMatchTest(offset=offset, value=expected_value, message=message,
                                                   parent=current_test)
                        elif data_type == "guid":
                            test = GUIDTest(offset=offset, message=message, parent=current_test)
                        elif data_type == "indirect" or data_type == "indirect/r":
                            test = IndirectTest(matcher=matcher, offset=offset,
                                                relative=m.group("data_type").endswith("r"),
                                                message=message, parent=current_test)
                        elif data_type == "use":
                            if test_str.startswith("^"):
                                flip_endianness = True
                                test_str = test_str[1:]
                            elif test_str.startswith("\\^"):
                                flip_endianness = True
                                test_str = test_str[2:]
                            else:
                                flip_endianness = False
                            if test_str not in matcher.named_tests:
                                late_binding = True
                                named_test: Union[str, NamedTest] = test_str
                            else:
                                late_binding = False
                                named_test = matcher.named_tests[test_str]
                            # named_test might be a string here (the test name) rather than an actual NamedTest object.
                            # This will happen if the named test is defined after the use (late binding).
                            # We will resolve this after the entire file is parsed.
                            test = UseTest(  # type: ignore
                                named_test,
                                offset=offset,
                                message=message,
                                parent=current_test,
                                flip_endianness=flip_endianness
                            )
                            if late_binding:
                                late_bindings.append(test)
                        elif data_type == "der":
                            # TODO: Update this as necessary once we fully implement the DERTest
                            test = DERTest(offset=offset, message=message, parent=current_test)
                        else:
                            try:
                                data_type = DataType.parse(data_type)
                                # in some definitions a space is put after the "&" in a numeric datatype:
                                if test_str == "&":
                                    test_str_remainder, message = _split_with_escapes(message)
                                    message = message.lstrip()
                                    test_str = f"&{test_str_remainder}"
                                if test_str in ("<", ">", "=", "!", "&", "^", "~"):
                                    # Some files will erroneously add whitespace between the operator and the
                                    # subsequent value:
                                    actual_operand, message = _split_with_escapes(message)
                                    test_str = f"{test_str}{actual_operand}"
                                constant = data_type.parse_expected(test_str)
                            except ValueError as e:
                                raise ValueError(f"{def_file!s} line {line_number}: {e!s}")
                            test = ConstantMatchTest(
                                offset=offset,
                                data_type=data_type,
                                constant=constant,
                                message=message,
                                parent=current_test
                            )
                        if test.level == 0:
                            matcher.tests.append(test)
                    current_test = test
                    continue
                m = MIME_PATTERN.match(line)
                if m:
                    if current_test is None:
                        raise ValueError(f"{def_file!s} line {line_number}: Unexpected mime type {line!r}")
                    elif current_test.mime is not None:
                        raise ValueError(f"{def_file!s} line {line_number}: Duplicate mime types for test "
                                         f"{current_test!r}: {current_test.mime!r} and {m.group(1)}")
                    current_test.mime = m.group(1)
                    continue
                m = EXTENSION_PATTERN.match(line)
                if m:
                    if current_test is None:
                        raise ValueError(f"{def_file!s} line {line_number}: Unexpected ext: {line!r}")
                    current_test.extensions.add(m.group(1))
                    continue
                raise ValueError(f"{def_file!s} line {line_number}: Unexpected line\n{raw_line!r}")
        return late_bindings

    @staticmethod
    def parse(*def_files: Union[str, Path]) -> "MagicMatcher":
        late_bindings: Dict[str, List[UseTest]] = {}
        matcher = MagicMatcher([])
        for file in def_files:
            late_bindings[file] = list(MagicMatcher._parse_file(file, matcher=matcher))
        # resolve any "use" tests with late binding:
        for def_file, use_tests in late_bindings.items():
            for use_test in use_tests:
                assert isinstance(use_test.named_test, str)
                if use_test.named_test not in matcher.named_tests:
                    raise ValueError(f"{def_file!s}: Named test {use_test.named_test!r} is not defined")
                use_test.named_test = matcher.named_tests[use_test.named_test]
        return matcher
