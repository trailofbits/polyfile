"""Custom magic compatibility decisions from issue #3576."""

from pathlib import Path

import pytest

from polyfile.magic import (
    DataType,
    MagicMatcher,
    MatchContext,
    MatchedTest,
    PascalStringType,
    RegexType,
    SearchType,
    StringType,
    libmagic_str_flags,
    libmagic_str_range,
)
from polyfile.magic import (
    TestType as MagicTestType,
)


def matcher(tmp_path: Path, definition: str) -> MagicMatcher:
    """Parse a custom definition without relying on bundled matches."""
    path = tmp_path / "compatibility.magic"
    path.write_text(definition)
    return MagicMatcher.parse(path)


@pytest.mark.parametrize(
    "alias,canonical",
    [
        ("string/W/c", "string/Wc"),
        ("string/16W/c", "string/16/Wc"),
        ("string/c16/W", "string/16/Wc"),
        ("ustring/W/c", "string/Wc"),
        ("string/0x10/c", "string/16/c"),
        ("string/0/c", "string/c"),
        ("string/4/c/16", "string/16/c"),
        ("search/40c/f", "search/40/cf"),
        ("search/c40/f", "search/40/cf"),
        ("search/c/40/f", "search/40/cf"),
        ("search/040/c/f", "search/32/cf"),
        ("search/0/c", "search/c"),
        ("regex/40C/c", "regex/40cC"),
        ("regex/C40/c", "regex/40cC"),
        ("regex/C/40/c", "regex/40cC"),
        ("pstring/B/t", "pstring/Bt"),
        ("pstring/t/B", "pstring/Bt"),
        ("pstring/B/b/t", "pstring/Btb"),
    ],
)
def test_modifier_spellings_share_their_canonical_type(
    alias: str, canonical: str
) -> None:
    assert DataType.parse(alias) is DataType.parse(canonical)


@pytest.mark.parametrize(
    "declaration",
    [
        "string//c",
        "string/c/",
        "string/c?",
        "string/B",
        "string/s",
        "search/40q",
        "search/40//c",
        "search/-1/c",
        "regex/W",
        "regex/H",
        "pstring/s",
        "pstring/B//t",
        "pstring/40",
        "regexfoo/C",
    ],
)
def test_invalid_modifier_declarations_still_fail(declaration: str) -> None:
    with pytest.raises(ValueError):
        DataType.parse(declaration)


@pytest.mark.parametrize("flags,bits", [("c", 0x0004), ("C", 0x0008), ("cC", 0x000C)])
def test_regex_case_flags_match_and_keep_distinct_sort_bits(
    flags: str, bits: int
) -> None:
    data_type = RegexType.parse(f"regex/{flags}")
    assert data_type.match(b"AB\n", data_type.parse_expected("aB"))
    assert libmagic_str_flags(data_type) == bits
    assert DataType.parse(data_type.name) is DataType.parse(f"regex/{flags}")


def test_regex_uppercase_modifier_loads_with_other_definitions(tmp_path: Path) -> None:
    matches = matcher(tmp_path, "0\tregex/C\taB\tHIT\n0\tstring\tZZ\tother\n")
    assert {str(match) for match in matches.match(b"AB\n")} == {"HIT, ASCII text"}


@pytest.mark.parametrize(
    "declaration,passes",
    [
        ("pstring/B", MagicTestType.BINARY),
        ("pstring/Bt", MagicTestType.TEXT),
        ("pstring/Bb", MagicTestType.BINARY),
        ("pstring/Btb", MagicTestType.TEXT | MagicTestType.BINARY),
    ],
)
def test_pascal_string_declared_passes(declaration: str, passes: MagicTestType) -> None:
    data_type = PascalStringType.parse(declaration)
    assert data_type.test_types(data_type.parse_expected("abcdefghi")) == passes
    assert data_type.declared_test_types() == (
        MagicTestType.UNKNOWN if declaration == "pstring/B" else passes
    )


def test_text_pascal_string_reports_its_text_description(tmp_path: Path) -> None:
    matches = matcher(tmp_path, "0\tpstring/B/t\tabcdefghi\tHIT\n")
    assert {str(match) for match in matches.match(b"\tabcdefghi")} == {
        "HIT, ASCII text, with no line terminators"
    }


@pytest.mark.parametrize(
    "flags,data,expected",
    [
        ("t", b"\tabcdefghi", True),
        ("b", b"\tabcdefghi", False),
        ("t", b"\x03abc", False),
        ("b", b"\x03abc", True),
        ("tb", b"\tabcdefghi", True),
        ("tb", b"\x03abc", True),
    ],
)
def test_pascal_string_pass_flags_gate_matching(
    tmp_path: Path, flags: str, data: bytes, expected: bool
) -> None:
    matches = matcher(tmp_path, f"0\tpstring/B{flags}\tx\tHIT\n")
    assert any("HIT" in str(match) for match in matches.match(data)) == expected


def test_pascal_length_modifiers_use_the_last_width() -> None:
    data_type = PascalStringType.parse("pstring/H/l/B/t")
    assert data_type.byte_length == 1
    assert data_type.length_modifier == "B"
    assert data_type.match(b"\x03abc", data_type.parse_expected("abc"))


def test_bare_regex_line_modifier_has_no_artificial_line_limit() -> None:
    data = b"x\n" * 199 + b"TARGET\n"
    expression = RegexType.parse("regex/l")
    assert expression.match(data, expression.parse_expected("TARGET"))
    assert libmagic_str_range(expression) == 0
    limited = RegexType.parse("regex/100l")
    assert not limited.match(data, limited.parse_expected("TARGET"))
    assert not expression.match(
        b"x\n" * 5000 + b"TARGET\n", expression.parse_expected("TARGET")
    )


