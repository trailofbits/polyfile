import sys
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from enum import Enum
import struct as python_struct
from typing import BinaryIO, Optional, Tuple, Type, TypeVar, Union

if sys.version_info < (3, 7):
    from typing import Dict as OrderedDictType
elif sys.version_info < (3, 9):
    # typing.OrderedDict was added in Python 3.7
    from typing import OrderedDict as OrderedDictType
else:
    # In Python 3.9 and newer, collections.OrderedDict is subscriptable
    OrderedDictType = OrderedDict


class Endianness(Enum):
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"
    NETWORK = "!"


class SizeReference:
    def __init__(self, size_member_name: str):
        self.size_member_name: str = size_member_name

    def __str__(self):
        return self.size_member_name


T = TypeVar("T")


class AnnotatedType(ABCMeta):
    endianness: Optional[Endianness] = None

    def __class_getitem__(mcs, endianness: Optional[Endianness]) -> "AnnotatedType":
        name = mcs.__name__
        if endianness is not None:
            name = f"{name}{endianness.name}"
        else:
            name = f"{name}DefaultEndianness"
        ret = type(name, (AnnotatedType,), {
            "endianness": endianness
        })
        return ret


def struct_fmt_int(size: int, signed: bool) -> str:
    if size == 1:
        fmt = "b"
    elif size == 2:
        fmt = "h"
    elif size == 4:
        fmt = "i"
    elif size == 8:
        fmt = "q"
    else:
        raise TypeError(f"Unsupported struct integer size: {size}")
    if not signed:
        fmt = fmt.upper()
    return fmt


class AnnotatedSizeType(AnnotatedType):
    size: Union[int, SizeReference]

    def __class_getitem__(mcs: T, size: Union[int, str, SizeReference]) -> T:
        if isinstance(size, str):
            size = SizeReference(size)
        name = f"{mcs.__name__}{size!s}"
        return type(name, (mcs,), {
            "endianness": None,
            "size": size
        })


IntTypeArgs = Union[
    Tuple[Union[int, str, SizeReference], bool],
    Tuple[Union[int, str, SizeReference], bool, Optional[Endianness]]
]


class AnnotatedIntType(AnnotatedType):
    size: Union[int, SizeReference]
    signed: bool

    def __class_getitem__(mcs: T, args: IntTypeArgs) -> T:
        if len(args) == 3:
            size, signed, endianness = args
        elif len(args) == 2:
            size, signed = args
            endianness = None
        else:
            raise TypeError(f"{mcs.__name__}[{','.join(map(repr, args))}] must have either two or three arguments")
        if isinstance(size, str):
            size = SizeReference(size)
        if endianness is None:
            endianness_name = "DefaultEndianness"
        else:
            endianness_name = endianness.name
        if signed:
            signed_name = "Signed"
        else:
            signed_name = "Unsigned"
        name = f"{signed_name}{mcs.__name__}{endianness_name}{size!s}"
        endianness_type = super().__class_getitem__(endianness)
        return type(name, (mcs, endianness_type), {
            "size": size,
            "signed": signed
        })

    def __str__(self):
        if self.endianness is not None:
            s = f"{self.endianness.name.lower()} endian "
        else:
            s = ""
        s = f"{s}{self.size}-byte "
        if not self.signed:
            s = f"{s}un"
        s = f"{s}signed integer"
        return s


class Field(metaclass=AnnotatedType):
    start_offset: int
    num_bytes: int

    @classmethod
    @abstractmethod
    def read(cls: Type[T], struct: "Struct", field_name: str, stream: BinaryIO, endianness: Endianness) -> T:
        raise NotImplementedError()


class IntField(int, Field, metaclass=AnnotatedIntType):
    def __class_getitem__(cls: T, args: IntTypeArgs) -> T:
        if not isinstance(args[0], int):
            raise TypeError("An int field must have a constant integer size")

        class BoundIntField(cls, metaclass=AnnotatedIntType[args]):
            pass

        return BoundIntField

    @classmethod
    def read(cls: Type[T], struct: "Struct", field_name: str, stream: BinaryIO, endianness: Endianness) -> T:
        data = stream.read(cls.size)
        if len(data) != cls.size:
            raise StructReadError(f"Reached the end of stream while expecting {cls!s} for "
                                  f"{struct.__class__.__name__}.{field_name}")
        try:
            return cls(python_struct.unpack(f"{endianness.value}{struct_fmt_int(cls.size, cls.signed)}", data)[0])
        except python_struct.error:
            raise StructReadError(f"Error unpacking {cls!s} from {data!r} for {struct.__class__.__name__}.{field_name}")


