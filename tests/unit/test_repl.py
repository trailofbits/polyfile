from unittest.mock import patch

import pytest

from polyfile.repl import (
    ANSIWriter,
    Command,
    CommandInfo,
    REPL,
    REPLCompleter,
    arg_completer,
    command,
)


class ExampleREPL(REPL):
    def __init__(self) -> None:
        self.calls: list[str] = []
        super().__init__("example", prompt="> ")

    @command(help="record an argument", aliases=("r",))
    def record(self, arguments: str) -> None:
        self.calls.append(arguments)

    @arg_completer("record")
    def record_completer(
        self, index: int, arg: str, prev_arguments: tuple[str, ...]
    ) -> list[str]:
        return [f"{index}:{arg}:{','.join(prev_arguments)}"]


def test_command_registration_preserves_aliases_and_callbacks() -> None:
    repl = ExampleREPL()

    repl.run_command("r value")

    assert repl.calls == ["value"]
    assert repl.get_command("record").usage() == "record an argument"
    assert repl.get_command("r") is repl.get_command("record")


def test_argument_completer_supports_readline_and_direct_calls() -> None:
    repl = ExampleREPL()
    complete = repl.get_completer(repl.get_command("record"))

    assert complete("a beta", 2, 6) == ["1:beta:a"]
    assert repl.record_completer(1, "beta", ("a",)) == ["1:beta:a"]
    assert repl.record_completer(index=1, arg="beta", prev_arguments=("a",)) == [
        "1:beta:a"
    ]
    with pytest.raises(TypeError, match="exactly three arguments"):
        repl.record_completer("a", 0)


def test_wrapped_command_preserves_the_requested_base_class() -> None:
    class CustomCommand(Command):
        def usage(self) -> str:
            return "custom"

        def run(self, arguments: str) -> str:
            return arguments

    def record(repl: REPL, arguments: str) -> str:
        return arguments

    wrapped = CustomCommand.wrap(record, CommandInfo("custom", "custom help", ()))

    assert issubclass(wrapped, CustomCommand)


def test_completion_returns_a_space_and_then_the_terminal_sentinel() -> None:
    complete = REPLCompleter(ExampleREPL()).complete

    with (
        patch("polyfile.repl.readline.get_line_buffer", return_value=""),
        patch("polyfile.repl.readline.get_endidx", return_value=0),
    ):
        assert complete("rec", 0) == "record "
        assert complete("rec", 1) is None


def test_ansi_writer_returns_none_and_formats_byte_context() -> None:
    writer = ANSIWriter(use_ansi=False)

    assert writer.write("header\n") is None
    writer.write_context(b"abc", offset=1, context_bytes=1)

    assert str(writer) == "header\nabc\n ^ \n"
