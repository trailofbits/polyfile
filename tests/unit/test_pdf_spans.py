"""PDF token operations retain byte-accurate or conservative whole-token source spans."""

from collections.abc import Callable, Iterator
import codecs
import json
from typing import cast

import pytest

from polyfile.pdf import PDFDeciphered, PDFList, PSBytes, PSInt, PSStr, PSToken
from polyfile.polyfile import Match, Matcher


def span(value: object) -> tuple[int, int]:
    assert isinstance(value, PSToken)
    return value.pdf_offset, value.pdf_bytes


def token(binary: bool, value: str = "abcde", size: int | None = None) -> PSStr | PSBytes:
    length = len(value) if size is None else size
    if binary:
        return PSBytes(value.encode("ascii"), pdf_offset=7, pdf_bytes=length)
    return PSStr(value, pdf_offset=7, pdf_bytes=length)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize(
    ("selection", "offset", "length"),
    [
        (slice(None), 7, 5),
        (slice(1, 3), 8, 2),
        (slice(1, 1), 8, 0),
        (slice(5, None), 12, 0),
        (slice(100, None), 12, 0),
        (slice(-3, -1), 9, 2),
        (slice(None, -1), 7, 4),
        (slice(None, None, -1), 7, 5),
        (slice(1, 4, 2), 8, 3),
        (slice(4, 0, -2), 9, 3),
        (slice(-100, 100), 7, 5),
        (slice(-100, -100), 7, 0),
    ],
)
def test_aligned_slice_spans_stay_within_the_parent(
    binary: bool,
    selection: slice,
    offset: int,
    length: int,
) -> None:
    source = token(binary)
    result = source[selection]
    value = b"abcde" if binary else "abcde"
    assert result == value[selection]
    assert span(result) == (offset, length)
    assert 7 <= span(result)[0] <= sum(span(result)) <= 12
    assert span(source) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize(
    "selection", [slice(None), slice(1, 1), slice(-3, -1), slice(None, None, -1)]
)
def test_nonlinear_slices_retain_the_original_whole_span(binary: bool, selection: slice) -> None:
    source = token(binary, size=9)
    result = source[selection]
    value = b"abcde" if binary else "abcde"
    assert result == value[selection]
    assert span(result) == (7, 9)
    assert span(source) == (7, 9)


@pytest.mark.parametrize("binary", [False, True])
def test_reversed_values_do_not_reclassify_as_aligned(binary: bool) -> None:
    reverse = token(binary)[::-1]
    assert len(reverse) == span(reverse)[1]
    result = reverse[1:2]
    assert result == (b"d" if binary else "d")
    assert span(result) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
def test_sparse_slice_keeps_its_enclosing_span_when_sliced_again(binary: bool) -> None:
    sparse = token(binary)[1:4:2]
    result = sparse[1:]
    assert result == (b"d" if binary else "d")
    assert span(result) == (8, 3)


@pytest.mark.parametrize("binary", [False, True])
def test_equal_length_nonlinear_results_retain_the_original_mapping(binary: bool) -> None:
    source = token(binary, "abcdefgh", size=2)
    first = source[:2]
    assert len(first) == span(first)[1]
    result = first[1:2]
    assert result == (b"b" if binary else "b")
    assert span(result) == (7, 2)


def test_deciphered_slices_use_base_wrappers_with_the_original_span() -> None:
    source = PDFDeciphered(b"abcde", original_bytes=b"12345", pdf_offset=7, pdf_bytes=5)
    result = source[1:3]
    assert type(result) is PSBytes
    assert result == b"bc"
    assert span(result) == (7, 5)
    assert span(result[1:]) == (7, 5)


def test_decoding_and_encoding_do_not_reclassify_nonlinear_values() -> None:
    source = PSBytes(b"a\x00", pdf_offset=7, pdf_bytes=2)
    encoded = source.decode("utf-16-le").encode("utf-16-le")
    assert encoded == b"a\x00"
    assert len(encoded) == span(encoded)[1]
    result = encoded[:1]
    assert span(result) == (7, 2)


def test_equal_length_deciphering_stays_nonlinear_through_conversions() -> None:
    source = PDFDeciphered(b"abcde", original_bytes=b"12345", pdf_offset=7, pdf_bytes=5)
    encoded = source.decode().encode()
    copied = PSBytes(encoded, pdf_offset=7, pdf_bytes=5)
    result = copied[1:3]
    assert result == b"bc"
    assert span(result) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
