"""Serialization rejects corrupt data and preserves acyclic object identity."""

from io import BytesIO
import subprocess
import sys
from typing import cast

import pytest

from polyfile import serialization


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(serialization, "CUSTOM_ENCODINGS", dict(serialization.CUSTOM_ENCODINGS))
    monkeypatch.setattr(
        serialization, "CUSTOM_ENCODINGS_BY_ID", dict(serialization.CUSTOM_ENCODINGS_BY_ID)
    )


@pytest.mark.parametrize("value", [-1, -128, -(2**128)])
def test_negative_integers_are_rejected_without_corruption(value: int) -> None:
    with pytest.raises(serialization.EncodingError, match="nonnegative"):
        serialization.dumps(value)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\x81",
        b"\x81\x85\x83ab",
        b"\x81\x84\x83ab",
        b"\x82\x83\xaa\x81\x88\x82\x80",
        b"\x81\x82\x82",
        b"\x81\x86\x82\x80",
        b"\x81\xff",
        b"\x81\x80",
        b"\x81\x8b\xff\x80",
        b"\x81\x81\x81\x81",
        b"\x80\x81\x81\x81",
        b"\x82\x81",
        b"\x81\x84\x81\xff",
    ],
)
def test_invalid_streams_raise_encoding_errors(data: bytes) -> None:
    with pytest.raises(serialization.EncodingError):
        serialization.loads(data)


@pytest.mark.parametrize("fields", [(1, 5), (1, 2), (1, 11), (1, 6), (1,)])
def test_huge_invalid_fields_raise_encoding_errors(fields: tuple[int, ...]) -> None:
    stream = BytesIO()
    for value in (*fields, 1 << 20000):
        serialization.write_int(value, stream)
    with pytest.raises(serialization.EncodingError):
        serialization.loads(stream.getvalue())


def test_custom_arguments_are_snapshotted_once(registry: None) -> None:
    @serialization.serializable
    class Value:
        def __init__(self, items: list[int]):
            self.items = items
            self.calls = 0

        def serialize(self) -> tuple[list[int]]:
            self.calls += 1
            return (list(self.items),)

    source = Value([1, 2, 3])
    restored = serialization.loads(serialization.dumps(source))

    assert isinstance(restored, Value)
    assert restored.items == source.items
    assert source.calls == 1


def test_repeated_registration_preserves_class_ids(registry: None) -> None:
    @serialization.serializable
    class First:
        def __init__(self, value: int):
            self.value = value

        def serialize(self) -> tuple[int]:
            return (self.value,)

    original_id = serialization.CUSTOM_ENCODINGS[First]
    serialization.serializable(First)

    @serialization.serializable
    class Second(First):
        pass

    restored = serialization.loads(serialization.dumps(First(42)))

    assert serialization.CUSTOM_ENCODINGS[First] == original_id
    assert serialization.CUSTOM_ENCODINGS[Second] != original_id
    assert type(restored) is First
    assert restored.value == 42


def test_custom_constructor_errors_have_context(registry: None) -> None:
    @serialization.serializable
    class Value:
        def __init__(self, value: int):
            raise ValueError("rejected value")

        def serialize(self) -> tuple[int]:
            return (42,)

    stream = BytesIO()
    for value in (2, 3, 42, 1, 11, serialization.CUSTOM_ENCODINGS[Value], 2, 0):
        serialization.write_int(value, stream)

    with pytest.raises(serialization.EncodingError, match="Value") as error:
        serialization.loads(stream.getvalue())
    assert isinstance(error.value.__cause__, ValueError)


class _ShortReader:
    def __init__(self, value: bytes):
        self.value = value
        self.position = 0

    def read(self, size: int = -1) -> bytes:
        start = self.position
        end = start + 1
        data = self.value[start:end]
        self.position += len(data)
        return data


class _ShortWriter:
    def __init__(self):
        self.value = bytearray()

    def write(self, value: bytes) -> int:
        self.value.extend(value[:1])
        return min(len(value), 1)


@pytest.mark.parametrize("payload", [b"", b"abc", b"\0\xff" * 50000])
def test_short_reads_and_writes_do_not_require_seeking(payload: bytes) -> None:
    output = _ShortWriter()
    value = {"message": payload, "values": [1, 128, None, True]}
    serialization.dump(value, output)
    source = _ShortReader(bytes(output.value))

    assert serialization.load(source) == value


@pytest.mark.parametrize("result", [None, 0, -1, 100, "invalid", 1.5])
def test_invalid_write_progress_fails_clearly(result: object) -> None:
    class Writer:
        def write(self, value: bytes) -> object:
            return result

    with pytest.raises(serialization.EncodingError, match="writ"):
        serialization.dump(b"abc", cast(serialization.BinaryWriter, Writer()))


@pytest.mark.parametrize("result", [None, "invalid", b"too many bytes"])
def test_invalid_binary_reads_fail_clearly(result: object) -> None:
    class Reader:
        def read(self, size: int = -1) -> object:
            return result

    with pytest.raises(serialization.EncodingError, match="read"):
        serialization.load(cast(serialization.BinaryReader, Reader()))


def test_custom_serialization_errors_have_context(registry: None) -> None:
    @serialization.serializable
    class Broken:
        def serialize(self) -> tuple[object, ...]:
            raise ValueError("broken arguments")

    with pytest.raises(serialization.EncodingError, match="Broken") as error:
        serialization.dumps(Broken())
    assert isinstance(error.value.__cause__, ValueError)


