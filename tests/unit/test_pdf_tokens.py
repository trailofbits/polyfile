from array import array
import ctypes
import sys

import pytest
from typing import SupportsIndex, cast

from polyfile.pdf import PSBytes, PSFloat, PSInt, PSStr, PSToken


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (PSInt(-42, pdf_offset=7, pdf_bytes=3), -42.0),
        (PSFloat(1.25, pdf_offset=7, pdf_bytes=4), 1.25),
        (PSStr("-4.25", pdf_offset=7, pdf_bytes=5), -4.25),
        (PSBytes(b"12.5", pdf_offset=7, pdf_bytes=4), 12.5),
    ],
    ids=["integer", "float", "text", "bytes"],
)
def test_float_protocol_returns_a_native_value(token: PSToken, expected: float) -> None:
    provenance = token.pdf_offset, token.pdf_bytes

    result = float(token)

    assert type(result) is float
    assert result == expected
    assert (token.pdf_offset, token.pdf_bytes) == provenance


def test_invalid_float_conversion_raises_value_error() -> None:
    token = PSStr("invalid", pdf_offset=7, pdf_bytes=7)

    with pytest.raises(ValueError):
        float(token)


def test_string_encoding_defaults_preserve_source_coordinates() -> None:
    token = PSStr("café", pdf_offset=11, pdf_bytes=6)

    result = token.encode()

    assert isinstance(result, PSBytes)
    assert result == b"caf\xc3\xa9"
    assert (result.pdf_offset, result.pdf_bytes) == (11, 6)


def test_string_encoding_respects_explicit_arguments() -> None:
    token = PSStr("café", pdf_offset=11, pdf_bytes=6)

    result = token.encode("ascii", "replace")

    assert result == b"caf?"
    assert (result.pdf_offset, result.pdf_bytes) == (11, 6)
    with pytest.raises(UnicodeEncodeError):
        token.encode("ascii")


@pytest.mark.parametrize("value", ["", "value", " \tvalue\r\n", " \t\r\n"])
def test_text_stripping_defaults(value: str) -> None:
    token = PSStr(value, pdf_offset=11, pdf_bytes=len(value))

    assert token.lstrip() == value.lstrip(" \t\n\r")
    assert token.rstrip() == value.rstrip(" \t\n\r")
    assert token.strip() == value.strip(" \t\n\r")
    assert (token.pdf_offset, token.pdf_bytes) == (11, len(value))


def test_text_stripping_respects_explicit_characters() -> None:
    token = PSStr("[]value[]", pdf_offset=11, pdf_bytes=9)

    assert token.lstrip("[]") == "value[]"
    assert token.rstrip("[]") == "[]value"
    assert token.strip("[]") == "value"
    assert token.strip("") is token


def test_text_stripping_without_whitespace_preserves_provenance() -> None:
    token = PSStr("value", pdf_offset=11, pdf_bytes=7)

    result = token.strip()

    assert result is token
    assert (result.pdf_offset, result.pdf_bytes) == (11, 7)


def test_byte_stripping_remains_supported() -> None:
    token = PSBytes(b" \tvalue\r\n", pdf_offset=11, pdf_bytes=9)

    assert token.lstrip() == b"value\r\n"
    assert token.rstrip() == b" \tvalue"
    assert token.strip() == b"value"
    assert token.strip(b" \t\r\nve") == b"alu"


def test_integer_hex_conversion_uses_python_three_protocol() -> None:
    assert hex(PSInt(42, pdf_offset=7, pdf_bytes=2)) == "0x2a"


@pytest.mark.parametrize("value", [-1.5, 0.0, 1.5])
def test_float_tokens_convert_to_native_integers(value: float) -> None:
    token = PSFloat(value, pdf_offset=7, pdf_bytes=4)
    assert type(int(token)) is int
    assert int(token) == int(value)
    assert (token.pdf_offset, token.pdf_bytes) == (7, 4)


@pytest.mark.parametrize(
    ("value", "error"), [(float("inf"), OverflowError), (float("nan"), ValueError)]
)
def test_invalid_float_to_integer_conversions_keep_builtin_errors(
    value: float, error: type[Exception]
) -> None:
    token = PSFloat(value, pdf_offset=7, pdf_bytes=4)
    with pytest.raises(error):
        int(token)