@pytest.mark.parametrize("data", [b"A", b"\0", b"\xff", b"\n"])
def test_one_byte_files_have_the_short_file_verdict(data: bytes) -> None:
    matches = list(
        MagicMatcher.DEFAULT_INSTANCE.match(MatchContext(data, only_match_mime=True))
    )
    assert [str(match) for match in matches] == ["very short file (no magic)"]
    assert [set(match.mimetypes) for match in matches] == [{"application/octet-stream"}]
    result = matches[0][0]
    assert isinstance(result, MatchedTest)
    assert (result.offset, result.length, result.value) == (0, 1, data)


def test_one_byte_files_skip_custom_magic(tmp_path: Path) -> None:
    matches = matcher(tmp_path, "0\tstring\tA\tHIT\n")
    assert [str(match) for match in matches.match(b"A")] == [
        "very short file (no magic)"
    ]
    assert [str(match) for match in matches.match(b"AB")] == ["HIT"]


def test_short_negated_string_comparison_still_matches() -> None:
    data_type = StringType.parse("string")
    assert data_type.match(b"Z", data_type.parse_expected("!ABC"))


def test_indirect_soft_magic_still_checks_a_one_byte_subbuffer(tmp_path: Path) -> None:
    matches = matcher(
        tmp_path, "0\tstring\tHEAD\tmarker\n>4\tindirect\tx\n0\tbyte\t65\tfound\n"
    )
    match = next(matches.match(b"HEADA"))
    assert any(
        result.test.message.resolve(match.context) == "found" for result in match
    )


@pytest.mark.parametrize(
    "data,trim,raw,value",
    [
        (b"abc\ndef\n", False, b"abc\ndef\n", "abc\ndef\n"),
        (b"abc\rdef\r\n", False, b"abc\rdef\r\n", "abc\rdef\r\n"),
        (b"abc\0def\n", False, b"abc", "abc"),
        (b" \tabc\ndef\n \t", True, b" \tabc\ndef\n \t", "abc\ndef"),
        (b" \tabc\0def\n", True, b" \tabc", "abc"),
    ],
)
def test_wildcard_search_keeps_line_breaks_until_nul(
    data: bytes, trim: bool, raw: bytes, value: str
) -> None:
    data_type = SearchType.parse("search/2/T" if trim else "search/2")
    result = data_type.match(data, data_type.parse_expected("x"))
    assert result.raw_match == raw
    assert result.value == value


def test_default_wildcard_search_gets_the_text_description(tmp_path: Path) -> None:
    matches = matcher(tmp_path, "0\tsearch/40\tx\tV[%s]\n")
    assert {str(match) for match in matches.match(b"abc\ndef\n")} == {
        "V[abc\ndef\n], ASCII text"
    }


def test_other_string_relations_keep_their_declared_pass_rules() -> None:
    search = SearchType.parse("search/40")
    assert search.test_types(search.parse_expected("!ABC")) == MagicTestType.TEXT
    assert search.test_types(search.parse_expected(">ABC")) == MagicTestType.BINARY
    string = StringType.parse("string")
    assert string.test_types(string.parse_expected("x")) == MagicTestType.BINARY
    pascal = PascalStringType.parse("pstring")
    assert pascal.test_types(pascal.parse_expected("x")) == MagicTestType.BINARY


@pytest.mark.parametrize(
    "modifier,prefix",
    [("H", b"\0\x02"), ("h", b"\x02\0"), ("L", b"\0\0\0\x02"), ("l", b"\x02\0\0\0")],
)
def test_multibyte_pascal_equality_uses_its_actual_content(
    modifier: str, prefix: bytes
) -> None:
    data_type = PascalStringType.parse(f"pstring/{modifier}")
    assert data_type.match(prefix + b"ab", data_type.parse_expected("ab"))
    assert not data_type.match(prefix + b"ac", data_type.parse_expected("ab"))


def test_case_folding_stays_ascii_only() -> None:
    data_type = StringType.parse("string/c")
    assert not data_type.match(b"\xc9x", data_type.parse_expected(r"\xe9x"))
    assert data_type.match(b"AX", data_type.parse_expected("ax"))


@pytest.mark.parametrize("declaration", ["search/40", "regex"])
def test_truncated_utf8_values_remain_binary(declaration: str) -> None:
    data_type = DataType.parse(declaration)
    if isinstance(data_type, SearchType):
        passes = data_type.test_types(data_type.parse_expected(r"\xc3"))
    else:
        assert isinstance(data_type, RegexType)
        passes = data_type.test_types(data_type.parse_expected(r"\xc3"))
    assert passes == MagicTestType.BINARY


def test_direct_caret_remains_a_regex_anchor() -> None:
    data_type = RegexType.parse("regex")
    assert data_type.match(b"target\n", data_type.parse_expected("^target"))
    assert not data_type.match(b"xxtarget\n", data_type.parse_expected("^target"))


def test_nonwildcard_search_values_remain_line_delimited() -> None:
    search = SearchType.parse("search/40")
    result = search.match(b"ABC\nsuffix\n", search.parse_expected("!missing"))
    assert result.raw_match == b"ABC"
    assert not search.match(b"ABC\nsuffix\n", search.parse_expected(">ABC"))