class ByteField(bytes, Field, metaclass=AnnotatedSizeType):
    def __class_getitem__(cls: T, size: Union[str, int, SizeReference]) -> T:
        class BoundByteField(cls, metaclass=AnnotatedSizeType[size]):
            pass
        return BoundByteField

    @classmethod
    def read(cls: Type[T], struct: "Struct", field_name: str, stream: BinaryIO, endianness: Endianness) -> T:
        if isinstance(cls.size, SizeReference):
            if not hasattr(struct, cls.size.size_member_name):
                raise StructReadError(f"{struct.__class__.__name__}.{field_name} has a size bound to field "
                                      f"{cls.size.size_member_name!r}, which does not exist")
            size: int = getattr(struct, cls.size.size_member_name)
            if size is None or not isinstance(size, int):
                raise StructReadError(f"{struct.__class__.__name__}.{field_name} has a size bound to "
                                      f"{struct.__class__.__name__}.{field_name}={size}, which is not an int")
        else:
            size = cls.size
        data = stream.read(size)
        if len(data) != size:
            raise StructReadError(f"Reached the end of stream while expecting {size} bytes for "
                                  f"{struct.__class__.__name__}.{field_name}")
        return cls(data)


Int8 = IntField[1, True]
Int16 = IntField[2, True]
Int32 = IntField[4, True]
Int64 = IntField[8, True]
UInt8 = IntField[1, False]
UInt16 = IntField[2, False]
UInt32 = IntField[4, False]
UInt64 = IntField[8, False]
Int8BE = IntField[1, True, Endianness.BIG]
Int16BE = IntField[2, True, Endianness.BIG]
Int32BE = IntField[4, True, Endianness.BIG]
Int64BE = IntField[8, True, Endianness.BIG]
UInt8BE = IntField[1, False, Endianness.BIG]
UInt16BE = IntField[2, False, Endianness.BIG]
UInt32BE = IntField[4, False, Endianness.BIG]
UInt64BE = IntField[8, False, Endianness.BIG]
Int8LE = IntField[1, True, Endianness.LITTLE]
Int16LE = IntField[2, True, Endianness.LITTLE]
Int32LE = IntField[4, True, Endianness.LITTLE]
Int64LE = IntField[8, True, Endianness.LITTLE]
UInt8LE = IntField[1, False, Endianness.LITTLE]
UInt16LE = IntField[2, False, Endianness.LITTLE]
UInt32LE = IntField[4, False, Endianness.LITTLE]
UInt64LE = IntField[8, False, Endianness.LITTLE]


class Constant(ByteField):
    constant: bytes

    def __class_getitem__(cls: T, to_match: bytes) -> T:
        c = super().__class_getitem__(len(to_match))
        setattr(c, "constant", to_match)
        return c

    @classmethod
    def read(cls: Type[T], struct: "Struct", field_name: str, stream: BinaryIO, endianness: Endianness) -> T:
        ret = super().read(struct, field_name, stream, endianness)
        if ret != cls.constant:
            raise StructReadError(f"Expected {cls.constant!r} but instead found {ret!r} while parsing "
                                  f"{struct.__class__.__name__}.{field_name}")
        return ret


class StructMeta(ABCMeta):
    fields: OrderedDictType[str, Type[Field]]

    def __init__(cls, name, bases, clsdict):
        cls.fields = OrderedDict()
        if "__annotations__" in clsdict:
            for field_name, field_type in clsdict["__annotations__"].items():
                if isinstance(field_type, type) and issubclass(field_type, Field):
                    if field_name in cls.fields:
                        raise TypeError(f"Invalid redeclaration of struct field {field_name} in {cls.__name__}")
                    cls.fields[field_name] = field_type
        super().__init__(name, bases, clsdict)


class StructError(RuntimeError):
    pass


class StructReadError(StructError):
    pass


class Struct(metaclass=StructMeta):
    endianness: Endianness = Endianness.NATIVE
    start_offset: int
    num_bytes: int

    @classmethod
    def read(cls: Type[T], stream: BinaryIO) -> T:
        ret = cls()
        setattr(ret, "start_offset", stream.tell())
        for field_name, field in cls.fields.items():
            if field.__class__.endianness is not None:
                endianness = field.__class__.endianness
            else:
                endianness = cls.endianness
            offset_before = stream.tell()
            value = field.read(ret, field_name, stream, endianness)
            setattr(ret, field_name, value)
            setattr(value, "start_offset", offset_before)
            setattr(value, "num_bytes", stream.tell() - offset_before)
        setattr(ret, "num_bytes", stream.tell() - ret.start_offset)
        return ret


if __name__ == "__main__":
    from io import BytesIO

    class Test(Struct):
        foo: UInt8LE
        bar: Int32LE
        data: ByteField["foo"]

    test = Test.read(BytesIO(b"\x03234567890"))
    print(test.foo, test.bar, test.data)
