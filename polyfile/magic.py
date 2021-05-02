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
from typing import Callable, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union

DEFS_DIR: Path = Path(__file__).absolute().parent / "magic_defs"

MAGIC_DEFS: List[Path] = [
    path
    for path in DEFS_DIR.glob("*")
    if path.name not in ("COPYING", "magic.mgc") and not path.name.startswith(".")
]


class Match:
    def __init__(self, test: "MagicTest", offset: int, length: int, parent: Optional["Match"] = None):
        self.test: MagicTest = test
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


class Endianness(Enum):
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"


def parse_numeric(text: str) -> int:
    text = text.strip()
    if text.startswith("0x"):
        return int(text, 16)
    elif text.startswith("0") and len(text) > 1:
        return int(text, 8)
    else:
        return int(text)


class Offset(ABC):
    @abstractmethod
    def to_absolute(self, last_match: Optional[Match]) -> int:
        raise NotImplementedError()

    @staticmethod
    def parse(offset: str) -> "Offset":
        if offset.startswith("&"):
            return RelativeOffset(parse_numeric(offset[1:]))
        elif offset.startswith("("):
            raise NotImplementedError("TODO: Implement indirect offsets")
        else:
            return AbsoluteOffset(parse_numeric(offset))


class AbsoluteOffset(Offset):
    def __init__(self, offset: int):
        self.offset: int = offset

    def to_absolute(self, last_match: Optional[Match]) -> int:
        return self.offset

    def __repr__(self):
        return f"{self.__class__.__name__}(offset={self.offset})"

    def __str__(self):
        return str(self.offset)


class RelativeOffset(Offset):
    def __init__(self, relative_offset: int):
        self.relative_offset: int = relative_offset

    def to_absolute(self, last_match: Optional[Match]) -> int:
        return last_match.offset + last_match.length + self.relative_offset

    def __repr__(self):
        return f"{self.__class__.__name__}(relative_offset={self.relative_offset})"

    def __str__(self):
        return f"&{self.relative_offset}"


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
        m = self.test(data, self.offset.to_absolute(parent_match), parent_match)
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


class DataType(ABC, Generic[T]):
    def __init__(self, name: str):
        self.name: str = name

    @abstractmethod
    def parse_expected(self, specification: str) -> T:
        raise NotImplementedError()

    @abstractmethod
    def match(self, data: bytes, expected: T) -> Optional[bytes]:
        raise NotImplementedError()

    @staticmethod
    def parse(fmt: str) -> "DataType":
        if fmt in TYPES_BY_NAME:
            return TYPES_BY_NAME[fmt]
        elif fmt.startswith("string"):
            dt = StringType.parse(fmt)
        elif fmt.startswith("pstring"):
            dt = PascalStringType.parse(fmt)
        elif fmt == "regex":
            dt = RegexType()
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


class StringType(DataType[str]):
    def __init__(self, case_insensitive: bool = False, compact_whitespace: bool = False, optional_blanks: bool = False):
        if not case_insensitive and not compact_whitespace and not optional_blanks:
            name = "string"
        else:
            name = f"string/{['', 'B'][compact_whitespace]}{['', 'b'][optional_blanks]}{['', 'c'][case_insensitive]}"
        super().__init__(name)

    @staticmethod
    def parse_string(specification: str) -> str:
        chars: List[str] = []
        escaped = False
        escapes = {
            "0": "\0",
            " ": " ",
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "\\": "\\"
        }
        for c in specification:
            if escaped:
                escaped = False
                if c not in escapes:
                    raise ValueError(f"Unexpected escape character \"\\{c}\" in {specification!r}")
                chars.append(escapes[c])
            elif c == "\\":
                escaped = True
            else:
                chars.append(c)
        return "".join(chars)

    def parse_expected(self, specification: str) -> str:
        return StringType.parse_string(specification)

    def match(self, data: bytes, expected: str) -> Optional[bytes]:
        e = expected.encode("utf-8")
        if data.startswith(e):
            return e
        else:
            return None

    STRING_TYPE_FORMAT: re.Pattern = re.compile(r"^string(/[Bbc]*)?$")

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
            case_insensitive="c" in options,
            compact_whitespace="B" in options,
            optional_blanks="b" in options
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
        return StringType.parse_string(specification).encode("utf-8")

    def match(self, data: bytes, expected: bytes) -> Optional[bytes]:
        if len(data) < self.byte_length:
            return None
        elif self.byte_length == 1:
            length = data[0]
        elif self.byte_length == 2:
            if self.endianness == Endianness.BIG:
                length = struct.unpack(">H", data[:2])
            else:
                length = struct.unpack("<H", data[:2])
        elif self.endianness == Endianness.BIG:
            length = struct.unpack(">I", data[:4])
        else:
            length = struct.unpack("<I", data[:4])
        if self.count_includes_length:
            length -= self.byte_length
        if len(data) < self.byte_length + length:
            return None
        elif len(expected) != length:
            return None
        if data[self.byte_length:self.byte_length + length] == expected:
            return expected
        else:
            return None

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


class RegexType(DataType[re.Pattern]):
    def __init__(self):
        super().__init__("regex")

    def parse_expected(self, specification: str) -> re.Pattern:
        return re.compile(specification.encode("utf-8"))

    def match(self, data: bytes, expected: re.Pattern) -> Optional[bytes]:
        m = expected.match(data)
        if m:
            return m.group(0)
        else:
            return None


BASE_NUMERIC_TYPES_BY_NAME: Dict[str, "BaseNumericDataType"] = {}


