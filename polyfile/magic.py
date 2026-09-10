"""
A pure Python implementation of libmagic.

This is to avoid having libmagic be a dependency, as well as to add the ability for searching for matches at arbitrary
byte offsets.

This implementation is also optimized to only test for the file's MIME types; it skips all of the tests for printing
details about the file.

"""
from abc import ABC, abstractmethod
import codecs
from collections import defaultdict
import csv
import functools
from datetime import datetime
from enum import Enum, IntFlag
from importlib import resources
from io import StringIO
import json
import logging
from pathlib import Path
import re
import struct
import sys
from time import gmtime, localtime, strftime
from typing import (
    Any, BinaryIO, Callable, Dict, FrozenSet, Generic, Iterable, Iterator, KeysView, List,
    NamedTuple, Optional, Set, Tuple, Type, TypeVar, Union
)
from uuid import UUID

from .arithmetic import CStyleInt, make_c_style_int
from .der import DERHeader, DERSpecification, InvalidDER, mime_type_for_message
from .fileutils import Streamable
from .iterators import LazyIterableSet
from .logger import getStatusLogger, TRACE
from .repl import ANSIColor, ANSIWriter

from . import magic_defs


if sys.version_info < (3, 9):
    from typing import Pattern
else:
    from re import Pattern


log = getStatusLogger("libmagic")


if sys.version_info < (3, 11):
    def get_resource_path(name: str) -> Path:
        with resources.path(magic_defs, name) as path:
            return path

    def get_resource_contents(package):
        return resources.contents(package)
else:
    def get_resource_path(name: str) -> Path:
        with resources.as_file(resources.files(magic_defs).joinpath(name)) as f:
            return f

    def get_resource_contents(package):
        return (resource.name for resource in resources.files(package).iterdir() if resource.is_file())


MAGIC_DEFS: List[Path] = sorted([
    get_resource_path(resource_name)
    for resource_name in get_resource_contents(magic_defs)
    if resource_name not in ("COPYING", "magic.mgc", "__pycache__") and not resource_name.startswith(".")
], key=lambda p: p.name)


WHITESPACE: bytes = b" \r\t\n\v\f"
# a whitespace byte of an `re.escape`-ed pattern, with or without the backslash that escaped it
BLANK_IN_PATTERN: Pattern[bytes] = re.compile(rb"\\?[ \t\n\v\f\r]")
# a wildcard string value ends at the first of these, per `file/src/softmagic.c:683-684`
VALUE_TERMINATOR: Pattern[bytes] = re.compile(rb"[\0\r\n]")
# `MAXstring`, the size of the buffer libmagic copies a string value into: `file/src/file.h:179`
MAX_STRING_BYTES: int = 128
ESCAPES = {
    "n": ord("\n"),
    "r": ord("\r"),
    "b": ord("\b"),
    "v": ord("\v"),
    "t": ord("\t"),
    "f": ord("\f")
}


def unescape(to_unescape: Union[str, bytes]) -> bytes:
    """Processes unicode escape sequences. Also handles libmagic's support for single digit `\\x#` hex escapes."""
    # first, process single digit hex escapes:
    b = bytearray()
    escaped: Optional[str] = None
    if isinstance(to_unescape, str):
        to_unescape = to_unescape.encode("utf-8")
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


class TestResult(ABC):
    def __init__(self, test: "MagicTest", offset: int, parent: Optional["TestResult"] = None):
        self.test: MagicTest = test
        self.offset: int = offset
        self.parent: Optional["TestResult"] = parent
        if parent is not None and bool(self):
            assert self.test.named_test is self.test or parent.test.level == self.test.level - 1
            if not isinstance(self.test, UseTest):
                parent.child_matched = True
        self._child_matched: bool = False

    @abstractmethod
    def explain(self, writer: ANSIWriter, file: Streamable):
        raise NotImplementedError()

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
        return hash((self.test, self.offset))

    def __eq__(self, other):
        return isinstance(other, TestResult) and other.test == self.test and other.offset == self.offset

    @abstractmethod
    def __bool__(self):
        raise NotImplementedError()

    def __repr__(self):
        return f"{self.__class__.__name__}(test={self.test!r}, offset={self.offset}, parent={self.parent!r})"

    def __str__(self):
        if self.test.message is not None:
            # TODO: Fix pasting our value in
            return str(self.test.message)
            #if self.value is not None and "%" in self.test.message:
            #    return self.test.message % (self.value,)
            #else:
            #    return self.test.message
        else:
            return f"Match[{self.offset}]"


class MatchedTest(TestResult):
    def __init__(
            self, test: "MagicTest",
            value: Any,
            offset: int,
            length: int,
            parent: Optional["TestResult"] = None
    ):
        super().__init__(test=test, offset=offset, parent=parent)
        self.value: Any = value
        self.length: int = length
        self._relative_base: Optional[int] = None

    @property
    def relative_base(self) -> int:
        """The absolute offset that a relative (``&``) offset in a subsequent test resolves against.

        This is the end of this match unless a test moves it. The ``der`` tests move it past the DER
        object they matched, so that the following test at the same level reads the next DER object.
        """
        if self._relative_base is None:
            return self.offset + self.length
        return self._relative_base

    @relative_base.setter
    def relative_base(self, absolute_offset: int):
        self._relative_base = absolute_offset

    def explain(self, writer: ANSIWriter, file: Streamable):
        if self.parent is not None:
            self.parent.explain(writer, file=file)
        indent = self.test.write(writer)
        if not isinstance(self.test, (NamedTest, UseTest)):
            writer.write(f"{indent}Matched ", bold=True, color=ANSIColor.GREEN)
            writer.write(str(self.length), bold=True)
            writer.write(f" byte{['','s'][self.length != 1]} at offset ", bold=True, color=ANSIColor.GREEN)
            writer.write(f"{self.offset}\n", bold=True)
            writer.write_context(file, offset=self.offset, context_bytes=max(0, (80 - len(indent) - self.length) // 2),
                                 num_bytes=self.length, indent=indent)

    def __hash__(self):
        return hash((self.test, self.offset, self.length))

    def __eq__(self, other):
        return isinstance(other, MatchedTest) and other.test == self.test and other.offset == self.offset \
               and other.length == self.length

    def __bool__(self):
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}(test={self.test!r}, offset={self.offset}, length={self.length}, " \
               f"parent={self.parent!r})"

    def __str__(self):
        if self.test.message is not None:
            # TODO: Fix pasting our value in
            return str(self.test.message)
            #if self.value is not None and "%" in self.test.message:
            #    return self.test.message % (self.value,)
            #else:
            #    return self.test.message
        else:
            return f"Match[{self.offset}:{self.offset + self.length}]"


class FailedTest(TestResult):
    def __init__(self, test: "MagicTest", offset: int, message: str, parent: Optional["TestResult"] = None):
        super().__init__(test=test, offset=offset, parent=parent)
        self.message: str = message

    def __bool__(self):
        return False

    def explain(self, writer: ANSIWriter, file: Streamable):
        writer.write(f"{self.test} did not match at offset {self.offset} because {self.message}\n", dim=True)


class Endianness(Enum):
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"
    PDP = "me"


class StrengthOp(Enum):
    NONE = ""
    PLUS = "+"
    MINUS = "-"
    TIMES = "*"
    DIV = "/"


STRENGTH_MULT: int = 10
"""libmagic's strength unit, ``MULT`` in ``file/src/apprentice.c:928``."""

STRENGTH_BASELINE: int = 2 * STRENGTH_MULT
"""The strength every test starts from, before its type and relation terms."""

RELATION_STRENGTH: Dict[str, int] = {
    "=": STRENGTH_MULT,
    ">": -2 * STRENGTH_MULT,
    "<": -2 * STRENGTH_MULT,
    "^": -STRENGTH_MULT,
    "&": -STRENGTH_MULT,
}
"""How each relational operator adjusts a test's strength (``file/src/apprentice.c:1034-1051``).

An exact match is the most specific, so it gains a unit; an inequality is the least specific of the
operators that still read a value, so it loses two.
"""

UNSELECTIVE_RELATIONS: FrozenSet[str] = frozenset({"x", "!"})
"""The relations libmagic zeroes the strength for, because they match anything or almost anything."""

LIBMAGIC_TYPE_CODES: Dict[str, int] = {
    "invalid": 0, "byte": 1, "short": 2, "default": 3, "long": 4, "string": 5, "date": 6,
    "beshort": 7, "belong": 8, "bedate": 9, "leshort": 10, "lelong": 11, "ledate": 12,
    "pstring": 13, "ldate": 14, "beldate": 15, "leldate": 16, "regex": 17, "bestring16": 18,
    "lestring16": 19, "search": 20, "medate": 21, "meldate": 22, "melong": 23, "quad": 24,
    "lequad": 25, "bequad": 26, "qdate": 27, "leqdate": 28, "beqdate": 29, "qldate": 30,
    "leqldate": 31, "beqldate": 32, "float": 33, "befloat": 34, "lefloat": 35, "double": 36,
    "bedouble": 37, "ledouble": 38, "beid3": 39, "leid3": 40, "indirect": 41, "qwdate": 42,
    "leqwdate": 43, "beqwdate": 44, "name": 45, "use": 46, "clear": 47, "der": 48, "guid": 49,
    "leguid": 50, "beguid": 51, "offset": 52, "bevarint": 53, "levarint": 54, "msdosdate": 55,
    "lemsdosdate": 56, "bemsdosdate": 57, "msdostime": 58, "lemsdostime": 59, "bemsdostime": 60,
    "octal": 61,
}
"""libmagic's ``FILE_*`` type number for each type name a definition can declare.

The number, not the name, is what orders two tests of equal strength, because libmagic compares
their raw ``struct magic`` bytes (``file/src/apprentice.c:216-283`` and
``file/src/file.h:245-306``).
"""

TYPE_MODIFIER: Pattern[str] = re.compile(r"[/&|^+\-*%]")
"""The characters that start the modifiers a type declaration can carry after its name."""

FLAG_INDIR: int = 0x01
FLAG_UNSIGNED: int = 0x08
FLAG_NOSPACE: int = 0x10
FLAG_OFFNEGATIVE: int = 0x80
"""The ``struct magic`` flag bits a level 0 test can carry (``file/src/file.h:225-235``).

``OFFADD`` and ``INDIROFFADD`` are missing because libmagic rejects a relative offset at level 0
(``file/src/apprentice.c:2132-2137``), and ``BINTEST`` and ``TEXTTEST`` because they only record
which of `MagicMatcher.match`'s two passes a test belongs to.
"""

STRING_DEFAULT_RANGE: int = 100
"""The ``str_range`` libmagic gives a ``search`` that declared none (``file/src/file.h:433``)."""

STRING_FLAG_BITS: Tuple[Tuple[str, int], ...] = (
    ("compact_whitespace", 0x0001),
    ("optional_blanks", 0x0002),
    ("case_insensitive_lower", 0x0004),
    ("case_insensitive_upper", 0x0008),
    ("match_to_start", 0x0010),
    ("force_text", 0x0020),
    ("trim", 0x2000),
    ("full_word_match", 0x4000),
)
"""Each string modifier PolyFile records, with the ``str_flags`` bit libmagic sets for it.

See ``file/src/file.h:414-432`` for the bit numbering and ``file/src/apprentice.c:1946-1980`` for
the modifier characters they come from.
"""


def libmagic_field(value: int, num_bytes: int) -> bytes:
    """Lays `value` out the way ``memcmp`` reads an integer field of ``struct magic``.

    Args:
        value: The number the field holds.
        num_bytes: The width of the field.

    Returns:
        The field's bytes, least significant first, because libmagic runs on little endian
        hardware.
    """
    return (value & ((1 << (8 * num_bytes)) - 1)).to_bytes(num_bytes, "little")


def libmagic_base_type(declaration: str) -> str:
    """Strips a type declaration down to the name libmagic's type table holds.

    Args:
        declaration: A type as a definition wrote it, such as ``ubelong&0x00ffffff``.

    Returns:
        A key of `LIBMAGIC_TYPE_CODES`.
    """
    name = TYPE_MODIFIER.split(declaration, maxsplit=1)[0]
    if name.startswith("u") and name[1:] in LIBMAGIC_TYPE_CODES:
        return name[1:]
    return name


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
        if text.lower().endswith("h"):
            # Some hex constants now end with "h" 🤷
            # (see https://github.com/file/file/blob/7a4e60a8f56ed45f76f28d2812a88d82efdc4bb8/magic/Magdir/sniffer#L369)
            text = text[:-1]
        return int(text, 16) * factor
    elif text.startswith("0") and len(text) > 1:
        return int(text, 8) * factor
    else:
        return int(text) * factor


class Offset(ABC):
    @abstractmethod
    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
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

    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
        if not allow_invalid and self.offset >= len(data):
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

    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
        while last_match is not None and not last_match.test is self.test:
            last_match = last_match.parent

        if last_match is not None:
            # At this point, last_match should be equal to the match generated from the NamedTest,
            # and its parent should be the match associated with the UseTest
            last_match = last_match.parent

        if last_match is None:
            raise ValueError(f"Could not resolve the match associated with {self!r}")

        assert isinstance(last_match.test, UseTest)

        if not allow_invalid and last_match.offset + self.offset >= len(data):
            raise InvalidOffsetError(offset=self)
        return last_match.offset + self.offset

    def __repr__(self):
        return f"{self.__class__.__name__}(test={self.test!r}, offset={self.offset})"


class NegativeOffset(Offset):
    def __init__(self, magnitude: int):
        self.magnitude: int = magnitude

    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
        if not allow_invalid and self.magnitude > len(data):
            raise InvalidOffsetError(offset=self)
        return len(data) - self.magnitude

    def __repr__(self):
        return f"{self.__class__.__name__}(magnitude={self.magnitude})"

    def __str__(self):
        return f"{self.magnitude}"


class RelativeOffset(Offset):
    def __init__(self, relative_to: Offset):
        self.relative_to: Offset = relative_to

    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
        if isinstance(self.relative_to, NegativeOffset):
            difference = -self.relative_to.magnitude
        else:
            difference = self.relative_to.to_absolute(data, last_match)
        if not isinstance(last_match, MatchedTest):
            raise InvalidOffsetError(f"The last test was expected to be a match, but instead got {last_match!s}",
                                     offset=self)
        offset = last_match.relative_base + difference
        if not allow_invalid and len(data) < offset < 0:
            raise InvalidOffsetError(offset=self)
        return offset

    def __repr__(self):
        return f"{self.__class__.__name__}(relative_to={self.relative_to})"

    def __str__(self):
        return f"&{self.relative_to}"


def decode_id3_synchsafe(value: int) -> int:
    """Decodes a 32-bit ID3v2 synchsafe integer.

    An ID3v2 tag stores its size with only seven significant bits per byte so that the encoded
    size can never be mistaken for an MPEG frame sync. This mirrors `cvt_id3` in libmagic's
    `src/softmagic.c`, which libmagic applies to the `i` and `I` indirect offset types before
    any offset arithmetic.

    Args:
        value: The four size bytes, already interpreted in the field's byte order.

    Returns:
        The decoded 28-bit integer.
    """
    return ((value & 0x7F)
            | ((value >> 8 & 0x7F) << 7)
            | ((value >> 16 & 0x7F) << 14)
            | ((value >> 24 & 0x7F) << 21))


