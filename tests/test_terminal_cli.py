"""Keep terminal presentation separate from scan semantics and result streams."""

import io
import json
import re
import signal
from contextlib import redirect_stderr, redirect_stdout

import pytest
from rich.console import Console

from polyfile import logger
from polyfile.__main__ import main
from polyfile.matchtree import Discovery, MatchTree
from polyfile.polyfile import PARSERS, ParserFunctionWrapper
from tests.test_logger import Terminal
from tests.test_zipmatcher import MEMBERS, PNG, build_zip

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@pytest.fixture
def sample(tmp_path, monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("CI", raising=False)
    path = tmp_path / "sample.zip"
    path.write_bytes(build_zip(members={**MEMBERS, "image.png": PNG}))
    return str(path)


def invoke(path, *args, tty=False, stdout_tty=False):
    output = Terminal() if stdout_tty else io.StringIO()
    errors = Terminal() if tty else io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        main(["polyfile", *args, path])
    return output.getvalue(), ANSI.sub("", errors.getvalue())


def final_tree(errors):
    return errors.rsplit("PolyFile  ", 1)[-1]


def screen_text(transcript: str) -> str:
    """Apply Rich's line erasure and cursor movement to a shared terminal transcript."""
    lines: list[str] = [""]
    row, column = 0, 0
    tokens: list[str] = re.findall(r"\x1b\[[0-?]*[ -/]*[@-~]|\r|\n|[^\x1b\r\n]+", transcript)
    for token in tokens:
        if token == "\r":
            column = 0
        elif token == "\n":
            row += 1
            lines.extend([""] * (row + 1 - len(lines)))
            column = 0
        elif token == "\x1b[2K":
            lines[row] = ""
        elif token.startswith("\x1b[") and token.endswith("A"):
            row = max(0, row - int(token[2:-1] or "1"))
        elif not token.startswith("\x1b["):
            line = lines[row].ljust(column)
            lines[row] = line[:column] + token + line[column + len(token) :]
            column += len(token)
    return "\n".join(lines)


@pytest.mark.parametrize("format", ["file", "mime", "explain", "json", "sbud", "html"])
def test_shared_terminal_keeps_requested_output(sample, format):
    expected, _ = invoke(sample, "--format", format, stdout_tty=True)
    terminal = Terminal()
    with redirect_stdout(terminal), redirect_stderr(terminal):
        main(["polyfile", "--format", format, sample])
    visible = screen_text(terminal.getvalue()).rstrip()
    assert "Complete |" in visible
    assert visible.endswith(ANSI.sub("", expected).rstrip())


def test_shared_terminal_keeps_mixed_stdout_after_summary(sample):
    args = ("-r", "mime", "-r", "json", "--no-contents", "-r", "file")
    expected, _ = invoke(sample, *args, stdout_tty=True)
    terminal = Terminal()
    with redirect_stdout(terminal), redirect_stderr(terminal):
        main(["polyfile", *args, sample])
    visible = screen_text(terminal.getvalue()).rstrip()
    assert visible.count("Complete |") == 1
    assert visible.endswith(expected.rstrip())


def test_redirected_stdout_follows_terminal_summary(sample):
    errors = Terminal()

    class Results(io.StringIO):
        def write(self, text: str) -> int:
            assert "Complete |" in screen_text(errors.getvalue())
            return super().write(text)

    output = Results()
    with redirect_stdout(output), redirect_stderr(errors):
        main(["polyfile", "--format", "sbud", sample])
    assert json.loads(output.getvalue())["struc"]


@pytest.mark.parametrize("data", [b"plain text\n", b"\xff\x00\xff", b"X", b""])
def test_explicit_filetype_omits_unrequested_fallbacks(tmp_path, data):
    path = tmp_path / "input"
    path.write_bytes(data)
    for output in ("file", "mime", "json"):
        args = ("--filetype", "application/pdf", "--format", output)
        result, _ = invoke(str(path), *args)
        if output == "json":
            assert json.loads(result)["struc"] == []
        else:
            assert result == ""
        with pytest.raises(SystemExit) as rejected:
            invoke(str(path), *args, "--require-match")
        assert rejected.value.code == 127
    assert invoke(str(path), "-r", "mime")[0]


def test_filetype_wildcards_and_punctuation(tmp_path):
    path = tmp_path / "input"
    path.write_bytes(PNG)
    for selector in ("image/png", "image/p?g", "image/p*g"):
        assert invoke(str(path), "-f", selector, "-r", "mime")[0] == "image/png\n"
    for selector in ("image/p??ng", "application/vndXsqlite3"):
        with pytest.raises(SystemExit) as rejected:
            invoke(str(path), "-f", selector)
        assert rejected.value.code == 1
    for selector in ("application/epub+zip", "application/vnd.sqlite3"):
        assert invoke(str(path), "-f", selector, "-r", "mime")[0] == ""
    path.write_text("plain text\n")
    assert invoke(str(path), "-f", "text/plain", "-r", "mime")[0] == "text/plain\n"


def test_large_tree_precedes_sbud_output(tmp_path, monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("CI", raising=False)
    path = tmp_path / "many_members.zip"
    members = {f"member_{index:02}.txt": b"hello\n" for index in range(30)}
    path.write_bytes(build_zip(members=members))
    terminal = Terminal()
    with redirect_stdout(terminal), redirect_stderr(terminal):
        main(["polyfile", "--format", "sbud", "--no-contents", str(path)])
    tree, result = screen_text(terminal.getvalue()).split("Complete |", 1)
    assert len(tree.splitlines()) > 30
    assert "member_00.txt" in tree
    assert "member_29.txt" in tree
    assert json.loads(result.split("\n", 1)[1])["struc"]


@pytest.mark.parametrize("refresh", [False, True])
def test_repeated_nested_suspension_keeps_terminal_results(sample, refresh):
    terminal = Terminal()
    with redirect_stdout(terminal), logger.logging_context(stream=terminal) as session:
        session.start_scan("input", recursive=False)
        for index in range(3):
            with session.suspend():
                print(f"result {index}")
                with session.suspend():
                    print(f"nested result {index}")
            if refresh:
                session.live.refresh()
    visible = screen_text(terminal.getvalue())
    for index in range(3):
        assert f"result {index}\nnested result {index}\n" in visible


@pytest.mark.parametrize("format", ["file", "mime", "explain", "json", "sbud", "html"])
def test_stderr_terminal_does_not_change_stdout(sample, format):
    plain, errors = invoke(sample, "--format", format)
    pretty, terminal = invoke(sample, "--format", format, tty=True)
    assert plain == pretty
    assert errors == ""
    assert "Complete |" in final_tree(terminal)
    if format == "file":
        assert "archive" in final_tree(terminal).lower()
    else:
        assert "application/zip" in final_tree(terminal)


@pytest.mark.parametrize("format", ["file", "mime"])
def test_result_terminal_does_not_change_plain_results(sample, format):
    plain, _ = invoke(sample, "--format", format)
    pretty, _ = invoke(sample, "--format", format, tty=True, stdout_tty=True)
    assert plain == pretty
    assert "\x1b" not in pretty


def test_tree_respects_existing_analysis_scope(sample):
    _, shallow = invoke(sample, "--format", "mime", tty=True)
    _, recursive = invoke(sample, "--format", "json", tty=True)
    assert "image/png" not in final_tree(shallow)
    assert "image/png" in final_tree(recursive)
    assert "image.png" in final_tree(recursive)
    assert "decoded:" in final_tree(recursive)
    assert "LocalFileHeader" not in final_tree(recursive)
    assert "compressed_data" not in final_tree(recursive)


def test_mixed_output_formats_preserve_results(sample):
    args = ("-r", "mime", "-r", "json", "--no-contents", "-r", "file")
    plain, _ = invoke(sample, *args)
    pretty, errors = invoke(sample, *args, tty=True)
    assert plain == pretty
    tree = final_tree(errors)
    assert "image/png" in tree
    assert tree.count("application/zip") == 1


def test_zero_match_limit_does_not_start_an_unrequested_scan(sample):
    output, errors = invoke(sample, "-r", "json", "--max-matches", "0", tty=True)
    assert json.loads(output)["struc"] == []
    assert "Match limit reached | 0 matches" in final_tree(errors)


def test_match_limit_retains_partial_tree(sample):
    output, errors = invoke(sample, "-r", "json", "--max-matches", "1", tty=True)
    assert len(json.loads(output)["struc"]) == 1
    assert "Match limit reached" in final_tree(errors)
    assert "application/zip" in final_tree(errors)


def test_resource_limit_is_visible_without_parser_fields(sample):
    _, errors = invoke(sample, "-r", "json", "--max-depth", "0", tty=True)
    tree = final_tree(errors)
    assert "limited" in tree
    assert "image/png" not in tree


def test_no_matches_and_require_match(sample):
    output, errors = invoke(sample, "-r", "json", "--max-matches", "0", tty=True)
    assert json.loads(output)["struc"] == []
    assert "No matches found" in final_tree(errors)
    with pytest.raises(SystemExit) as error:
        invoke(sample, "-r", "json", "--max-matches", "0", "--require-match")
    assert error.value.code == 127


def test_final_tree_includes_nodes_hidden_in_live_view():
    tree = MatchTree()
    tree.add(Discovery("root", "container"))
    for index in range(30):
        tree.add(Discovery(str(index), f"type_{index:02}", parent="root"))
    live, final = io.StringIO(), io.StringIO()
    Console(file=live).print(tree.render(limit=4))
    Console(file=final).print(tree.render())
    assert "27 earlier matches hidden" in live.getvalue()
    assert "container" in live.getvalue()
    assert "type_29" in live.getvalue()
    assert "type_00" not in live.getvalue()
    assert all(f"type_{index:02}" in final.getvalue() for index in range(30))


def test_discovery_labels_are_literal_and_sources_are_distinct():
    tree = MatchTree()
    for source in ("file", "decoded:0"):
        tree.add(
            Discovery(
                source,
                "[red]type",
                source=source,
                member="name\n\x1b[2J",
                offset=4,
                size=8,
            )
        )
    output = io.StringIO()
    Console(file=output, width=120).print(tree.render())
    text = output.getvalue()
    assert "[red]type" in text
    assert "name\\n\\x1b[2J" in text
    assert "\x1b" not in text
    assert "decoded:0" in text
    assert len(tree) == 2


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, signal.SIGTERM])
def test_interruption_preserves_partial_tree_and_restores_signal_handler(
    sample, interrupt
):
    def stop(stream, match):
        if interrupt is KeyboardInterrupt:
            raise KeyboardInterrupt
        signal.raise_signal(signal.SIGTERM)
        return iter(())

    parser = ParserFunctionWrapper(stop)
    previous = signal.getsignal(signal.SIGTERM)
    PARSERS["application/zip"].add(parser)
    output, errors = io.StringIO(), Terminal()
    try:
        with (
            redirect_stdout(output),
            redirect_stderr(errors),
            pytest.raises(SystemExit) as error,
        ):
            main(["polyfile", "-r", "json", sample])
        assert error.value.code == 128 + signal.SIGTERM
    finally:
        PARSERS["application/zip"].remove(parser)
    tree = final_tree(ANSI.sub("", errors.getvalue()))
    assert (
        "Interrupted" in tree
        if interrupt is KeyboardInterrupt
        else "Terminated" in tree
    )
    assert "Complete |" not in tree
    assert signal.getsignal(signal.SIGTERM) is previous
    assert "\x1b[?25h" in errors.getvalue()
    if interrupt == signal.SIGTERM:
        assert json.loads(output.getvalue())["struc"]


