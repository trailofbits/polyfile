"""Conversions and reconstruction retain returned PDF values and their source mapping."""

import copy
import operator
import pickle
from collections.abc import Callable

import pytest

from polyfile.pdf import (
    PDFDeciphered, PDFDict, PDFList, PDFStreamFilter, PNGPredictor,
    PSBool, PSBytes, PSFloat, PSInt, PSStr, PSToken, has_provenance, parse_object,
)
from polyfile.polyfile import Match, Matcher


def token_values() -> list[PSToken]:
    original = PSBytes(b"encoded", pdf_offset=7, pdf_bytes=7)
    return [
        PSInt(42, pdf_offset=7, pdf_bytes=2),
        PSFloat(1.25, pdf_offset=7, pdf_bytes=4),
        PSStr("abc", pdf_offset=7, pdf_bytes=3),
        original,
        PDFDeciphered(b"abc", original_bytes=original, pdf_offset=7, pdf_bytes=7),
        PDFStreamFilter(
            b"abc", original_bytes=original, name="FlateDecode", pdf_offset=7, pdf_bytes=7,
        ),
        PNGPredictor(
            b"abc", original_bytes=original,
            params=PDFDict({}, pdf_offset=0, pdf_bytes=2), pdf_offset=7, pdf_bytes=7,
        ),
    ]


@pytest.mark.parametrize(
    "token_index", range(7), ids=[type(token).__name__ for token in token_values()],
)
@pytest.mark.parametrize(
    "operation", [copy.copy, copy.deepcopy, lambda value: pickle.loads(pickle.dumps(value))],
)
@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("source_base", [0, 117])
def test_copy_preserves_value_wrapper_state_and_emitted_span(
    token_index: int, operation: Callable[[PSToken], PSToken], source: str, source_base: int,
) -> None:
    token = token_values()[token_index]
    result = operation(token)
    assert type(result) is type(token)
    assert result == token
    assert result.__dict__ == token.__dict__
    assert result is not token
    matcher = Matcher(parse=False)
    parent = Match(
        "PDF", None, relative_offset=source_base, length=64, matcher=matcher, source=source,
    )
    list(parse_object(result, matcher, parent, pdf_header_offset=source_base))
    emitted = parent.children[0].to_obj()
    assert (emitted["offset"], emitted["size"], emitted["source"]) == (
        source_base + token.pdf_offset, token.pdf_bytes, source,
    )


@pytest.mark.parametrize("token", token_values(), ids=lambda token: type(token).__name__)
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_pickle_restores_required_constructor_arguments(token: PSToken, protocol: int) -> None:
    result = pickle.loads(pickle.dumps(token, protocol))
    assert type(result) is type(token)
    assert result == token
    assert result.__dict__ == token.__dict__


@pytest.mark.parametrize(
    "operation", [copy.deepcopy, lambda value: pickle.loads(pickle.dumps(value))],
)
def test_container_reconstruction_preserves_cycles_and_delimiter_spans(operation) -> None:
    array = PDFList([], pdf_offset=7, pdf_bytes=2)
    array.append(array)
    dictionary = PDFDict({}, pdf_offset=10, pdf_bytes=4)
    dictionary["self"] = dictionary
    result = operation(array)
    assert result[0] is result
    assert (result.pdf_offset, result.pdf_bytes) == (7, 2)
    result = operation(dictionary)
    assert result["self"] is result
    assert (result.pdf_offset, result.pdf_bytes) == (10, 4)


@pytest.mark.parametrize("binary", [False, True])
def test_reconstruction_preserves_nonlinear_mapping(binary: bool) -> None:
    value = PSBytes(b"abc", pdf_offset=7) if binary else PSStr("abc", pdf_offset=7, pdf_bytes=3)
    value = value[::-1]
    for result in (copy.copy(value), copy.deepcopy(value), pickle.loads(pickle.dumps(value))):
        part = result[1:2]
        assert has_provenance(part)
        assert (part.pdf_offset, part.pdf_bytes) == (7, 3)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (PSInt(42, pdf_offset=7, pdf_bytes=2), "42"),
        (PSFloat(1.25, pdf_offset=7, pdf_bytes=4), "1.25"),
        (PSStr("abc", pdf_offset=7, pdf_bytes=3), "abc"),
        (PSBytes(b"abc", pdf_offset=7), "b'abc'"),
        (PSBool(True, pdf_offset=7, pdf_bytes=4), "True"),
    ],
)
def test_string_conversion_returns_tagged_text_without_debug_state(token, expected: str) -> None:
    result = str(token)
    assert isinstance(result, PSStr)
    assert result == expected
    assert (result.pdf_offset, result.pdf_bytes) == (token.pdf_offset, token.pdf_bytes)
    assert str(result) == expected


def test_integer_byte_conversion_uses_native_count_semantics() -> None:
    token = PSInt(3, pdf_offset=7, pdf_bytes=1)
    result = bytes(token)
    assert isinstance(result, PSBytes)
    assert result == bytes(3)
    assert (result.pdf_offset, result.pdf_bytes) == (7, 1)
    assert (result[:1].pdf_offset, result[:1].pdf_bytes) == (7, 1)
    with pytest.raises(ValueError):
        bytes(PSInt(-1, pdf_offset=7, pdf_bytes=2))


def test_serialized_float_value_is_plain_text_with_separate_location() -> None:
    token = PSFloat(1.25, pdf_offset=7, pdf_bytes=4)
    matcher = Matcher(parse=False)
    parent = Match("PDF", None, length=64, matcher=matcher)
    emitted = list(parse_object(token, matcher, parent))[0].to_obj()
    assert type(emitted["value"]) is str
    assert emitted["value"] == "1.25"
    assert (emitted["offset"], emitted["size"]) == (7, 4)


@pytest.mark.parametrize(
    "token", [PSFloat(1.25, pdf_offset=7, pdf_bytes=4), PSStr("abc", pdf_offset=7, pdf_bytes=3)],
)
def test_unsupported_byte_conversions_raise_type_error(token: PSToken) -> None:
    with pytest.raises(TypeError):
        bytes(token)


@pytest.mark.parametrize("binary", [False, True])
def test_index_protocol_is_evaluated_once_and_retains_selected_value_span(binary: bool) -> None:
    class Index:
        calls = 0

        def __index__(self) -> int:
            self.calls += 1
            return -1

    index = Index()
    token = PSBytes(b"abc", pdf_offset=7) if binary else PSStr("abc", pdf_offset=7, pdf_bytes=3)
    result = token[index]
    assert result == (99 if binary else "c")
    assert has_provenance(result)
    assert (result.pdf_offset, result.pdf_bytes) == (9, 1)
    assert index.calls == 1
    assert type(operator.index(PSInt(2, pdf_offset=7, pdf_bytes=1))) is int
