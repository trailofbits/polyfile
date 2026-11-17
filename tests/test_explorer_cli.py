"""Validate terminal explorer options before a scan or terminal write starts."""

from collections.abc import Callable, Generator, Iterator, Sequence
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import argparse
import inspect
import io
import os
from pathlib import Path
import subprocess
import signal
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile import __main__ as cli
import polyfile
from polyfile.polyfile import Analyzer, Match


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def terminal_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Present terminal streams without permitting validation tests to start a scan."""
    monkeypatch.setattr(sys, "stdin", Terminal())
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setattr(sys, "stderr", Terminal())
    monkeypatch.setenv("TERM", "xterm-256color")
    path = tmp_path / "sample.bin"
    path.write_bytes(b"sample")
    yield path


CONFLICTS = (
    ("--format", "json"),
    ("-r", "mime"),
    ("--output", "unused.json"),
    ("-o", "unused.json"),
    ("--html", "unused.html"),
    ("-t", "unused.html"),
    ("--list",),
    ("-l",),
    ("--only-match-mime",),
    ("-I",),
    ("--explain",),
    ("--debugger",),
    ("--eval-command", "quit"),
    ("--no-debug-python",),
    ("--no-contents",),
    ("--version",),
    ("-dumpversion",),
)


@pytest.mark.parametrize("options", CONFLICTS)
@pytest.mark.parametrize("explore_first", (True, False))
def test_explorer_rejects_conflicting_options_before_scanning(
    terminal_cli: Path,
    options: tuple[str, ...],
    explore_first: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_scan(args: object) -> None:
        pytest.fail("invalid explorer options started a scan")

    monkeypatch.setattr(cli, "run_analysis", unexpected_scan)
    options = ("--explore", *options) if explore_first else (*options, "--explore")
    with pytest.raises(SystemExit) as exiting:
        cli.main(["polyfile", str(terminal_cli), *options])
    assert exiting.value.code == 2
    assert "--explore cannot be combined with" in capsys.readouterr().err
    assert not Path("unused.json").exists()
    assert not Path("unused.html").exists()


@pytest.mark.parametrize("filename", (None, "-", "missing", "."))
def test_explorer_requires_a_named_regular_file(
    terminal_cli: Path,
    filename: str | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = ["polyfile", "--explore"]
    if filename is not None:
        args.append(filename)
    with pytest.raises(SystemExit) as exiting:
        cli.main(args)
    assert exiting.value.code == 2
    assert "requires a" in capsys.readouterr().err


@pytest.mark.parametrize("stream", ("stdin", "stdout"))
def test_explorer_requires_terminal_streams(
    terminal_cli: Path,
    stream: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, stream, io.StringIO())
    with pytest.raises(SystemExit) as exiting:
        cli.main(["polyfile", "--explore", str(terminal_cli)])
    assert exiting.value.code == 2
    assert "requires terminal input and output" in capsys.readouterr().err


@pytest.mark.parametrize("term", ("", "dumb", "unknown"))
def test_explorer_requires_a_capable_terminal(
    terminal_cli: Path,
    term: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    monkeypatch.setenv("TERM", term)
    with pytest.raises(SystemExit) as exiting:
        cli.main(["polyfile", "--explore", str(terminal_cli)])
    assert exiting.value.code == 2
    assert "capable terminal" in capsys.readouterr().err


def test_redirected_explorer_does_not_write_terminal_controls(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"sample")
    result = subprocess.run(
        [sys.executable, "-m", "polyfile", "--explore", str(path)],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert b"\x1b" not in result.stderr
    assert b"requires terminal input and output" in result.stderr


def test_ordinary_cli_does_not_import_textual(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.write_bytes(b"")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from polyfile.__main__ import main; "
                "main(['polyfile', '--quiet', sys.argv[1]]); "
                "assert not any(n == 'textual' or n.startswith('textual.') for n in sys.modules)"
            ),
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"empty" in result.stdout
    assert result.stderr == b""


def test_module_entrypoint_does_not_import_itself_before_execution() -> None:
    result = subprocess.run(
        [sys.executable, "-Werror::RuntimeWarning", "-m", "polyfile", "--help"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    assert b"--explore" in result.stdout


@pytest.mark.parametrize("arguments", (None, ("polyfile", "-dumpversion")))
def test_public_entrypoint_delegates_the_original_arguments(
    arguments: Sequence[str] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Sequence[str] | None] = []
    signature = inspect.signature(cli.main)

    def delegate(argv: Sequence[str] | None = None) -> None:
        calls.append(argv)

    monkeypatch.setattr(cli, "main", delegate)
    assert inspect.signature(polyfile.main) == signature
    polyfile.main(arguments)
    assert len(calls) == 1
    assert calls[0] is arguments


def test_ordinary_help_preserves_argparse_color(monkeypatch: pytest.MonkeyPatch) -> None:
    if not hasattr(argparse.ArgumentParser(), "color"):
        pytest.skip("argparse color output requires Python 3.14 or newer")
    monkeypatch.delenv("NO_COLOR", raising=False)
    result = subprocess.run(
        [sys.executable, "-m", "polyfile", "--help"],
        capture_output=True,
        timeout=10,
        env={**os.environ, "FORCE_COLOR": "1", "PYTHON_COLORS": "1"},
    )
    assert result.returncode == 0
    assert result.stderr == b""
    assert b"\x1b" in result.stdout


@pytest.fixture
def explored(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Sequence[Match], bool]]:
    """Record the analysis crossing the terminal-UI boundary."""
    from polyfile.explorer import runner

    calls: list[tuple[Sequence[Match], bool]] = []

    def launch(
        path: str | Path,
        matches: Sequence[Match],
        *,
        partial: bool = False,
        terminated: Callable[[], bool] | None = None,
    ) -> int:
        calls.append((matches, partial))
        return 0

    monkeypatch.setattr(runner, "run_explorer", launch)
    return calls


def write_archive(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("hello.json", b'{"hello": "world"}')


def descendants(matches: Sequence[Match]) -> Iterator[Match]:
    stack = list(matches)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)


def run_in_terminal(arguments: list[str]) -> str:
    """Provide terminal output streams during the test call, after pytest's capture setup."""
    output = Terminal()
    with redirect_stdout(output), redirect_stderr(Terminal()):
        cli.main(arguments)
    return output.getvalue()