class BaseNumericDataType(Enum):
    BYTE = ("byte", "b", 1)
    SHORT = ("short", "h", 2)
    LONG = ("long", "l", 4)
    QUAD = ("quad", "i", 8)
    FLOAT = ("float", "f", 4)
    DOUBLE = ("double", "d", 8)

    def __init__(self, name: str, struct_fmt: str, num_bytes: int):
        self.struct_fmt: str = struct_fmt
        self.num_bytes: int = num_bytes
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
            and_with: Optional[int] = None
    ):
        super().__init__(name)
        self.base_type: BaseNumericDataType = base_type
        self.unsigned: bool = unsigned
        self.endianness: Endianness = endianness
        self.and_with = and_with

    def parse_expected(self, specification: str) -> NumericValue:
        if specification == "x":
            return NumericWildcard()
        else:
            return NumericValue.parse(specification, self.base_type.num_bytes)

    def match(self, data: bytes, expected: NumericValue) -> Optional[bytes]:
        if self.unsigned and self.base_type not in (BaseNumericDataType.DOUBLE, BaseNumericDataType.FLOAT):
            struct_fmt = self.base_type.value.upper()
        else:
            struct_fmt = self.base_type.value
        struct_fmt = f"{self.endianness.value}{struct_fmt}"
        value = struct.unpack(struct_fmt, data)
        if self.and_with is not None:
            value &= self.and_with
        if expected.test(value):
            return data[:self.base_type.num_bytes]
        else:
            return None

    @staticmethod
    def parse(fmt: str) -> "DataType":
        name = fmt
        if fmt.startswith("u"):
            if fmt.startswith("double") or fmt.startswith("float"):
                raise ValueError(f"{name[1:]} cannot be unsigned")
            unsigned = True
            fmt = fmt[1:]
        else:
            unsigned = False
        if fmt.startswith("le"):
            endianness = Endianness.LITTLE
            fmt = fmt[2:]
        elif fmt.startswith("be"):
            endianness = Endianness.BIG
            fmt = fmt[2:]
        else:
            endianness = Endianness.NATIVE
        amp_pos = fmt.find("&")
        if amp_pos > 0:
            and_with: Optional[int] = parse_numeric(fmt[amp_pos+1:])
            fmt = fmt[:amp_pos]
        else:
            and_with = None
        if fmt not in BASE_NUMERIC_TYPES_BY_NAME:
            raise ValueError(f"Invalid numeric data type: {name!r}")
        return NumericDataType(
            name=name,
            base_type=BASE_NUMERIC_TYPES_BY_NAME[fmt],
            unsigned=unsigned,
            endianness=endianness,
            and_with=and_with
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
        matched_bytes = self.data_type.match(data[absolute_offset:], self.constant)
        if matched_bytes is not None:
            return Match(self, absolute_offset, len(matched_bytes), parent=parent_match)
        else:
            return None


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
            return Match(self, parent_match.offset + parent_match.length, 0, parent=parent_match)
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
            parent: Optional["MagicTest"] = None
    ):
        super().__init__(offset=offset, mime=mime, extensions=extensions, message=message, parent=parent)
        self.named_test: NamedTest = named_test

    def _match(
            self,
            data: bytes,
            only_match_mime: bool = False,
            parent_match: Optional[Match] = None
    ) -> Iterator[Match]:
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
        if parent_match is None:
            return Match(self, absolute_offset, 0)
        else:
            return None


TEST_PATTERN: re.Pattern = re.compile(
    r"^(?P<level>[>]*)(?P<offset>&?-?(0x[\dA-Za-z]+|\d+))\s+(?P<data_type>[^\s]+)\s+(?P<remainder>.+)$"
)
MIME_PATTERN: re.Pattern = re.compile(r"^!:mime\s+([^\s]+)\s*$")
EXTENSION_PATTERN: re.Pattern = re.compile(r"^!:ext\s+([^\s]+)\s*$")


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


class MagicDefinition:
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
    def parse(def_file: Union[str, Path]) -> "MagicDefinition":
        current_test: Optional[MagicTest] = None
        definition = MagicDefinition([])
        with open(def_file, "rb") as f:
            for line_number, raw_line in enumerate(f.readlines()):
                line_number += 1
                raw_line = raw_line.strip()
                if not raw_line or raw_line.startswith(b"#"):
                    # skip empty lines and comments
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
                    message = message.lstrip()
                    try:
                        offset = Offset.parse(m.group("offset"))
                    except ValueError as e:
                        raise ValueError(f"{def_file!s} line {line_number}: {e!s}")
                    if m.group("data_type") == "name":
                        if current_test is not None:
                            raise ValueError(f"{def_file!s} line {line_number}: A named test must be at level 0")
                        elif test in definition.named_tests:
                            raise ValueError(f"{def_file!s} line {line_number}: Duplicate test named {test!r}")
                        test = NamedTest(name=test_str, offset=offset, message=message)
                        definition.named_tests[test_str] = test
                    else:
                        if m.group("data_type") == "default":
                            if current_test is None:
                                raise NotImplementedError("TODO: Add support for default tests at level 0")
                            test = DefaultTest(offset=offset, message=message, parent=current_test)
                        elif m.group("data_type") == "use":
                            if test_str not in definition.named_tests:
                                raise ValueError(f"{def_file!s} line {line_number}: Unknown test named {test_str!r}")
                            test = UseTest(
                                definition.named_tests[test_str],
                                offset=offset,
                                message=message,
                                parent=current_test
                            )
                        else:
                            try:
                                data_type = DataType.parse(m.group("data_type"))
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
                        definition.tests.append(test)
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
        return definition
