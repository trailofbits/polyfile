"""PDF-derived values retain disjoint and cross-source inputs through supported operations."""

from collections.abc import Callable
import copy
import operator
import math
import pickle

import pytest

from polyfile.pdf import (
    PDFDeciphered,
    PDFDict,
    PDFList,
    PDFStreamFilter,
    PNGPredictor,
    PSBytes,
    PSFloat,
    PSInt,
    PSStr,
    PSToken,
    parse_object,
    pdf_parser,
)
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher
from polyfile.provenance import SourceSpan, normalize_spans
from pdf_fixtures import CATALOG, object_stream_pdf, pdf_fixture


def numbers() -> tuple[PSInt, PSFloat]:
    return (
        PSInt(4, pdf_offset=7, pdf_bytes=1, pdf_source="file"),
        PSFloat(2.5, pdf_offset=9, pdf_bytes=3, pdf_source="decoded:0"),
    )


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (operator.add, 6.5),
        (operator.sub, 1.5),
        (operator.mul, 10.0),
        (operator.truediv, 1.6),
        (operator.floordiv, 1.0),
        (operator.mod, 1.5),
    ],
)
def test_binary_numeric_operations_keep_both_sources(
    operation: Callable[[object, object], object],
    expected: float,
) -> None:
    left, right = numbers()
    result = operation(left, right)
    assert isinstance(result, PSToken)
    assert result == expected
    assert result.pdf_location is None
    assert result.pdf_dependencies == normalize_spans(
        (
            SourceSpan("file", 7, 1),
            SourceSpan("decoded:0", 9, 3),
        )
    )
    assert left.pdf_location == SourceSpan("file", 7, 1)
    assert right.pdf_location == SourceSpan("decoded:0", 9, 3)


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (lambda value: 2 + value, 6),
        (lambda value: 2 - value, -2),
        (lambda value: 2 * value, 8),
        (lambda value: 2 / value, 0.5),
        (lambda value: 9 // value, 2),
        (lambda value: 9 % value, 1),
        (operator.neg, -4),
        (operator.pos, 4),
        (operator.abs, 4),
    ],
)
def test_reflected_and_unary_operations_retain_the_tagged_operand(
    operation: Callable[[PSInt], object],
    expected: int | float,
) -> None:
    value, _ = numbers()
    result = operation(value)
    assert isinstance(result, PSToken)
    assert result == expected
    assert result.pdf_location is None
    assert result.pdf_dependencies == (SourceSpan("file", 7, 1),)


@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("origin", [0, 117])
def test_computed_values_serialize_at_the_owner_with_independent_input_locations(
    source: str,
    origin: int,
) -> None:
    left, right = numbers()
    result = left.as_float() + right.as_float()
    assert isinstance(result, PSToken)
    parent = Match(
        "owner",
        None,
        relative_offset=origin,
        length=32,
        matcher=Matcher(parse=False),
        source=source,
    )
    assert parent.matcher is not None
    node = list(parse_object(result, parent.matcher, parent, pdf_header_offset=origin))[0]
    output = node.to_obj()
    assert (output["source"], output["offset"], output["size"], output["value"]) == (
        source,
        origin,
        0,
        "6.5",
    )
    assert output["dependencies"] == [span.to_obj() for span in result.pdf_dependencies]


def test_unattached_dependency_intervals_bind_to_the_selected_analysis_view() -> None:
    left = PSInt(1, pdf_offset=7, pdf_bytes=1)
    right = PSInt(2, pdf_offset=10, pdf_bytes=1)
    result = left + right
    parent = Match(
        "owner",
        None,
        relative_offset=117,
        length=32,
        source="decoded:0",
        matcher=Matcher(False),
    )
    assert parent.matcher is not None
    node = list(parse_object(result, parent.matcher, parent, pdf_header_offset=117))[0]
    assert node.to_obj()["dependencies"] == [
        {"source": "decoded:0", "offset": 124, "size": 1},
        {"source": "decoded:0", "offset": 127, "size": 1},
    ]


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("right_source", ["file", "decoded:0"])
def test_noncontiguous_concatenation_keeps_every_contribution(
    binary: bool,
    right_source: str,
) -> None:
    constructor = PSBytes if binary else PSStr
    left = constructor(b"ab" if binary else "ab", pdf_offset=3, pdf_bytes=2, pdf_source="file")
    right = constructor(
        b"cd" if binary else "cd",
        pdf_offset=9,
        pdf_bytes=2,
        pdf_source=right_source,
    )
    result = left + right
    assert isinstance(result, PSToken)
    assert result == (b"abcd" if binary else "abcd")
    assert result.pdf_location is None
    assert result.pdf_dependencies == normalize_spans(
        (
            SourceSpan("file", 3, 2),
            SourceSpan(right_source, 9, 2),
        )
    )