class IndirectOffset(Offset):
    OctalIndirectOffset = -1

    STRUCT_FORMATS: Dict[int, str] = {1: "B", 2: "H", 4: "I", 8: "Q"}

    TYPE_NUM_BYTES: Dict[str, int] = {
        "b": 1, "c": 1,
        "h": 2, "s": 2,
        "i": 4, "l": 4,
        "e": 8, "f": 8, "g": 8, "q": 8,
        "o": OctalIndirectOffset,
    }

    def __init__(self, offset: Offset, num_bytes: int, endianness: Endianness, signed: bool,
                 post_process: Callable[[int], int] = lambda n: n, *, is_id3: bool = False):
        self.offset: Offset = offset
        self.num_bytes: int = num_bytes
        self.endianness: Endianness = endianness
        self.signed: bool = signed
        self.post_process: Callable[[int], int] = post_process
        self.is_id3: bool = is_id3
        if self.endianness != Endianness.LITTLE and self.endianness != endianness.BIG:
            raise ValueError(f"Invalid endianness: {endianness!r}")
        elif num_bytes not in (1, 2, 4, 8, IndirectOffset.OctalIndirectOffset):
            raise ValueError(f"Invalid number of bytes: {num_bytes}")
        elif is_id3 and num_bytes != 4:
            raise ValueError(f"An ID3 indirect offset must be four bytes, not {num_bytes}")

    def _octal_to_absolute(self, data: bytes, last_match: Optional[TestResult],
                           allow_invalid: bool) -> int:
        # This is for the octal type used here:
        # https://github.com/file/file/blob/7a4e60a8f56ed45f76f28d2812a88d82efdc4bb8/magic/Magdir/gentoo#L81
        offset = self.offset.to_absolute(data, last_match)
        octal_string_end = offset
        while octal_string_end < len(data) and ord('0') <= data[octal_string_end] <= ord('7'):
            octal_string_end += 1
        value: Optional[int] = None
        if octal_string_end > offset:
            try:
                value = int(data[:octal_string_end], 8)
            except ValueError:
                pass
        if value is None:
            if not allow_invalid:
                return len(data)
            value = 0
        return self.post_process(value)

    def _struct_format(self) -> str:
        fmt = IndirectOffset.STRUCT_FORMATS[self.num_bytes]
        if self.signed:
            fmt = fmt.lower()
        if self.endianness == Endianness.LITTLE:
            return f"<{fmt}"
        return f">{fmt}"

    def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
        if self.num_bytes == IndirectOffset.OctalIndirectOffset:
            return self._octal_to_absolute(data, last_match, allow_invalid)
        offset = self.offset.to_absolute(data, last_match)
        to_unpack = data[offset:offset + self.num_bytes]
        if len(to_unpack) < self.num_bytes:
            if allow_invalid:
                return len(data)
            else:
                raise InvalidOffsetError(offset=self)
        value = struct.unpack(self._struct_format(), to_unpack)[0]
        if self.is_id3:
            value = decode_id3_synchsafe(value)
        return self.post_process(value)

    NUMBER_PATTERN: str = r"(0[xX][\dA-Fa-f]+|\d+)L?"
    INDIRECT_OFFSET_PATTERN: Pattern[str] = re.compile(
        r"^\("
        rf"(?P<offset>&?-?{NUMBER_PATTERN})"
        r"((?P<signedness>[.,])(?P<type>[bBcCeEfFgGhHiILlmsSqQo]))?"
        rf"(?P<post_process>[*&/]?[+-]?({NUMBER_PATTERN}|\(-?{NUMBER_PATTERN}\)))?"
        r"\)$"
    )

    @staticmethod
    def _parse_post_process(pp: Optional[str]) -> Callable[[int], int]:
        if pp is None:
            return lambda n: n
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
            return lambda n: n * operand
        elif bitwise_and:
            return lambda n: n & operand
        elif divide:
            return lambda n: n // operand
        return lambda n: n + operand

    @classmethod
    def parse(cls, offset: str) -> "IndirectOffset":
        """Parses an indirect offset such as `(6.I+10)`.

        The type character selects the width and byte order of the field to read, following
        libmagic's `parse_type` in `src/apprentice.c`: `l`/`L` are four-byte integers, `i`/`I`
        are four-byte ID3v2 synchsafe integers, and an absent type defaults to a four-byte
        integer. A lowercase character means little endian and an uppercase one big endian.

        Args:
            offset: The parenthesized text of the offset, including its surrounding parentheses.

        Returns:
            The parsed offset.

        Raises:
            ValueError: If `offset` is not a valid indirect offset, or names an unsupported type.
            NotImplementedError: If `offset` uses middle endianness.
        """
        m = cls.INDIRECT_OFFSET_PATTERN.match(offset)
        if not m:
            raise ValueError(f"Invalid indirect offset: {offset!r}")
        t = m.group("type")
        if t is None:
            t = "L"
        if t == "m":
            raise NotImplementedError("TODO: Add support for middle endianness")
        elif t.islower():
            endianness = Endianness.LITTLE
        else:
            endianness = Endianness.BIG
        t = t.lower()
        if t not in cls.TYPE_NUM_BYTES:
            raise ValueError(f"Unsupported indirect specifier type: {m.group('type')!r}")
        return IndirectOffset(
            offset=Offset.parse(m.group("offset")),
            num_bytes=cls.TYPE_NUM_BYTES[t],
            endianness=endianness,
            signed=m.group("signedness") == ",",
            post_process=cls._parse_post_process(m.group("post_process")),
            is_id3=t == "i"
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(offset={self.offset!r}, num_bytes={self.num_bytes}, "\
               f"endianness={self.endianness!r}, signed={self.signed}, "\
               f"post_process={self.post_process!r}, is_id3={self.is_id3})"

    def __str__(self):
        if self.num_bytes == IndirectOffset.OctalIndirectOffset:
            num_bytes = "o"
        else:
            num_bytes = str(self.num_bytes)
        return f"({self.offset!s}{['.', ','][self.signed]}{num_bytes}{self.endianness.value})"


INDIRECT_OFFSET_TYPES: Dict[Tuple[int, Endianness], str] = {
    (1, Endianness.LITTLE): "byte", (1, Endianness.BIG): "byte",
    (2, Endianness.LITTLE): "leshort", (2, Endianness.BIG): "beshort",
    (4, Endianness.LITTLE): "lelong", (4, Endianness.BIG): "belong",
    (8, Endianness.LITTLE): "lequad", (8, Endianness.BIG): "bequad",
}
"""The type libmagic reads an indirect offset through, by width and byte order.

See the character it comes from in ``file/src/apprentice.c:2158-2215``.
"""


def libmagic_indirect_type(offset: IndirectOffset) -> str:
    """Names the type libmagic stores in ``in_type`` for `offset`.

    Args:
        offset: An indirect offset.

    Returns:
        A key of `LIBMAGIC_TYPE_CODES`.
    """
    if offset.is_id3:
        return "leid3" if offset.endianness is Endianness.LITTLE else "beid3"
    elif offset.num_bytes == IndirectOffset.OctalIndirectOffset:
        return "octal"
    return INDIRECT_OFFSET_TYPES.get((offset.num_bytes, offset.endianness), "long")


def libmagic_offset_fields(offset: Offset) -> Tuple[int, int, str]:
    """The ``struct magic`` fields that `offset` decides.

    libmagic steps over the sign of a negative offset before it reads the number, so the field
    holds the magnitude and the sign lives in a flag bit
    (``file/src/apprentice.c:2140-2144``).

    Args:
        offset: The offset a definition declared.

    Returns:
        The flag bits `offset` sets, the number libmagic stores in the ``offset`` field, and the
        name of the type an indirect offset reads through, which is ``"invalid"`` for a direct
        offset.
    """
    if isinstance(offset, RelativeOffset):
        offset = offset.relative_to
    if isinstance(offset, IndirectOffset):
        base = offset.offset
        return (FLAG_INDIR,
                base.offset if isinstance(base, AbsoluteOffset) else 0,
                libmagic_indirect_type(offset))
    elif isinstance(offset, NegativeOffset):
        return FLAG_OFFNEGATIVE, offset.magnitude, "invalid"
    elif isinstance(offset, AbsoluteOffset):
        return 0, offset.offset, "invalid"
    return 0, 0, "invalid"


class SourceInfo:
    def __init__(self, path: Union[str, Path], line: int, original_line: Optional[str] = None):
        self.path: Path = Path(path)
        self.line: int = line
        self.original_line: Optional[str] = original_line

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self.path!r}, line={self.line}, original_line={self.original_line!r})"

    def __str__(self):
        return f"{self.path!s}:{self.line}"


class MatchContext:
    def __init__(self, data: bytes, path: Optional[Path] = None, only_match_mime: bool = False):
        self.data: bytes = data
        self.path: Optional[Path] = path
        self.only_match_mime: bool = only_match_mime

    def __getitem__(self, s: slice) -> "MatchContext":
        if not isinstance(s, slice):
            raise ValueError("Match contexts can only be sliced")
        return MatchContext(data=self.data[s], path=self.path, only_match_mime=self.only_match_mime)

    @property
    def is_executable(self) -> bool:
        if self.path is None:
            log.warning("Unable to determine if the input data is executable; assuming it is not.")
            return False
        try:
            return bool(self.path.stat().st_mode & 0o111)
        except FileNotFoundError:
            log.warning(f"Unable to determine if the data from {self.path} is executable; assuming it is not.")
            return False

    @staticmethod
    def load(stream_or_path: Union[str, Path, BinaryIO], only_match_mime: bool = False) -> "MatchContext":
        if isinstance(stream_or_path, str) or isinstance(stream_or_path, Path):
            with open(stream_or_path, "rb") as f:
                return MatchContext.load(f, only_match_mime)
        if hasattr(stream_or_path, "name") and stream_or_path.name is not None:
            path: Optional[Path] = Path(stream_or_path.name)
        else:
            path = None
        return MatchContext(stream_or_path.read(), path, only_match_mime)


class Message(ABC):
    @abstractmethod
    def resolve(self, context: MatchContext) -> str:
        raise NotImplementedError()

    @abstractmethod
    def possibilities(self) -> Iterator[str]:
        raise NotImplementedError()

    @staticmethod
    def parse(message: str) -> "Message":
        try:
            return TernaryExecutableMessage.parse(message)
        except ValueError:
            return ConstantMessage(message)


class ConstantMessage(Message):
    def __init__(self, message: str):
        self.message: str = message

    def possibilities(self) -> Iterator[str]:
        yield self.message

    def resolve(self, context: MatchContext) -> str:
        return self.message

    def __eq__(self, other):
        return isinstance(other, ConstantMessage) and other.message == self.message

    def __str__(self):
        return self.message


class TernaryMessage(Message, ABC):
    def __init__(self, true_value: str, false_value: str):
        self.true_value: str = true_value
        self.false_value: str = false_value

    def possibilities(self) -> Iterator[str]:
        yield self.true_value
        yield self.false_value

    def __eq__(self, other):
        return isinstance(other, TernaryMessage) and other.false_value == self.false_value and \
               other.true_value == self.true_value and other.__class__ == self.__class__


class TernaryExecutableMessage(TernaryMessage):
    def resolve(self, context: MatchContext) -> str:
        if context.is_executable:
            return self.true_value
        else:
            return self.false_value

    TERNARY_EXECUTABLE_PATTERN: Pattern[str] = re.compile(
        r"^(?P<before>.*?)\${x\?(?P<true>[^:]+):(?P<false>[^}]+)}(?P<after>.*)$"
    )

    @staticmethod
    def parse(message: str) -> "TernaryExecutableMessage":
        m = TernaryExecutableMessage.TERNARY_EXECUTABLE_PATTERN.match(message)
        if not m:
            raise ValueError(f"Invalid ternary message: {message!r}")
        before = m.group("before")
        after = m.group("after")
        true_msg = f"{before}{m.group('true')}{after}"
        false_msg = f"{before}{m.group('false')}{after}"
        return TernaryExecutableMessage(true_value=true_msg, false_value=false_msg)

    def __str__(self):
        return f"${{x?{self.true_value}:{self.false_value}}}"


TEST_TYPES: Set[Type["MagicTest"]] = set()

_UNIMPLEMENTED_TESTS: Set["MagicTest"] = set()
"""The tests that have already been reported as unimplemented, so each one is only logged once."""


class Comment:
    def __init__(self, message: str, source_info: Optional[SourceInfo] = None):
        self.message: str = message
        self.source_info: Optional[SourceInfo] = source_info

    def __str__(self):
        return self.message


class TestType(IntFlag):
    UNKNOWN = 0
    BINARY = 1
    TEXT = 2