def test_explorer_recursively_analyzes_without_serializing_contents(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unwanted_serialization(*args: object, **kwargs: object) -> None:
        pytest.fail("explorer serialized the input as SBUD")

    monkeypatch.setattr(Analyzer, "sbud", unwanted_serialization)
    write_archive(terminal_cli)
    output = run_in_terminal(["polyfile", "--quiet", "--explore", str(terminal_cli)])
    matches, partial = explored[0]
    assert not partial
    nodes = list(descendants(matches))
    assert any(node.name == "application/zip" for node in nodes)
    assert any(node.decoded == b'{"hello": "world"}' for node in nodes)
    assert output == ""


def test_explorer_honors_matcher_and_parser_controls(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
) -> None:
    write_archive(terminal_cli)
    run_in_terminal(
        [
            "polyfile",
            "--quiet",
            "--explore",
            "--only-match",
            "--filetype",
            "application/zip",
            str(terminal_cli),
        ]
    )
    matches, partial = explored[0]
    assert not partial
    assert {node.name for node in matches} == {"application/zip"}
    assert all(not node.children for node in matches)


@pytest.mark.parametrize("limit", ("--max-depth", "--max-member-bytes", "--max-total-bytes"))
def test_explorer_honors_resource_limits(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
    limit: str,
) -> None:
    write_archive(terminal_cli)
    run_in_terminal(["polyfile", "--quiet", "--explore", limit, "0", str(terminal_cli)])
    nodes = list(descendants(explored[0][0]))
    assert any(node.analysis_status == "limited" for node in nodes)
    assert all(node.decoded is None for node in nodes)


@pytest.mark.parametrize("limit", ("0", "1"))
def test_explorer_marks_match_limited_results_partial(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
    limit: str,
) -> None:
    run_in_terminal(["polyfile", "--quiet", "--explore", "--max-matches", limit, str(terminal_cli)])
    assert explored[0][1]
    assert len(explored[0][0]) <= int(limit)


def test_explorer_requires_a_match_before_opening(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
) -> None:
    with pytest.raises(SystemExit) as exiting:
        run_in_terminal(
            [
                "polyfile",
                "--quiet",
                "--explore",
                "--max-matches",
                "0",
                "--require-match",
                str(terminal_cli),
            ]
        )
    assert exiting.value.code == 127
    assert explored == []


def test_explorer_retains_partial_scan_after_interrupt(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = Analyzer.matches

    def interrupt_scan(analyzer: Analyzer) -> Iterator[Match]:
        yield next(matches(analyzer))
        raise KeyboardInterrupt

    monkeypatch.setattr(Analyzer, "matches", interrupt_scan)
    monkeypatch.setattr(
        cli.KeyboardInterruptHandler, "handle_interrupt", staticmethod(lambda: True)
    )
    run_in_terminal(["polyfile", "--quiet", "--explore", str(terminal_cli)])
    assert explored[0][0]
    assert explored[0][1]


def test_scan_sigterm_takes_precedence_over_require_match(
    terminal_cli: Path,
    explored: list[tuple[Sequence[Match], bool]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def terminate_scan(analyzer: Analyzer) -> Iterator[Match]:
        os.kill(os.getpid(), signal.SIGTERM)
        yield from ()

    monkeypatch.setattr(Analyzer, "matches", terminate_scan)
    with pytest.raises(SystemExit) as exiting:
        run_in_terminal(
            [
                "polyfile",
                "--quiet",
                "--explore",
                "--require-match",
                str(terminal_cli),
            ]
        )
    assert exiting.value.code == 143
    assert explored == []


def test_sigterm_during_explorer_preparation_does_not_open_ui(
    terminal_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from polyfile.explorer import runner
    from polyfile.explorer.model import ExplorerModel

    model = runner.ExplorerModel

    def prepare(
        path: str | Path, matches: Sequence[Match], *, partial: bool = False
    ) -> ExplorerModel:
        os.kill(os.getpid(), signal.SIGTERM)
        return model(path, matches, partial=partial)

    def unexpected_ui(app: object) -> None:
        pytest.fail("explorer opened after receiving SIGTERM during preparation")

    monkeypatch.setattr(runner, "ExplorerModel", prepare)
    monkeypatch.setattr(runner.ExplorerApp, "run", unexpected_ui)
    previous = signal.getsignal(signal.SIGTERM)
    with pytest.raises(SystemExit) as exiting:
        run_in_terminal(["polyfile", "--quiet", "--explore", str(terminal_cli)])
    assert exiting.value.code == 143
    assert signal.getsignal(signal.SIGTERM) == previous


def test_sigterm_after_handler_installation_exits_before_pending_ui_work(
    terminal_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from polyfile.explorer import runner
    from polyfile.explorer.app import ExplorerApp

    signals, run = runner.explorer_signals, ExplorerApp.run

    @contextmanager
    def signal_before_run(app: ExplorerApp) -> Generator[None, None, None]:
        with signals(app):
            os.kill(os.getpid(), signal.SIGTERM)
            yield

    def headless(app: ExplorerApp) -> int | None:
        return run(app, headless=True)

    monkeypatch.setattr(runner, "explorer_signals", signal_before_run)
    monkeypatch.setattr(ExplorerApp, "run", headless)
    previous = signal.getsignal(signal.SIGTERM)
    with pytest.raises(SystemExit) as exiting:
        run_in_terminal(["polyfile", "--quiet", "--explore", str(terminal_cli)])
    assert exiting.value.code == 143
    assert signal.getsignal(signal.SIGTERM) == previous