def test_dumb_terminal_prints_static_summary_without_cursor_codes(sample, monkeypatch):
    monkeypatch.setenv("TERM", "dumb")
    errors = Terminal()
    with redirect_stdout(io.StringIO()), redirect_stderr(errors):
        main(["polyfile", sample])
    assert "\x1b" not in errors.getvalue()
    assert "Complete |" in errors.getvalue()


def test_quiet_produces_no_terminal_status(sample):
    _, errors = invoke(sample, "--quiet", "-r", "json", tty=True)
    assert errors == ""


def test_failed_stderr_still_restores_logging():
    class BrokenTerminal(Terminal):
        def write(self, text):
            raise OSError("stderr closed")

    import logging

    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    with (
        pytest.raises(OSError, match="stderr closed"),
        logger.logging_context(stream=BrokenTerminal()) as session,
    ):
        session.title = "input"
    assert root.handlers == handlers
    assert root.level == level


def test_ascii_terminal_escapes_unencodable_labels(sample):
    class AsciiTerminal(io.TextIOWrapper):
        def isatty(self):
            return True

    buffer = io.BytesIO()
    errors = AsciiTerminal(buffer, encoding="ascii")
    with logger.logging_context(stream=errors) as session:
        session.start_scan("café.zip", recursive=False)
        session.tree.add(Discovery("1", "type", member="λ.txt"))
        logger.getStatusLogger("polyfile").warning("could not read λ.txt")
    errors.flush()
    assert b"caf\\xe9.zip" in buffer.getvalue()
    assert b"\\u03bb.txt" in buffer.getvalue()


def test_terminal_resize_keeps_recent_matches_visible(sample):
    from tests.test_logger import frame

    with logger.logging_context(stream=Terminal()) as session:
        session.start_scan("input", recursive=False)
        for index in range(30):
            session.tree.add(Discovery(str(index), f"type_{index:02}"))
        session.console.height = 15
        large = frame(session)
        session.console.height = 10
        small = frame(session)
        assert "type_29" in small
        assert len(small.splitlines()) < len(large.splitlines())


def test_debugger_logging_disables_live_status(sample):
    terminal = Terminal()
    with logger.logging_context(stream=terminal, interactive=False) as session:
        logger.start_scan("input", recursive=True)
        log = logger.getStatusLogger("polyfile")
        log.status("working")
        assert list(log.range([1, 2])) == [1, 2]
        assert not session.live.is_started
    assert terminal.getvalue() == ""
