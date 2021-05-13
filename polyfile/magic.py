"""
A pure Python implementation of libmagic.

This is to avoid having libmagic be a dependency, as well as to add the ability for searching for matches at arbitrary
byte offsets.

This implementation is also optimized to only test for the file's MIME types; it skips all of the tests for printing
details about the file.

"""
from abc import ABC, abstractmethod
from collections import defaultdict
import csv
from enum import Enum
from io import StringIO
import json
import logging
from pathlib import Path
import re
import struct
import sys
from time import gmtime, localtime, strftime
from typing import (
    Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union
)
from uuid import UUID

from .iterators import LazyIterableSet
from .logger import getStatusLogger, TRACE

if sys.version_info < (3, 9):
    from typing import Pattern
else:
    from re import Pattern


log = getStatusLogger("libmagic")

DEFS_DIR: Path = Path(__file__).absolute().parent / "magic_defs"

MAGIC_DEFS: List[Path] = [
    path
    for path in DEFS_DIR.glob("*")
    if path.name not in ("COPYING", "magic.mgc") and not path.name.startswith(".")
]


WHITESPACE: bytes = b" \r\t\n\v\f"


def unescape(to_unescape: Union[str, bytes]) -> bytes:
    """Processes unicode escape sequences. Also handles libmagic's support for single digit `\\x#` hex escapes."""
    # first, process single digit hex escapes:
    b = bytearray()
    escaped: Optional[str] = None
    if isinstance(to_unescape, str):
        to_unescape = to_unescape.encode("utf-8")
    ESCAPES = {
        "n": ord("\n"),
        "r": ord("\r"),
        "b": ord("\b"),
        "v": ord("\v"),
        "t": ord("\t"),
        "f": ord("\f")
    }
    terminator = object()
    for c in to_unescape:
        if escaped is not None:
            char = chr(c)
            if escaped.isnumeric():
                if not char.isnumeric() or len(escaped) == 3 or not int(char) < 8:
                    # this is an octal escape sequence like "\1", "\12", or "\123"
                    b.append(int(escaped, 8))
                    escaped = None
                else:
                    escaped = f"{escaped}{char}"
                    continue
            elif escaped.startswith("x"):
                # we are processing a hex escape
                if not char.isnumeric() and not ord("a") <= c <= ord("f") and not ord("A") <= c <= ord("F"):
                    if len(escaped) == 1:
                        raise ValueError(f"Invalid \\x hex escape in {to_unescape!r}")
                    b.append(int(escaped[1:], 16))
                    escaped = None
                elif len(escaped) == 2:
                    b.append(int(f"{escaped[1:]}{char}", 16))
                    escaped = None
                    continue
                else:
                    escaped = f"{escaped}{char}"
                    continue
            elif not escaped:
                # the last character was a '\' and this is the first character of the escape
                if char == "x" or char.isnumeric():
                    # The escape is either a hex or octal escape
                    escaped = char
                elif char in ESCAPES:
                    b.append(ESCAPES[char])
                    escaped = None
                else:
                    b.append(c)
                    escaped = None
                continue
        assert escaped is None
        if c == ord("\\"):
            escaped = ""
        else:
            b.append(c)
    if escaped is not None:
        if escaped.startswith("x"):
            if len(escaped) == 1:
                raise ValueError(f"Invalid \\x hex escape in {to_unescape!r}")
            else:
                b.append(int(escaped[1:], 16))
        elif escaped.isnumeric():
            b.append(int(escaped, 8))
        else:
            raise ValueError(f"Unterminated escape in {to_unescape!r}")
    return bytes(b)


class TestResult:
    def __init__(
            self, test: "MagicTest",
            value: Any,
            offset: int,
            length: int,
            parent: Optional["TestResult"] = None
    ):
        self.test: MagicTest = test
        self.value: Any = value
        self.offset: int = offset
        self.length: int = length
        self.parent: Optional[TestResult] = parent
        if parent is not None:
            assert self.test.named_test is self.test or parent.test.level == self.test.level - 1
            if not isinstance(self.test, UseTest):
                parent.child_matched = True
        self._child_matched: bool = False

    @property
    def child_matched(self) -> bool:
        return self._child_matched

    @child_matched.setter
    def child_matched(self, did_match: bool):
        if did_match and isinstance(self.test, NamedTest):
            assert isinstance(self.parent.test, UseTest)
            self.parent.child_matched = True
            if self.parent.parent is not None:
                self.parent.parent.child_matched = True
        self._child_matched = did_match


    def __hash__(self):
        return hash((self.test, self.offset, self.length))

    def __eq__(self, other):
        return isinstance(other, TestResult) and other.test == self.test and other.offset == self.offset \
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


def parse_numeric(text: Union[str, bytes]) -> int:
    if isinstance(text, bytes):
        text = text.decode("utf-8")
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
    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
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


class InvalidOffsetError(IndexError):
    def __init__(self, message: Optional[str] = None, offset: Optional[Offset] = None):
        if message is None:
            if offset is not None:
                message = f"Invalid Offset: {offset!r}"
            else:
                message = "Invalid Offset"
        super().__init__(message)
        self.offset: Optional[Offset] = offset


class AbsoluteOffset(Offset):
    def __init__(self, offset: int):
        self.offset: int = offset

    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
        if self.offset >= len(data):
            raise InvalidOffsetError(offset=self)
        return self.offset

    def __repr__(self):
        return f"{self.__class__.__name__}(offset={self.offset})"

    def __str__(self):
        return str(self.offset)