def test_ascii_wrapper_conversions_keep_aligned_spans(binary: bool) -> None:
    source = token(binary)
    converted = source.decode() if isinstance(source, PSBytes) else source.encode()
    result = converted[1:3]
    assert span(result) == (8, 2)


@pytest.mark.parametrize("binary", [False, True])
def test_split_and_strip_metadata_covers_the_returned_aligned_values(binary: bool) -> None:
    source = token(binary, "ab cd")
    pieces = source.split()
    assert [span(part) for part in pieces] == [(7, 2), (10, 2)]
    assert span(source.split(None, 0)[0]) == (7, 5)
    value = token(binary, "a,,b,")
    separator = b"," if binary else ","
    assert [span(part) for part in value.split(separator)] == [
        (7, 1),
        (9, 0),
        (10, 1),
        (12, 0),
    ]
    stripped = token(binary, " ab ").strip()
    assert span(stripped) == (8, 2)


@pytest.mark.parametrize("binary", [False, True])
def test_empty_sources_and_invalid_slice_steps(binary: bool) -> None:
    source = token(binary, "")
    result = source[::-1]
    assert span(result) == (7, 0)
    with pytest.raises(ValueError, match="slice step cannot be zero"):
        source[::0]


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("index", [0, 2, -1])
def test_aligned_integer_selection_reports_one_source_byte(binary: bool, index: int) -> None:
    source = token(binary)
    result = source[index]
    assert span(result) == (7 + index % 5, 1)


def test_list_selection_preserves_existing_element_provenance() -> None:
    first = PSInt(3, pdf_offset=9, pdf_bytes=1)
    last = PSStr("ab", pdf_offset=12, pdf_bytes=2)
    values = PDFList.load([first, last])
    assert values[0] is first
    assert values[-1] is last
    part = values[1:]
    assert span(part) == (9, 5)
    assert part[0] is last
    assert span(last) == (12, 2)


def test_uninstrumented_list_elements_use_the_whole_parent_span() -> None:
    values = PDFList.load([])
    values.extend([3, "ab"])
    values.pdf_offset = 7
    values.pdf_bytes = 7
    for index in (0, 1):
        result = values[index]
        assert span(result) == (7, 7)


def test_alignment_metadata_is_not_part_of_serialized_matches() -> None:
    value = token(False)[::-1]
    match = Match("token", value, matcher=Matcher())
    assert "_pdf_byte_aligned" not in json.dumps(match.to_obj())


@pytest.mark.parametrize("binary", [False, True])
def test_empty_suffix_preserves_nonlinear_mapping(binary: bool) -> None:
    source = token(binary)[::-1]
    assert isinstance(source, (PSStr, PSBytes))
    result = cast(bytes, source) + b"" if isinstance(source, PSBytes) else cast(str, source) + ""
    assert result == (b"edcba" if binary else "edcba")
    assert span(result) == (7, 5)
    assert span(result[1:2]) == (7, 5)
    copied = type(source)(result, pdf_offset=7, pdf_bytes=5)
    assert span(copied[1:2]) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
def test_unpositioned_suffix_does_not_reactivate_alignment(binary: bool) -> None:
    source = token(binary, "ab", size=4)
    result = (
        cast(bytes, source) + b"cd" if isinstance(source, PSBytes) else cast(str, source) + "cd"
    )
    assert result == (b"abcd" if binary else "abcd")
    assert span(result) == (7, 4)
    assert span(result[1:2]) == (7, 4)


@pytest.mark.parametrize("binary", [False, True])
def test_empty_suffix_retains_aligned_mapping(binary: bool) -> None:
    source = token(binary)
    result = cast(bytes, source) + b"" if isinstance(source, PSBytes) else cast(str, source) + ""
    assert span(result) == (7, 5)
    assert span(result[1:2]) == (8, 1)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("nonlinear", [None, "left", "right"])
def test_contiguous_concatenation_combines_source_spans(
    binary: bool, nonlinear: str | None,
) -> None:
    left = token(binary, "abc")
    right = token(binary, "de")
    right.pdf_offset = 10
    if nonlinear == "left":
        left = left[::-1]
    elif nonlinear == "right":
        right = right[::-1]
    if isinstance(left, PSBytes):
        assert isinstance(right, PSBytes)
        result = cast(bytes, left) + cast(bytes, right)
        expected = bytes(left) + bytes(right)
    else:
        assert isinstance(left, PSStr) and isinstance(right, PSStr)
        result = cast(str, left) + cast(str, right)
        expected = str(left) + str(right)
    assert result == expected
    assert span(result) == (7, 5)
    assert span(result[1:2]) == ((8, 1) if nonlinear is None else (7, 5))


