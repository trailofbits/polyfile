"""Serialize acyclic Python values without recursive traversal.

This retained library utility has no internal analysis-path callers. It supports
None, bool, nonnegative int, str, bytes, list, tuple, dict, set, frozenset, and
classes registered with ``serializable``. Shared references retain identity;
cycles raise EncodingError. Do not mutate a value while it is being serialized.

Custom classes supply constructor arguments through ``serialize()``. Register
the same classes in the same order before reading and writing: class identifiers
are process-local registration numbers. The wire format has no version header,
and its byte representation is not canonical. Existing unsigned, acyclic records
remain readable. Register only trusted classes and load only trusted data:
decoding invokes their constructors and does not enforce resource limits.

Binary streams need read/write operations at their current position, without
seeking. Short reads and writes are supported; operations that make no progress
fail. ``load`` consumes the stream through EOF. I/O failures propagate, and an
output stream can contain a partial record if encoding or writing fails.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
import io
from itertools import chain
from typing import Protocol, TypeVar, cast


SerializableT = TypeVar("SerializableT")
PairT = TypeVar("PairT")
ENCODINGS_BY_TYPE: dict[type[object], "EncodeTypes"] = {}
ENCODINGS_BY_ID: dict[int, "EncodeTypes"] = {}
CUSTOM_ENCODINGS: dict[type[object], int] = {}
CUSTOM_ENCODINGS_BY_ID: dict[int, type[object]] = {}


class EncodingError(RuntimeError):
    """An unsupported value or malformed serialized record prevents conversion."""


class BinaryReader(Protocol):
    """Minimal binary input contract used by the serializer."""

    def read(self, size: int = -1, /) -> bytes: ...


class BinaryWriter(Protocol):
    """Minimal binary output contract; writes report the number of accepted bytes."""

    def write(self, data: bytes, /) -> int | None: ...


class _Serializable(Protocol):
    def serialize(self) -> Iterable[object]: ...


def _integer_description(value: int) -> str:
    if value.bit_length() > 64:
        return f"{value.bit_length()}-bit integer"
    return str(value)


def _write_all(data: bytes, stream: BinaryWriter) -> None:
    position = 0
    size = min(len(data), 64 * 1024)
    while position < len(data):
        end = position + size
        chunk = data[position:end]
        written = stream.write(chunk)
        if not isinstance(written, int) or not 0 < written <= len(chunk):
            raise EncodingError("Binary stream write did not make valid forward progress")
        position += written
        if written < len(chunk):
            size = written
        else:
            size = min(size * 2, len(data) - position, 64 * 1024)


def _read_chunk(stream: BinaryReader, size: int) -> bytes:
    data = stream.read(size)
    if not isinstance(data, bytes) or len(data) > size:
        raise EncodingError("Binary stream read must return at most the requested bytes")
    return data


def _read_exact(stream: BinaryReader, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        chunk = _read_chunk(stream, min(size - len(result), 64 * 1024))
        if not chunk:
            expected = _integer_description(size)
            raise EncodingError(
                f"Truncated record: expected {expected} bytes, received {len(result)}"
            )
        result.extend(chunk)
    return bytes(result)


def write_int(i: int, stream: BinaryWriter) -> None:
    """Write a nonnegative integer using the existing seven-bit encoding.

    Args:
        i: Integer to encode.
        stream: Writable binary output at the desired position.

    Raises:
        EncodingError: If the value is not a nonnegative integer or output makes no progress.
    """
    if not isinstance(i, int) or i < 0:
        raise EncodingError("Integer serialization requires a nonnegative integer")
    bits = max(i.bit_length(), 1)
    for bit_group in reversed(range((bits - 1) // 7 + 1)):
        byte = (i >> (bit_group * 7)) & 0b01111111
        if bit_group == 0:
            byte |= 0b10000000
        _write_all(bytes([byte]), stream)


def _read_integer(stream: BinaryReader, prefix: bytes = b"") -> int:
    value = 0
    byte = prefix or _read_exact(stream, 1)
    while True:
        value = (value << 7) | (byte[0] & 0b01111111)
        if byte[0] & 0b10000000:
            return value
        byte = _read_exact(stream, 1)


def read_int(stream: BinaryReader) -> int:
    """Read a seven-bit encoded nonnegative integer.

    Args:
        stream: Binary input at the beginning of an encoded integer.

    Raises:
        EncodingError: If the integer is truncated or input is not binary.
    """
    return _read_integer(stream)


def encode_int(i: int, _: Mapping[int, int] | None, stream: BinaryWriter) -> None:
    write_int(i, stream)


def decode_int(_: Mapping[int, object], stream: BinaryReader) -> int:
    return read_int(stream)


def encode_bytes(s: bytes, _: Mapping[int, int] | None, stream: BinaryWriter) -> None:
    write_int(len(s), stream)
    _write_all(s, stream)


def encode_string(s: str, _: Mapping[int, int] | None, stream: BinaryWriter) -> None:
    """Write UTF-8 text, reporting unencodable strings as EncodingError.

    Args:
        s: Text to encode.
        _: The unused object identifier table.
        stream: Writable binary output at the desired position.

    Raises:
        EncodingError: If the text contains an unencodable surrogate.
    """
    try:
        encoded = s.encode("utf-8")
    except UnicodeEncodeError as error:
        raise EncodingError("Cannot encode STRING value as UTF-8") from error
    encode_bytes(encoded, None, stream)


def decode_bytes(_: Mapping[int, object] | None, stream: BinaryReader) -> bytes:
    return _read_exact(stream, read_int(stream))


def decode_string(_: Mapping[int, object], stream: BinaryReader) -> str:
    return decode_bytes(None, stream).decode("utf-8")


def encode_list(lst: Iterable[object], obj_ids: Mapping[int, int], stream: BinaryWriter) -> None:
    for obj in lst:
        write_int(obj_ids[id(obj)], stream)
    write_int(EncodeTypes.END.encoding_id, stream)


encode_tuple = encode_list
encode_set = encode_list
encode_frozenset = encode_list


def _decode_to_end(stream: BinaryReader) -> Iterator[int]:
    while True:
        identity = read_int(stream)
        if identity == EncodeTypes.END.encoding_id:
            return
        yield identity


def pairwise(iterable: Iterable[PairT]) -> Iterator[tuple[PairT, PairT]]:
    """Yield adjacent pairs, rejecting an unmatched final value.

    Args:
        iterable: Values to consume in pairs.

    Yields:
        Each consecutive pair of values.

    Raises:
        EncodingError: If an unmatched final value remains.
    """
    iterator = iter(iterable)
    for first in iterator:
        try:
            second = next(iterator)
        except StopIteration as error:
            raise EncodingError("Pairwise input has an unmatched final value") from error
        yield first, second


def decode_list(objs: Mapping[int, object], stream: BinaryReader) -> list[object]:
    return [_reference(objs, identity) for identity in _decode_to_end(stream)]


def _reference(objs: Mapping[int, object], identity: int) -> object:
    try:
        return objs[identity]
    except KeyError as error:
        label = _integer_description(identity)
        raise EncodingError(f"Undefined object reference #{label}") from error


def decode_tuple(objs: Mapping[int, object], stream: BinaryReader) -> tuple[object, ...]:
    return tuple(decode_list(objs, stream))


def decode_set(objs: Mapping[int, object], stream: BinaryReader) -> set[object]:
    return set(decode_list(objs, stream))


def decode_frozenset(objs: Mapping[int, object], stream: BinaryReader) -> frozenset[object]:
    return frozenset(decode_list(objs, stream))


def encode_dict(
    d: Mapping[object, object],
    obj_ids: Mapping[int, int],
    stream: BinaryWriter,
) -> None:
    for key, item in d.items():
        write_int(obj_ids[id(key)], stream)
        write_int(obj_ids[id(item)], stream)
    write_int(EncodeTypes.END.encoding_id, stream)


def decode_dict(objs: Mapping[int, object], stream: BinaryReader) -> dict[object, object]:
    return {
        _reference(objs, key): _reference(objs, value)
        for key, value in pairwise(_decode_to_end(stream))
    }


def encode_none(*args: object, **kwargs: object) -> None:
    pass


def decode_none(*args: object, **kwargs: object) -> None:
    return None


def encode_bool(b: bool, _: Mapping[int, int], stream: BinaryWriter) -> None:
    write_int(int(b), stream)


def decode_bool(_: Mapping[int, object], stream: BinaryReader) -> bool:
    value = read_int(stream)
    if value not in (0, 1):
        received = _integer_description(value)
        raise EncodingError(f"Boolean record must contain 0 or 1, received {received}")
    return bool(value)


def _custom_arguments(value: object) -> tuple[object, ...]:
    try:
        return tuple(cast(_Serializable, value).serialize())
    except Exception as error:
        raise EncodingError(
            f"Cannot serialize constructor arguments for {type(value).__name__}"
        ) from error


def encode_custom(c: object, obj_ids: Mapping[int, int], stream: BinaryWriter) -> None:
    write_int(CUSTOM_ENCODINGS[type(c)], stream)
    encode_list(_custom_arguments(c), obj_ids, stream)


def decode_custom(objs: Mapping[int, object], stream: BinaryReader) -> object:
    class_id = read_int(stream)
    custom_type = CUSTOM_ENCODINGS_BY_ID.get(class_id)
    if custom_type is None:
        raise EncodingError(f"Unknown registered class identifier {_integer_description(class_id)}")
    arguments = decode_list(objs, stream)
    try:
        return cast(Callable[..., object], custom_type)(*arguments)
    except Exception as error:
        raise EncodingError(f"Cannot construct registered class {custom_type.__name__}") from error


class _EndObject:
    pass


class _CustomObject:
    pass


def serializable(SerializableClass: type[SerializableT]) -> type[SerializableT]:
    """Register a trusted class whose serialize method returns constructor arguments.

    Repeated registration of the same class preserves its identifier. Readers
    must register classes in the same order as writers.

    Args:
        SerializableClass: Class with a callable instance ``serialize()`` method.

    Returns:
        The original class, suitable for use as a decorator.

    Raises:
        ValueError: If the value is not a class with a callable serialize method.
    """
    if not isinstance(SerializableClass, type):
        raise ValueError("Serializable registration requires a class")
    if not callable(getattr(SerializableClass, "serialize", None)):
        raise ValueError(
            f"Serializable class {SerializableClass} needs a callable serialize method"
        )
    if SerializableClass not in CUSTOM_ENCODINGS:
        class_id = len(CUSTOM_ENCODINGS)
        CUSTOM_ENCODINGS[SerializableClass] = class_id
        CUSTOM_ENCODINGS_BY_ID[class_id] = SerializableClass
    return SerializableClass


class EncodeTypes(Enum):
    END = (0, _EndObject, None, None, None)
    NONE = (1, type(None), encode_none, decode_none, lambda _: ())
    BOOL = (2, bool, encode_bool, decode_bool, lambda _: ())
    INT = (3, int, encode_int, decode_int, lambda _: ())
    STRING = (4, str, encode_string, decode_string, lambda _: ())
    BYTES = (5, bytes, encode_bytes, decode_bytes, lambda _: ())
    LIST = (6, list, encode_list, decode_list, iter)
    TUPLE = (7, tuple, encode_tuple, decode_tuple, iter)
    DICT = (8, dict, encode_dict, decode_dict, lambda value: chain(value.keys(), value.values()))
    SET = (9, set, encode_set, decode_set, iter)
    FROZENSET = (10, frozenset, encode_frozenset, decode_frozenset, iter)
    CUSTOM = (11, _CustomObject, encode_custom, decode_custom, lambda value: value.serialize())

    def __init__(
        self,
        encoding_id: int,
        source_type: type[object],
        encoding_function: Callable[..., None] | None,
        decoding_function: Callable[..., object] | None,
        children: Callable[..., Iterable[object]] | None,
    ):
        self.encoding_id = encoding_id
        self.source_type = source_type
        self.encode = encoding_function
        self.decode = decoding_function
        self.children = children
        ENCODINGS_BY_TYPE[source_type] = self
        ENCODINGS_BY_ID[encoding_id] = self

    @staticmethod
    def get_by_type(source_type: type[object]) -> "EncodeTypes | None":
        return ENCODINGS_BY_TYPE.get(source_type)

    @staticmethod
    def get_by_id(encoding_id: int) -> "EncodeTypes | None":
        return ENCODINGS_BY_ID.get(encoding_id)


@dataclass(frozen=True)
class _Record:
    original: object
    value: object
    encoding: EncodeTypes
    children: tuple[object, ...]


def _record(value: object) -> _Record:
    encoding = EncodeTypes.get_by_type(type(value))
    if encoding is None:
        if type(value) not in CUSTOM_ENCODINGS:
            raise EncodingError(
                f"No encoding implemented for objects of type {type(value).__name__}"
            )
        encoding = EncodeTypes.CUSTOM
    if encoding is EncodeTypes.CUSTOM:
        return _Record(value, value, encoding, _custom_arguments(value))
    if encoding is EncodeTypes.INT and cast(int, value) < 0:
        raise EncodingError("Integer serialization requires a nonnegative value")
    if encoding is EncodeTypes.DICT:
        snapshot = dict(cast(Mapping[object, object], value))
        return _Record(value, snapshot, encoding, tuple(chain(snapshot.keys(), snapshot.values())))
    if encoding in (EncodeTypes.LIST, EncodeTypes.TUPLE, EncodeTypes.SET, EncodeTypes.FROZENSET):
        items = tuple(cast(Iterable[object], value))
        return _Record(value, items, encoding, items)
    return _Record(value, value, encoding, ())


def _collect(obj: object) -> tuple[list[_Record], dict[int, int]]:
    stack = [(obj, False)]
    active: set[int] = set()
    records: dict[int, _Record] = {}
    ordered: list[_Record] = []
    object_ids: dict[int, int] = {}
    next_id = 1
    while stack:
        value, closing = stack.pop()
        identity = id(value)
        if closing:
            active.remove(identity)
            ordered.append(records[identity])
            continue
        if identity in active:
            raise EncodingError(f"Cannot serialize a cyclic object graph ({type(value).__name__})")
        object_ids[identity] = next_id
        next_id += 1
        if identity in records:
            continue
        record = _record(value)
        records[identity] = record
        active.add(identity)
        stack.append((value, True))
        stack.extend((child, False) for child in record.children)
    return ordered, object_ids


def encode(obj: object, stream: BinaryWriter) -> None:
    """Write an acyclic value graph, preserving shared references.

    Args:
        obj: Supported primitive, container, or registered custom value.
        stream: Writable binary output at the desired position.

    Raises:
        EncodingError: If values are unsupported, cyclic, or cannot be encoded.
    """
    records, object_ids = _collect(obj)
    for record in records:
        write_int(object_ids[id(record.original)], stream)
        write_int(record.encoding.encoding_id, stream)
        if record.encoding is EncodeTypes.CUSTOM:
            write_int(CUSTOM_ENCODINGS[type(record.original)], stream)
            encode_list(record.children, object_ids, stream)
        else:
            encoder = record.encoding.encode
            if encoder is None:
                raise EncodingError(f"Unsupported encoding {record.encoding.name}")
            encoder(record.value, object_ids, stream)


def _decode_record(
    encoding: EncodeTypes, objs: Mapping[int, object], stream: BinaryReader
) -> object:
    decoder = encoding.decode
    if decoder is None:
        raise EncodingError(f"Encoding {encoding.name} cannot start an object record")
    try:
        return decoder(objs, stream)
    except (KeyError, TypeError, ValueError) as error:
        raise EncodingError(f"Invalid {encoding.name} record: {error}") from error


def decode(stream: BinaryReader) -> object:
    """Read one graph through EOF, rejecting incomplete or inconsistent records.

    Args:
        stream: Binary input positioned at the first serialized record.

    Returns:
        The root value identified by object number one.

    Raises:
        EncodingError: If a record, reference, or registered constructor is invalid.
    """
    objects: dict[int, object] = {}
    while True:
        prefix = _read_chunk(stream, 1)
        if not prefix:
            break
        identity = _read_integer(stream, prefix)
        if identity == 0 or identity in objects:
            label = _integer_description(identity)
            raise EncodingError(f"Reserved or duplicate object identifier {label}")
        encoding_id = read_int(stream)
        encoding = EncodeTypes.get_by_id(encoding_id)
        if encoding is None:
            label = _integer_description(encoding_id)
            owner = _integer_description(identity)
            raise EncodingError(f"Unknown encoding identifier {label} for object {owner}")
        objects[identity] = _decode_record(encoding, objects, stream)
    if 1 not in objects:
        raise EncodingError("Serialized stream does not contain root object #1")
    return objects[1]


def dump(obj: object, stream: BinaryWriter) -> None:
    """Write a supported value to a binary stream; see encode for its contract."""
    encode(obj, stream)


def load(stream: BinaryReader) -> object:
    """Read a supported value through EOF; see decode for its contract."""
    return decode(stream)


def dumps(obj: object) -> bytes:
    """Return encoded bytes for a supported acyclic value graph."""
    stream = io.BytesIO()
    dump(obj, stream)
    return stream.getvalue()


def loads(string: bytes) -> object:
    """Decode a complete byte string using the current trusted class registry."""
    with io.BytesIO(string) as stream:
        return load(stream)
