from collections.abc import Iterator
from unittest.mock import patch

import pytest

from polyfile.debugger import (
    BooleanVariable,
    Breakpoint,
    Debugger,
    ExtensionBreakpoint,
    FileBreakpoint,
    InstrumentedParser,
    InstrumentedTest,
    MimeBreakpoint,
    StepMode,
)
from polyfile.fileutils import FileStream
from polyfile.languagematcher import BFMatcher
from polyfile.magic import MatchedTest
from polyfile.polyfile import Match, Matcher, Parser, Submatch


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("MIME:text/plain", MimeBreakpoint),
        ("EXT:txt", ExtensionBreakpoint),
        ("archive:3", FileBreakpoint),
    ],
)
def test_breakpoint_factories_return_their_concrete_types(
    text: str, expected_type: type[Breakpoint]
) -> None:
    assert isinstance(Breakpoint.from_str(text), expected_type)
    assert Breakpoint.from_str("invalid breakpoint") is None


def test_boolean_variable_preserves_value_and_parsing_contract() -> None:
    variable = BooleanVariable(True)

    assert variable.parse("false") is False
    assert variable.parse("0") is False
    variable.value = variable.parse("true")
    assert variable.value is True


def test_magic_test_instrumentation_preserves_and_restores_results() -> None:
    debugger = Debugger(break_on_parsing=False)
    original = BFMatcher.test
    instrumented = InstrumentedTest(BFMatcher, debugger)
    test = BFMatcher()

    try:
        result = test.test(b"[->+<]." * 4, 0, parent_match=None)
        assert isinstance(result, MatchedTest)
        assert debugger.last_result is result
        assert debugger.last_test is test
    finally:
        instrumented.uninstrument()

    assert BFMatcher.test is original


def test_parser_instrumentation_preserves_the_bound_callback() -> None:
    class HeaderParser(Parser):
        def parse(self, stream: FileStream, match: Match) -> Iterator[Match]:
            yield Submatch(
                "header", stream.read(1), relative_offset=0, length=1, parent=match
            )

    parser = HeaderParser()
    original = parser.parse
    debugger = Debugger(break_on_parsing=False)
    instrumented = InstrumentedParser(parser, debugger)
    parent = Match("root", b"abc", length=3, matcher=Matcher())

    try:
        with FileStream(b"abc") as stream, patch("builtins.input", return_value="n"):
            matches = list(parser.parse(stream, parent))
    finally:
        instrumented.uninstrument()

    assert [match.name for match in matches] == ["header"]
    assert matches[0].parent is parent
    assert parser.parse == original


def test_debugger_callback_preserves_keyword_arguments_and_nullable_abort() -> None:
    debugger = Debugger(break_on_parsing=False)

    def add(first: int, second: int) -> int:
        return first + second

    with (
        patch("sys.gettrace", return_value=None),
        patch("polyfile.debugger.Pdb") as pdb,
    ):
        pdb.return_value.runcall.return_value = None

        result = debugger._debug(add, first=2, second=3)

        assert result is None
        pdb.return_value.runcall.assert_called_once_with(add, first=2, second=3)


def test_blank_input_repeats_the_last_debugger_command() -> None:
    debugger = Debugger(break_on_parsing=False)

    with patch.object(debugger, "input", return_value="step"):
        debugger.repl()
    assert debugger.last_command == "step"

    debugger.step_mode = StepMode.RUNNING
    with patch.object(debugger, "input", return_value=""):
        debugger.repl()

    assert debugger.step_mode is StepMode.SINGLE_STEPPING
    assert debugger.last_command == "step"