@pytest.mark.parametrize("binary", [False, True])
def test_contiguous_concatenation_keeps_full_nonlinear_source_spans(binary: bool) -> None:
    left = token(binary, "abc", size=5)
    right = token(binary, "de")
    right.pdf_offset = 12
    if isinstance(left, PSBytes):
        assert isinstance(right, PSBytes)
        result = cast(bytes, left) + cast(bytes, right)
    else:
        assert isinstance(right, PSStr)
        result = cast(str, left) + cast(str, right)
    assert span(result) == (7, 7)
    assert span(result[1:2]) == (7, 7)


@pytest.mark.parametrize("binary", [False, True])
def test_split_after_concatenation_preserves_nonlinear_mapping(binary: bool) -> None:
    source = token(binary, "ab cd")[::-1]
    assert isinstance(source, (PSStr, PSBytes))
    result = cast(bytes, source) + b"" if isinstance(source, PSBytes) else cast(str, source) + ""
    assert [span(part) for part in result.split()] == [(7, 5), (7, 5)]


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("prefix", ["", "xy"])
def test_native_prefix_preserves_nonlinear_mapping(binary: bool, prefix: str) -> None:
    source = token(binary)[::-1]
    assert isinstance(source, (PSStr, PSBytes))
    if isinstance(source, PSBytes):
        result = prefix.encode("ascii") + cast(bytes, source)
        expected = prefix.encode("ascii") + b"edcba"
    else:
        result = prefix + cast(str, source)
        expected = prefix + "edcba"
    assert result == expected
    assert span(result) == (7, 5)
    assert span(result[1:2]) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
def test_aligned_native_prefix_keeps_legacy_inferred_positions(binary: bool) -> None:
    source = token(binary)
    result = (
        b"xy" + cast(bytes, source) if isinstance(source, PSBytes) else "xy" + cast(str, source)
    )
    assert span(result) == (5, 7)
    assert span(result[1:2]) == (6, 1)
    assert span(source) == (7, 5)


@pytest.mark.parametrize("binary", [False, True])
def test_reflected_concatenation_combines_known_contiguous_spans(binary: bool) -> None:
    left = token(binary, "abc", size=5)
    right = token(binary, "de")
    right.pdf_offset = 12
    result = cast(Callable[[str | bytes], str | bytes], right.__radd__)(left)
    assert result == (b"abcde" if binary else "abcde")
    assert span(result) == (7, 7)
    assert span(result[1:2]) == (7, 7)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("as_int", [False, True])
def test_numeric_roundtrip_retains_conservative_source_mapping(binary: bool, as_int: bool) -> None:
    source = token(binary, "1234")[::-1]
    assert isinstance(source, (PSStr, PSBytes))
    number = source.as_int() if as_int else PSInt(source, pdf_offset=7, pdf_bytes=4)
    assert span(number) == (7, 4)
    copied = PSInt(number, pdf_offset=7, pdf_bytes=4)
    result = PSStr(copied, pdf_offset=7, pdf_bytes=4)
    assert result == "4321"
    assert span(result[:1]) == (7, 4)
    assert span(source) == (7, 4)


def test_equal_length_lossy_encoding_retains_the_whole_span() -> None:
    source = PSStr(chr(0xD800) + "é", pdf_offset=7, pdf_bytes=2)
    result = source.encode("utf-8", "ignore")
    assert result == b"\xc3\xa9"
    assert span(result[:1]) == (7, 2)
    assert span(result.decode("latin-1").encode("latin-1")[:1]) == (7, 2)


def test_decoding_replacements_do_not_infer_a_byte_map() -> None:
    source = PSBytes(b"\xffa", pdf_offset=7, pdf_bytes=2)
    result = source.decode("utf-8", "replace")
    assert result == "\ufffda"
    assert span(result[:1]) == (7, 2)


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("encoding", ["ascii", "UTF8", "latin_1"])
@pytest.mark.parametrize("errors", ["strict", "ignore", "replace"])
def test_known_one_byte_codec_mappings_remain_exact(
    binary: bool, encoding: str, errors: str,
) -> None:
    source = token(binary, "ab")
    converted = (
        source.decode(encoding, errors) if isinstance(source, PSBytes)
        else source.encode(encoding, errors)
    )
    assert span(converted[1:2]) == (8, 1)


def test_latin_one_non_ascii_mappings_remain_exact() -> None:
    raw = PSBytes(b"\xe9x", pdf_offset=7, pdf_bytes=2)
    decoded = raw.decode("latin-1")
    assert decoded == "éx"
    assert span(decoded[1:2]) == (8, 1)
    encoded = decoded.encode("latin-1")
    assert encoded == b"\xe9x"
    assert span(encoded[1:2]) == (8, 1)