class NamedAbsoluteOffset(AbsoluteOffset):
    def __init__(self, test: "NamedTest", offset: int):
        super().__init__(offset)
        self.test: NamedTest = test

    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
        while last_match is not None and not last_match.test is self.test:
            last_match = last_match.parent

        if last_match is not None:
            # At this point, last_match should be equal to the match generated from the NamedTest,
            # and its parent should be the match associated with the UseTest
            last_match = last_match.parent

        if last_match is None:
            raise ValueError(f"Could not resolve the match associated with {self!r}")

        assert isinstance(last_match.test, UseTest)

        if last_match.offset + self.offset >= len(data):
            raise InvalidOffsetError(offset=self)
        return last_match.offset + self.offset

    def __repr__(self):
        return f"{self.__class__.__name__}(test={self.test!r}, offset={self.offset})"


class NegativeOffset(Offset):
    def __init__(self, magnitude: int):
        self.magnitude: int = magnitude

    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
        if self.magnitude > len(data):
            raise InvalidOffsetError(offset=self)
        return len(data) - self.magnitude

    def __repr__(self):
        return f"{self.__class__.__name__}(magnitude={self.magnitude})"

    def __str__(self):
        return f"{self.magnitude}"


class RelativeOffset(Offset):
    def __init__(self, relative_to: Offset):
        self.relative_to: Offset = relative_to

    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
        if isinstance(self.relative_to, NegativeOffset):
            difference = -self.relative_to.magnitude
        else:
            difference = self.relative_to.to_absolute(data, last_match)
        offset = last_match.offset + last_match.length + difference
        if len(data) < offset < 0:
            raise InvalidOffsetError(offset=self)
        return offset

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

    def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
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
        to_unpack = data[offset:offset + self.num_bytes]
        if len(to_unpack) < self.num_bytes:
            raise InvalidOffsetError(offset=self)
        return self.post_process(struct.unpack(fmt, to_unpack)[0])

    NUMBER_PATTERN: str = r"(0[xX][\dA-Fa-f]+|\d+)L?"
    INDIRECT_OFFSET_PATTERN: Pattern[str] = re.compile(
        r"^\("
        rf"(?P<offset>&?-?{NUMBER_PATTERN})"
        r"((?P<signedness>[.,])(?P<type>[bBcCeEfFgGhHiILlmsSqQ]))?"
        rf"(?P<post_process>[*&/]?[+-]?({NUMBER_PATTERN}|\(-?{NUMBER_PATTERN}\)))?"
        r"\)$"
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
               f"endianness={self.endianness!r}, signed={self.signed}, post_process={self.post_process!r})"

    def __str__(self):
        if self.addend == 0:
            addend = ""
        elif self.addend < 0:
            addend = str(self.addend)
        else:
            addend = f"+{self.addend}"
        return f"({self.offset!s}{['.', ','][self.signed]}{self.num_bytes}{self.endianness}{addend})"


class SourceInfo:
    def __init__(self, path: Path, line: int, original_line: Optional[str] = None):
        self.path: Path = path
        self.line: int = line
        self.original_line: Optional[str] = original_line

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self.path!r}, line={self.line}, original_line={self.original_line!r})"

    def __str__(self):
        return f"{self.path!s}:{self.line}"


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
        self._mime: Optional[str] = None
        self.extensions: Set[str] = set(extensions)
        self.message: str = message
        self._parent: Optional[MagicTest] = parent
        self.children: List[MagicTest] = []
        if parent is not None:
            self.level: int = self.parent.level + 1
            parent.children.append(self)
            self.named_test: Optional[NamedTest] = parent.named_test
            if self.named_test is not None and isinstance(offset, AbsoluteOffset):
                self.offset = NamedAbsoluteOffset(self.named_test, offset.offset)
            if mime is not None:
                parent.can_match_mime = True
        else:
            self.level = 0
            self.named_test: Optional[NamedTest] = None
        self.can_match_mime: bool = mime is not None
        """
        Whether or not this test or any of its descendants can match a MIME type.
        This is currently set after parsing all of the definition files.
        Any custom implementation should set it manually after this object is created.
        
        """
        self.can_be_indirect: bool = False
        """
        Whether or not this test or any of its descendants can be an indirect test.
        This is currently set after parsing all of the definition files.
        Any custom implementation should set it manually after this object is created.

        """
        self.mime = mime
        self.source_info: Optional[SourceInfo] = None

    @property
    def parent(self) -> Optional["MagicTest"]:
        return self._parent

    def ancestors(self) -> Iterator["MagicTest"]:
        """Yields all ancestors of this test. NamedTest will also include all UseTest ancestors that call it."""
        stack: List[MagicTest] = [self]
        history: Set[MagicTest] = set(stack)
        while stack:
            test = stack.pop()
            if test is not self:
                yield test
            if isinstance(test, NamedTest):
                new_tests = test.used_by - history
                stack.extend(new_tests)
                history |= new_tests
            if test.parent is not None and test.parent not in history:
                stack.append(test.parent)
                history.add(test.parent)

    def descendants(self) -> Iterator["MagicTest"]:
        """
        Yields all descendants of this test.
        UseTests will also include all referenced NamedTests and their descendants.

        """
        stack: List[MagicTest] = [self]
        history: Set[MagicTest] = set(stack)
        while stack:
            test = stack.pop()
            if test is not self:
                yield test
            if test.parent is not None and test.parent not in history:
                new_tests = [child for child in test.children if child not in history]
                stack.extend(reversed(new_tests))
                history |= set(new_tests)
            if isinstance(test, UseTest):
                stack.append(test.referenced_test)
                history.add(test.referenced_test)

    def referenced_tests(self) -> Set["NamedTest"]:
        result: Set[NamedTest] = set()
        for child in self.children:
            result |= child.referenced_tests()
        return result

    @property
    def mime(self) -> Optional[str]:
        return self._mime

    @mime.setter
    def mime(self, new_mime: Optional[str]):
        if self._mime is not None:
            if self._mime == new_mime:
                return
            raise ValueError("The mime type of a test may not be changed once it is set")
        elif new_mime is None:
            # the mime is already None, and we are setting it to None, so just ignore
            return
        self._mime = new_mime
        self.can_match_mime = True

    def _mimetypes(self) -> Iterator[str]:
        """Yields all possible MIME types that this test or any of its descendants could match against"""
        if not self.can_match_mime:
            return
        yielded: Set[str] = set()
        if self.mime is not None:
            yield self.mime
            yielded.add(self.mime)
        for d in self.descendants():
            if d.mime is not None:
                yield d.mime
                yielded.add(d.mime)

    def mimetypes(self) -> LazyIterableSet[str]:
        """Returns the set of all possible MIME types that this test or any of its descendants could match against"""
        return LazyIterableSet(self._mimetypes())

    def _all_extensions(self) -> Iterator[str]:
        """Yields all possible extensions that this test or any of its descendants could match against"""
        yield from self.extensions
        yielded = set(self.extensions)
        for d in self.descendants():
            new_extensions = d.extensions - yielded
            yield from new_extensions
            yielded |= new_extensions

    def all_extensions(self) -> LazyIterableSet[str]:
        """Returns the set of all possible extensions that this test or any of its descendants could match against"""
        return LazyIterableSet(self._all_extensions())

    @abstractmethod
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        raise NotImplementedError()

    def _match(
            self,
            data: bytes,
            only_match_mime: bool = False,
            parent_match: Optional[TestResult] = None
    ) -> Iterator[TestResult]:
        if only_match_mime and not self.can_match_mime:
            return
        try:
            absolute_offset = self.offset.to_absolute(data, parent_match)
        except InvalidOffsetError:
            return None
        m = self.test(data, absolute_offset, parent_match)
        if logging.root.level <= TRACE and (m is not None or self.level > 0):
            log.trace(
                f"{self.source_info!s}\t{m is not None}\t{absolute_offset}\t"
                f"{data[absolute_offset:absolute_offset + 20]!r}"
            )
        if m is not None:
            if not only_match_mime or self.mime is not None:
                yield m
            for child in self.children:
                if not only_match_mime or child.can_match_mime:
                    yield from child._match(data=data, only_match_mime=only_match_mime, parent_match=m)

    def match(self, data: bytes, only_match_mime: bool = False) -> Iterator[TestResult]:
        """Yields all matches for the given data"""
        return self._match(data, only_match_mime=only_match_mime)

    def __str__(self):
        if self.source_info is not None and self.source_info.original_line is not None:
            s = f"{self.source_info.path.name}:{self.source_info.line} {self.source_info.original_line}"
        else:
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

    def __init__(self, raw_match: Optional[bytes] = None, value: Optional[Any] = None, initial_offset: int = 0):
        self.raw_match: Optional[bytes] = raw_match
        if value is None and raw_match is not None:
            self.value: Optional[bytes] = raw_match
        else:
            self.value = value
        self.initial_offset: int = initial_offset

    def __bool__(self):
        return self.raw_match is not None

    def __repr__(self):
        if self.initial_offset != 0:
            io = f", initial_offset={self.initial_offset}"
        else:
            io = ""
        return f"{self.__class__.__name__}(raw_match={self.raw_match!r}, value={self.value!r}{io})"

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
        elif fmt == "guid":
            dt = GUIDType()
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


