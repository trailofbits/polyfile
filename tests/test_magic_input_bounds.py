"""Bounded magic tests do not allocate a copy of the remaining input."""

import tracemalloc
from pathlib import Path
from typing import TypeVar, cast
from uuid import UUID

import pytest

from polyfile.magic import (
    MAX_STRING_BYTES,
    REGEX_MAX,
    AbsoluteOffset,
    ConstantMatchTest,
    DataType,
    DataTypeMatch,
    Endianness,
    GUIDType,
    MagicMatcher,
    MatchedTest,
    NegatedStringTest,
    NumericDataType,
    PascalStringType,
    RegexType,
    SearchType,
    StringMatch,
    StringTest,
    StringType,
    UTF16Type,
)

T = TypeVar("T")


@pytest.mark.parametrize(
    "declaration,value",
    [
        ("lelong", "123"),
        ("guid", "x"),
        ("lestring16", "TOKEN"),
        ("string", "TOKEN"),
        ("string", "x"),
        ("regex", "TOKEN"),
        ("regex/1l", "TOKEN"),
    ],
)
@pytest.mark.parametrize("flipped", [False, True])
def test_fixed_magic_allocation_does_not_grow_with_input(
    declaration: str, value: str, flipped: bool
) -> None:
    # This matrix pairs each dynamic declaration with that parser's own expected value.
    data_type = cast(DataType[object], DataType.parse(declaration))
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(value))
    run = test.test_flip_endianness if flipped else test.test
    inputs = (b"x" * 1_048_576, b"x" * 16_777_216)
    peaks = []
    for data in inputs:
        tracemalloc.start()
        try:
            run(data, 1, None)
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    assert peaks[1] - peaks[0] < 65_536


@pytest.mark.parametrize("length", [0, 5, 127, 128, 256])
@pytest.mark.parametrize("suffix", [b"", b" ", b"\0", b"x"])
def test_full_word_uses_the_byte_after_the_complete_literal(length: int, suffix: bytes) -> None:
    data_type = StringType(full_word_match=True)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected("A" * length))
    result = test.test(b"!" + b"A" * length + suffix, 1, None)
    assert bool(result) == (suffix != b"x")
    if result:
        assert isinstance(result, MatchedTest)
        assert result.offset == 1
        assert result.length == length
        assert result.value == "A" * length


@pytest.mark.parametrize("value", ["x", "!Z", "<Z"])
def test_string_relations_keep_the_complete_bounded_value(value: str) -> None:
    data_type = StringType()
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(value))
    result = test.test(b"!" + b"A" * 10_000, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.length == MAX_STRING_BYTES
    assert result.value == "A" * MAX_STRING_BYTES


@pytest.mark.parametrize("flags", ["W", "w", "Ww"])
def test_string_blank_padding_does_not_report_the_copy_or_padding(flags: str) -> None:
    data_type = StringType.parse(f"string/{flags}")
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(r"A\ \0"))
    result = test.test(b"!A" + b" " * 10_000, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.length == MAX_STRING_BYTES - 1
    assert result.value == "A" + " " * (MAX_STRING_BYTES - 2)


@pytest.mark.parametrize("declaration", ["lestring16", "bestring16"])
def test_utf16_value_at_eof_and_truncation(declaration: str) -> None:
    data_type = DataType.parse(declaration)
    assert isinstance(data_type, UTF16Type)
    expected = data_type.parse_expected("TOKEN")
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, expected)
    result = test.test(b"!" + expected, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == "TOKEN"
    assert result.length == len(expected)
    assert not test.test(b"!" + expected[:-1], 1, None)
    assert not test.test(b"!", 1, None)


@pytest.mark.parametrize("declaration", ["guid", "beguid"])
def test_guid_keeps_its_byte_order_and_truncation(declaration: str) -> None:
    data_type = DataType.parse(declaration)
    assert isinstance(data_type, GUIDType)
    expected = UUID("00112233-4455-6677-8899-aabbccddeeff")
    payload = expected.bytes_le if declaration == "guid" else expected.bytes
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, expected)
    result = test.test(b"!" + payload + b"tail", 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == expected
    assert result.offset == 1
    assert result.length == 16
    assert not test.test(b"!" + payload[:-1], 1, None)


@pytest.mark.parametrize(
    "offset,valid", [(3, True), (-4, True), (7, False), (8, False), (-100, False)]
)
def test_numeric_offsets_keep_slice_and_eof_behavior(offset: int, valid: bool) -> None:
    data_type = DataType.parse("lelong")
    assert isinstance(data_type, NumericDataType)
    test = ConstantMatchTest(AbsoluteOffset(0), data_type, data_type.parse_expected("123"))
    result = test.test(b"abc{\0\0\0", offset, None)
    assert bool(result) == valid
    if valid:
        assert isinstance(result, MatchedTest)
        assert result.offset == offset
        assert result.value == 123


def test_flipped_numeric_match_reads_its_original_width() -> None:
    data_type = DataType.parse("lelong")
    assert isinstance(data_type, NumericDataType)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected("123"))
    data = b"!\0\0\0{" + b"tail" * 1000
    assert not test.test(data, 1, None)
    result = test.test_flip_endianness(data, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.offset == 1
    assert result.length == 4
    assert result.value == 123


@pytest.mark.parametrize("declaration", ["regex", "regex/0", "regex/0l", "regex/1l"])
def test_regex_keeps_its_existing_region_termination(declaration: str) -> None:
    data_type = DataType.parse(declaration)
    assert isinstance(data_type, RegexType)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected("TOKEN"))
    assert not test.test(b"!" + b"A" * (REGEX_MAX - 5) + b"TOKEN" + b"tail", 1, None)
    if declaration != "regex/1l":
        result = test.test(b"!" + b"A" * (REGEX_MAX - 6) + b"TOKENx" + b"tail", 1, None)
        assert isinstance(result, MatchedTest)
        assert result.offset == REGEX_MAX - 5
        assert result.length == 5