def test_legacy_custom_record_remains_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(serialization, "CUSTOM_ENCODINGS", {})
    monkeypatch.setattr(serialization, "CUSTOM_ENCODINGS_BY_ID", {})

    @serialization.serializable
    class Legacy:
        def __init__(self, value: int):
            self.value = value

        def serialize(self) -> tuple[int]:
            return (self.value,)

    restored = serialization.loads(bytes.fromhex("8283aa818b808280"))
    assert isinstance(restored, Legacy)
    assert restored.value == 42


@pytest.mark.parametrize("method", [None, 5])
def test_registration_requires_a_callable_method(method: object) -> None:
    invalid = type("Invalid", (), {"serialize": method})
    with pytest.raises(ValueError, match="callable"):
        serialization.serializable(invalid)


def test_missing_serialization_method_is_rejected() -> None:
    class Missing:
        pass

    with pytest.raises(ValueError, match="callable"):
        serialization.serializable(Missing)


def test_nonclass_registration_preserves_the_registry(registry: None) -> None:
    class Instance:
        def serialize(self) -> tuple[object, ...]:
            return ()

    before_classes = dict(serialization.CUSTOM_ENCODINGS)
    before_ids = dict(serialization.CUSTOM_ENCODINGS_BY_ID)
    with pytest.raises(ValueError, match="class"):
        serialization.serializable(cast(type[object], Instance()))
    assert serialization.CUSTOM_ENCODINGS == before_classes
    assert serialization.CUSTOM_ENCODINGS_BY_ID == before_ids


def test_unsupported_value_types_fail_clearly() -> None:
    with pytest.raises(serialization.EncodingError, match="float"):
        serialization.dumps(1.5)


@pytest.mark.parametrize("text", ["\ud800", "\udfff", "before\ud800after"])
def test_unencodable_strings_have_context(text: str) -> None:
    with pytest.raises(serialization.EncodingError, match="STRING.*UTF-8") as error:
        serialization.dumps(text)
    assert isinstance(error.value.__cause__, UnicodeEncodeError)


def test_direct_unsigned_writer_rejects_negative_values() -> None:
    with pytest.raises(serialization.EncodingError, match="nonnegative"):
        serialization.write_int(-1, BytesIO())


@pytest.mark.parametrize("value", [1.5, "1", None, b"1"])
def test_direct_unsigned_writer_rejects_nonintegers(value: object) -> None:
    with pytest.raises(serialization.EncodingError, match="nonnegative integer"):
        serialization.write_int(cast(int, value), BytesIO())


@pytest.mark.parametrize("value", [False, True, 0, 127, 128])
def test_direct_unsigned_writer_retains_integer_and_bool_handling(value: int) -> None:
    stream = BytesIO()
    serialization.write_int(value, stream)
    stream.seek(0)
    assert serialization.read_int(stream) == value


def test_io_failures_propagate() -> None:
    class Broken:
        def read(self, size: int = -1) -> bytes:
            raise OSError("input failed")

        def write(self, value: bytes) -> int:
            raise OSError("output failed")

    with pytest.raises(OSError, match="input failed"):
        serialization.load(Broken())
    with pytest.raises(OSError, match="output failed"):
        serialization.dump(1, Broken())


def test_stream_position_is_respected() -> None:
    stream = BytesIO(b"prefix")
    stream.seek(6)
    serialization.dump([1, 2], stream)
    stream.seek(6)
    assert serialization.load(stream) == [1, 2]
    assert stream.tell() == len(stream.getvalue())


@pytest.mark.parametrize("shape", ["self", "mutual", "custom"])
def test_cycles_fail_without_hanging(shape: str) -> None:
    script = """
import sys
from polyfile import serialization

if sys.argv[1] == 'custom':
    @serialization.serializable
    class Cycle:
        def serialize(self):
            return (self,)
    value = Cycle()
else:
    value = []
    value.append(value if sys.argv[1] == 'self' else [value])
try:
    serialization.dumps(value)
except serialization.EncodingError as error:
    assert 'cyclic' in str(error)
else:
    raise AssertionError('a cycle was serialized')
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script, shape], capture_output=True, timeout=3, check=False
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Cyclic serialization exceeded its three-second budget", pytrace=False)
    assert result.returncode == 0, result.stderr.decode()


def test_large_shared_graph_is_processed_once_per_object(registry: None) -> None:
    @serialization.serializable
    class Node:
        def __init__(self, children: list[object]):
            self.children = children
            self.calls = 0

        def serialize(self) -> tuple[list[object]]:
            self.calls += 1
            assert self.calls == 1, "shared node serialized more than once"
            return (self.children,)

    nodes = [Node([])]
    for _ in range(100):
        nodes.append(Node([nodes[-1], nodes[-1]]))
    restored = serialization.loads(serialization.dumps(nodes[-1]))

    assert all(node.calls == 1 for node in nodes)
    for _ in range(100):
        assert isinstance(restored, Node)
        assert restored.children[0] is restored.children[1]
        restored = restored.children[0]


def test_deep_graph_does_not_use_python_recursion() -> None:
    value: object = b"leaf"
    for _ in range(5000):
        value = [value]
    restored = serialization.loads(serialization.dumps(value))
    for _ in range(5000):
        assert isinstance(restored, list)
        restored = restored[0]
    assert restored == b"leaf"