class UUIDWildcard:
    pass


class GUIDType(DataType[Union[UUID, UUIDWildcard]]):
    def __init__(self):
        super().__init__("guid")

    def parse_expected(self, specification: str) -> Union[UUID, UUIDWildcard]:
        if specification.strip() == "x":
            return UUIDWildcard()
        # there is a bug in the `asf` definition where a guid is missing its last two characters:
        if specification.strip().upper() == "B61BE100-5B4E-11CF-A8FD-00805F5C44":
            specification = "B61BE100-5B4E-11CF-A8FD-00805F5C442B"
        return UUID(specification)

    def match(self, data: bytes, expected: Union[UUID, UUIDWildcard]) -> DataTypeMatch:
        if len(data) < 16:
            return DataTypeMatch.INVALID
        try:
            uuid = UUID(bytes_le=data[:16])
        except ValueError:
            return DataTypeMatch.INVALID
        if isinstance(expected, UUIDWildcard) or uuid == expected:
            return DataTypeMatch(data[:16], uuid)
        else:
            return DataTypeMatch.INVALID


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
        specification = unescape(specification).decode("utf-8")
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


class StringTest(ABC):
    def __init__(self, trim: bool = False, compact_whitespace: bool = False):
        self.trim: bool = trim
        self.compact_whitespace: bool = compact_whitespace

    def post_process(self, data: bytes) -> DataTypeMatch:
        value = data
        if self.compact_whitespace:
            value = b"".join(c for prev, c in zip(b"\0" + data, data) if c not in WHITESPACE or prev not in WHITESPACE)
        if self.trim:
            value = value.strip()
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            pass
        return DataTypeMatch(data, value)

    @abstractmethod
    def matches(self, data: bytes) -> DataTypeMatch:
        raise NotImplementedError()

    @staticmethod
    def parse(specification: str,
              trim: bool = False,
              compact_whitespace: bool = False,
              case_insensitive_lower: bool = False,
              case_insensitive_upper: bool = False,
              optional_blanks: bool = False) -> "StringTest":
        if specification.strip() == "x":
            return StringWildcard(trim=trim, compact_whitespace=compact_whitespace)
        if specification.startswith("!"):
            negate = True
            specification = specification[1:]
        else:
            negate = False
        if specification.startswith(">") or specification.startswith("<"):
            test = StringLengthTest(
                to_match=unescape(specification[1:]),
                test_smaller=specification.startswith("<"),
                trim=trim,
                compact_whitespace=compact_whitespace
            )
        else:
            if specification.startswith("="):
                specification = specification[1:]
            test = StringMatch(
                to_match=unescape(specification),
                trim=trim,
                compact_whitespace=compact_whitespace,
                case_insensitive_lower=case_insensitive_lower,
                case_insensitive_upper=case_insensitive_upper,
                optional_blanks=optional_blanks
            )
        if negate:
            return NegatedStringTest(test)
        else:
            return test


