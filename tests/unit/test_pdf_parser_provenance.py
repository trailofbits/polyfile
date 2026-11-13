"""Numeric PDF parsing retains provenance across pdfminer conversion boundaries."""

from collections.abc import Callable
from typing import BinaryIO, cast

from pdfminer.pdftypes import float_value, int_value, num_value
import pytest

from polyfile.fileutils import FileStream
from polyfile.pdf import (
    PDFLiteral,
    PDFParser,
    PSBytes,
    PSFloat,
    PSInt,
    PSStr,
    RawPDFStream,
    parse_object,
)
from polyfile.polyfile import Match, Matcher

NUMBERS = (
    (b"0", PSInt, 0),
    (b"-42", PSInt, -42),
    (b"123456789012345678901234567890", PSInt, 123456789012345678901234567890),
    (b"3.125", PSFloat, 3.125),
    (b"-.5", PSFloat, -0.5),
)
READ_POSITIONS = (
    0,
    PDFParser.BUFSIZ - 2,
    PDFParser.BUFSIZ - 1,
    PDFParser.BUFSIZ,
    PDFParser.BUFSIZ * 2 - 1,
)


def _parse_token(
    literal: bytes, position: int, nested: bool
) -> PSInt | PSFloat | PSBytes | PDFLiteral:
    data = b" " * position + literal + b" "
    prefix = b"nested!" if nested else b""
    backing = b"!" * 37 + prefix + data + b"outside"
    with (
        FileStream(backing, start=37) as outer,
        FileStream(outer, start=len(prefix), length=len(data)) as stream,
    ):
        parser = PDFParser(cast(BinaryIO, RawPDFStream(stream)))
        offset, token = parser.nexttoken()
    assert offset == position
    assert isinstance(token, (PSInt, PSFloat, PSBytes, PDFLiteral))
    return token


@pytest.mark.parametrize("number", NUMBERS)
@pytest.mark.parametrize("position", READ_POSITIONS)
@pytest.mark.parametrize("nested", (False, True))
def test_numeric_parser_returns_instrumented_values_across_read_boundaries(
    number: tuple[bytes, type[PSInt] | type[PSFloat], int | float],
    position: int,
    nested: bool,
) -> None:
    literal, token_type, expected = number
    token = _parse_token(literal, position, nested)

    assert type(token) is token_type
    assert token == expected
    assert (token.pdf_offset, token.pdf_bytes) == (position, len(literal))


@pytest.mark.parametrize("number", NUMBERS)
@pytest.mark.parametrize("source_base", (0, 117))
@pytest.mark.parametrize("decoded", (False, True))
def test_numeric_parser_output_retains_token_metadata_and_analysis_source(
    number: tuple[bytes, type[PSInt] | type[PSFloat], int | float],
    source_base: int,
    decoded: bool,
) -> None:
    literal, token_type, expected = number
    position = PDFParser.BUFSIZ - 1
    token = _parse_token(literal, position, nested=True)
    parent = Match(
        "PDF",
        None,
        relative_offset=source_base,
        length=position + len(literal),
        matcher=Matcher(parse=False),
        source="decoded:0" if decoded else "file",
    )
    assert parent.matcher is not None

    matches = list(parse_object(token, parent.matcher, parent, pdf_header_offset=source_base))

    assert len(matches) == 1
    match = matches[0]
    assert match.match is token
    assert type(match.match) is token_type
    assert match.match == expected
    assert (match.match.pdf_offset, match.match.pdf_bytes) == (position, len(literal))
    assert (match.offset, match.relative_offset, match.length) == (
        source_base + position,
        position,
        len(literal),
    )
    output = match.to_obj()
    assert (output["offset"], output["size"], output["source"]) == (
        source_base + position,
        len(literal),
        parent.source,
    )


@pytest.mark.parametrize(
    ("literal", "resolver"),
    (
        (b"42", int_value),
        (b"42", num_value),
        (b"3.125", float_value),
        (b"3.125", num_value),
    ),
)
def test_pdfminer_numeric_resolvers_retain_the_returned_token(
    literal: bytes,
    resolver: Callable[[object], int | float],
) -> None:
    position = PDFParser.BUFSIZ - 1
    token = _parse_token(literal, position, nested=True)

    resolved = resolver(token)

    assert resolved is token
    assert isinstance(resolved, (PSInt, PSFloat))
    assert (resolved.pdf_offset, resolved.pdf_bytes) == (position, len(literal))


@pytest.mark.parametrize(
    ("literal", "expected", "relative_offset", "length"),
    [(b"/Token", "Token", 0, 6), (b"(abc)", b"abc", 1, 3)],
)
@pytest.mark.parametrize("position", READ_POSITIONS)
@pytest.mark.parametrize("nested", (False, True))
def test_text_parser_retains_metadata_after_string_and_bytes_conversions(
    literal: bytes,
    expected: str | bytes,
    relative_offset: int,
    length: int,
    position: int,
    nested: bool,
) -> None:
    token = _parse_token(literal, position, nested)

    assert (token.pdf_offset, token.pdf_bytes) == (position + relative_offset, length)
    if isinstance(expected, str):
        assert isinstance(token, PDFLiteral)
        assert isinstance(token.name, PSStr)
        assert token.name == expected
        assert (token.name.pdf_offset, token.name.pdf_bytes) == (position + 1, length - 1)
    else:
        assert isinstance(token, PSBytes)
        assert bytes(token) is token
        assert token == expected

    parent = Match("PDF", None, length=position + len(literal), matcher=Matcher(parse=False))
    assert parent.matcher is not None
    list(parse_object(token, parent.matcher, parent))
    emitted = next(match for match in parent.children if match.match is token)
    assert (emitted.offset, emitted.length) == (position + relative_offset, length)
    serialized = emitted.to_obj()
    assert (serialized["offset"], serialized["size"]) == (position + relative_offset, length)