def test_conversions_slicing_and_reconstruction_keep_derived_dependencies() -> None:
    left = PSInt(2, pdf_offset=1, pdf_bytes=1, pdf_source="file")
    right = PSInt(3, pdf_offset=7, pdf_bytes=1, pdf_source="file")
    value = left + right
    assert isinstance(value, PSToken)
    text = str(value)
    assert isinstance(text, PSStr)
    encoded = text.encode()
    results = [
        text,
        encoded,
        encoded[:1],
        encoded.decode(),
        text.as_int(),
        value.as_float(),
        copy.copy(value),
        copy.deepcopy(encoded),
        pickle.loads(pickle.dumps(encoded)),
    ]
    for result in results:
        assert isinstance(result, PSToken)
        assert result.pdf_location is None
        assert result.pdf_dependencies == value.pdf_dependencies
    assert type(int(value)) is int
    assert type(float(value)) is float
    assert type(operator.index(value)) is int


@pytest.mark.parametrize("operation", [operator.truediv, operator.floordiv, operator.mod])
def test_native_arithmetic_errors_propagate(operation) -> None:
    left, _ = numbers()
    with pytest.raises(ZeroDivisionError):
        operation(left, 0)
    with pytest.raises(TypeError):
        operation(left, None)


def test_unsupported_operations_preserve_native_dispatch() -> None:
    left, _ = numbers()

    class Foreign:
        def __radd__(self, other: object) -> str:
            assert other is left
            return "foreign"

    assert left + Foreign() == "foreign"
    assert type(left**2) is int
    assert type(left & 1) is int