class MagicTest(ABC):
    AUTO_REGISTER_TEST: bool = True

    def __init__(
            self,
            offset: Offset,
            mime: Optional[Union[str, TernaryExecutableMessage]] = None,
            extensions: Iterable[str] = (),
            message: Union[str, Message] = "",
            parent: Optional["MagicTest"] = None,
            comments: Iterable[Comment] = ()
    ):
        self.offset: Offset = offset
        self._mime: Optional[Message] = None
        self.extensions: Set[str] = set(extensions)
        if isinstance(message, Message):
            self._message: Message = message
        else:
            self._message = Message.parse(message)
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
        self.comments: Tuple[Comment, ...] = tuple(comments)
        self._type: TestType = TestType.UNKNOWN
        self.strength_op: StrengthOp = StrengthOp.NONE
        self.strength_factor: int = 0

    def __init_subclass__(cls, **kwargs):
        if cls.AUTO_REGISTER_TEST:
            TEST_TYPES.add(cls)
        return super().__init_subclass__(**kwargs)

    @property
    def message(self) -> Message:
        return self._message

    @message.setter
    def message(self, new_value: Message):
        self._message = new_value

    @property
    def test_type(self) -> TestType:
        if self._type == TestType.UNKNOWN:
            if hasattr(self, "__calculating_test_type") and getattr(self, "__calculating_test_type"):
                return TestType.UNKNOWN
            setattr(self, "__calculating_test_type", True)
            if self.can_be_indirect:
                # indirect tests can execute any other (binary) test, so classify ourselves as binary
                self._type = TestType.BINARY
            else:
                if any(bool(child.test_type & TestType.BINARY) for child in self.children):
                    self._type = TestType.BINARY
                else:
                    self._type = self.subtest_type()
                    if (self._type == TestType.UNKNOWN and self.children) or bool(self._type & TestType.TEXT):
                        # A pattern is considered to be a text test when all its patterns are text patterns;
                        # otherwise, it is considered to be a binary pattern.
                        if all(bool(child.test_type & TestType.TEXT) for child in self.children):
                            self._type = TestType.TEXT
                        else:
                            self._type = TestType.UNKNOWN
            delattr(self, "__calculating_test_type")
        return self._type

    @property
    def appends_text_encoding(self) -> bool:
        """Whether libmagic appends its text-encoding description to this test's message.

        The description comes from ``file_ascmagic``, which ``file_buffer`` reaches only after its
        binary soft magic pass printed nothing, so it lands on whatever the ``TEXTTEST`` soft magic
        pass printed (``src/funcs.c`` and ``src/ascmagic.c``). ``set_test_type`` in
        ``src/apprentice.c`` decides which pass a definition runs in from the type and flags of its
        level 0 test alone, and that is what `subtest_type` reports. `test_type`, which chooses the
        pass PolyFile itself runs the test in, cannot answer this: it reports a group with any
        binary subtest as binary, which is why libmagic describes the encoding of
        ``file/tests/pnm1.testfile`` while PolyFile matches it in its binary pass.

        Returns:
            True if libmagic would append the description to this test's message.
        """
        return bool(self.subtest_type() & TestType.TEXT)

    @test_type.setter
    def test_type(self, value: TestType):
        if self._type != TestType.UNKNOWN:
            if value != self._type:
                raise ValueError(f"Cannot assign type {value} to test {self} because it already has value {value}")
        else:
            self._type = value

    @abstractmethod
    def subtest_type(self) -> TestType:
        raise NotImplementedError()

    def type_strength(self) -> int:
        """The term this test's type contributes to its strength.

        libmagic grows the term with how much of the file the type inspects, so a wider integer or
        a longer string outranks a narrower one (``file/src/apprentice.c:930-1030``). The types
        that only dispatch another test — ``indirect``, ``name``, ``use``, and ``clear`` — add
        nothing.

        Returns:
            The number to add to the baseline strength.
        """
        return 0

    def relation(self) -> str:
        """The relational operator libmagic parsed for this test.

        Every type takes an operator from the head of its value, defaulting to ``=`` when the value
        names none (``file/src/apprentice.c:2366-2401``).

        Returns:
            One of ``=``, ``<``, ``>``, ``&``, ``^``, ``!``, or ``x``.
        """
        return "="

    def base_strength(self) -> int:
        """Computes the base strength value before applying !:strength modifier.

        This is libmagic's ``apprentice_magic_strength_1``
        (``file/src/apprentice.c:925-1058``): a fixed baseline plus a term for the type, then
        adjusted by the relational operator. A relation that matches anything discards both terms.

        Returns:
            The strength before the ``!:strength`` factor, the clamp, and the description bonus.
        """
        rel = self.relation()
        if rel in UNSELECTIVE_RELATIONS:
            return 0
        return STRENGTH_BASELINE + self.type_strength() + RELATION_STRENGTH[rel]

    def compute_strength(self) -> int:
        """Computes the test strength for sorting, mimicking libmagic's algorithm.

        This is libmagic's ``file_magic_strength`` (``file/src/apprentice.c:1064-1120``): the base
        strength, then the ``!:strength`` factor, then a clamp to a positive value, and finally a
        bonus for a test with no description, which depends on its children to print anything.

        A description made only of blanks counts as absent, because libmagic skips the blanks
        between the value and the description before it copies what remains
        (``file/src/apprentice.c:2425-2436``).

        Returns:
            The sort key libmagic would use for this test.
        """
        val = self.base_strength()
        if self.strength_op == StrengthOp.PLUS:
            val += self.strength_factor
        elif self.strength_op == StrengthOp.MINUS:
            val -= self.strength_factor
        elif self.strength_op == StrengthOp.TIMES:
            val *= self.strength_factor
        elif self.strength_op == StrengthOp.DIV and self.strength_factor != 0:
            val //= self.strength_factor
        if val <= 0:
            val = 1
        if not str(self.message).strip():
            val += 1
        return val

    def libmagic_type(self) -> str:
        """Names the type libmagic stores in this test's ``struct magic``.

        Returns:
            A key of `LIBMAGIC_TYPE_CODES`.
        """
        return "invalid"

    def libmagic_flag(self) -> int:
        """The ``flag`` word libmagic would give this test.

        Returns:
            The bits named in `FLAG_INDIR` and its neighbors.
        """
        flag, _, _ = libmagic_offset_fields(self.offset)
        if str(self.message).startswith("\b"):
            flag |= FLAG_NOSPACE
        return flag

    def libmagic_value_fields(self) -> Tuple[int, bytes, bytes]:
        """The fields of libmagic's ``struct magic`` that hold this test's value.

        Returns:
            The value's length in bytes, the eight bytes that carry ``str_range`` and
            ``str_flags``, and the value itself.
        """
        return 0, bytes(8), b""

    def libmagic_sort_key(self) -> Tuple[Any, ...]:
        """The key that orders this test the way libmagic's ``apprentice_sort`` would.

        libmagic sorts by descending strength and settles a tie by comparing the two entries'
        ``struct magic`` bytes with ``memcmp``, putting the greater one first
        (``file/src/apprentice.c:1126-1152``). This key repeats that comparison over the fields
        that decide it, in the order they sit in memory, so a descending sort by the key
        reproduces libmagic's order.

        The key stops at the value. ``desc``, ``mimetype``, ``apple``, and ``ext`` follow it in
        the struct, but libmagic writes a definition file's name into an empty ``desc``
        (``file/src/apprentice.c:2438``) and PolyFile has already unescaped the description, so
        neither compares byte for byte. ``in_op``, ``mask_op``, and ``in_offset`` are skipped
        because PolyFile folds each of them into a callable instead of keeping the number.

        Returns:
            A tuple to sort by in descending order.
        """
        value_length, string_flags, value = self.libmagic_value_fields()
        _, offset, indirect_type = libmagic_offset_fields(self.offset)
        return (
            self.compute_strength(),
            libmagic_field(self.libmagic_flag(), 2),
            libmagic_field(self.strength_factor, 1),
            libmagic_field(ord(self.relation()), 1),
            libmagic_field(value_length, 1),
            libmagic_field(LIBMAGIC_TYPE_CODES[self.libmagic_type()], 1),
            libmagic_field(LIBMAGIC_TYPE_CODES[indirect_type], 1),
            libmagic_field(ord(self.strength_op.value or "\0"), 1),
            libmagic_field(offset, 4),
            string_flags,
            value.ljust(MAX_STRING_BYTES, b"\0")[:MAX_STRING_BYTES],
        )

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

    def _compute_descendants(self) -> Tuple["MagicTest", ...]:
        """Compute all descendants of this test (internal, called once)."""
        result: List[MagicTest] = []
        stack: List[MagicTest] = [self]
        history: Set[MagicTest] = set(stack)
        while stack:
            test = stack.pop()
            if test is not self:
                result.append(test)
            new_tests = [child for child in test.children if child not in history]
            stack.extend(reversed(new_tests))
            history |= set(new_tests)
            if isinstance(test, UseTest):
                stack.append(test.referenced_test)
                history.add(test.referenced_test)
        return tuple(result)

    @functools.cached_property
    def descendants(self) -> Tuple["MagicTest", ...]:
        """
        Returns all descendants of this test (cached).
        UseTests will also include all referenced NamedTests and their descendants.

        """
        return self._compute_descendants()

    def referenced_tests(self) -> Set["NamedTest"]:
        result: Set[NamedTest] = set()
        for child in self.children:
            result |= child.referenced_tests()
        return result

    @property
    def mime(self) -> Optional[Message]:
        return self._mime

    @mime.setter
    def mime(self, new_mime: Optional[Union[str, Message]]):
        if isinstance(new_mime, str):
            new_mime = Message.parse(new_mime)
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
            yielded |= set(self.mime.possibilities())
            yield from yielded
        for d in self.descendants:
            if d.mime is not None:
                possibilities = set(d.mime.possibilities())
                new_mimes = possibilities - yielded
                yield from new_mimes
                yielded |= new_mimes

    @functools.cached_property
    def mimetypes(self) -> Tuple[str, ...]:
        """Returns all possible MIME types that this test or any of its descendants could match against"""
        return tuple(self._mimetypes())

    def _all_extensions(self) -> Iterator[str]:
        """Yields all possible extensions that this test or any of its descendants could match against"""
        yield from self.extensions
        yielded = set(self.extensions)
        for d in self.descendants:
            new_extensions = d.extensions - yielded
            yield from new_extensions
            yielded |= new_extensions

    @functools.cached_property
    def all_extensions(self) -> Tuple[str, ...]:
        """Returns all possible extensions that this test or any of its descendants could match against"""
        return tuple(self._all_extensions())

    def test_flip_endianness(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        raise NotImplementedError(f"TODO: Implement test_flip_endianness for {self.__class__.__name__}")

    @abstractmethod
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        raise NotImplementedError()

    def write(self, writer: ANSIWriter, is_current_test: bool = False, pre_mime_text: str = "") -> str:
        for comment in self.comments:
            if comment.source_info is not None and comment.source_info.original_line is not None:
                writer.write(f"  {comment.source_info.path.name}", dim=True, color=ANSIColor.CYAN)
                writer.write(":", dim=True)
                writer.write(f"{comment.source_info.line}\t", dim=True, color=ANSIColor.CYAN)
                writer.write(comment.source_info.original_line.strip(), dim=True)
                writer.write("\n")
            else:
                writer.write(f"  # {comment!s}\n", dim=True)
        if is_current_test:
            writer.write("→ ", bold=True)
        else:
            writer.write("  ")
        if self.source_info is not None and self.source_info.original_line is not None:
            source_prefix = f"{self.source_info.path.name}:{self.source_info.line}"
            indent = f"{' ' * len(source_prefix)}\t"
            writer.write(self.source_info.path.name, dim=True, color=ANSIColor.CYAN)
            writer.write(":", dim=True)
            writer.write(self.source_info.line, dim=True, color=ANSIColor.CYAN)
            writer.write("\t")
            writer.write(self.source_info.original_line.strip(), color=ANSIColor.BLUE, bold=True)
        else:
            indent = ""
            writer.write(f"{'>' * self.level}{self.offset!s}\t")
            writer.write(self.message, color=ANSIColor.BLUE, bold=True)
        if self.level == 0:
            if self.test_type & TestType.BINARY:
                writer.write(f" \uF5BB BINARY TEST", color=ANSIColor.BLUE)
            elif self.test_type & TestType.TEXT:
                writer.write(f" \uF5B9 ASCII TEST", color=ANSIColor.BLUE)
        writer.write(pre_mime_text)
        if self.mime is not None:
            writer.write(f"\n  {indent}!:mime ", dim=True)
            writer.write(self.mime, color=ANSIColor.BLUE)
        for e in self.extensions:
            writer.write(f"\n  {indent}!:ext  ", dim=True)
            writer.write(str(e), color=ANSIColor.BLUE)
        writer.write("\n")
        return f"  {indent}"

    def calculate_absolute_offset(self, data: bytes, parent_match: Optional[TestResult] = None) -> int:
        return self.offset.to_absolute(data, parent_match)

    def _run_test(
            self,
            context: MatchContext,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            flip_endianness: bool
    ) -> TestResult:
        """Runs this test, treating a test that is not implemented as a non-match.

        A definition file can name a test that PolyFile does not implement yet. Reporting that as a
        failure keeps the omission out of the caller's exception path, where it would abort an
        otherwise successful match.
        """
        try:
            if flip_endianness:
                return self.test_flip_endianness(context.data, absolute_offset, parent_match)
            return self.test(context.data, absolute_offset, parent_match)
        except NotImplementedError as e:
            if self not in _UNIMPLEMENTED_TESTS:
                _UNIMPLEMENTED_TESTS.add(self)
                log.warning(f"{self.source_info!s}: {e!s}")
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message=str(e))

    def _match(
            self,
            context: MatchContext,
            parent_match: Optional[TestResult] = None,
            flip_endianness: bool = False
    ) -> Iterator[MatchedTest]:
        if context.only_match_mime and not self.can_match_mime:
            return
        try:
            absolute_offset = self.calculate_absolute_offset(context.data, parent_match)
        except InvalidOffsetError:
            return
        m = self._run_test(context, absolute_offset, parent_match, flip_endianness)
        if logging.root.level <= TRACE and (bool(m) or self.level > 0):
            log.trace(
                f"{self.source_info!s}\t{bool(m)}\t{absolute_offset}\t"
                f"{context.data[absolute_offset:absolute_offset + 20]!r}"
            )
        if bool(m):
            if not context.only_match_mime or self.mime is not None:
                yield m
            for child in self.children:
                if not context.only_match_mime or child.can_match_mime:
                    yield from child._match(context=context, parent_match=m, flip_endianness=flip_endianness)

    def match(self, to_match: Union[bytes, BinaryIO, str, Path, MatchContext]) -> Iterator[TestResult]:
        """Yields all matches for the given data"""
        if isinstance(to_match, bytes):
            to_match = MatchContext(data=to_match)
        elif not isinstance(to_match, MatchContext):
            to_match = MatchContext.load(to_match)
        return self._match(to_match)

    def __str__(self):
        if self.source_info is not None and self.source_info.original_line is not None:
            s = f"{self.source_info.path.name}:{self.source_info.line} {self.source_info.original_line.strip()}"
        else:
            s = f"{'>' * self.level}{self.offset!s}\t{self.message}"
        if self.mime is not None:
            s = f"{s}\n!:mime\t{self.mime}"
        for e in self.extensions:
            s = f"{s}\n!:ext\t{e}"
        return s


class DynamicMagicTest(MagicTest, ABC):
    """A test that can be bound with a dynamically generated message"""

    def __init__(
            self,
            offset: Offset,
            mime: Optional[Union[str, TernaryExecutableMessage]] = None,
            extensions: Iterable[str] = (),
            default_message: Union[str, Message] = "",
            parent: Optional["MagicTest"] = None,
            comments: Iterable[Comment] = ()
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, parent=parent, comments=comments,
                         message=default_message)
        self._bound_message: Optional[Message] = None

    @property
    def default_message(self) -> Message:
        return super().message

    @property
    def message(self) -> Message:
        if self._bound_message is None:
            return self.default_message
        else:
            return self._bound_message

    def bind(self, message: Union[str, Message]) -> MagicTest:
        if self._bound_message is not None:
            raise ValueError(f"{self!r} already has a bound message: {self.message!s}")
        elif not isinstance(message, Message):
            message = Message.parse(message)
        result: DynamicMagicTest = type(f"Bound{self.__class__.__name__}", (self.__class__,), dict(self.__dict__))()
        result._bound_message = message
        return result


TYPES_BY_NAME: Dict[str, "DataType"] = {}


T = TypeVar("T")


class DataTypeMatch:
    """The portion of the tested data that a :class:`DataType` matched.

    Attributes:
        raw_match: The bytes that matched, or `None` if the data type did not match.
        value: The value to interpolate into the message of the test that matched.
        initial_offset: The offset of `raw_match` within the data that was tested.
        relative_base: The offset within the tested data that a subsequent relative (`&`) offset
            resolves against, or `None` to resolve against the end of `raw_match`.
    """

    INVALID: "DataTypeMatch"

    def __init__(
            self,
            raw_match: Optional[bytes] = None,
            value: Optional[Any] = None,
            initial_offset: int = 0,
            relative_base: Optional[int] = None
    ):
        self.raw_match: Optional[bytes] = raw_match
        if value is None and raw_match is not None:
            self.value: Optional[bytes] = raw_match
        else:
            self.value = value
        self.initial_offset: int = initial_offset
        self.relative_base: Optional[int] = relative_base

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

    def allows_invalid_offsets(self, expected: T) -> bool:
        return False

    def strength_term(self, expected: T) -> int:
        """The term this type contributes to a test's strength.

        Args:
            expected: The value the test compares against, which sizes the term for the types
                whose values vary in length.

        Returns:
            The number to add to the baseline strength.
        """
        return 0

    def relation(self, expected: T) -> str:
        """The relational operator that `expected` carried in the definition.

        Args:
            expected: The parsed value, which records the operator it was declared with.

        Returns:
            One of ``=``, ``<``, ``>``, ``&``, ``^``, ``!``, or ``x``.
        """
        return "="

    @abstractmethod
    def is_text(self, value: T) -> bool:
        raise NotImplementedError()

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
        elif fmt == "lestring16" or fmt.startswith("lestring16/"):
            num_bytes = None
            if fmt.startswith("lestring16/"):
                num_bytes = int(fmt[11:])
            dt = UTF16Type(endianness=Endianness.LITTLE, num_bytes=num_bytes)
        elif fmt == "bestring16" or fmt.startswith("bestring16/"):
            num_bytes = None
            if fmt.startswith("bestring16/"):
                num_bytes = int(fmt[11:])
            dt = UTF16Type(endianness=Endianness.BIG, num_bytes=num_bytes)
        elif fmt.startswith("pstring"):
            dt = PascalStringType.parse(fmt)
        elif fmt.startswith("search"):
            dt = SearchType.parse(fmt)
        elif fmt.startswith("regex"):
            dt = RegexType.parse(fmt)
        elif fmt in ("guid", "leguid", "beguid"):
            if fmt == "beguid":
                dt = GUIDType(endianness=Endianness.BIG)
            else:
                dt = GUIDType(endianness=Endianness.LITTLE)
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
    # NOTE: libmagic renders `guid` and its `leguid` alias with the first three fields byte-swapped,
    #       the mixed-endian layout Microsoft uses, and `beguid` with the bytes in file order.
    #       See file_print_guid and file_print_beguid in libmagic's src/funcs.c.
    def __init__(self, endianness: Endianness = Endianness.LITTLE):
        if endianness == Endianness.LITTLE:
            super().__init__("guid")
        elif endianness == Endianness.BIG:
            super().__init__("beguid")
        else:
            raise ValueError(f"GUIDs only support big and little endianness, not {endianness!r}")
        self.endianness: Endianness = endianness

    def is_text(self, value: Union[UUID, UUIDWildcard]) -> bool:
        return False

    def strength_term(self, expected: Union[UUID, UUIDWildcard]) -> int:
        """A GUID is sized like the sixteen-byte integer it is (``file/src/apprentice.c:912-915``)."""
        return 16 * STRENGTH_MULT

    def relation(self, expected: Union[UUID, UUIDWildcard]) -> str:
        return "x" if isinstance(expected, UUIDWildcard) else "="

    def parse_expected(self, specification: str) -> Union[UUID, UUIDWildcard]:
        if specification.strip() == "x":
            return UUIDWildcard()
        # there is a bug in the `asf` definition where a guid is missing its last two characters:
        if specification.strip().upper() == "B61BE100-5B4E-11CF-A8FD-00805F5C44":
            specification = "B61BE100-5B4E-11CF-A8FD-00805F5C442B"
        return UUID(str(specification.strip()))

    def match(self, data: bytes, expected: Union[UUID, UUIDWildcard]) -> DataTypeMatch:
        if len(data) < 16:
            return DataTypeMatch.INVALID
        try:
            if self.endianness == Endianness.BIG:
                uuid = UUID(bytes=data[:16])
            else:
                uuid = UUID(bytes_le=data[:16])
        except ValueError:
            return DataTypeMatch.INVALID
        if isinstance(expected, UUIDWildcard) or uuid == expected:
            return DataTypeMatch(data[:16], uuid)
        else:
            return DataTypeMatch.INVALID


class UTF16Type(DataType[bytes]):
    def __init__(self, endianness: Endianness, num_bytes: Optional[int] = None):
        name = "lestring16" if endianness == Endianness.LITTLE else "bestring16"
        if num_bytes is not None:
            name = f"{name}/{num_bytes}"
        if endianness not in (Endianness.LITTLE, Endianness.BIG):
            raise ValueError(f"UTF16 strings only support big and little endianness, not {endianness!r}")
        super().__init__(name)
        self.endianness: Endianness = endianness
        self.num_bytes: Optional[int] = num_bytes

    def is_text(self, value: bytes) -> bool:
        return True

    def strength_term(self, expected: bytes) -> int:
        """Half of what the same value would score as a `string` (``file/src/apprentice.c:1003``).

        libmagic stores a sixteen-bit string's value as the bytes the definition spelled and widens
        it only when matching, so its ``vallen`` counts characters, not the code units PolyFile
        holds here.
        """
        return len(expected) // 2 * STRENGTH_MULT // 2

    def parse_expected(self, specification: str) -> bytes:
        specification = unescape(specification).decode("utf-8")
        if self.endianness == Endianness.LITTLE:
            return specification.encode("utf-16-le")
        else:
            return specification.encode("utf-16-be")

    def match(self, data: bytes, expected: bytes) -> DataTypeMatch:
        if self.num_bytes is not None:
            data = data[:self.num_bytes]
        if data.startswith(expected):
            if self.endianness == Endianness.LITTLE:
                return DataTypeMatch(expected, expected.decode("utf-16-le"))
            else:
                return DataTypeMatch(expected, expected.decode("utf-16-be"))
        else:
            return DataTypeMatch.INVALID


