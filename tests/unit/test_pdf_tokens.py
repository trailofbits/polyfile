import pytest

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
def test_float_conversion_preserves_source_token(
    token: PSToken, expected: float
) -> None:
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