@pytest.mark.parametrize("value,valid", [(r"A\ B", False), (r"!A\ B", True)])
def test_optional_blanks_still_require_the_declared_length(value: str, valid: bool) -> None:
    data_type = StringType(optional_blanks=True)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(value))
    result = test.test(b"!AB", 1, None)
    assert bool(result) == valid


def test_negative_direct_string_limit_keeps_the_full_tail() -> None:
    data_type = StringType(num_bytes=-1)
    value = "A" * 256
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(value))
    result = test.test(b"!" + value.encode() + b"x", 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == value


def test_negative_direct_utf16_limit_keeps_the_full_tail() -> None:
    data_type = UTF16Type(Endianness.LITTLE, num_bytes=-1)
    expected = data_type.parse_expected("TOKEN")
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, expected)
    result = test.test(b"!" + expected + b"x", 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == "TOKEN"


def test_negative_direct_regex_limit_keeps_the_full_tail() -> None:
    data_type = RegexType(length=-1)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected("TOKEN"))
    result = test.test(b"!" + b"A" * REGEX_MAX + b"TOKENxx", 1, None)
    assert isinstance(result, MatchedTest)
    assert result.offset == REGEX_MAX + 1
    assert result.value == "TOKEN"


def test_search_blank_runs_keep_context_beyond_the_start_range() -> None:
    data_type = DataType.parse("search/2/W")
    assert isinstance(data_type, SearchType)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(r"A\ B"))
    result = test.test(b"!A" + b" " * 10_000 + b"B", 1, None)
    assert isinstance(result, MatchedTest)
    assert result.offset == 1
    assert result.length == 10_002


def test_pascal_string_retains_its_declared_body() -> None:
    data_type = DataType.parse("pstring/H")
    assert isinstance(data_type, PascalStringType)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected("TOKEN"))
    payload = b"TOKEN" + b"x" * 1000
    result = test.test(b"!" + len(payload).to_bytes(2, "big") + payload, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.offset == 1
    assert result.length == len(payload) + 2


class CompleteInputType(DataType[int]):
    def parse_expected(self, specification: str) -> int:
        return int(specification)

    def match(self, data: bytes, expected: int) -> DataTypeMatch:
        return DataTypeMatch(data[:1], len(data))


class CompleteInputStringType(StringType):
    def match(self, data: bytes, expected: StringTest) -> DataTypeMatch:
        return DataTypeMatch(data[:1], len(data))


@pytest.mark.parametrize("data_type", [CompleteInputType("custom"), CompleteInputStringType()])
@pytest.mark.parametrize("flipped", [False, True])
def test_custom_types_receive_the_complete_remaining_input(
    data_type: DataType[T], flipped: bool
) -> None:
    expected = data_type.parse_expected("123")
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, expected)
    run = test.test_flip_endianness if flipped else test.test
    result = run(b"!" + b"A" * 10_000, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == 10_000


class CompleteInputStringMatch(StringMatch):
    def matches(self, data: bytes) -> DataTypeMatch:
        if data.endswith(b"END"):
            return DataTypeMatch(data[:1], len(data))
        return DataTypeMatch.INVALID


def test_custom_string_values_and_negations_keep_the_complete_input() -> None:
    expected = CompleteInputStringMatch("A")
    data = b"!" + b"A" * 10_000 + b"END"
    test = ConstantMatchTest(AbsoluteOffset(1), StringType(), expected)
    result = test.test(data, 1, None)
    assert isinstance(result, MatchedTest)
    assert result.value == len(data) - 1
    negated = ConstantMatchTest(AbsoluteOffset(1), StringType(), NegatedStringTest(expected))
    assert not negated.test(data, 1, None)


def test_relative_and_indirect_continuations_keep_the_original_buffer(tmp_path: Path) -> None:
    definition = tmp_path / "continuations.magic"
    definition.write_text(
        "1\tstring/w\tA\\ B\thead\n>&0\tbyte\t90\trelative\n>(6.b)\tstring\tEND\tindirect\n",
        encoding="utf-8",
    )
    match = next(MagicMatcher.parse(definition).match(b"!ABCZx\x08xEND"))
    first, relative, indirect = match[0], match[1], match[2]
    assert isinstance(first, MatchedTest)
    assert first.offset == 1
    assert first.length == 2
    assert first.relative_base == 4
    assert relative.offset == 4
    assert indirect.offset == 8
    assert str(match) == "head relative indirect"