class StringTest(ABC):
    def __init__(self, trim: bool = False, compact_whitespace: bool = False, num_bytes: Optional[int] = None):
        self.trim: bool = trim
        self.compact_whitespace: bool = compact_whitespace
        self.num_bytes: Optional[int] = num_bytes

    @property
    def value_length(self) -> int:
        """The number of unescaped bytes in this test's value, libmagic's ``m->vallen``.

        libmagic reads no value at all for the ``x`` relation, so a wildcard has none
        (``file/src/apprentice.c:2409``).

        Returns:
            The length that sizes this test's strength term.
        """
        return 0

    @property
    def relation(self) -> str:
        """The relational operator this test was declared with.

        Returns:
            One of ``=``, ``<``, ``>``, ``!``, or ``x``.
        """
        return "x"

    def post_process(self, data: bytes, initial_offset: int = 0) -> DataTypeMatch:
        value = data
        # if self.compact_whitespace:
        #     value = b"".join(c for prev, c in zip(b"\0" + data, data) if c not in WHITESPACE or prev not in WHITESPACE)
        if self.trim:
            value = value.strip()
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            pass
        return DataTypeMatch(data, value, initial_offset=initial_offset)

    @abstractmethod
    def matches(self, data: bytes) -> DataTypeMatch:
        raise NotImplementedError()

    @abstractmethod
    def is_always_text(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def search(self, data: bytes) -> DataTypeMatch:
        raise NotImplementedError()

    @staticmethod
    def parse(specification: str,
              trim: bool = False,
              compact_whitespace: bool = False,
              case_insensitive_lower: bool = False,
              case_insensitive_upper: bool = False,
              optional_blanks: bool = False,
              full_word_match: bool = False,
              num_bytes: Optional[int] = None) -> "StringTest":
        if specification.strip() == "x":
            return StringWildcard(trim=trim, compact_whitespace=compact_whitespace, num_bytes=num_bytes)
        if specification.startswith("!"):
            negate = True
            specification = specification[1:]
        else:
            negate = False
        if specification.startswith(">") or specification.startswith("<"):
            test = StringLengthTest(
                to_match=specification[1:],
                test_smaller=specification.startswith("<"),
                trim=trim,
                compact_whitespace=compact_whitespace,
                num_bytes=num_bytes,
            )
        else:
            if specification.startswith("="):
                specification = specification[1:]
            test = StringMatch(
                to_match=specification,
                trim=trim,
                compact_whitespace=compact_whitespace,
                case_insensitive_lower=case_insensitive_lower,
                case_insensitive_upper=case_insensitive_upper,
                optional_blanks=optional_blanks,
                full_word_match=full_word_match,
                num_bytes=num_bytes
            )
        if negate:
            return NegatedStringTest(test)
        else:
            return test


class StringWildcard(StringTest):
    def value_end(self, data: bytes, max_bytes: Optional[int] = None) -> int:
        """Finds the length of the value that libmagic would read from the head of `data`.

        A wildcard value ends at the first null byte, carriage return, or line feed, whichever
        comes first (``file/src/softmagic.c:683-684`` and ``909-910``).

        Args:
            data: The bytes at the offset being tested.
            max_bytes: The most bytes to read, if the type or the buffer bounds it.

        Returns:
            The number of bytes of `data` that make up the value.
        """
        end = len(data) if max_bytes is None else min(max_bytes, len(data))
        terminator = VALUE_TERMINATOR.search(data, 0, end)
        if terminator is None:
            return end
        return terminator.start()

    def matches(self, data: bytes) -> DataTypeMatch:
        if self.num_bytes is None:
            max_bytes = MAX_STRING_BYTES
        else:
            max_bytes = min(self.num_bytes, MAX_STRING_BYTES)
        return self.post_process(data[:self.value_end(data, max_bytes)])

    def is_always_text(self) -> bool:
        return False

    def search(self, data: bytes) -> DataTypeMatch:
        """Reads the value that a `search` test reports.

        `num_bytes` bounds the start offsets a search tries, not the extent of the value it
        yields, and a search reads the buffer in place rather than copying it into libmagic's
        128-byte value union (``file/src/softmagic.c:1389-1395``), so neither bound applies here.

        Args:
            data: The bytes at the offset being tested.

        Returns:
            The value, ending at the first null byte, carriage return, or line feed.
        """
        return self.post_process(data[:self.value_end(data)])

    def __str__(self):
        return "null-terminated string"


class NegatedStringTest(StringWildcard):
    def __init__(self, parent_test: StringTest):
        super().__init__(trim=parent_test.trim, compact_whitespace=parent_test.compact_whitespace)
        self.parent: StringTest = parent_test

    @property
    def value_length(self) -> int:
        return self.parent.value_length

    @property
    def relation(self) -> str:
        return "!"

    def is_always_text(self) -> bool:
        return self.parent.is_always_text()

    def matches(self, data: bytes) -> DataTypeMatch:
        result = self.parent.matches(data)
        if result == DataTypeMatch.INVALID:
            return super().matches(data)
        else:
            return DataTypeMatch.INVALID

    def search(self, data: bytes) -> DataTypeMatch:
        result = self.parent.search(data)
        if result == DataTypeMatch.INVALID:
            return super().search(data)
        else:
            return DataTypeMatch.INVALID

    def __str__(self):
        return f"something other than {self.parent!s}"


class StringLengthTest(StringWildcard):
    def __init__(self, to_match: str, test_smaller: bool, trim: bool = False, compact_whitespace: bool = False,
                 num_bytes: Optional[int] = None):
        super().__init__(trim=trim, compact_whitespace=compact_whitespace, num_bytes=num_bytes)
        self.raw_pattern: str = to_match
        self.to_match: bytes = unescape(to_match)
        self._value_length: int = len(self.to_match)
        null_termination_index = self.to_match.find(0)
        if null_termination_index >= 0:
            self.to_match = self.to_match[:null_termination_index]
        self.desired_length: int = len(self.to_match)
        self.test_smaller: bool = test_smaller

    @property
    def value_length(self) -> int:
        """The declared length, which libmagic counts past an embedded null byte."""
        return self._value_length

    @property
    def relation(self) -> str:
        return "<" if self.test_smaller else ">"

    def matches(self, data: bytes) -> DataTypeMatch:
        match = super().matches(data)
        if self.desired_length == 0:
            return match
        elif self.test_smaller and match.raw_match[:self.desired_length] < self.to_match:
            return match
        elif not self.test_smaller and match.raw_match[:self.desired_length] > self.to_match:
            return match
        else:
            return DataTypeMatch.INVALID

    def is_always_text(self) -> bool:
        return False

    def search(self, data: bytes) -> DataTypeMatch:
        match = super().search(data)
        if self.test_smaller and match.raw_match < self.to_match:
            return match
        elif not self.test_smaller and match.raw_match > self.to_match:
            return match
        else:
            return DataTypeMatch.INVALID

    def __repr__(self):
        return f"{self.__class__.__name__}(to_match={self.raw_pattern!r}, test_smaller={self.test_smaller!r}, " \
               f"trim={self.trim!r}, compact_whitespace={self.compact_whitespace!r}, num_bytes={self.num_bytes!r})"

    def __str__(self):
        return f"{['>', '<'][self.test_smaller]}{repr(self.to_match)}"


class StringMatch(StringTest):
    def __init__(self,
                 to_match: str,
                 trim: bool = False,
                 compact_whitespace: bool = False,
                 case_insensitive_lower: bool = False,
                 case_insensitive_upper: bool = False,
                 optional_blanks: bool = False,
                 full_word_match: bool = False,
                 num_bytes: Optional[int] = None
    ):
        super().__init__(trim=trim, compact_whitespace=compact_whitespace, num_bytes=num_bytes)
        self.raw_pattern: str = to_match
        self.string: bytes = unescape(to_match)
        self.case_insensitive_lower: bool = case_insensitive_lower
        self.case_insensitive_upper: bool = case_insensitive_upper
        self.optional_blanks: bool = optional_blanks
        self.full_word_match: bool = full_word_match
        self._is_always_text: Optional[bool] = None
        self._pattern: Optional[re.Pattern] = None
        _ = self.pattern

    @property
    def value_length(self) -> int:
        return len(self.string)

    @property
    def relation(self) -> str:
        return "="

    def pattern_string(self) -> bytes:
        """Builds the regular expression that implements this test's string flags.

        A definition may set both ``W`` (compact whitespace) and ``w`` (optional blanks);
        ``polyfile/magic_defs/sgml`` does. libmagic keeps both bits and lets ``W`` win, because
        ``file_strncmp`` tests it first (``file/src/softmagic.c:2103-2120``).

        Returns:
            The pattern to compile, with the flags folded into it.
        """
        pattern = re.escape(self.string)
        if self.case_insensitive_lower and not self.case_insensitive_upper:
            # treat lower case letters as either lower or upper case
            delta = ord('A') - ord('a')
            for ordinal in range(ord('a'), ord('z') + 1):
                pattern = pattern.replace(bytes([ordinal]), f"[{chr(ordinal)}{chr(ordinal+delta)}]".encode("utf-8"))
        elif not self.case_insensitive_lower and self.case_insensitive_upper:
            # treat upper case letters as either lower or upper case
            delta = ord('a') - ord('A')
            for ordinal in range(ord('A'), ord('Z') + 1):
                pattern = pattern.replace(bytes([ordinal]), f"[{chr(ordinal)}{chr(ordinal+delta)}]".encode("utf-8"))
        if self.compact_whitespace:
            new_pattern_bytes: List[Tuple[bytes, int]] = []
            escaped = False
            for c in (bytes([b]) for b in pattern):
                if escaped:
                    c = b"\\" + c
                    escaped = False
                elif c == b"\\":
                    escaped = True
                    continue
                if new_pattern_bytes and new_pattern_bytes[-1][0] == c:
                    new_pattern_bytes[-1] = (c, new_pattern_bytes[-1][1] + 1)
                else:
                    new_pattern_bytes.append((c, 1))
            if escaped:
                raise ValueError(f"Error parsing search pattern {self.string!r}")
            pattern_bytes = bytearray()
            for c, count in new_pattern_bytes:
                pattern_bytes.extend(c)
                if c in (b'\\ ', b'\\s', b'\\t', b'\\r', b'\\v', b'\\f'):
                    # this is whitespace
                    if count == 1:
                        pattern_bytes.extend(b"+")
                    else:
                        pattern_bytes.extend(f"{{{count},}}".encode("utf-8"))
                elif count > 1:
                    pattern_bytes.extend(f"{{{count}}}".encode("utf-8"))
            pattern = bytes(pattern_bytes)
        elif self.optional_blanks:
            pattern = BLANK_IN_PATTERN.sub(rb"\\s*", pattern)
        if self.full_word_match:
            pattern = rb"\b" + pattern + rb"\b"
        return pattern

    def pattern_flags(self) -> int:
        flags: int = 0
        if self.case_insensitive_upper and self.case_insensitive_lower:
            flags |= re.IGNORECASE
        return flags

    @property
    def pattern(self) -> re.Pattern:
        if self._pattern is None:
            self._pattern = re.compile(self.pattern_string(), flags=self.pattern_flags())
        return self._pattern

    def is_always_text(self) -> bool:
        r"""Whether libmagic classifies a test looking for this value as a text test.

        libmagic decides from ``file_looks_utf8`` over the value it unescaped while parsing the
        definition (``file/src/apprentice.c:1277-1283``), so an escaped space is a space rather
        than a null byte: ``\040`` is text, and only a genuine control character or a byte
        sequence that is not valid UTF-8 makes the value binary.

        Returns:
            True if the unescaped value is valid UTF-8 made only of text characters.
        """
        if self._is_always_text is None:
            self._is_always_text = _looks_like_utf8(self.string)
        return self._is_always_text

    def matches(self, data: bytes) -> DataTypeMatch:
        if self.num_bytes is not None:
            data = data[:self.num_bytes]
        m = self.pattern.match(data)
        if m:
            return self.post_process(bytes(m.group(0)))
        return DataTypeMatch.INVALID

    def search(self, data: bytes) -> DataTypeMatch:
        if self.num_bytes is None:
            end_pos = len(data)
        else:
            # libmagic tries `num_bytes` successive start offsets, so the window it reads is that
            # many bytes plus the length of the string it is looking for
            end_pos = min(len(data), self.num_bytes + len(self.string))
        m = self.pattern.search(data, 0, end_pos)
        if m:
            return self.post_process(bytes(m.group(0)), initial_offset=m.start())
        return DataTypeMatch.INVALID

    def __str__(self):
        return repr(self.string)


class StringType(DataType[StringTest]):
    def __init__(
            self,
            case_insensitive_lower: bool = False,
            case_insensitive_upper: bool = False,
            compact_whitespace: bool = False,
            optional_blanks: bool = False,
            full_word_match: bool = False,
            trim: bool = False,
            force_text: bool = False,
            num_bytes: Optional[int] = None
    ):
        if not any((num_bytes is not None, case_insensitive_lower, case_insensitive_upper, compact_whitespace,
                    optional_blanks, trim, force_text)):
            name = "string"
        else:
            if num_bytes is not None:
                name = f"{num_bytes}/"
            else:
                name = ""
            name = f"string/{name}{['', 'W'][compact_whitespace]}{['', 'w'][optional_blanks]}"\
                   f"{['', 'C'][case_insensitive_upper]}{['', 'c'][case_insensitive_lower]}"\
                   f"{['', 'T'][trim]}{['', 'f'][full_word_match]}{['', 't'][force_text]}"
        super().__init__(name)
        self.case_insensitive_lower: bool = case_insensitive_lower
        self.case_insensitive_upper: bool = case_insensitive_upper
        self.compact_whitespace: bool = compact_whitespace
        self.optional_blanks: bool = optional_blanks
        self.full_word_match: bool = full_word_match
        self.trim: bool = trim
        self.force_text: bool = force_text
        self.num_bytes: Optional[int] = num_bytes

    def is_text(self, value: StringTest) -> bool:
        return self.force_text

    def strength_term(self, expected: StringTest) -> int:
        """One unit per byte of the value, the dominant term for most definitions.

        See ``file/src/apprentice.c:998-1000``.
        """
        return expected.value_length * STRENGTH_MULT

    def relation(self, expected: StringTest) -> str:
        return expected.relation

    def allows_invalid_offsets(self, expected: StringTest) -> bool:
        return isinstance(expected, NegatedStringTest)

    def parse_expected(self, specification: str) -> StringTest:
        return StringTest.parse(
            specification,
            trim=self.trim,
            case_insensitive_lower=self.case_insensitive_lower,
            case_insensitive_upper=self.case_insensitive_upper,
            compact_whitespace=self.compact_whitespace,
            optional_blanks=self.optional_blanks,
            full_word_match=self.full_word_match,
            num_bytes=self.num_bytes
        )

    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
        return expected.matches(data)

    STRING_TYPE_FORMAT: Pattern[str] = re.compile(r"^u?string(/(?P<numbytes>\d+))?(?P<opts>/[BbCctTWwf]*)?$")

    @classmethod
    def parse(cls, format_str: str) -> "StringType":
        m = cls.STRING_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid string type declaration: {format_str!r}")
        if m.group("numbytes") is None:
            num_bytes: Optional[int] = None
        else:
            num_bytes = int(m.group("numbytes"))
        if m.group("opts") is None:
            options: Iterable[str] = ()
        else:
            options = m.group("opts")
        unsupported_options = {opt for opt in options if opt not in "/WwcCtbTf"}
        if unsupported_options:
            log.warning(f"{format_str!r} has invalid option(s) that will be ignored: {', '.join(unsupported_options)}")
        return StringType(
            case_insensitive_lower="c" in options,
            case_insensitive_upper="C" in options,
            compact_whitespace="W" in options,
            optional_blanks="w" in options,
            full_word_match="f" in options,
            trim="T" in options,
            force_text="t" in options,
            num_bytes=num_bytes
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
            full_word_match: bool = False,
            trim: bool = False,
            force_binary: bool = False
    ):
        if repetitions is not None and repetitions <= 0:
            raise ValueError("repetitions must be either None or a positive integer")
        super().__init__(
            case_insensitive_lower=case_insensitive_lower,
            case_insensitive_upper=case_insensitive_upper,
            compact_whitespace=compact_whitespace,
            optional_blanks=optional_blanks,
            full_word_match=full_word_match,
            trim=trim
        )
        self.num_bytes = repetitions
        if repetitions is None:
            rep_str = ""
        else:
            rep_str = f"/{repetitions}"
        assert self.name.startswith("string")
        self.name = f"search{rep_str}{self.name[6:]}"
        self.match_to_start: bool = match_to_start
        self.force_binary: bool = force_binary
        if match_to_start:
            self._name_flag("s", rep_str)
        if force_binary:
            self._name_flag("b", rep_str)

    def _name_flag(self, flag: str, rep_str: str) -> None:
        """Records `flag` in this type's name, opening the flag group if it is the first one.

        `DataType.parse` keys its cache of parsed types on the name, so a flag left out of the
        name would make a declaration that carries it share an instance with one that does not.

        Args:
            flag: The declaration letter of the flag.
            rep_str: The repetition count as it appears in the name, or an empty string.
        """
        if self.name == f"search{rep_str}":
            self.name = f"search{rep_str}/{flag}"
        else:
            self.name = f"{self.name}{flag}"

    @property
    def repetitions(self) -> Optional[int]:
        """The number of start offsets libmagic tries, from the ``search/N`` declaration.

        Returns:
            The value of ``N``, or ``None`` if the declaration omitted it, in which case the
            whole buffer is searched.
        """
        return self.num_bytes

    def is_text(self, value: StringTest) -> bool:
        """Whether libmagic runs a search for `value` in its text pass.

        An explicit ``b`` flag decides on its own: ``set_test_type`` sets ``BINTEST`` from the
        declared string flags and breaks out of the case before it ever reaches
        ``file_looks_utf8`` (``file/src/apprentice.c:1258-1283``).

        Args:
            value: The parsed value the search looks for.

        Returns:
            True if libmagic classifies the search as a text test.
        """
        if self.force_binary:
            return False
        return value.is_always_text()

    def strength_term(self, expected: StringTest) -> int:
        """Far less than a `string` of the same length, because a search roams the buffer.

        libmagic caps the per-byte credit so the whole term never exceeds one unit's worth for a
        value of two bytes or more (``file/src/apprentice.c:1008-1012``): ``vallen * max(MULT //
        vallen, 1)`` is ``MULT`` for a one-byte value and ``vallen`` beyond that.
        """
        vallen = expected.value_length
        if vallen == 0:
            return 0
        return vallen * max(STRENGTH_MULT // vallen, 1)

    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
        return expected.search(data)

    SEARCH_TYPE_FORMAT: Pattern[str] = re.compile(
        r"^search"
        r"((/(?P<repetitions1>(0[xX][\dA-Fa-f]+|\d+)))(/(?P<flags1>[BbCctTWwsf]*)?)?|"
        r"/((?P<flags2>[BbCctTWwsf]*)/?)?(?P<repetitions2>(0[xX][\dA-Fa-f]+|\d+)))$"
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
            compact_whitespace="W" in options,
            optional_blanks="w" in options,
            full_word_match="f" in options,
            trim="T" in options,
            match_to_start="s" in options,
            force_binary="b" in options
        )


class PascalStringType(DataType[StringTest]):
    STRING_FLAGS: str = "CcTWwft"

    def __init__(
            self,
            byte_length: int = 1,
            endianness: Endianness = Endianness.BIG,
            count_includes_length: bool = False,
            string_flags: str = ""
    ):
        """A length-prefixed string.

        Args:
            byte_length: The width of the length prefix, in bytes: 1, 2, or 4.
            endianness: The byte order of a two- or four-byte length prefix.
            count_includes_length: Whether the length prefix counts itself.
            string_flags: The string modifier letters of the declaration, such as ``T``. libmagic
                accepts them on ``pstring`` as it does on ``string``
                (``file/src/apprentice.c:1943-2020``).

        Raises:
            ValueError: If `byte_length` or `endianness` is not one libmagic supports.
        """
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
        super().__init__(f"pstring/{modifier}{string_flags}")
        self.byte_length: int = byte_length
        self.endianness: Endianness = endianness
        self.count_includes_length: int = count_includes_length
        self.string_type: StringType = StringType.parse(f"string/{string_flags}")

    def is_text(self, value: StringTest) -> bool:
        # TODO: See if Pascal strings should sometimes be forced to be text
        return False

    def strength_term(self, expected: StringTest) -> int:
        """Scored like a `string`, counting the length prefix as part of the value.

        ``getstr`` folds ``file_pstring_length_size`` into ``m->vallen`` for a ``pstring``
        (``file/src/apprentice.c:3181-3188``), so the prefix widens the term.
        """
        return (expected.value_length + self.byte_length) * STRENGTH_MULT

    def relation(self, expected: StringTest) -> str:
        return expected.relation

    def parse_expected(self, specification: str) -> StringTest:
        return self.string_type.parse_expected(specification)

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
        content = data[self.byte_length:self.byte_length + length]
        m = expected.matches(content)
        if m:
            # Use strlen (excluding null terminator) for match length to match libmagic behavior
            # for relative offset calculations
            null_pos = content.find(b'\x00')
            effective_len = null_pos if null_pos != -1 else length
            m.raw_match = data[:self.byte_length + effective_len]
        return m

    PSTRING_TYPE_FORMAT: Pattern[str] = re.compile(r"^pstring(?P<opts>/[JBHhLlCcTWwft]*)?$")

    @classmethod
    def parse(cls, format_str: str) -> "PascalStringType":
        m = cls.PSTRING_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid pstring type declaration: {format_str!r}")
        if m.group("opts") is None:
            options: str = ""
        else:
            options = m.group("opts")
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
            count_includes_length="J" in options,
            string_flags="".join(opt for opt in options if opt in cls.STRING_FLAGS)
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


def nonmagic(pattern: bytes) -> int:
    """Counts the literal characters of a regular expression, libmagic's ``nonmagic``.

    Metacharacters describe how to match rather than what to match, so they earn no strength
    (``file/src/apprentice.c:813-849``). A bracketed class counts one, for its closing bracket; a
    braced repetition counts nothing; an escape counts one, whatever it escapes.

    Note that libmagic applies this to the *unescaped* value, so a pattern written ``\\.`` arrives
    here as a bare ``.`` and counts zero, which is why libmagic warns to write ``\\\\.`` instead.
    For the same reason an escaped null byte ends the count, because libmagic walks the value as a
    C string.

    Args:
        pattern: The unescaped pattern bytes.

    Returns:
        The number of literal characters, at least one.
    """
    count = 0
    i = 0
    terminator = pattern.find(b"\0")
    if terminator >= 0:
        pattern = pattern[:terminator]
    while i < len(pattern):
        char = pattern[i:i + 1]
        if char == b"\\":
            i += 2 if i + 1 < len(pattern) else 1
            count += 1
        elif char in (b"?", b"*", b".", b"+", b"^", b"$"):
            i += 1
        elif char == b"[":
            closing = pattern.find(b"]", i)
            i = len(pattern) if closing < 0 else closing
        elif char == b"{":
            closing = pattern.find(b"}", i)
            i = len(pattern) if closing < 0 else closing + 1
        else:
            i += 1
            count += 1
    return max(count, 1)


class MagicRegex:
    """A definition's regular expression, alongside the literal count libmagic scores it by.

    libmagic counts literals on the value as its own unescaping left it
    (``file/src/apprentice.c:1015``), which is before PolyFile rewrites POSIX character classes
    into their Python equivalents. The rewrite drops the inner ``:]`` that ends libmagic's bracket
    scan, so the count is one lower per class unless it is taken first.
    """

    def __init__(self, specification: bytes, flags: int = 0):
        """Compiles `specification`, counting its literals before the POSIX rewrite.

        Args:
            specification: The unescaped pattern, as libmagic would hold it.
            flags: The regular expression flags to compile with.

        Raises:
            re.error: If `specification` is not a valid regular expression.
        """
        self.literal_count: int = nonmagic(specification)
        self.pattern: bytes = posix_to_python_re(specification)
        self.compiled: Pattern[bytes] = re.compile(self.pattern, flags)

    def search(self, data: bytes) -> Optional["re.Match[bytes]"]:
        return self.compiled.search(data)

    def match(self, data: bytes) -> Optional["re.Match[bytes]"]:
        return self.compiled.match(data)

    def __str__(self):
        return self.pattern.decode("utf-8", errors="replace")


class RegexType(DataType[MagicRegex]):
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

    DOLLAR_PATTERN = re.compile(rb"(^|[^\\])\$", re.MULTILINE)

    def is_text(self, value: MagicRegex) -> bool:
        try:
            _ = value.pattern.decode("ascii")
            return True
        except UnicodeDecodeError:
            return False

    def strength_term(self, expected: MagicRegex) -> int:
        """One unit per literal character, capped the way a `search` is.

        See ``file/src/apprentice.c:1014-1017``.
        """
        literals = expected.literal_count
        return literals * max(STRENGTH_MULT // literals, 1)

    def parse_expected(self, specification: str) -> MagicRegex:
        if specification.startswith("="):
            # libmagic parses a leading `=` as the equality operator, not as part of the pattern
            # (`file/src/apprentice.c:2383-2384`)
            specification = specification[1:]
        flags = re.MULTILINE
        if self.case_insensitive:
            flags |= re.IGNORECASE
        try:
            return MagicRegex(unescape(specification), flags)
        except re.error as e:
            raise ValueError(str(e))

    def matched_extent(self, m: "re.Match[bytes]", subject_offset: int) -> DataTypeMatch:
        """Builds the match that libmagic reports for a regular expression match.

        libmagic reports only the bytes between `pmatch.rm_so` and `pmatch.rm_eo`, positioned at
        `rm_so` (`file/src/softmagic.c:2413-2416`, printed at `file/src/softmagic.c:785-801`).

        Args:
            m: The regular expression match.
            subject_offset: The offset of `m`'s subject within the data that was tested.

        Returns:
            A match covering only the matched bytes, positioned at the start of the match.
        """
        raw_match = m.group()
        try:
            value: Any = raw_match.decode("utf-8")
        except UnicodeDecodeError:
            value = raw_match
        if self.trim:
            value = value.strip()
        start = subject_offset + m.start()
        if self.match_to_start:
            # the `s` flag resolves a subsequent relative offset from the start of the match rather
            # than from its end (`CHAR_REGEX_OFFSET_START` in `file/src/file.h:419`, applied in
            # `moffset`'s `FILE_REGEX` case at `file/src/softmagic.c:959-963`)
            return DataTypeMatch(raw_match, value, initial_offset=start, relative_base=start)
        return DataTypeMatch(raw_match, value, initial_offset=start)

    def match(self, data: bytes, expected: MagicRegex) -> DataTypeMatch:
        if not self.limit_lines:
            m = expected.search(data[:self.length])
            if m is None:
                return DataTypeMatch.INVALID
            return self.matched_extent(m, 0)
        offset = 0
        # libmagic uses an implicit byte limit that assumes 80 characters per line
        byte_limit = 80 * self.length
        for _ in range(self.length):
            line_offset = data.find(b"\n", offset, byte_limit)
            if line_offset < 0:
                return DataTypeMatch.INVALID
            m = expected.match(data[offset:line_offset])
            if m is not None:
                return self.matched_extent(m, offset)
            offset = line_offset + 1
        return DataTypeMatch.INVALID

    REGEX_TYPE_FORMAT: Pattern[str] = re.compile(
        r"^regex(/(?P<length>\d+)?(?P<flags1>[cslTt]*)(/(?P<flags2>[cslTt]*))?(b\d*)?)?$"
    )
    # NOTE: some specification files like `cad` use `regex/b`, which is undocumented, and it's unclear from the libmagic
    #       source code whether it is simply ignored or if it has a purpose. We ignore it here.
    # NOTE: the `t` flag (force text) is also supported but currently ignored as it's a hint for output formatting.
    # NOTE: flags can appear either after length directly (regex/31cs) or with a slash (regex/31/cs).

    @classmethod
    def parse(cls, format_str: str) -> "RegexType":
        m = cls.REGEX_TYPE_FORMAT.match(format_str)
        if not m:
            raise ValueError(f"Invalid regex type declaration: {format_str!r}")
        options: str = ""
        if m.group("flags1") is not None:
            options += m.group("flags1")
        if m.group("flags2") is not None:
            options += m.group("flags2")
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


DATETIME_FORMAT: str = "%a %b %e %H:%M:%S %Y"
DATE_FORMAT: str = "%a %b %e %Y"
TIME_FORMAT: str = "%H:%M:%S"


def local_date(ms_since_epoch: int) -> str:
    return strftime(DATETIME_FORMAT, localtime(ms_since_epoch / 1000.0))


def utc_date(ms_since_epoch: int) -> str:
    return strftime(DATETIME_FORMAT, gmtime(ms_since_epoch / 1000.0))


MSDOS_DATE_FORMAT: str = "%b %d %Y"


def msdos_date(value: int) -> str:
    day = value & 0b11111
    value >>= 5
    # MS-DOS stores month as 1-12, convert to 0-11 for datetime
    month_raw = value & 0b1111
    month = month_raw - 1
    value >>= 4
    year = 1980 + (value & 0b1111111)
    # Sanity check: clamp invalid months to 0 (January), matching libmagic behavior
    if month < 0 or month > 11:
        month = 0
    # Clamp invalid day to valid range
    if day < 1:
        day = 1
    if day > 31:
        day = 31
    # Convert back to 1-based month for datetime
    month += 1
    try:
        return strftime(MSDOS_DATE_FORMAT, datetime(year, month, day).timetuple())
    except ValueError:
        # Handle invalid date combinations (e.g., Feb 31)
        return f"{year}-{month:02d}-{day:02d}"


def msdos_time(value: int) -> str:
    seconds = (value & 0b11111) * 2
    value >>= 5
    minutes = value & 0b111111
    value >>= 6
    hour = value & 0b11111
    return strftime(TIME_FORMAT, datetime(1, 1, 1, hour, minutes, seconds).timetuple())


class BaseNumericDataType(Enum):
    BYTE = ("byte", "b", 1)
    BYTE1 = ("1", "b", 1)
    SHORT = ("short", "h", 2)
    SHORT2 = ("2", "h", 2)
    LONG = ("long", "l", 4)
    LONG4 = ("4", "l", 4)
    QUAD = ("quad", "q", 8)
    QUAD8 = ("8", "q", 8)
    FLOAT = ("float", "f", 4)
    DOUBLE = ("double", "d", 8)
    DATE = ("date", "L", 4, lambda n: utc_date(n * 1000))
    QDATE = ("qdate", "Q", 8, lambda n: utc_date(n * 1000))
    LDATE = ("ldate", "L", 4, lambda n: local_date(n * 1000))
    QLDATE = ("qldate", "Q", 8, lambda n: local_date(n * 1000))
    QWDATE = ("qwdate", "Q", 8)
    MSDOSDATE = ("msdosdate", "h", 2, msdos_date)
    MSDOSTIME = ("msdostime", "h", 2, msdos_time)

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

    def __init__(self, symbol: str, test: Union[
            Callable[[int, int], bool],
            Callable[[float, float], bool],
            Callable[[CStyleInt, CStyleInt], bool]
    ]):
        self.symbol: str = symbol
        self.test: Union[
            Callable[[int, int], bool], Callable[[float, float], bool], Callable[[CStyleInt, CStyleInt], bool]
        ] = test
        NUMERIC_OPERATORS_BY_SYMBOL[symbol] = self

    @staticmethod
    def get(symbol: str) -> "NumericOperator":
        return NUMERIC_OPERATORS_BY_SYMBOL[symbol]

    def __str__(self):
        return self.symbol


class NumericValue(Generic[T]):
    def __init__(self, value: T, operator: NumericOperator = NumericOperator.EQUALS):
        self.value: T = value
        self.operator: NumericOperator = operator

    def test(self, to_match: T, unsigned: bool, num_bytes: int, preprocess: Callable[[T], T] = lambda x: x) -> bool:
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

    def __str__(self):
        return f"{self.operator}{self.value!s}"


class NumericWildcard(NumericValue):
    def __init__(self):
        super().__init__(None)

    def test(self, to_match, unsigned, num_bytes, preprocess: Callable[[int], int] = lambda x: x) -> bool:
        return True


class IntegerValue(NumericValue[int]):
    def test(
            self,
            to_match: int,
            unsigned: bool,
            num_bytes: int,
            preprocess: Callable[[CStyleInt], CStyleInt] = lambda x: x
    ) -> bool:
        to_test = make_c_style_int(value=self.value, num_bytes=num_bytes, signed=not unsigned)
        to_match = make_c_style_int(value=to_match, num_bytes=num_bytes, signed=not unsigned)
        return self.operator.test(preprocess(to_match), to_test)

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

    def is_text(self, value: NumericValue) -> bool:
        return False

    def strength_term(self, expected: NumericValue) -> int:
        """One unit per byte the type reads (``file/src/apprentice.c:975-996``)."""
        return self.base_type.num_bytes * STRENGTH_MULT

    def relation(self, expected: NumericValue) -> str:
        if isinstance(expected, NumericWildcard):
            return "x"
        return expected.operator.symbol

    def parse_expected(self, specification: str) -> NumericValue:
        if specification.strip() == "x":
            return NumericWildcard()
        else:
            return NumericValue.parse(specification, self.base_type.num_bytes)

    def match(self, data: bytes, expected: NumericValue) -> DataTypeMatch:
        if len(data) < self.base_type.num_bytes:
            return DataTypeMatch.INVALID
        elif self.endianness == Endianness.PDP:
            assert self.base_type.num_bytes == 4
            if self.unsigned:
                value = (struct.unpack("<H", data[:2])[0] << 16) | struct.unpack("<H", data[2:4])[0]
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

    def flip_endianness(self) -> "NumericDataType":
        """Return a copy with LITTLE/BIG endianness flipped."""
        if self.endianness == Endianness.LITTLE:
            new_endianness = Endianness.BIG
        elif self.endianness == Endianness.BIG:
            new_endianness = Endianness.LITTLE
        else:
            new_endianness = self.endianness  # NATIVE and PDP unchanged
        return NumericDataType(
            name=self.name,
            base_type=self.base_type,
            unsigned=self.unsigned,
            endianness=new_endianness,
            preprocess=self.preprocess
        )

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


def libmagic_string_flags(data_type: DataType) -> bytes:
    """The ``str_range`` and ``str_flags`` word libmagic gives a string type.

    Args:
        data_type: The type a definition declared.

    Returns:
        Eight bytes, which are zero for a type that carries no string modifiers.
    """
    if not isinstance(data_type, (StringType, PascalStringType, RegexType, UTF16Type)):
        return bytes(8)
    string_range = getattr(data_type, "num_bytes", None) or 0
    if isinstance(data_type, SearchType) and string_range == 0:
        string_range = STRING_DEFAULT_RANGE
    flags = 0
    for attribute, bit in STRING_FLAG_BITS:
        if getattr(data_type, attribute, False):
            flags |= bit
    return libmagic_field(string_range, 4) + libmagic_field(flags, 4)


def libmagic_string_value(constant: StringTest) -> bytes:
    """The bytes libmagic would copy into ``value.s`` for a string test.

    Args:
        constant: The parsed value of a string, search, or Pascal string test.

    Returns:
        The unescaped value, which is empty for a test that declared none.
    """
    if isinstance(constant, NegatedStringTest):
        return libmagic_string_value(constant.parent)
    elif isinstance(constant, StringMatch):
        return constant.string
    elif isinstance(constant, StringLengthTest):
        return unescape(constant.raw_pattern)
    return b""


def libmagic_numeric_value(data_type: DataType, value: Union[int, float]) -> bytes:
    """The bytes libmagic would copy into a numeric test's value union.

    Args:
        data_type: The type a definition declared, which sizes a floating point value.
        value: The parsed value.

    Returns:
        The value's little endian bytes.
    """
    if isinstance(value, float):
        base_type = getattr(data_type, "base_type", None)
        if getattr(base_type, "num_bytes", 8) == 4:
            return struct.pack("<f", value)
        return struct.pack("<d", value)
    return libmagic_field(value, 8)


def libmagic_value(data_type: DataType, constant: Any) -> Tuple[int, bytes]:
    """The ``vallen`` and value bytes libmagic would store for a parsed test value.

    libmagic reads no value at all for the ``x`` relation, so a wildcard leaves both zeroed
    (``file/src/apprentice.c:2407-2412``).

    Args:
        data_type: The type a definition declared.
        constant: The value the type parsed.

    Returns:
        The value's declared length and its bytes.
    """
    if isinstance(constant, StringTest):
        return constant.value_length, libmagic_string_value(constant)
    elif isinstance(constant, MagicRegex):
        return len(constant.pattern), constant.pattern
    elif isinstance(constant, bytes):
        return len(constant), constant
    elif isinstance(constant, NumericValue) and not isinstance(constant, NumericWildcard):
        return 0, libmagic_numeric_value(data_type, constant.value)
    return 0, b""


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

    def libmagic_type(self) -> str:
        return libmagic_base_type(self.data_type.name)

    def libmagic_flag(self) -> int:
        flag = super().libmagic_flag()
        if isinstance(self.data_type, NumericDataType) and self.data_type.unsigned:
            flag |= FLAG_UNSIGNED
        return flag

    def libmagic_value_fields(self) -> Tuple[int, bytes, bytes]:
        value_length, value = libmagic_value(self.data_type, self.constant)
        return value_length, libmagic_string_flags(self.data_type), value

    def type_strength(self) -> int:
        return self.data_type.strength_term(self.constant)

    def relation(self) -> str:
        return self.data_type.relation(self.constant)

    def subtest_type(self) -> TestType:
        if self.data_type.is_text(self.constant):
            return TestType.TEXT
        else:
            return TestType.BINARY

    def calculate_absolute_offset(self, data: bytes, parent_match: Optional[TestResult] = None) -> int:
        return self.offset.to_absolute(data, parent_match, self.data_type.allows_invalid_offsets(self.constant))

    def matched_test(
            self, match: DataTypeMatch, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> MatchedTest:
        """Records a successful match, with the relative base that libmagic would resolve against.

        A data type that knows its own base reports it as `DataTypeMatch.relative_base`, and that
        wins: the `regex` `s` flag uses it to resolve against the start of the match instead of its
        end (`file/src/softmagic.c:959-963`).

        Failing that, a relative (`&`) offset after a `string` test with an `=` relation resolves
        against the declared length of the magic value rather than the number of bytes the match
        consumed (`file/src/softmagic.c:904-905`). The two differ when the `w` flag matches fewer
        blanks than the value declares. A `search` measures from where it found its value, which
        PolyFile records as the extent it matched; libmagic adds the declared length there too, but
        zeroes it for the `s` flag (`file/src/softmagic.c:966-968`), which PolyFile does not model
        yet. A `pstring` carries its own length prefix, so neither rule takes this path.

        Args:
            match: The match that this test's data type produced.
            absolute_offset: The offset in the file at which the data type was applied.
            parent_match: The result of the test that this one is nested under, if any.

        Returns:
            The result of the test, carrying a relative base when either rule applies.
        """
        result = MatchedTest(self, offset=absolute_offset + match.initial_offset,
                             length=len(match.raw_match), value=match.value, parent=parent_match)
        declares_its_length = (isinstance(self.data_type, StringType)
                               and not isinstance(self.data_type, SearchType)
                               and isinstance(self.constant, StringMatch))
        if match.relative_base is not None:
            result.relative_base = absolute_offset + match.relative_base
        elif declares_its_length:
            result.relative_base = result.offset + len(self.constant.string)
        return result

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        match = self.data_type.match(data[absolute_offset:], self.constant)
        if match:
            return self.matched_test(match, absolute_offset, parent_match)
        else:
            return FailedTest(
                self,
                offset=absolute_offset,
                parent=parent_match,
                message=f"expected {self.constant!s}"
            )

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        if isinstance(self.data_type, NumericDataType):
            data_type = self.data_type.flip_endianness()
        else:
            data_type = self.data_type
        match = data_type.match(data[absolute_offset:], self.constant)
        if match:
            return self.matched_test(match, absolute_offset, parent_match)
        else:
            return FailedTest(
                self,
                offset=absolute_offset,
                parent=parent_match,
                message=f"expected {self.constant!s}"
            )


class OffsetMatchTest(MagicTest):
    def __init__(
            self,
            offset: Offset,
            value: IntegerValue,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None,
            subtraction: int = 0,
            modulo: int = 0
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.value: IntegerValue = value
        self.subtraction: int = subtraction
        self.modulo: int = modulo

    def libmagic_type(self) -> str:
        return "offset"

    def type_strength(self) -> int:
        """``offset`` is an eight-byte quantity (``file/src/apprentice.c:906-908``)."""
        return 8 * STRENGTH_MULT

    def relation(self) -> str:
        if isinstance(self.value, NumericWildcard):
            return "x"
        return self.value.operator.symbol

    def subtest_type(self) -> TestType:
        return TestType.UNKNOWN

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        computed_value = absolute_offset - self.subtraction
        if self.modulo != 0:
            computed_value = computed_value % self.modulo
        if self.value.test(computed_value, unsigned=True, num_bytes=8):
            return MatchedTest(self, offset=0, length=absolute_offset, value=computed_value, parent=parent_match)
        else:
            return FailedTest(
                test=self,
                offset=absolute_offset,
                parent=parent_match,
                message=f"expected {self.value!r}"
            )

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class IndirectResult(MatchedTest):
    def __init__(self, test: "IndirectTest", offset: int, parent: Optional[TestResult] = None):
        super().__init__(test, value=None, offset=offset, length=0, parent=parent)

    def explain(self, writer: ANSIWriter, file: Streamable):
        writer.write(f"Indirect test {self.test} matched at offset {self.offset}\n", dim=True)


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
        self._type = TestType.BINARY
        p = parent
        while p is not None:
            p.can_be_indirect = True
            p.can_match_mime = True
            p._type = TestType.BINARY
            p = p.parent

    def libmagic_type(self) -> str:
        return "indirect"

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if self.relative:
            if parent_match is None:
                return FailedTest(
                    test=self,
                    offset=absolute_offset,
                    parent=parent_match,
                    message="the test is relative but it does not have a parent test (this is likely a bug in the magic"
                            " definition file)"
                )
            absolute_offset += parent_match.offset
        return IndirectResult(self, absolute_offset, parent_match)

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


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
            def to_absolute(self, data: bytes, last_match: Optional[TestResult], allow_invalid: bool = False) -> int:
                assert last_match is not None
                return last_match.offset
        offset = NamedTestOffset()
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=None)
        self.name: str = name
        self.named_test = self
        self.used_by: Set[UseTest] = set()

    def libmagic_type(self) -> str:
        return "name"

    def subtest_type(self) -> TestType:
        return TestType.UNKNOWN

    def test_flip_endianness(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if parent_match is not None:
            return MatchedTest(self, offset=parent_match.offset + parent_match.length, length=0, value=self.name,
                               parent=parent_match)
        else:
            raise ValueError("A named test must always be called from a `use` test.")

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> MatchedTest:
        if parent_match is not None:
            return MatchedTest(self, offset=parent_match.offset + parent_match.length, length=0, value=self.name,
                               parent=parent_match)
        else:
            raise ValueError("A named test must always be called from a `use` test.")

    def __str__(self):
        return self.name


def prints_a_message(result: TestResult, context: MatchContext) -> bool:
    """Reports whether a test result would print something.

    libmagic raises its ``found_match`` flag only for an entry whose description is not empty
    (``file/src/softmagic.c:323`` and ``:439``), and it strips a leading ``\\b`` — the NOSPACE
    flag — off the description while parsing the entry (``file/src/apprentice.c:2427-2435``).
    A bare ``name`` line therefore prints nothing and raises nothing.

    Args:
        result: The result of running a test. A failed test never prints.
        context: The context that the test ran against, used to resolve the message.

    Returns:
        True if the result is a match whose resolved message is not empty.
    """
    if not result:
        return False
    return bool(result.test.message.resolve(context).removeprefix("\b"))


class UseTest(MagicTest):
    def __init__(
            self,
            referenced_test: NamedTest,
            offset: Offset,
            mime: Optional[str] = None,
            extensions: Iterable[str] = (),
            message: str = "",
            parent: Optional["MagicTest"] = None,
            flip_endianness: bool = False,
            late_binding: bool = False
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.referenced_test: NamedTest = referenced_test
        self.flip_endianness: bool = flip_endianness
        self.late_binding: bool = late_binding
        referenced_test.used_by.add(self)

    def libmagic_type(self) -> str:
        return "use"

    def subtest_type(self) -> TestType:
        return self.referenced_test.test_type

    def referenced_tests(self) -> Set[NamedTest]:
        result = super().referenced_tests() | {self.referenced_test}
        if self.named_test is None or self.named_test.name != self.referenced_test.name:
            result |= self.referenced_test.referenced_tests()
        return result

    def _match(
            self,
            context: MatchContext,
            parent_match: Optional[TestResult] = None,
            flip_endianness: bool = False
    ) -> Iterator[TestResult]:
        flip_endianness = flip_endianness ^ self.flip_endianness
        try:
            absolute_offset = self.offset.to_absolute(context.data, last_match=parent_match)
        except InvalidOffsetError:
            return None
        use_match = MatchedTest(self, None, absolute_offset, 0, parent=parent_match)
        named_results = self._match_referenced_test(context, use_match, flip_endianness)
        matched = any(prints_a_message(result, context) for result in named_results)
        log.trace(
            f"{self.source_info!s}\t{matched}\t{absolute_offset}\t"
            f"{context.data[absolute_offset:absolute_offset + 20]!r}"
        )
        if not matched:
            return
        yield use_match
        for named_result in named_results:
            if not context.only_match_mime or named_result.test.mime is not None:
                yield named_result
        if context.only_match_mime and not self.can_match_mime:
            # none of our children can produce a mime type
            return
        for child in self.children:
            if not context.only_match_mime or child.can_match_mime:
                yield from child._match(context=context, parent_match=use_match, flip_endianness=flip_endianness)

    def _match_referenced_test(
            self, context: MatchContext, use_match: MatchedTest, flip_endianness: bool
    ) -> List[TestResult]:
        """Runs the referenced named test list and collects everything it matched.

        libmagic evaluates the whole named list and uses the number of entries that printed as the
        ``use`` test's truth value (``file/src/softmagic.c:2001-2039`` and ``:2429-2430``), so
        MIME-only pruning is lifted for the run: whether the list can report a MIME type must not
        decide whether the ``use`` succeeds. The caller reapplies the pruning when it picks the
        results to yield.

        Args:
            context: The context to match against.
            use_match: The match for this ``use`` test, which parents the named test's results.
            flip_endianness: Whether the named test reads its operands with flipped endianness.

        Returns:
            Every result the named test list matched, in the order it produced them.
        """
        if context.only_match_mime:
            context = MatchContext(data=context.data, path=context.path)
        return list(self.referenced_test._match(context, use_match, flip_endianness=flip_endianness))

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        raise NotImplementedError("This function should never be called")


JSON_WHITESPACE: str = " \t\n\r"
"""The characters that libmagic's `json_skip_space` skips (`file/src/is_json.c`)."""


class ParsedJSON(NamedTuple):
    """A buffer that parsed as JSON under libmagic's rules."""

    value: Any
    """The first top-level JSON value in the buffer."""

    newline_delimited: bool
    """Whether a second top-level JSON value follows the first one."""


def _skip_json_whitespace(text: str, offset: int) -> int:
    while offset < len(text) and text[offset] in JSON_WHITESPACE:
        offset += 1
    return offset


def parse_json(raw: bytes) -> ParsedJSON:
    """Parses a buffer as JSON the way libmagic's `file_is_json` does.

    libmagic implements JSON detection with a C parser rather than with the magic DSL, and its
    rules are narrower than `json.loads`:

    * The top-level value must be an object or an array, because libmagic only reports JSON when
      `st[JSON_OBJECT]` or `st[JSON_ARRAYN]` is set (`file/src/is_json.c`). A bare scalar such as
      `42` is therefore not JSON, even though `json.loads` accepts one.
    * If more data follows the first value, it is newline-delimited JSON as long as the next byte
      equals the first byte of the first value and a second value parses there. libmagic stops
      after that second value, so trailing garbage does not disqualify the buffer.

    Args:
        raw: the bytes to parse, starting at the first byte of the candidate JSON value.

    Returns:
        The first top-level value, and whether a second top-level value follows it.

    Raises:
        json.JSONDecodeError: if the buffer is not JSON under libmagic's rules.
        UnicodeDecodeError: if the buffer is not text in an encoding that JSON allows.
    """
    text = raw.decode(json.detect_encoding(raw), "surrogatepass")
    decoder = json.JSONDecoder()
    start = _skip_json_whitespace(text, 0)
    value, offset = decoder.raw_decode(text, start)
    if not isinstance(value, (dict, list)):
        raise json.JSONDecodeError("the top-level JSON value is neither an object nor an array", text, start)
    offset = _skip_json_whitespace(text, offset)
    if offset >= len(text):
        return ParsedJSON(value, False)
    if text[offset] != text[start]:
        raise json.JSONDecodeError("the data after the top-level JSON value does not start another one",
                                   text, offset)
    decoder.raw_decode(text, offset)
    return ParsedJSON(value, True)


class JSONTest(MagicTest):
    """Matches a buffer that holds a single top-level JSON object or array.

    `NEWLINE_DELIMITED` selects which of libmagic's two JSON verdicts this test accepts, so the
    two messages come from two tests in `polyfile/magic_defs/json` rather than from reassigning
    `MagicTest.message` at match time. Test objects are shared across calls to
    `MagicMatcher.match`, so a message assigned during one match would leak into the next.
    """

    NEWLINE_DELIMITED: bool = False
    """Whether this test matches newline-delimited JSON rather than a single JSON value."""

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        try:
            parsed = parse_json(data[absolute_offset:])
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return FailedTest(test=self, offset=absolute_offset, parent=parent_match, message=str(e))
        if parsed.newline_delimited != self.NEWLINE_DELIMITED:
            if parsed.newline_delimited:
                reason = "the data holds more than one top-level JSON value"
            else:
                reason = "the data holds only one top-level JSON value"
            return FailedTest(test=self, offset=absolute_offset, parent=parent_match, message=reason)
        return MatchedTest(self, offset=absolute_offset, length=len(data) - absolute_offset, value=parsed.value,
                           parent=parent_match)

    def subtest_type(self) -> TestType:
        return TestType.TEXT

    @property
    def appends_text_encoding(self) -> bool:
        """libmagic never appends its text-encoding description to a JSON verdict.

        ``file_is_json`` runs ahead of soft magic in ``file_buffer`` and its match ends the run, so
        ``file_ascmagic`` never sees it: `file` reports ``JSON text data``, not
        ``JSON text data, ASCII text``.

        Returns:
            False.
        """
        return False

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class NDJSONTest(JSONTest):
    """Matches newline-delimited JSON, which libmagic names separately from single-value JSON."""

    NEWLINE_DELIMITED: bool = True


class CSVTest(MagicTest):
    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        try:
            text = data[absolute_offset:].decode("utf-8")
        except UnicodeDecodeError as e:
            return FailedTest(test=self, offset=absolute_offset, parent=parent_match, message=str(e))
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
                return MatchedTest(self, offset=absolute_offset, length=len(data) - absolute_offset, value=dialect,
                                   parent=parent_match)
        return FailedTest(
            test=self,
            offset=absolute_offset,
            parent=parent_match,
            message=f"the input did not match a known CSV dialect ({', '.join(csv.list_dialects())})"
        )

    def subtest_type(self) -> TestType:
        return TestType.TEXT

    @property
    def appends_text_encoding(self) -> bool:
        """libmagic never appends its text-encoding description to a CSV verdict.

        ``file_is_csv`` runs ahead of soft magic in ``file_buffer``, names the encoding itself, and
        its match ends the run, so ``file_ascmagic`` never sees it.

        Returns:
            False.
        """
        return False

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class DefaultTest(MagicTest):
    def libmagic_type(self) -> str:
        return "default"

    def subtest_type(self) -> TestType:
        return TestType.UNKNOWN

    def base_strength(self) -> int:
        """Zero, so that a `default` sorts last (``file/src/apprentice.c:932-938``).

        libmagic returns before reaching the relation term here, and its own clamp then raises the
        zero to one, so a `default` is the weakest test rather than a strengthless one.
        """
        return 0

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if parent_match is None or not parent_match.child_matched:
            return MatchedTest(self, offset=absolute_offset, length=0, value=True, parent=parent_match)
        else:
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message="the parent test already "
                                                                                         "has a child that matched")

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class ClearTest(MagicTest):
    def libmagic_type(self) -> str:
        return "clear"

    def subtest_type(self) -> TestType:
        return TestType.UNKNOWN

    def relation(self) -> str:
        """``clear`` takes no value, so libmagic parses it as the ``x`` relation."""
        return "x"

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> MatchedTest:
        if parent_match is None:
            return MatchedTest(self, offset=absolute_offset, length=0, value=None)
        else:
            parent_match.child_matched = False
            return MatchedTest(self, offset=absolute_offset, length=0, parent=parent_match, value=None)

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class DERTest(MagicTest):
    """Matches one Distinguished Encoding Rules object against a :class:`DERSpecification`."""

    def __init__(
            self,
            offset: Offset,
            specification: DERSpecification,
            mime: Optional[Union[str, TernaryExecutableMessage]] = None,
            extensions: Iterable[str] = (),
            message: Union[str, Message] = "",
            parent: Optional["MagicTest"] = None,
            comments: Iterable[Comment] = ()
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message,
                         parent=parent, comments=comments)
        self.specification: DERSpecification = specification

    def libmagic_type(self) -> str:
        return "der"

    def type_strength(self) -> int:
        """One flat unit, whatever the specification says (``file/src/apprentice.c:1024-1026``)."""
        return STRENGTH_MULT

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        try:
            header = DERHeader.parse(data, absolute_offset)
            value = self.specification.match(header, data)
        except InvalidDER as e:
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message=str(e))
        if isinstance(parent_match, MatchedTest):
            # The next test at this level reads the DER object that follows the one we just matched.
            parent_match.relative_base = header.end
        return MatchedTest(self, value=value, offset=absolute_offset, length=header.header_length,
                           parent=parent_match)

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


TEXT_CHAR_NONE: int = 0
TEXT_CHAR_ASCII: int = 1
TEXT_CHAR_ISO_8859: int = 2
TEXT_CHAR_EXTENDED: int = 3


def _text_char_classes() -> bytes:
    """Reproduces the ``text_chars`` table of libmagic's ``src/encoding.c``.

    Returns:
        A 256 byte table mapping each byte value to one of the ``TEXT_CHAR_*`` classes.
    """
    classes = bytearray(256)
    for byte in range(0x20, 0x7F):
        classes[byte] = TEXT_CHAR_ASCII
    for byte in range(0x80, 0xA0):
        classes[byte] = TEXT_CHAR_EXTENDED
    for byte in range(0xA0, 0x100):
        classes[byte] = TEXT_CHAR_ISO_8859
    for byte in (0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x1A, 0x1B, 0x85):
        classes[byte] = TEXT_CHAR_ASCII
    return bytes(classes)


TEXT_CHAR_CLASSES: bytes = _text_char_classes()

_ASCII_BYTES: bytes = bytes(b for b in range(256) if TEXT_CHAR_CLASSES[b] == TEXT_CHAR_ASCII)
_ISO_8859_BYTES: bytes = bytes(
    b for b in range(256) if TEXT_CHAR_CLASSES[b] in (TEXT_CHAR_ASCII, TEXT_CHAR_ISO_8859)
)
_TEXT_BYTES: bytes = bytes(b for b in range(256) if TEXT_CHAR_CLASSES[b] != TEXT_CHAR_NONE)
_UTF8_SAFE_BYTES: bytes = bytes(
    b for b in range(256) if b >= 0x80 or TEXT_CHAR_CLASSES[b] == TEXT_CHAR_ASCII
)

_UCS_BYTE_ORDER_MARKS: Tuple[Tuple[bytes, str, int], ...] = (
    (b"\xff\xfe\x00\x00", "utf-32le", 4),
    (b"\x00\x00\xfe\xff", "utf-32be", 4),
    (b"\xff\xfe", "utf-16le", 2),
    (b"\xfe\xff", "utf-16be", 2),
)


def _only_contains(data: bytes, allowed: bytes) -> bool:
    return not data.translate(None, delete=allowed)


def _looks_like_utf8(data: bytes) -> bool:
    if not _only_contains(data, _UTF8_SAFE_BYTES):
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _looks_like_ucs(data: bytes) -> Optional[str]:
    for bom, encoding, unit in _UCS_BYTE_ORDER_MARKS:
        if not data.startswith(bom):
            continue
        body = data[len(bom):]
        body = body[:len(body) - len(body) % unit]
        try:
            decoded = body.decode(encoding)
        except UnicodeDecodeError:
            continue
        if all(char >= "\x80" or TEXT_CHAR_CLASSES[ord(char)] == TEXT_CHAR_ASCII
               for char in decoded):
            return encoding
    return None


def _eight_bit_encoding(data: bytes) -> Optional[str]:
    if not _only_contains(data, _TEXT_BYTES):
        return None
    elif _only_contains(data, _ISO_8859_BYTES):
        return "iso-8859-1"
    else:
        return "unknown-8bit"


def detect_text_encoding(data: bytes) -> Optional[str]:
    """Decides whether `data` is text, and names the character encoding family it belongs to.

    This mirrors ``file_encoding`` in libmagic's ``src/encoding.c``: membership in a text
    encoding is decided by character class alone, with no statistical inference. Every byte in
    ``0xA0``-``0xFF`` is a printable ISO-8859 character, so a buffer of ASCII with a handful of
    accented characters is text.

    Args:
        data: the bytes to classify.

    Returns:
        The name of the encoding family, or None if `data` belongs to no text character class.
    """
    if len(data) < 2:
        return None
    elif _only_contains(data, _ASCII_BYTES):
        return "ascii"
    elif _looks_like_utf8(data):
        return "utf-8"
    ucs_encoding = _looks_like_ucs(data)
    if ucs_encoding is not None:
        return ucs_encoding
    return _eight_bit_encoding(data)


LIBMAGIC_ENCODING_NAMES: Dict[str, str] = {
    "ascii": "ASCII",
    "utf-8": "Unicode text, UTF-8",
    "utf-16le": "Unicode text, UTF-16, little-endian",
    "utf-16be": "Unicode text, UTF-16, big-endian",
    "utf-32le": "Unicode text, UTF-32, little-endian",
    "utf-32be": "Unicode text, UTF-32, big-endian",
    "iso-8859-1": "ISO-8859",
    "unknown-8bit": "Non-ISO extended-ASCII",
}
"""libmagic's name for each encoding `detect_text_encoding` reports, from ``src/encoding.c``."""

MAX_LINE_LENGTH: int = 300
"""libmagic's ``MAXLINELEN``: the longest line it considers sane (``src/ascmagic.c``)."""

TEXT_ENCODING_MAX_BYTES: int = 64 * 1024
"""libmagic's ``FILE_ENCODING_MAX``: how many bytes it decodes to describe text (``src/file.h``)."""

_EIGHT_BIT_ENCODINGS: FrozenSet[str] = frozenset({"ascii", "iso-8859-1", "unknown-8bit"})

_UCS_BOM_LENGTHS: Dict[str, int] = {
    encoding: len(bom) for bom, encoding, _ in _UCS_BYTE_ORDER_MARKS
}

_LINE_TERMINATOR_PATTERN: Pattern[str] = re.compile("[\n\r\x85]")


def _decode_text(data: bytes, encoding: str) -> str:
    """Decodes the prefix of `data` that libmagic examines when it describes text.

    libmagic decodes at most ``FILE_ENCODING_MAX`` bytes into the buffer that
    ``file_ascmagic_with_encoding`` scans, so a line that only grows long past that point does not
    count as a long line. Each eight bit encoding it names copies a byte's value straight into that
    buffer, which is what decoding as Latin-1 does.

    Args:
        data: the bytes to decode.
        encoding: the encoding `detect_text_encoding` named for `data`.

    Returns:
        The decoded characters, dropping any character the byte limit cut in half.
    """
    prefix = data[:TEXT_ENCODING_MAX_BYTES]
    if encoding in _EIGHT_BIT_ENCODINGS:
        return prefix.decode("latin-1")
    prefix = prefix[_UCS_BOM_LENGTHS.get(encoding, 0):]
    return codecs.getincrementaldecoder(encoding)().decode(prefix, final=False)


def _longest_line(text: str) -> int:
    """Measures the longest line of `text`, as libmagic's ``has_long_lines`` counter does.

    Args:
        text: the decoded characters to measure.

    Returns:
        The length of the longest line, or 0 when every line is at most `MAX_LINE_LENGTH`
        characters long.
    """
    longest = 0
    line_start = -1
    for terminator in _LINE_TERMINATOR_PATTERN.finditer(text):
        longest = max(longest, terminator.start() - 1 - line_start)
        line_start = terminator.start()
    longest = max(longest, len(text) - 1 - line_start)
    if longest > MAX_LINE_LENGTH:
        return longest
    return 0


class TextEncodingDescription:
    """How libmagic describes a text file: its character encoding and the shape of its lines.

    ``file_ascmagic_with_encoding`` in libmagic's ``src/ascmagic.c`` rewrites the tail of whatever
    soft magic printed, appends the name of the character encoding, and then reports the file's
    longest line, the line terminators it uses, and whether it holds escape or backspace
    characters. `describe` applies that rewrite to one match's message.
    """

    def __init__(self, code: str, text: str):
        """
        Args:
            code: libmagic's name for the encoding, such as ``ASCII``.
            text: the decoded characters libmagic would scan.
        """
        self.code: str = code
        self.crlf: int = text.count("\r\n")
        self.lf: int = text.count("\n") - self.crlf
        # libmagic counts a CR when it reads the character after it, so a CR that ends the buffer
        # only counts if it is the only line terminator there is
        ends_with_cr = text.endswith("\r")
        self.cr: int = text.count("\r") - self.crlf - int(ends_with_cr)
        if ends_with_cr and self.cr == 0 and self.crlf == 0:
            self.cr = 1
        self.nel: int = text.count("\x85")
        self.longest_line: int = _longest_line(text)
        self.has_escapes: bool = "\x1b" in text
        self.has_overstriking: bool = "\b" in text

    @classmethod
    def detect(cls, data: bytes) -> Optional["TextEncodingDescription"]:
        """Classifies `data` and measures the line shape libmagic would report for it.

        Args:
            data: the bytes to classify.

        Returns:
            The description, or None if `data` is not text.

        Raises:
            ValueError: if `detect_text_encoding` named an encoding that
                `LIBMAGIC_ENCODING_NAMES` does not describe.
        """
        encoding = detect_text_encoding(data)
        if encoding is None:
            return None
        if encoding not in LIBMAGIC_ENCODING_NAMES:
            raise ValueError(f"there is no libmagic description for the text encoding "
                             f"{encoding!r}; add one to LIBMAGIC_ENCODING_NAMES")
        return cls(LIBMAGIC_ENCODING_NAMES[encoding], _decode_text(data, encoding))

    def _splice(self, message: str) -> Tuple[str, bool]:
        """Replaces a soft magic message's trailing ``text`` with the separator libmagic uses.

        libmagic rewrites the tail of its output buffer with ``file_replace(ms, " text$", ", ")``,
        falling back to ``" text executable$"`` and then to appending ``", "``, so
        ``POSIX shell script text executable`` becomes ``POSIX shell script, `` and keeps its
        ``executable`` to print after the encoding.

        Args:
            message: the message soft magic produced, which is empty if nothing matched.

        Returns:
            The rewritten message, and whether it named an executable.
        """
        if not message:
            return "", False
        elif message.endswith(" text"):
            return f"{message[:-len(' text')]}, ", False
        elif message.endswith(" text executable"):
            return f"{message[:-len(' text executable')]}, ", True
        return f"{message}, ", False

    def _line_terminators(self) -> str:
        """Names the line terminators the text uses.

        libmagic reports terminators only when it finds one that is not LF, or when it finds none
        at all, so a file with Unix line endings gets no clause.

        Returns:
            The clause to append, or the empty string when there is nothing to report.
        """
        present = [name for count, name in
                   ((self.crlf, "CRLF"), (self.cr, "CR"), (self.lf, "LF"), (self.nel, "NEL"))
                   if count]
        if not present:
            return ", with no line terminators"
        elif present == ["LF"]:
            return ""
        return f", with {', '.join(present)} line terminators"

    def describe(self, message: str) -> str:
        """Appends this description to the message a match's soft magic tests produced.

        Args:
            message: the message soft magic produced, which is empty if nothing matched.

        Returns:
            The description libmagic reports for the file.
        """
        head, executable = self._splice(message)
        description = f"{head}{self.code} text"
        if executable:
            description = f"{description} executable"
        if self.longest_line:
            description = f"{description}, with very long lines ({self.longest_line})"
        description = f"{description}{self._line_terminators()}"
        if self.has_escapes:
            description = f"{description}, with escape sequences"
        if self.has_overstriking:
            description = f"{description}, with overstriking"
        return description


class PlainTextTest(MagicTest):
    """Matches any buffer that libmagic would classify as text.

    The test carries no message of its own. libmagic names the encoding in the description that
    `TextEncodingDescription.describe` builds, which `MagicMatcher.match` attaches to the match
    instead, so this test holds no per-match state and is safe to share across matches.
    """

    AUTO_REGISTER_TEST = False

    def __init__(
            self,
            offset: Offset = AbsoluteOffset(0),
            mime: Union[str, TernaryExecutableMessage] = "text/plain",
            extensions: Iterable[str] = ("txt",),
            parent: Optional["MagicTest"] = None,
            comments: Iterable[Comment] = ()
    ):
        super().__init__(offset, mime, extensions, "", parent, comments)

    def subtest_type(self) -> TestType:
        return TestType.TEXT

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        content = data[absolute_offset:]
        encoding = detect_text_encoding(content)
        if encoding is None:
            return FailedTest(self, offset=absolute_offset, parent=parent_match, message="the data do not appear to "
                                                                                         "be encoded in a text format")
        try:
            value: Union[str, bytes] = content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            value = content
        return MatchedTest(self, offset=absolute_offset, length=len(content), parent=parent_match,
                           value=value)

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


class OctetStreamTest(MagicTest):
    AUTO_REGISTER_TEST = False

    def __init__(
            self,
            offset: Offset = AbsoluteOffset(0),
            mime: Union[str, TernaryExecutableMessage] = "application/octet-stream",
            extensions: Iterable[str] = (),
            message: Union[str, Message] = "data",
            parent: Optional["MagicTest"] = None,
            comments: Iterable[Comment] = ()
    ):
        super().__init__(offset, mime, extensions, message, parent, comments)

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        # Everything is an octet stream!
        return MatchedTest(self, offset=absolute_offset, length=len(data) - absolute_offset, parent=parent_match,
                           value=data)

    def test_flip_endianness(
            self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]
    ) -> TestResult:
        return self.test(data, absolute_offset, parent_match)


TEST_PATTERN: Pattern[str] = re.compile(
    r"^(?P<level>[>]*)(?P<offset>[^\s!][^\s]*)\s+(?P<data_type>[^\s]+)\s+(?P<remainder>.+)$"
)
MIME_PATTERN: Pattern[str] = re.compile(r"^!:mime\s+([^#]+?)\s*(#.*)?$")
EXTENSION_PATTERN: Pattern[str] = re.compile(r"^!:ext\s+([^\s]+)\s*(#.*)?$")


def _split_with_escapes(text: str) -> Tuple[str, str]:
    first_length = 0
    escaped = False
    delimiter_length = 1
    for c in text:
        if escaped:
            escaped = False
        elif c == "\\":
            escaped = True
        elif c == "\n":
            if first_length > 0 and text[first_length - 1] == "\r":
                # strip the \r from trailing \r\n
                first_length -= 1
                delimiter_length = 2
            break
        elif c == " " or c == "\t":
            break
        first_length += 1
    return text[:first_length], text[first_length + delimiter_length:]


class Match:
    """One level 0 test's verdict on a buffer, and the results of the subtests it reached."""

    def __init__(
            self,
            matcher: "MagicMatcher",
            context: MatchContext,
            results: Iterable[TestResult],
            text_encoding: Optional[TextEncodingDescription] = None
    ):
        """
        Args:
            matcher: the matcher that produced this match.
            context: the buffer the tests ran against.
            results: the result of every test that matched.
            text_encoding: the text description libmagic appends to this match's message, or None
                when libmagic would leave the message alone.
        """
        self.matcher: MagicMatcher = matcher
        self.context: MatchContext = context
        self.text_encoding: Optional[TextEncodingDescription] = text_encoding
        self._result_iter: Optional[Iterator[TestResult]] = iter(results)
        self._results: List[TestResult] = []

    @property
    def data(self) -> bytes:
        return self.context.data

    @property
    def only_match_mime(self) -> bool:
        return self.context.only_match_mime

    @property
    def mimetypes(self) -> LazyIterableSet[str]:
        return LazyIterableSet((
            result.test.mime.resolve(self.context) for result in self if result.test.mime is not None)
        )

    @property
    def extensions(self) -> LazyIterableSet[str]:
        def _extensions():
            for result in self:
                yield from result.test.extensions
        return LazyIterableSet(_extensions())

    def explain(self, file: Streamable, ansi_color: Optional[bool] = None) -> str:
        if ansi_color is None:
            ansi_color = sys.stdout.isatty()
        writer = ANSIWriter(use_ansi=ansi_color)
        for result in self:
            result.explain(writer, file=file)
        return str(writer)

    def __bool__(self):
        return any(m for m in self.mimetypes) or any(e for e in self.extensions) or bool(self.message())

    def __len__(self):
        if self._result_iter is not None:
            # we have not yet finished collecting the results
            for _ in self:
                pass
        assert self._result_iter is None
        return len(self._results)

    def __getitem__(self, index: int) -> TestResult:
        while self._result_iter is not None and index >= len(self._results):
            # we have not yet finished collecting the results
            try:
                result = next(self._result_iter)
                self._results.append(result)
                if isinstance(result, IndirectResult):
                    for match in self.matcher.match(self.context[result.offset:]):
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

    def _soft_magic_message(self) -> str:
        """Concatenates the message of every test that matched.

        Returns:
            The description soft magic alone produces, which is empty when nothing printed.
        """
        msg = ""
        for result in self:
            m = result.test.message.resolve(self.context).lstrip()
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
                result_str = result_str.replace("%ll", "%")
                result_str = result_str.replace("%#ll", "0x%")
                try:
                    result_str = result_str % (result.value,)
                except ValueError as e:
                    log.error(f"Error formatting message {result_str!r} with value {result.value!r}: {e!s}")
            result_str = result_str.replace("%%", "%")
            msg = f"{msg}{result_str}"
        return msg

    def message(self) -> str:
        """Describes this match the way `file` describes it.

        Returns:
            What soft magic printed, followed by the text description libmagic appends to a text
            file's description when it applies.
        """
        msg = self._soft_magic_message()
        if self.text_encoding is None:
            return msg
        return self.text_encoding.describe(msg)

    __str__ = message


class DefaultMagicMatcher:
    _DEFAULT_INSTANCE: Optional["MagicMatcher"] = None

    def __get__(self, instance, owner) -> "MagicMatcher":
        if DefaultMagicMatcher._DEFAULT_INSTANCE is None:
            DefaultMagicMatcher._DEFAULT_INSTANCE = MagicMatcher.parse(*MAGIC_DEFS)
        return DefaultMagicMatcher._DEFAULT_INSTANCE

    def __set__(self, instance, value: Optional["MagicMatcher"]):
        DefaultMagicMatcher._DEFAULT_INSTANCE = value

    def __delete__(self, instance):
        DefaultMagicMatcher._DEFAULT_INSTANCE = None


class MagicMatcher:
    DEFAULT_INSTANCE: "MagicMatcher" = DefaultMagicMatcher()  # type: ignore

    def __init__(self, tests: Iterable[MagicTest] = ()):
        self._tests: List[MagicTest] = []
        self.named_tests: Dict[str, NamedTest] = {}
        self._tests_by_mime: Dict[str, Set[MagicTest]] = defaultdict(set)
        self._tests_by_ext: Dict[str, Set[MagicTest]] = defaultdict(set)
        self._tests_that_can_be_indirect: Set[MagicTest] = set()
        self._non_text_tests: Dict[MagicTest, None] = {}
        self._text_tests: Dict[MagicTest, None] = {}
        self._dirty: bool = True
        for test in tests:
            self.add(test)

    @property
    def tests_by_mime(self) -> Dict[str, Set[MagicTest]]:
        self._reassign_test_types()
        return self._tests_by_mime

    @property
    def tests_by_ext(self) -> Dict[str, Set[MagicTest]]:
        self._reassign_test_types()
        return self._tests_by_ext

    @property
    def tests_that_can_be_indirect(self) -> Set[MagicTest]:
        self._reassign_test_types()
        return self._tests_that_can_be_indirect

    @property
    def non_text_tests(self) -> KeysView[MagicTest]:
        """The level 0 tests of `MagicMatcher.match`'s binary pass, in the order it runs them."""
        self._reassign_test_types()
        return self._non_text_tests.keys()

    @property
    def text_tests(self) -> KeysView[MagicTest]:
        """The level 0 tests of `MagicMatcher.match`'s text pass, in the order it runs them."""
        self._reassign_test_types()
        return self._text_tests.keys()

    def add(self, test: Union[MagicTest, Path], test_type: TestType = TestType.UNKNOWN) -> List[MagicTest]:
        if not isinstance(test, MagicTest):
            level_zero_tests, _, tests_with_mime, indirect_tests = self._parse_file(test, self)
            for test in tests_with_mime:
                assert test.can_match_mime
                for ancestor in test.ancestors():
                    ancestor.can_match_mime = True
            for test in indirect_tests:
                assert test.can_be_indirect
                assert test.can_match_mime
                for ancestor in test.ancestors():
                    ancestor.can_be_indirect = True
            for test in level_zero_tests:
                self.add(test, test_type=test_type)
            return list(level_zero_tests)

        if test_type != TestType.UNKNOWN:
            test.test_type = test_type

        self._dirty = True

        if isinstance(test, NamedTest):
            if test.name in self.named_tests:
                raise ValueError(f"A test named {test.name} already exists in this matcher!")
            self.named_tests[test.name] = test
        else:
            self._tests.append(test)

        return [test]

    def _sort_tests(self):
        """Puts the level 0 tests in the order libmagic would run them.

        libmagic sorts strongest first and settles a tie with `MagicTest.libmagic_sort_key`. A tie
        that key cannot settle keeps the order the definitions were read in, which is the order
        libmagic itself hands its entries to ``qsort``: by definition file name
        (``file/src/apprentice.c:1593``) and then by line.
        """
        self._tests.sort(key=lambda test: (
            "" if test.source_info is None else test.source_info.path.name,
            0 if test.source_info is None else test.source_info.line
        ))
        self._tests.sort(key=lambda test: test.libmagic_sort_key(), reverse=True)

    def _reassign_test_types(self):
        if not self._dirty:
            return
        self._dirty = False
        self._sort_tests()
        self._text_tests = {}
        self._non_text_tests = {}
        self._tests_that_can_be_indirect = set()
        self._tests_by_ext = defaultdict(set)
        self._tests_by_mime = defaultdict(set)
        for test in self._tests:
            if test.test_type == TestType.TEXT:
                self._text_tests[test] = None
            else:
                self._non_text_tests[test] = None
            if test.can_be_indirect:
                self._tests_that_can_be_indirect.add(test)
            for mime in test.mimetypes:
                self._tests_by_mime[mime].add(test)
            for ext in test.all_extensions:
                self._tests_by_ext[ext].add(test)

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
            if not any(True for _ in indirect_test.mimetypes)
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
        """Yields the level 0 tests in the order `MagicMatcher.match` runs them."""
        self._reassign_test_types()
        return iter(self._tests)

    @property
    def mimetypes(self) -> Iterable[str]:
        """Returns the set of MIME types this matcher is capable of matching"""
        return self.tests_by_mime.keys()

    @property
    def extensions(self) -> Iterable[str]:
        """Returns the set of extensions this matcher is capable of matching"""
        return self.tests_by_ext.keys()

    def _run_tests(
            self,
            tests: Iterable[MagicTest],
            context: MatchContext,
            text_encoding: Optional[TextEncodingDescription],
            description: str
    ) -> Iterator[Match]:
        """Yields a match for each of `tests` that matches `context`.

        Args:
            tests: the level 0 tests to run.
            context: the buffer to run them against.
            text_encoding: the description of `context`'s text encoding, or None if it is not text.
            description: the label for the progress log.

        Yields:
            One match per test that matched, carrying `text_encoding` if libmagic would append it
            to that test's message.
        """
        for test in log.range(tests, desc=description, unit=" tests", delay=1.0):
            m = Match(matcher=self, context=context, results=test.match(context))
            # the description is how a match is rendered, so it must not make an empty message
            # look like a match
            if m and (not context.only_match_mime or any(t is not None for t in m.mimetypes)):
                if test.appends_text_encoding:
                    m.text_encoding = text_encoding
                yield m

    def match(self, to_match: Union[bytes, BinaryIO, str, Path, MatchContext]) -> Iterator[Match]:
        if isinstance(to_match, bytes):
            to_match = MatchContext(to_match)
        elif not isinstance(to_match, MatchContext):
            to_match = MatchContext.load(to_match)
        text_encoding = TextEncodingDescription.detect(to_match.data)
        yielded = False
        for m in self._run_tests(self.non_text_tests, to_match, text_encoding, "binary matching"):
            yield m
            yielded = True
        # is this a plain text file?
        text_matcher = Match(matcher=self, context=to_match, results=PlainTextTest().match(to_match))
        is_text = text_matcher and (not to_match.only_match_mime or any(t is not None for t in text_matcher.mimetypes))
        if is_text:
            text_matcher.text_encoding = text_encoding
            # this is a text file, so try all of the textual tests:
            for m in self._run_tests(self.text_tests, to_match, text_encoding, "text matching"):
                yield m
                yielded = True
        if not yielded:
            if is_text:
                yield text_matcher
            else:
                yield Match(matcher=self, context=to_match, results=OctetStreamTest().match(to_match))

    @staticmethod
    def parse_test(
            line: str,
            def_file: Path,
            line_number: int,
            parent: Optional[MagicTest] = None,
            matcher: Optional["MagicMatcher"] = None
    ) -> Optional[MagicTest]:
        m = TEST_PATTERN.match(line)
        if not m:
            return None
        level = len(m.group("level"))
        while parent is not None and parent.level >= level:
            parent = parent.parent
        if parent is None and level != 0:
            raise ValueError(f"{def_file!s} line {line_number}: Invalid level for test {line!r}")
        test_str, message = _split_with_escapes(m.group("remainder"))
        message = unescape(message).decode("utf-8")
        try:
            offset = Offset.parse(m.group("offset"))
        except ValueError as e:
            raise ValueError(f"{def_file!s} line {line_number}: {e!s}")
        data_type = m.group("data_type")
        if data_type == "name":
            if parent is not None:
                raise ValueError(f"{def_file!s} line {line_number}: A named test must be at level 0")
            elif test_str in matcher.named_tests:
                raise ValueError(f"{def_file!s} line {line_number}: Duplicate test named {test_str!r}")
            test = NamedTest(name=test_str, offset=offset, message=message)
            matcher.named_tests[test_str] = test
            test.source_info = SourceInfo(def_file, line_number, line)
        else:
            if data_type == "default":
                if parent is None:
                    raise NotImplementedError("TODO: Add support for default tests at level 0")
                test = DefaultTest(offset=offset, message=message, parent=parent)
            elif data_type == "clear":
                if parent is None:
                    raise NotImplementedError("TODO: Add support for clear tests at level 0")
                test = ClearTest(offset=offset, message=message, parent=parent)
            elif data_type == "offset" or data_type.startswith("offset-") or data_type.startswith("offset%"):
                subtraction = 0
                modulo = 0
                if data_type.startswith("offset-"):
                    try:
                        subtraction = parse_numeric(data_type[7:])
                    except ValueError:
                        raise ValueError(f"{def_file!s} line {line_number}: Invalid offset type: {data_type!r}")
                elif data_type.startswith("offset%"):
                    try:
                        modulo = parse_numeric(data_type[7:])
                    except ValueError:
                        raise ValueError(f"{def_file!s} line {line_number}: Invalid offset type: {data_type!r}")
                if test_str.strip() == "x":
                    expected_value: NumericValue = NumericWildcard()
                else:
                    expected_value = IntegerValue.parse(test_str, num_bytes=8)
                test = OffsetMatchTest(offset=offset, value=expected_value, message=message,
                                       parent=parent, subtraction=subtraction, modulo=modulo)
            elif data_type == "json":
                test = JSONTest(offset=offset, message=message, parent=parent)
            elif data_type == "ndjson":
                test = NDJSONTest(offset=offset, message=message, parent=parent)
            elif data_type == "csv":
                test = CSVTest(offset=offset, message=message, parent=parent)
            elif data_type == "indirect" or data_type == "indirect/r":
                test = IndirectTest(matcher=matcher, offset=offset,
                                    relative=m.group("data_type").endswith("r"),
                                    message=message, parent=parent)
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
                    parent=parent,
                    flip_endianness=flip_endianness,
                    late_binding=late_binding
                )
            elif data_type == "der":
                test = DERTest(offset=offset, specification=DERSpecification(test_str),
                               mime=mime_type_for_message(message), message=message,
                               parent=parent)
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
                    parent=parent
                )
        test.source_info = SourceInfo(def_file, line_number, line)
        return test

    STRENGTH_OPS: Dict[str, StrengthOp] = {
        "+": StrengthOp.PLUS,
        "-": StrengthOp.MINUS,
        "*": StrengthOp.TIMES,
        "/": StrengthOp.DIV,
    }

    @staticmethod
    def parse_strength(specification: bytes, current_test: MagicTest):
        """Records a ``!:strength`` factor on the entry that the directive applies to.

        libmagic assigns the factor to ``me->mp[0]``, the level-0 test of the entry, whatever depth
        the directive appears at, and keeps the first factor an entry declares
        (``file/src/apprentice.c:2470-2497``). A ``name`` entry rejects the directive outright.

        Args:
            specification: The rest of the line after ``!:strength``.
            current_test: The most recently parsed test, which locates the entry.
        """
        entry = current_test
        while entry.parent is not None:
            entry = entry.parent
        if isinstance(entry, NamedTest) or entry.strength_op != StrengthOp.NONE:
            return
        spec = specification.strip().decode("utf-8")
        if not spec:
            return
        op = MagicMatcher.STRENGTH_OPS.get(spec[0])
        if op is None:
            factor_str, op = spec, StrengthOp.PLUS
        else:
            factor_str = spec[1:].strip()
        try:
            entry.strength_factor = int(factor_str)
        except ValueError:
            return
        entry.strength_op = op

    @staticmethod
    def _parse_file(
            def_file: Union[str, Path], matcher: "MagicMatcher"
    ) -> Tuple[Iterable[MagicTest], Iterable[UseTest], Set[MagicTest], Set[IndirectTest]]:
        current_test: Optional[MagicTest] = None
        late_bindings: List[UseTest] = []
        level_zero_tests: List[MagicTest] = []
        tests_with_mime: Set[MagicTest] = set()
        indirect_tests: Set[IndirectTest] = set()
        comments: List[Comment] = []
        with open(def_file, "rb") as f:
            for line_number, raw_line in enumerate(f.readlines()):
                line_number += 1
                raw_line = raw_line.lstrip()
                if not raw_line:
                    # skip empty lines
                    comments = []
                    continue
                elif raw_line.startswith(b"#"):
                    # this is a comment
                    try:
                        comments.append(Comment(
                            message=raw_line[1:].strip().decode("utf-8"),
                            source_info=SourceInfo(def_file, line_number, raw_line.decode("utf-8"))
                        ))
                    except UnicodeDecodeError:
                        pass
                    continue
                elif raw_line.startswith(b"!:apple"):
                    continue
                elif raw_line.startswith(b"!:strength"):
                    if current_test is not None:
                        MagicMatcher.parse_strength(raw_line[10:], current_test)
                    continue
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                test = MagicMatcher.parse_test(line, def_file, line_number, current_test, matcher)
                if test is not None:
                    if test.mime is not None:
                        # a test can arrive with a MIME type that no `!:mime` line supplied
                        tests_with_mime.add(test)
                    if isinstance(test, NamedTest):
                        matcher.named_tests[test.name] = test
                    else:
                        if isinstance(test, IndirectTest):
                            indirect_tests.add(test)
                        elif isinstance(test, UseTest) and test.late_binding:
                            late_bindings.append(test)
                        if test.level == 0:
                            level_zero_tests.append(test)
                        test.source_info = SourceInfo(def_file, line_number, line)
                    test.comments = tuple(comments)
                    comments = []
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
