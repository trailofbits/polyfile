"""Behavior of the standalone expression evaluator and its token/RPN entry points."""

from collections import UserDict, defaultdict
from enum import Enum
from io import StringIO

import pytest

from polyfile.expressions import Expression, Tokenizer, infix_to_rpn, parse, to_int, tokenize


@pytest.mark.parametrize(
    ("text", "result"),
    [
        ("3-2", 1),
        ("3 - 2", 1),
        ("7", 7),
        ("0xF + 0o10 + 0b11 + 02", 28),
        ("(-2)", -2),
        ("1+-2", -1),
        ("3--2", 5),
        ("~+1", -2),
        ("not not 3", True),
        ("20/3%4", 2),
        ("-7/2", -4),
        ("1+2*3", 7),
        ("(1+2)*3", 9),
        ("8-3-2", 3),
        ("1 << 2 + 1 >> 1", 4),
        ("1 | 6 ^ 7 & 2", 5),
        ("2 < 3", True),
        ("3 > 4", False),
        ("2 <= 2", True),
        ("3 >= 4", False),
        ("2 == 2", True),
        ("3 != 3", False),
        ("1 or 0 and 0", 1),
        ("1 ? 4 : 9", 4),
        ("0 ? 4 : 9", 9),
        ("1 ? 0 ? 2 : 3 : 4", 3),
        ("0 ? 1 : 0 ? 2 : 3", 3),
        ("0 or 1 ? 5 : 6", 5),
        ("1 ? 2 : 0 ? 4 : 5", 2),
    ],
)
def test_operators(text, result):
    actual = parse(text).interpret()
    assert actual == result
    assert type(actual) is type(result)


def test_identifiers_and_whitespace():
    assert (
        parse("order\t-\nandrew + notary_2").interpret({"order": 9, "andrew": 3, "notary_2": 2})
        == 8
    )


def test_expression_reuse_and_member_lookup():
    expression = parse("record.active ? record.header.size : 0")
    assert expression.interpret({"record": UserDict(active=1, header={"size": 12})}) == 12
    assert expression.interpret({"record": {"active": 0}}) == 0


def test_name_access():
    class Marker(Enum):
        soi = 7

    assignments = {"marker": 7, "types": {"Marker": Marker}, "soi": "other"}
    assert parse("types.Marker::soi").interpret(assignments) is Marker.soi
    assert parse("marker != values::eoi").interpret({"marker": 7, "values": {"eoi": 0}})
    assert parse("record.field").interpret({"record": {"field": None}}) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0 and missing", 0),
        ("3 or (1/0)", 3),
        ("1 ? 5 : missing", 5),
        ("0 ? (1/0) : 8", 8),
        ("1 ? 1 ? 3 : missing : (1/0)", 3),
        ("0 ? missing : 1 ? 4 : (1/0)", 4),
    ],
)
def test_skipped_operands(text, expected):
    assert parse(text).interpret() == expected


@pytest.mark.parametrize(
    "text",
    [
        "missing",
        "1 and missing",
        "0 or missing",
        "1 ? missing : 8",
        "0 ? 8 : missing",
        "record.missing",
        "record::missing",
    ],
)
def test_selected_missing_name(text):
    with pytest.raises(KeyError, match="missing"):
        parse(text).interpret({"record": {}})


@pytest.mark.parametrize("text", ["1 and (1/0)", "0 or (1/0)", "0 ? 5 : 1/0", "1 ? 1/0 : 5"])
def test_selected_arithmetic_error(text):
    with pytest.raises(ZeroDivisionError):
        parse(text).interpret()


def test_assignment_types_and_conversion():
    assert parse("s + s").interpret({"s": "12"}) == "1212"
    assert parse("a*b").interpret({"a": "12", "b": bytearray(b"\x01\x02")}) == 3096
    assert parse("value").interpret({"value": b"bytes"}) == b"bytes"
    assert to_int(b"\x01\x02", "little") == 513
    assert to_int("") == to_int(b"") == 0
    with pytest.raises(ValueError):
        parse("-name").interpret({"name": "nonnumeric"})
    with pytest.raises(TypeError):
        parse("record.real").interpret({"record": 3})


@pytest.mark.parametrize(
    ("text", "at"),
    [
        ("", "end"),
        (" \t\n", "end"),
        ("1 +", "end"),
        ("()", ")"),
        ("(1", "("),
        ("1)", ")"),
        ("1 2", "2"),
        ("1(2)", "("),
        ("* 1", "*"),
        ("1 not 2", "not"),
        ("0b2", "0b2"),
        ("0x", "0x"),
        ("12name", "12name"),
        ("1 @ 3", "@"),
        ("a.3", "3"),
        ("a.(b)", "("),
        ("a::", "end"),
        ("1 : 2", ":"),
        ("1 ? 2", "?"),
        ("1 ? : 2", ":"),
        ("1 ? 2 :", "end"),
        ("1 ? (2 : 3)", ":"),
        ("(1 ? 2) : 3", "?"),
        ("a[0]", "["),
    ],
)
def test_invalid_syntax_at_parse_time(text, at):
    with pytest.raises(ValueError) as raised:
        parse(text)
    assert at in str(raised.value).lower()


def test_tokenizer_lookahead():
    lexer = Tokenizer(StringIO("(-1) + 2"))
    parts = []
    while lexer.has_next():
        token = lexer.peek()
        assert token is not None
        assert lexer.has_next()
        assert lexer.peek() is token
        assert lexer.next() is token
        parts.append(token.raw_token)
    assert parts == ["(", "-", "1", ")", "+", "2"]
    assert lexer.peek() is lexer.next() is None


def test_rpn_helpers():
    rpn = tuple(infix_to_rpn(tokenize(StringIO("x ? a+1 : b"))))
    assert [token.raw_token for token in rpn] == ["x", "a", "1", "+", "b", ":", "?"]
    expression = Expression(iter(rpn))
    assert Expression([2, 3, *tokenize("*")]).interpret() == 6
    assert expression.tokens == rpn
    assert expression.interpret({"x": 1, "a": 8}) == 9
    assert expression.interpret({"x": 0, "b": 4}) == 4


def test_long_expression():
    assert parse("+".join(["1"] * 2000)).interpret() == 2000


@pytest.mark.parametrize("rpn", ["", "1 2", "1 +", "1 2 ?", "1 2 :", "1 2 .", "("])
def test_invalid_rpn(rpn):
    with pytest.raises(ValueError):
        Expression(tokenize(rpn))


def test_original_examples():
    assert parse("(sampling_factors & -0xf0) >> 4").interpret({"sampling_factors": 1234}) == 65
    assert (
        parse("thumbnail_x * thumbnail_y * 3").interpret({"thumbnail_x": 5, "thumbnail_y": 7})
        == 105
    )
    marker = parse("marker != marker_enum::soi and marker != marker_enum::eoi")
    assert marker.interpret({"marker": 1, "marker_enum": {"soi": 0, "eoi": 3}}) is True


@pytest.mark.parametrize("text", ["missing", "record.missing", "record::missing"])
def test_missing_keys_leave_supplied_mappings_intact(text):
    fields: defaultdict[str, int] = defaultdict(int)
    assignments: defaultdict[str, object] = defaultdict(int, record=fields)
    with pytest.raises(KeyError, match="missing"):
        parse(text).interpret(assignments)
    assert "missing" not in assignments
    assert "missing" not in fields