@pytest.fixture
def reversing_codec() -> Iterator[str]:
    def encode(value: str, errors: str = "strict") -> tuple[bytes, int]:
        return value[::-1].encode("ascii"), len(value)

    def decode(value: object, errors: str = "strict") -> tuple[str, int]:
        assert isinstance(value, (bytes, bytearray, memoryview))
        raw = bytes(value)
        return raw[::-1].decode("ascii"), len(raw)

    def search(name: str) -> codecs.CodecInfo | None:
        if name == "pdf_provenance_reverse":
            return codecs.CodecInfo(name="utf-8", encode=encode, decode=decode)
        return None

    codecs.register(search)
    try:
        yield "pdf_provenance_reverse"
    finally:
        codecs.unregister(search)


@pytest.mark.parametrize("binary", [False, True])
def test_custom_codec_names_do_not_claim_native_byte_mappings(
    binary: bool, reversing_codec: str,
) -> None:
    source = token(binary, "ab")
    converted = (
        source.decode(reversing_codec) if isinstance(source, PSBytes)
        else source.encode(reversing_codec)
    )
    assert converted == ("ba" if binary else b"ba")
    assert span(converted[:1]) == (7, 2)


@pytest.fixture(params=["unregister", "replace"])
def transient_codec(request: pytest.FixtureRequest) -> Iterator[tuple[str, list[str]]]:
    calls: list[str] = []

    def encode(value: str, errors: str = "strict") -> tuple[bytes, int]:
        calls.append("encode")
        codecs.unregister(search)
        if request.param == "replace":
            codecs.register(replacement)
        return value[::-1].encode("ascii"), len(value)

    def decode(value: object, errors: str = "strict") -> tuple[str, int]:
        assert isinstance(value, (bytes, bytearray, memoryview))
        calls.append("decode")
        codecs.unregister(search)
        if request.param == "replace":
            codecs.register(replacement)
        raw = bytes(value)
        return raw[::-1].decode("ascii"), len(raw)

    def replacement(name: str) -> codecs.CodecInfo | None:
        return codecs.lookup("ascii") if name == "pdf_provenance_transient" else None

    def search(name: str) -> codecs.CodecInfo | None:
        if name == "pdf_provenance_transient":
            return codecs.CodecInfo(name="utf-8", encode=encode, decode=decode)
        return None

    codecs.register(search)
    try:
        yield "pdf_provenance_transient", calls
    finally:
        codecs.unregister(search)
        codecs.unregister(replacement)


@pytest.mark.parametrize("binary", [False, True])
def test_codec_registry_changes_do_not_affect_returned_provenance(
    binary: bool, transient_codec: tuple[str, list[str]],
) -> None:
    name, calls = transient_codec
    source = token(binary, "ab")
    converted = source.decode(name) if isinstance(source, PSBytes) else source.encode(name)
    assert converted == ("ba" if binary else b"ba")
    assert span(converted[:1]) == (7, 2)
    assert calls == (["decode"] if binary else ["encode"])


@pytest.mark.parametrize("binary", [False, True])
def test_native_codec_registry_change_control(
    binary: bool, transient_codec: tuple[str, list[str]],
) -> None:
    name, calls = transient_codec
    converted = b"ab".decode(name) if binary else "ab".encode(name)
    assert converted == ("ba" if binary else b"ba")
    assert calls == (["decode"] if binary else ["encode"])


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize(
    ("encoding", "errors"),
    [
        (None, "strict"),
        (42, "strict"),
        (b"ascii", "strict"),
        ("missing_codec", None),
        ("missing_codec", 42),
        (None, None),
        (42, None),
        ("\x00", "strict"),
        ("ascii", "\x00"),
        ("missing_codec", "\x00"),
        ("\x00", None),
        ("missing_codec", "strict"),
    ],
)
def test_codec_arguments_preserve_native_validation_order(
    binary: bool, encoding: object, errors: object,
) -> None:
    encoding, errors = cast(str, encoding), cast(str, errors)
    source = token(binary, "ab")
    with pytest.raises((TypeError, ValueError, LookupError)) as expected:
        if isinstance(source, PSBytes):
            b"ab".decode(encoding, errors)
        else:
            "ab".encode(encoding, errors)
    with pytest.raises(type(expected.value)) as actual:
        if isinstance(source, PSBytes):
            source.decode(encoding, errors)
        else:
            source.encode(encoding, errors)
    assert str(actual.value) == str(expected.value)