class StringWildcard(StringTest):
    def matches(self, data: bytes) -> DataTypeMatch:
        first_null = data.find(b"\0")
        if first_null >= 0:
            return self.post_process(data[:first_null])
        else:
            return self.post_process(data)


class NegatedStringTest(StringWildcard):
    def __init__(self, parent_test: StringTest):
        super().__init__(trim=parent_test.trim, compact_whitespace=parent_test.compact_whitespace)
        self.parent: StringTest = parent_test

    def matches(self, data: bytes) -> DataTypeMatch:
        result = self.parent.matches(data)
        if result == DataTypeMatch.INVALID:
            return super().matches(data)
        else:
            return DataTypeMatch.INVALID


class StringLengthTest(StringWildcard):
    def __init__(self, to_match: bytes, test_smaller: bool, trim: bool = False, compact_whitespace: bool = False):
        super().__init__(trim=trim, compact_whitespace=compact_whitespace)
        self.to_match: bytes = to_match
        self.test_smaller: bool = test_smaller

    def matches(self, data: bytes) -> DataTypeMatch:
        match = super().matches(data)
        if self.test_smaller and match.raw_match < self.to_match:
            return match
        elif not self.test_smaller and match.raw_match > self.to_match:
            return match
        else:
            return DataTypeMatch.INVALID


class StringMatch(StringTest):
    def __init__(self,
                 to_match: bytes,
                 trim: bool = False,
                 compact_whitespace: bool = False,
                 case_insensitive_lower: bool = False,
                 case_insensitive_upper: bool = False,
                 optional_blanks: bool = False,
    ):
        super().__init__(trim=trim, compact_whitespace=compact_whitespace)
        self.string: bytes = to_match
        self.case_insensitive_lower: bool = case_insensitive_lower
        self.case_insensitive_upper: bool = case_insensitive_upper
        self.optional_blanks: bool = optional_blanks

    def matches(self, data: bytes) -> DataTypeMatch:
        expected = self.string
        matched = bytearray()
        had_whitespace = False
        last_char: Optional[int] = None
        for b in data:
            if not expected:
                break
            matched.append(b)
            is_whitespace = bytes([b]) in WHITESPACE
            if self.trim and last_char is None and is_whitespace:
                # skip leading whitespace
                continue
            elif self.compact_whitespace and is_whitespace:
                if last_char is not None and bytes([last_char]) in WHITESPACE:  # type: ignore
                    # compact consecutive whitespace
                    continue
                else:
                    had_whitespace = True
            if not (
                    b == expected[0] or
                    (self.case_insensitive_lower and b == expected[0:1].lower()[0]) or
                    (self.case_insensitive_upper and b == expected[0:1].upper()[0])
            ):
                if not (self.optional_blanks and expected[0:1] in WHITESPACE):
                    return DataTypeMatch.INVALID
            expected = expected[1:]
        if expected:
            # we did not fully match the expected sequence (e.g., there were not enough bytes in the data)
            return DataTypeMatch.INVALID
        elif self.compact_whitespace and not had_whitespace:
            return DataTypeMatch.INVALID
        return self.post_process(bytes(matched))


