"""Runtime field specialization retains concrete subclasses and eager metadata."""

from io import BytesIO

import pytest

from polyfile.structs import (
    ByteField,
    Constant,
    Endianness,
    IntField,
    Struct,
    StructReadError,
    UInt8,
)


class Packet(Struct):
    count: UInt8
    payload: ByteField["count"]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    end: Constant[b"!"]  # ty: ignore[invalid-type-form]  # Runtime DSL.


def test_struct_read_keeps_the_concrete_class_and_field_positions() -> None:
    packet = Packet.read(BytesIO(b"\x03abc!"))
    assert isinstance(packet, Packet)
    assert (packet.start_offset, packet.num_bytes) == (0, 5)
    assert packet.count == 3
    assert (packet.count.start_offset, packet.count.num_bytes) == (0, 1)
    assert packet.payload == b"abc"
    assert (packet.payload.start_offset, packet.payload.num_bytes) == (1, 3)
    assert packet.end == b"!"


@pytest.mark.parametrize("data", [b"\x03ab", b"\x03abc?"])
def test_struct_read_rejects_truncated_and_incorrect_fields(data: bytes) -> None:
    with pytest.raises(StructReadError):
        Packet.read(BytesIO(data))


def test_integer_specialization_retains_a_user_subclass() -> None:
    class Integer(IntField):
        pass

    field = Integer[2, False, Endianness.BIG]
    value = field.read(Struct(), "value", BytesIO(b"\x01\x02"), Endianness.BIG)
    assert isinstance(value, Integer)
    assert type(value) is field
    assert value == 258
    assert field.size == 2
    assert field.signed is False
    assert field.endianness is Endianness.BIG


def test_byte_specialization_retains_a_user_subclass() -> None:
    class Bytes(ByteField):
        pass

    field = Bytes[2]
    value = field.read(Struct(), "value", BytesIO(b"ab"), Endianness.NATIVE)
    assert isinstance(value, Bytes)
    assert type(value) is field
    assert value == b"ab"


def test_missing_size_reference_has_a_field_specific_error() -> None:
    field = ByteField["missing"]
    with pytest.raises(StructReadError, match="value.*missing"):
        field.read(Struct(), "value", BytesIO(b"ab"), Endianness.NATIVE)