@pytest.mark.parametrize("value", ["ab cd ef", " ab cd ef ", "", "a,,b,", "aaaa"])
@pytest.mark.parametrize("separator", [None, " ", ",", "aa"])
@pytest.mark.parametrize("maxsplit", [-1, 0, 1, 2])
def test_text_split_values_match_builtin_sequences(
    value: str, separator: str | None, maxsplit: int
) -> None:
    token = PSStr(value, pdf_offset=7, pdf_bytes=len(value))
    assert token.split(separator, maxsplit) == value.split(separator, maxsplit)
    binary = value.encode()
    byte_token = PSBytes(binary, pdf_offset=7, pdf_bytes=len(binary))
    byte_separator = None if separator is None else separator.encode()
    assert byte_token.split(byte_separator, maxsplit) == binary.split(byte_separator, maxsplit)


@pytest.mark.parametrize("maximum", [-1, 0, 1])
def test_split_accepts_index_protocol_arguments(maximum: int) -> None:
    class SplitLimit:
        def __index__(self) -> int:
            return maximum

    value = "ab cd ef"
    token = PSStr(value, pdf_offset=7, pdf_bytes=len(value))
    assert token.split(None, SplitLimit()) == value.split(None, maximum)


def test_split_rejects_empty_separators() -> None:
    token = PSStr("value", pdf_offset=7, pdf_bytes=5)
    with pytest.raises(ValueError, match="empty separator"):
        token.split("")
    byte_token = PSBytes(b"value", pdf_offset=7, pdf_bytes=5)
    with pytest.raises(ValueError, match="empty separator"):
        byte_token.split(b"")


def test_split_rejects_non_index_arguments() -> None:
    token = PSStr("value", pdf_offset=7, pdf_bytes=5)
    invalid = cast(SupportsIndex, object())  # Deliberately exercise the runtime input boundary.
    with pytest.raises(TypeError, match="integer"):
        token.split(None, invalid)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("maximum", [-1, 0])
@pytest.mark.parametrize("separator", ["wrong-family", "", 0, False, [], object()])
def test_split_rejects_incompatible_separator_types(
    binary: bool,
    maximum: int,
    separator: object,
) -> None:
    if isinstance(separator, str) and not binary:
        separator = separator.encode()
    token = (
        PSBytes(b"ab,cd", pdf_offset=7, pdf_bytes=5)
        if binary
        else PSStr("ab,cd", pdf_offset=7, pdf_bytes=5)
    )
    invalid = cast(str | bytes, separator)  # Exercise the runtime separator boundary.
    with pytest.raises(TypeError):
        token.split(invalid, maximum)


@pytest.mark.parametrize("maximum", [-1, 0, 1])
@pytest.mark.parametrize("kind", ["bytearray", "memoryview", "array", "wide-array", "scalar"])
def test_byte_split_accepts_contiguous_buffer_separators(kind: str, maximum: int) -> None:
    if kind == "bytearray":
        separator = bytearray(b",")
    elif kind == "memoryview":
        separator = memoryview(b",")
    elif kind == "array":
        separator = array("B", [44])
    elif kind == "wide-array":
        separator = array("H", [0x2C2C])
    else:
        separator = ctypes.c_ubyte(44)
    value = b"a,,b,,"
    token = PSBytes(value, pdf_offset=7, pdf_bytes=len(value))
    argument = cast(bytes, separator)  # The builtin accepts any contiguous buffer provider.
    assert token.split(argument, maximum) == value.split(argument, maximum)


def test_byte_split_rejects_noncontiguous_and_released_buffers() -> None:
    token = PSBytes(b"a,,b", pdf_offset=7, pdf_bytes=4)
    sparse = memoryview(b",x,y")[::2]
    with pytest.raises(BufferError):
        token.split(cast(bytes, sparse))
    released = memoryview(b",")
    released.release()
    with pytest.raises(ValueError):
        token.split(cast(bytes, released))


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("maximum", [sys.maxsize + 1, -sys.maxsize - 2])
def test_split_rejects_index_size_overflow(binary: bool, maximum: int) -> None:
    token = (
        PSBytes(b"ab cd", pdf_offset=7, pdf_bytes=5)
        if binary
        else PSStr("ab cd", pdf_offset=7, pdf_bytes=5)
    )
    with pytest.raises(OverflowError):
        token.split(None, maximum)


def test_split_checks_overflow_after_index_conversion() -> None:
    class LargeIndex:
        def __index__(self) -> int:
            return sys.maxsize + 1

    token = PSStr("ab cd", pdf_offset=7, pdf_bytes=5)
    with pytest.raises(OverflowError):
        token.split(None, LargeIndex())


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("maximum", [sys.maxsize, -sys.maxsize - 1])
def test_split_accepts_index_size_boundaries(binary: bool, maximum: int) -> None:
    value = b"ab cd" if binary else "ab cd"
    token = (
        PSBytes(value, pdf_offset=7, pdf_bytes=5)
        if binary
        else PSStr(value, pdf_offset=7, pdf_bytes=5)
    )
    assert token.split(None, maximum) == value.split(None, maximum)