class StringType(DataType[StringTest]):
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

    def parse_expected(self, specification: str) -> StringTest:
        return StringTest.parse(specification)

    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
        return expected.matches(data)

    STRING_TYPE_FORMAT: Pattern[str] = re.compile(r"^u?string(/[BbCctTWw]*)?$")

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

    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
        if self.repetitions is None:
            rep = len(data)
        else:
            rep = self.repetitions
        if not self.optional_blanks and not self.case_insensitive_upper and not self.case_insensitive_lower and \
                isinstance(expected, StringMatch):
            # we can use built-in search for more efficiency
            # TODO: Add support for this optimization when the case insensitivity options are enabled
            first_match = data.find(expected.string)
            if 0 <= first_match <= rep:
                m = expected.matches(data[first_match:])
                assert m
                m.initial_offset = first_match
                return m
            else:
                return DataTypeMatch.INVALID
        for i in range(rep):
            match = super().match(data[i:], expected)
            if match:
                match.initial_offset = i
                return match
            elif isinstance(expected, (StringWildcard, StringLengthTest)):
                # TODO: Confirm that this short circuit is correct
                break
        return DataTypeMatch.INVALID

    SEARCH_TYPE_FORMAT: Pattern[str] = re.compile(
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


class PascalStringType(DataType[StringTest]):
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

    def parse_expected(self, specification: str) -> StringTest:
        return StringTest.parse(specification)

    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
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
        m = expected.matches(data[self.byte_length:self.byte_length + length])
        if m:
            m.raw_match = data[:self.byte_length + length]
        return m

    PSTRING_TYPE_FORMAT: Pattern[str] = re.compile(r"^pstring(/J?[BHhLl]?J?)?$")

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


def posix_to_python_re(match: bytes) -> bytes:
    for match_from, replace_with in (
            ("upper", "A-Z"),
            ("lower", "a-z"),
            ("alpha", "A-Za-z"),
            ("digit", "0-9"),
            ("xdigit", "0-9A-Fa-f"),
            ("alnum", "A-Za-z0-9"),
            ("punct", ",./<>?`;':\"\\[\\]{}\\|~!@#$%\\^&*()_+-=\\\\"),
            ("blank", " \t"),
            ("space", " \t\n\r\f\v"),
            ("cntrl", "\0-\x1f\x7f"),
            ("graph", "^\0-\x1f\x7f "),
            ("print", "^\0-\x1f\x7f"),
            ("word", "\\w")
    ):
        match = match.replace(f"[:{match_from}:]".encode("utf-8"), f"{replace_with}".encode("utf-8"))
    return match


class RegexType(DataType[Pattern[bytes]]):
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

    def parse_expected(self, specification: str) -> Pattern[bytes]:
        # handle POSIX-style character classes:
        unescaped_spec = posix_to_python_re(unescape(specification))
        try:
            if self.case_insensitive:
                return re.compile(unescaped_spec, re.IGNORECASE)
            else:
                return re.compile(unescaped_spec)
        except re.error as e:
            raise ValueError(str(e))

    def match(self, data: bytes, expected: Pattern[bytes]) -> DataTypeMatch:
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
                        value = match.decode("utf-8")
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
                    value = match.decode("utf-8")
                except UnicodeDecodeError:
                    value = match
                if self.trim:
                    value = value.strip()
                return DataTypeMatch(match, value)
            else:
                return DataTypeMatch.INVALID

    REGEX_TYPE_FORMAT: Pattern[str] = re.compile(r"^regex(/(?P<length>\d+)?(?P<flags>[cslT]*)(b\d*)?)?$")
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


DATE_FORMAT: str = "%a %b %e %H:%M:%S %Y"


def local_date(ms_since_epoch: int) -> str:
    return strftime(DATE_FORMAT, localtime(ms_since_epoch / 1000.0))


def utc_date(ms_since_epoch: int) -> str:
    return strftime(DATE_FORMAT, gmtime(ms_since_epoch / 1000.0))


class BaseNumericDataType(Enum):
    BYTE = ("byte", "b", 1)
    SHORT = ("short", "h", 2)
    LONG = ("long", "l", 4)
    QUAD = ("quad", "q", 8)
    FLOAT = ("float", "f", 4)
    DOUBLE = ("double", "d", 8)
    DATE = ("date", "L", 4, lambda n : utc_date(n * 1000))
    QDATE = ("qdate", "Q", 8, utc_date)
    LDATE = ("ldate", "L", 4, lambda n: local_date(n * 1000))
    QLDATE = ("qldate", "Q", 8, local_date)
    QWDATE = ("qwdate", "Q", 8)

    def __init__(
            self, name: str,
            struct_fmt: str,
            num_bytes: int,
            to_value: Callable[[int], Any] = lambda n: n
    ):
        self.struct_fmt: str = struct_fmt
        self.num_bytes: int = num_bytes
        self.to_value: Callable[[int], Any] = to_value
        BASE_NUMERIC_TYPES_BY_NAME[name] = self


NUMERIC_OPERATORS_BY_SYMBOL: Dict[str, "NumericOperator"] = {}


class NumericOperator(Enum):
    EQUALS = ("=", lambda a, b: a == b)
    LESS_THAN = ("<", lambda a, b: a < b)
    GREATER_THAN = (">", lambda a, b: a > b)
    ALL_BITS_SET = ("&", lambda a, b: (a & b) == b)  # value from the file (a) must have set all bits set in b
    ALL_BITS_CLEAR = ("^", lambda a, b: not (a & b))  # value from the file (a) must have clear all bits set in b
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

    def test(self, to_match: T, unsigned: bool, num_bytes: int, preprocess: Callable[[int], int] = lambda x: x) -> bool:
        return self.operator.test(preprocess(to_match), self.value)

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

    def test(self, to_match, unsigned, num_bytes, preprocess: Callable[[int], int] = lambda x: x) -> bool:
        return True


class IntegerValue(NumericValue[int]):
    @staticmethod
    def normalize_signedness(value: int, unsigned: bool, num_bytes: int) -> int:
        bits = 8 * num_bytes
        if unsigned:
            max_value = (1 << bits) - 1
            min_value = 0
            if value < 0:
                # convert the value to a bit-equivalent unsigned value
                value += 2**bits
        else:
            max_value = (1 << bits) >> 1
            min_value = ~max_value
            if value > max_value:
                # convert the value to a bit-equivalent signed value
                value -= 2 ** bits
        if not (min_value <= value <= max_value):
            raise ValueError(f"Invalid integer constant {value} for comparing to a "
                             f"{['signed', 'n unsigned'][unsigned]} {num_bytes}-byte integer")
        return value

    def test(self, to_match: int, unsigned: bool, num_bytes: int, preprocess: Callable[[int], int] = lambda x: x) -> bool:
        to_test = IntegerValue.normalize_signedness(self.value, unsigned, num_bytes)
        to_match = IntegerValue.normalize_signedness(preprocess(to_match), unsigned, num_bytes)
        return self.operator.test(to_match, to_test)

    @staticmethod
    def parse(value: Union[str, bytes], num_bytes: int) -> "IntegerValue":
        if isinstance(value, bytes):
            value = value.decode("utf-8")
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
        if operator in (NumericOperator.ALL_BITS_SET, NumericOperator.ALL_BITS_CLEAR):
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
        if expected.test(value, self.unsigned, self.base_type.num_bytes, self.preprocess):
            value = self.preprocess(value)
            return DataTypeMatch(data[:self.base_type.num_bytes], self.base_type.to_value(value))
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

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        match = self.data_type.match(data[absolute_offset:], self.constant)
        if match:
            return TestResult(self, offset=absolute_offset + match.initial_offset, length=len(match.raw_match),
                              value=match.value, parent=parent_match)
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

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        if self.value.test(absolute_offset, unsigned=True, num_bytes=8):
            return TestResult(self, offset=0, length=absolute_offset, value=absolute_offset, parent=parent_match)
        else:
            return None


class IndirectResult(TestResult):
    def __init__(self, test: "IndirectTest", offset: int, parent: Optional[TestResult] = None):
        super().__init__(test, value=None, offset=offset, length=0, parent=parent)


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
        self.can_match_mime = True
        self.can_be_indirect = True
        p = parent
        while p is not None:
            p.can_be_indirect = True
            p.can_match_mime = True
            p = p.parent

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[IndirectResult]:
        if self.relative:
            if parent_match is None:
                return None
            absolute_offset += parent_match.offset
        return IndirectResult(self, absolute_offset, parent_match)


class NamedTest(MagicTest):
    def __init__(
            self,
            name: str,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = ""
    ):
        if not message:
            # by default, named tests should not add a space if they don't contain an explicit message
            message = "\b"
        assert isinstance(offset, AbsoluteOffset) and offset.offset == 0

        class NamedTestOffset(Offset):
            def to_absolute(self, data: bytes, last_match: Optional[TestResult]) -> int:
                assert last_match is not None
                return last_match.offset
        offset = NamedTestOffset()
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=None)
        self.name: str = name
        self.named_test = self
        self.used_by: Set[UseTest] = set()

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        if parent_match is not None:
            return TestResult(self, offset=parent_match.offset + parent_match.length, length=0, value=self.name,
                              parent=parent_match)
        else:
            raise ValueError("A named test must always be called from a `use` test.")

    def __str__(self):
        return self.name


