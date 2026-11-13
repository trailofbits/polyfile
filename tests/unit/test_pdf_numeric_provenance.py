"""Explicit numeric conversions preserve the values used by PDF structure mapping."""

import math

import pytest

from polyfile.pdf import PSBytes, PSFloat, PSInt, PSStr, PSToken, parse_object
from polyfile.polyfile import Match, Matcher


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (PSInt(-42, pdf_offset=7, pdf_bytes=3), -42.0),
        (PSFloat(1.25, pdf_offset=7, pdf_bytes=4), 1.25),
        (PSStr("3.125", pdf_offset=7, pdf_bytes=9), 3.125),
        (PSBytes(b"3.125", pdf_offset=7, pdf_bytes=9), 3.125),
    ],
    ids=["integer", "float", "text", "bytes"],
)
@pytest.mark.parametrize("source_base", [0, 117])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_float_conversion_preserves_emitted_value_provenance(
    token: PSToken, expected: float, source_base: int, source: str
) -> None:
    converted = token.as_float()

    assert isinstance(converted, PSFloat)
    assert float(converted) == expected
    assert (converted.pdf_offset, converted.pdf_bytes) == (token.pdf_offset, token.pdf_bytes)
    matcher = Matcher(parse=False)
    parent = Match(
        "input", None, relative_offset=source_base, length=32, matcher=matcher, source=source
    )
    matches = list(parse_object(converted, matcher, parent, pdf_header_offset=source_base))

    assert len(matches) == 1
    match = matches[0]
    assert match.match is converted
    assert (match.offset, match.length, match.source) == (
        source_base + token.pdf_offset,
        token.pdf_bytes,
        source,
    )
    serialized = match.to_obj()
    assert (serialized["offset"], serialized["size"], serialized["source"]) == (
        source_base + token.pdf_offset,
        token.pdf_bytes,
        source,
    )


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -0.0])
def test_float_conversion_preserves_special_values_and_source_span(value: float) -> None:
    token = PSFloat(value, pdf_offset=13, pdf_bytes=6)

    converted = token.as_float()

    assert isinstance(converted, PSFloat)
    assert (converted.pdf_offset, converted.pdf_bytes) == (13, 6)
    if math.isnan(value):
        assert math.isnan(converted)
    else:
        assert float(converted) == value
        assert math.copysign(1, converted) == math.copysign(1, value)


@pytest.mark.parametrize(
    "token", [PSStr("invalid", pdf_offset=7, pdf_bytes=7), PSBytes(b"invalid", pdf_offset=7)]
)
def test_float_conversion_retains_invalid_number_errors(token: PSToken) -> None:
    with pytest.raises(ValueError):
        token.as_float()


def test_float_conversion_retains_integer_overflow() -> None:
    token = PSInt(10**1000, pdf_offset=7, pdf_bytes=1001)
    with pytest.raises(OverflowError):
        token.as_float()


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (PSStr(" 42 ", pdf_offset=7, pdf_bytes=4), 42),
        (PSBytes(b"-42", pdf_offset=7, pdf_bytes=5), -42),
        (PSFloat(42.5, pdf_offset=7, pdf_bytes=9), 42),
    ],
)
def test_integer_conversion_preserves_the_emitted_value(token: PSToken, expected: int) -> None:
    converted = token.as_int()

    assert isinstance(converted, PSInt)
    assert converted == expected
    assert (converted.pdf_offset, converted.pdf_bytes) == (token.pdf_offset, token.pdf_bytes)
    parent = Match("PDF", None, length=32, matcher=Matcher(parse=False))
    assert parent.matcher is not None
    emitted = list(parse_object(converted, parent.matcher, parent))
    assert len(emitted) == 1
    assert emitted[0].match is converted
    assert (emitted[0].offset, emitted[0].length) == (token.pdf_offset, token.pdf_bytes)