def test_real_pdf_values_combine_physical_and_decoded_dependencies() -> None:
    data, _ = object_stream_pdf([b"1.25", b"<< /A 42 >>"])
    parent = Match("PDF", None, length=len(data), matcher=Matcher(False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    decoded = next(node.match for node in nodes if node.name == "PSFloat")
    physical = next(node.match for node in nodes if node.name == "PSInt" and node.source == "file")
    assert isinstance(decoded, PSFloat) and isinstance(physical, PSInt)
    result = decoded.as_float() + physical.as_float()
    assert parent.matcher is not None
    output = list(parse_object(result, parent.matcher, parent))[0].to_obj()
    assert {span["source"] for span in output["dependencies"]} == {"file", decoded.pdf_source}
    assert output["size"] == 0


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_pickle_retains_cross_source_dependencies(protocol: int) -> None:
    left, right = numbers()
    value = left.as_float() * right
    assert isinstance(value, PSToken)
    result = pickle.loads(pickle.dumps(value, protocol=protocol))
    assert result == value
    assert type(result) is type(value)
    assert result.pdf_location is None
    assert result.pdf_dependencies == value.pdf_dependencies


@pytest.mark.parametrize("value", [-0.0, float("inf"), float("-inf"), float("nan")])
def test_float_arithmetic_preserves_native_values(value: float) -> None:
    token = PSFloat(value, pdf_offset=1, pdf_bytes=3, pdf_source="file")
    result = -token
    assert isinstance(result, PSFloat)
    if math.isnan(value):
        assert math.isnan(result)
    else:
        assert result == -value
        assert math.copysign(1, result) == math.copysign(1, -value)
    assert result.pdf_dependencies == token.pdf_dependencies


def test_integer_results_keep_arbitrary_precision_and_native_division_errors() -> None:
    value = PSInt(10**400, pdf_offset=1, pdf_bytes=401, pdf_source="file")
    result = value * value
    assert isinstance(result, PSInt)
    assert result == 10**800
    assert result.pdf_dependencies == value.pdf_dependencies
    with pytest.raises(OverflowError):
        value / 1


def test_list_reconstruction_does_not_invent_a_cross_source_extent() -> None:
    left, right = numbers()
    value = PDFList.load([left, right])
    assert value.pdf_location is None
    assert value.pdf_dependencies == normalize_spans(
        (*left.pdf_dependencies, *right.pdf_dependencies)
    )
    assert value[0] is left
    assert value[1] is right
    assert copy.deepcopy(value).pdf_dependencies == value.pdf_dependencies


def test_computed_dictionary_value_has_dependencies_without_a_lexeme() -> None:
    left, right = numbers()
    value = left.as_float() + right
    assert isinstance(value, PSFloat)
    key = PSStr("A", pdf_offset=3, pdf_bytes=1)
    dictionary = PDFDict({key: value}, pdf_offset=0, pdf_bytes=20)
    matcher = Matcher(False)
    parent = Match("owner", None, length=20, matcher=matcher)
    nodes = list(parse_object(dictionary, matcher, parent))
    output = next(node.to_obj() for node in nodes if node.name == "Value")
    assert (output["offset"], output["size"]) == (2, 0)
    assert output["dependencies"] == [span.to_obj() for span in value.pdf_dependencies]


def test_opaque_transformations_keep_whole_buffer_and_parameter_inputs() -> None:
    original = PSBytes(b"abc", pdf_offset=3, pdf_bytes=3, pdf_source="file")
    key = PSStr("Predictor", pdf_offset=20, pdf_bytes=9)
    params = PDFDict({key: PSInt(12, pdf_offset=30, pdf_bytes=2)}, pdf_offset=17, pdf_bytes=18)
    filter_name = PSStr("FlateDecode", pdf_offset=60, pdf_bytes=11, pdf_source="decoded:0")
    filtered = PDFStreamFilter(
        b"xyz",
        name=filter_name,
        original_bytes=original,
        pdf_offset=3,
        pdf_bytes=3,
    )
    predicted = PNGPredictor(
        b"xyz",
        original_bytes=filtered,
        params=params,
        pdf_offset=3,
        pdf_bytes=3,
    )
    deciphered = PDFDeciphered(b"xyz", original_bytes=predicted, pdf_offset=3, pdf_bytes=3)
    matcher = Matcher(False)
    parent = Match("owner", None, length=100, matcher=matcher)
    node = list(parse_object(deciphered, matcher, parent))[0]
    assert node.to_obj()["dependencies"] == [
        span.to_obj()
        for span in normalize_spans(
            (
                SourceSpan("file", 3, 3),
                SourceSpan("file", 17, 18),
                SourceSpan("decoded:0", 60, 11),
            )
        )
    ]
    assert deciphered[:1].pdf_dependencies == deciphered.pdf_dependencies


@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_nonlinear_strings_recurse_in_decoded_coordinates(escaped: bool, source: str) -> None:
    payload = b"GIF89a" + b"a" * 32
    body = (
        b"(" + b"".join(f"\\{byte:03o}".encode() for byte in payload) + b")"
        if escaped
        else b"<" + payload.hex().encode() + b">"
    )
    data = pdf_fixture([*CATALOG, body])
    parent = Match("PDF", None, length=len(data), source=source, matcher=Matcher(False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    decoded = next(
        node for node in nodes if node.name == "decoded_content" and node.decoded == payload
    )
    assert decoded.offset == 0
    assert decoded.source != source
    assert decoded.parent is not None
    assert decoded.parent.source == source
    assert (decoded.parent.offset, decoded.parent.length) == (data.index(body) + 1, len(body) - 2)
    gif = next(
        node for node in nodes if node.source == decoded.source and node.name != "decoded_content"
    )
    assert gif.offset == 0