class UseTest(MagicTest):
    def __init__(
            self,
            referenced_test: NamedTest,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None,
            flip_endianness: bool = False
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.referenced_test: NamedTest = referenced_test
        self.flip_endianness: bool = flip_endianness
        referenced_test.used_by.add(self)

    def referenced_tests(self) -> Set[NamedTest]:
        result = super().referenced_tests() | {self.referenced_test}
        if self.named_test is None or self.named_test.name != self.referenced_test.name:
            result |= self.referenced_test.referenced_tests()
        return result

    def _match(
            self,
            data: bytes,
            only_match_mime: bool = False,
            parent_match: Optional[TestResult] = None
    ) -> Iterator[TestResult]:
        if self.flip_endianness:
            raise NotImplementedError("TODO: Add support for use tests with flipped endianness")
        first_match: Optional[TestResult] = None
        try:
            absolute_offset = self.offset.to_absolute(data, last_match=parent_match)
        except InvalidOffsetError:
            return None
        log.trace(
            f"{self.source_info!s}\tTrue\t{absolute_offset}\t{data[absolute_offset:absolute_offset + 20]!r}"
        )
        use_match = TestResult(self, None, absolute_offset, 0, parent=parent_match)
        yielded = False
        for named_result in self.referenced_test._match(data, only_match_mime, use_match):
            if not yielded:
                yielded = True
                yield use_match
            yield named_result
        if not yielded:
            # the named test did not match anything, so don't try any of our children
            return
        elif only_match_mime and not self.can_match_mime:
            # none of our children can produce a mime type
            return
        for child in self.children:
            if not only_match_mime or child.can_match_mime:
                yield from child._match(data=data, only_match_mime=only_match_mime, parent_match=use_match)

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        raise NotImplementedError("This function should never be called")


class JSONTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        try:
            parsed = json.loads(data[absolute_offset:])
            return TestResult(self, offset=absolute_offset, length=len(data) - absolute_offset, value=parsed,
                              parent=parent_match)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


class CSVTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        try:
            text = data[absolute_offset:].decode("utf-8")
        except UnicodeDecodeError:
            return None
        for dialect in csv.list_dialects():
            string_data = StringIO(text, newline="")
            reader = csv.reader(string_data, dialect=dialect)
            valid = False
            try:
                for i, row in enumerate(reader):
                    if i == 0:
                        num_cols = len(row)
                        if num_cols < 2:
                            # CSVs should have at least two rows:
                            break
                        valid = True
                    elif len(row) != num_cols:
                        # every row of the CSV should have the same number of columns
                        valid = False
                        break
            except csv.Error:
                continue
            if valid:
                # every row was valid, and we had at least one row
                return TestResult(self, offset=absolute_offset, length=len(data) - absolute_offset, value=dialect,
                                  parent=parent_match)
        return None


class DefaultTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        if parent_match is None or not parent_match.child_matched:
            return TestResult(self, offset=absolute_offset, length=0, value=True, parent=parent_match)
        else:
            return None


class ClearTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        if parent_match is None:
            return TestResult(self, offset=absolute_offset, length=0, value=None)
        else:
            parent_match.child_matched = False
            return TestResult(self, offset=absolute_offset, length=0, parent=parent_match, value=None)


class DERTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> Optional[TestResult]:
        raise NotImplementedError(
            "TODO: Implement support for the DER test (e.g., using the Kaitai asn1_der.py parser)"
        )


TEST_PATTERN: Pattern[str] = re.compile(
    r"^(?P<level>[>]*)(?P<offset>[^\s!][^\s]*)\s+(?P<data_type>[^\s]+)\s+(?P<remainder>.+)$"
)
MIME_PATTERN: Pattern[str] = re.compile(r"^!:mime\s+([^\s]+)\s*(#.*)?$")
EXTENSION_PATTERN: Pattern[str] = re.compile(r"^!:ext\s+([^\s]+)\s*(#.*)?$")


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


class Match:
    def __init__(
            self, matcher: "MagicMatcher", data: bytes, results: Iterable[TestResult], only_match_mime: bool = False
    ):
        self.matcher: MagicMatcher = matcher
        self.data: bytes = data
        self.only_match_mime: bool = only_match_mime
        self._result_iter: Optional[Iterator[TestResult]] = iter(results)
        self._results: List[TestResult] = []

    @property
    def mimetypes(self) -> LazyIterableSet[str]:
        return LazyIterableSet((result.test.mime for result in self if result.test.mime is not None))

    @property
    def extensions(self) -> LazyIterableSet[str]:
        def _extensions():
            for result in self:
                yield from result.test.extensions
        return LazyIterableSet(_extensions())

    def __bool__(self):
        return any(m for m in self.mimetypes) or any(e for e in self.extensions) or bool(self.message())

    def __len__(self):
        if self._result_iter is not None:
            # we have not yet finished collecting the results
            for _ in self: pass
        assert self._result_iter is None
        return len(self._results)

    def __getitem__(self, index: int) -> TestResult:
        while self._result_iter is not None and index <= len(self._results):
            # we have not yet finished collecting the results
            try:
                result = next(self._result_iter)
                self._results.append(result)
                if isinstance(result, IndirectResult):
                    for match in self.matcher.match(self.data[result.offset:], self.only_match_mime):
                        self._results.extend(match)
            except StopIteration:
                self._result_iter = None
        return self._results[index]

    def __iter__(self) -> Iterator[TestResult]:
        if self._result_iter is None:
            yield from self._results
            return
        i = 0
        while True:
            try:
                yield self[i]
            except IndexError:
                break
            i += 1

    def message(self) -> str:
        msg = ""
        for result in self:
            m = result.test.message.lstrip()
            if not m:
                continue
            elif m.startswith("\b"):
                result_str = m[1:]
            else:
                result_str = m
                if msg and not msg[-1] in " \t\r\n\v\f":
                    msg = f"{msg} "
            if "%u" in result_str and result.value < 0:
                # sometimes we parsed a negative value and want to print it as an unsigned int:
                result_str = result_str % (result.value + 2**(8 * result.length),)
            elif "%" in result_str.replace("%%", ""):
                result_str = result_str % (result.value,)
            result_str = result_str.replace("%%", "%")
            msg = f"{msg}{result_str}"
        return msg

    __str__ = message


class MagicMatcher:
    _DEFAULT_INSTANCE: Optional["MagicMatcher"] = None

    def __init__(self, tests: Iterable[MagicTest] = ()):
        self._tests: List[MagicTest] = []
        self.named_tests: Dict[str, NamedTest] = {}
        self.tests_by_mime: Dict[str, Set[MagicTest]] = defaultdict(set)
        self.tests_by_ext: Dict[str, Set[MagicTest]] = defaultdict(set)
        self.tests_that_can_be_indirect: Set[MagicTest] = set()
        for test in tests:
            self.add(test)

    @classmethod
    @property
    def DEFAULT_INSTANCE(cls) -> "MagicMatcher":
        if cls._DEFAULT_INSTANCE is None:
            cls._DEFAULT_INSTANCE = MagicMatcher.parse(*MAGIC_DEFS)
        return cls._DEFAULT_INSTANCE

    def add(self, test: MagicTest):
        if isinstance(test, NamedTest):
            if test.name in self.named_tests:
                raise ValueError(f"A test named {test.name} already exists in this matcher!")
            self.named_tests[test.name] = test
        else:
            self._tests.append(test)
            for mime in test.mimetypes():
                self.tests_by_mime[mime].add(test)
            for ext in test.all_extensions():
                self.tests_by_ext[ext].add(test)
            if test.can_be_indirect:
                self.tests_that_can_be_indirect.add(test)

    def only_match(
            self,
            mimetypes: Optional[Iterable[str]] = None,
            extensions: Optional[Iterable[str]] = None
    ) -> "MagicMatcher":
        """
        Returns the simplest possible matcher that is capable of matching against all the given mimetypes or extensions.

        If either argument is None, the resulting matcher will match against all such values. Therefore, if both
        arguments are None, the resulting matcher will be equivalent to this matcher.

        """
        if mimetypes is None and extensions is None:
            return self
        tests: Set[MagicTest] = {
            indirect_test for indirect_test in self.tests_that_can_be_indirect
            if not any(True for _ in indirect_test.mimetypes())
        }
        if mimetypes is not None:
            for mime in mimetypes:
                tests |= self.tests_by_mime[mime]
        if extensions is not None:
            for ext in extensions:
                tests |= self.tests_by_ext[ext]
        # add in all necessary named tests:
        required_named_tests = set()
        for test in tests:
            required_named_tests |= test.referenced_tests()
        return MagicMatcher(tests | required_named_tests)

    def __iter__(self) -> Iterator[MagicTest]:
        return iter(self._tests)

    @property
    def mimetypes(self) -> Iterable[str]:
        """Returns the set of MIME types this matcher is capable of matching"""
        return self.tests_by_mime.keys()

    @property
    def extensions(self) -> Iterable[str]:
        """Returns the set of extensions this matcher is capable of matching"""
        return self.tests_by_ext.keys()

    def match(self, data: bytes, only_match_mime: bool = False) -> Iterator[Match]:
        for test in log.range(self._tests, desc="matching", unit=" tests", delay=1.0):
            m = Match(self, data, test.match(data, only_match_mime=only_match_mime), only_match_mime)
            if m and (not only_match_mime or any(t is not None for t in m.mimetypes)):
                yield m

    @staticmethod
    def _parse_file(
            def_file: Union[str, Path], matcher: "MagicMatcher"
    ) -> Tuple[Iterable[MagicTest], Iterable[UseTest], Set[MagicTest], Set[IndirectTest]]:
        current_test: Optional[MagicTest] = None
        late_bindings: List[UseTest] = []
        level_zero_tests: List[MagicTest] = []
        tests_with_mime: Set[MagicTest] = set()
        indirect_tests: Set[IndirectTest] = set()
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
                    message = unescape(message).decode("utf-8")
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
                        test.source_info = SourceInfo(def_file, line_number, line)
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
                        elif data_type == "json":
                            test = JSONTest(offset=offset, message=message, parent=current_test)
                        elif data_type == "csv":
                            test = CSVTest(offset=offset, message=message, parent=current_test)
                        elif data_type == "indirect" or data_type == "indirect/r":
                            test = IndirectTest(matcher=matcher, offset=offset,
                                                relative=m.group("data_type").endswith("r"),
                                                message=message, parent=current_test)
                            indirect_tests.add(test)
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
                                class LateBindingNamedTest(NamedTest):
                                    def __init__(self):
                                        super().__init__(test_str, offset=AbsoluteOffset(0))
                                named_test: NamedTest = LateBindingNamedTest()
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
                            level_zero_tests.append(test)
                    test.source_info = SourceInfo(def_file, line_number, line)
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
                    tests_with_mime.add(current_test)
                    continue
                m = EXTENSION_PATTERN.match(line)
                if m:
                    if current_test is None:
                        raise ValueError(f"{def_file!s} line {line_number}: Unexpected ext: {line!r}")
                    current_test.extensions |= {ext for ext in re.split(r"[/,]", m.group(1)) if ext}
                    continue
                raise ValueError(f"{def_file!s} line {line_number}: Unexpected line\n{raw_line!r}")
        return level_zero_tests, late_bindings, tests_with_mime, indirect_tests

    @staticmethod
    def parse(*def_files: Union[str, Path]) -> "MagicMatcher":
        late_bindings: Dict[str, List[UseTest]] = {}
        zero_level_tests: List[MagicTest] = []
        tests_with_mime: Set[MagicTest] = set()
        indirect_tests: Set[IndirectTest] = set()
        matcher = MagicMatcher([])
        for file in def_files:
            zl, lb, wm, it = MagicMatcher._parse_file(file, matcher=matcher)
            late_bindings[file] = list(lb)
            zero_level_tests.extend(zl)
            tests_with_mime |= wm
            indirect_tests |= it
        # resolve any "use" tests with late binding:
        for def_file, use_tests in late_bindings.items():
            for use_test in use_tests:
                if use_test.referenced_test.name not in matcher.named_tests:
                    raise ValueError(f"{def_file!s}: Named test {use_test.referenced_test.name!r} is not defined")
                named_test = matcher.named_tests[use_test.referenced_test.name]
                use_test.referenced_test = named_test
                named_test.used_by.add(use_test)
        for test in tests_with_mime:
            assert test.can_match_mime
            for ancestor in test.ancestors():
                ancestor.can_match_mime = True
        for test in indirect_tests:
            assert test.can_be_indirect
            assert test.can_match_mime
            for ancestor in test.ancestors():
                ancestor.can_be_indirect = True
        for test in zero_level_tests:
            matcher.add(test)
        return matcher
