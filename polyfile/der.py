from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Dict, IO, Optional, Type, TypeVar, Union

from .kaitai.parser import KaitaiParser
from .kaitai.parsers.asn1_der import Asn1Der

DER_PARSER = KaitaiParser.load("serialization/asn1/asn1_der.ksy")

C = TypeVar("C", bound="DERQuery")


class DERQuery:
    def __init__(self, der: Asn1Der, parent: Optional["DERQuery"] = None):
        self.der: Asn1Der = der  # type: ignore
        self.parent = parent

    @property
    def type_value(self) -> int:
        if isinstance(self.der.type_tag, int):
            return self.der.type_tag
        else:
            return self.der.type_tag.value

    @property
    def is_seq(self) -> bool:
        return self.type_value == 0x10 or self.type_value == 0x30

    @property
    def is_set(self) -> bool:
        return self.type_value == 0x31

    @classmethod
    def parse(cls: Type[C], data: Union[bytes, str, Path, BytesIO]) -> C:
        ast = DER_PARSER.parse(data).ast
        if isinstance(ast.obj, DER_PARSER.struct_type):
            return DERQuery(ast.obj)
        else:
            raise ValueError("Error parsing DER")


T = TypeVar("T", bound="Tag")


class Tag(ABC):
    TAGS: Dict[str, Type["Tag"]] = {}
    name: str

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "name") or cls.name is None:
            raise TypeError(f"DERTag subclass {cls.__name__} must define the `name` member variable")
        elif cls.name in Tag.TAGS:
            raise TypeError(f"DERTag name {cls.name} for {cls.__name__} is already assigned to "
                            f"{TAGS[cls.name].__name__}")
        Tag.TAGS[cls.name] = cls

    @classmethod
    @abstractmethod
    def with_value(cls: Type[T], value: str = "", number_modifier: Optional[int] = None) -> T:
        raise NotImplementedError()

    @abstractmethod
    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()

    @staticmethod
    def parse(tag: str) -> "Tag":
        original_tag = tag
        equals_index = tag.find("=")
        if equals_index > 0:
            value = tag[equals_index+1:]
            tag = tag[:equals_index]
        else:
            value = ""
        if tag in Tag.TAGS:
            return Tag.TAGS[tag].with_value(value)
        # Does it have a number modifier?
        number_modifier = ""
        while tag and tag[-1].isnumeric():
            number_modifier = f"{tag[-1]}{number_modifier}"
            tag = tag[:-1]
        if tag in Tag.TAGS:
            return Tag.TAGS[tag].with_value(value, number_modifier=int(number_modifier))
        if original_tag != tag:
            raise ValueError(f"Unknown DER tag {tag!r} in {original_tag!r}")
        else:
            raise ValueError(f"Unknown DER tag {tag!r}")

class BareTagMixin:
    @classmethod
    def with_value(cls: Type[T], value: str = "", number_modifier: Optional[int] = None) -> T:
        if value:
            raise ValueError(f"{cls.name} is not expected to have a value")
        elif number_modifier:
            raise ValueError(f"{cls.name} is not expected to have a number modifier")
        return cls()


class Seq(BareTagMixin, Tag):
    name = "seq"

    def test(self, query: DERQuery) -> DERQuery:
        if not query.is_seq:
            raise ValueError(f"{query.der.type_tag!r} is not a sequence type")
        return DERQuery(query.der.body, parent=query)


class Set(BareTagMixin, Tag):
    name = "set"

    def test(self, query: DERQuery) -> DERQuery:
        if not query.is_set:
            raise ValueError(f"{query.der.type_tag!r} is not a set type")
        return DERQuery(query.der.body, parent=query)


class Int(Tag):
    name = "int"

    def __init__(self, value: Optional[int], number_modifier: int):
        self.value: Optional[int] = value
        self.number_modifier: int = number_modifier

    @property
    def is_wildcard(self) -> bool:
        return self.value is None

    @classmethod
    def with_value(cls: Type[T], value: str = "", number_modifier: Optional[int] = None) -> T:
        if value.lower() == "x":
            # wildcard
            obj_value: Optional[int] = None
        else:
            obj_value = int(value, 16)
        if number_modifier is None:
            raise ValueError(f"{cls.name} requires a number modifier")
        return cls(value, number_modifier)

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class ObjId(Int):
    name = "obj_id"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class WildcardOnlyMixin:
    @classmethod
    def with_value(cls: Type[T], value: str = "", number_modifier: Optional[int] = None) -> T:
        if value and value.lower() != "x":
            raise ValueError(f"invalid value for {cls.name}: {value!r}")
        if number_modifier is not None:
            raise ValueError(f"{cls.name} does not support a number modifier")
        return cls()


class PrtStr(WildcardOnlyMixin, Tag):
    name = "prt_str"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class UTF8Str(WildcardOnlyMixin, Tag):
    name = "utf8_str"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class IA5Str(WildcardOnlyMixin, Tag):
    name = "ia5_str"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class Null(BareTagMixin, Tag):
    name = "null"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class UTCTime(WildcardOnlyMixin, Tag):
    name = "utc_time"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()


class EOC(BareTagMixin, Tag):
    name = "eoc"

    def test(self, query: DERQuery) -> DERQuery:
        raise NotImplementedError()
