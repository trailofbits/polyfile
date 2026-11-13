"""PolyMerge compares both trace groups and handles optional CLI inputs."""

import builtins
import io
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO, cast

import pytest

from polyfile import __version__
from polymerge import __main__ as cli


@pytest.fixture(autouse=True)
def restore_logging_level() -> Iterator[None]:
    level = logging.getLogger().level
    yield
    logging.getLogger().setLevel(level)


def trace_file(directory: Path, name: str, functions: tuple[str, ...]) -> str:
    path = directory / name
    path.write_text(
        json.dumps({function: [0] for function in functions}), encoding="utf-8"
    )
    return str(path)


@pytest.mark.parametrize("options", [[], ["--diff"]])
def test_single_input_without_a_diff_group_returns_normally(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    options: list[str],
) -> None:
    source = trace_file(tmp_path, "trace.json", ("reader",))
    assert cli.main(["polymerge", source, *options]) == 0
    assert capsys.readouterr().out == ""


def test_normal_merge_accepts_an_empty_legacy_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    structure = tmp_path / "structure.json"
    structure.write_text(json.dumps({"struc": []}), encoding="utf-8")
    trace = trace_file(tmp_path, "trace.json", ())
    cli.main(["polymerge", str(structure), trace])
    assert json.loads(capsys.readouterr().out) == {
        "struc": [],
        "versions": {"polymerge": __version__, "polytracker": "0.0.1"},
        "best_function_matches": {},
    }


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (("same",), ("same",), set()),
        (("shared", "left"), ("shared", "right"), {"left", "right"}),
        ((), ("right",), {"right"}),
        (("left",), (), {"left"}),
        ((), (), set()),
    ],
)
def test_diff_compares_the_two_input_groups(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    first: tuple[str, ...],
    second: tuple[str, ...],
    expected: set[str],
) -> None:
    first_file = trace_file(tmp_path, "first.json", first)
    second_file = trace_file(tmp_path, "second.json", second)
    with pytest.raises(SystemExit) as result:
        cli.main(["polymerge", first_file, "--diff", second_file])
    assert result.value.code == 0
    assert set(capsys.readouterr().out.strip().splitlines()) == expected


def test_diff_intersects_each_group_before_comparing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = [
        trace_file(tmp_path, f"first-{i}.json", ("shared", "left", f"one-{i}"))
        for i in range(2)
    ]
    second = [
        trace_file(tmp_path, f"second-{i}.json", ("shared", "right", f"two-{i}"))
        for i in range(2)
    ]
    with pytest.raises(SystemExit) as result:
        cli.main(["polymerge", *first, "--diff", *second])
    assert result.value.code == 0
    assert set(capsys.readouterr().out.strip().splitlines()) == {"left", "right"}


@pytest.mark.parametrize("mode", ["--diff", "--cfg"])
def test_demangling_reports_the_missing_optional_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    monkeypatch.setattr(cli, "cxxfilt", None)
    source = trace_file(tmp_path, "first.json", ("reader",))
    target = trace_file(tmp_path, "second.json", ("writer",))
    with pytest.raises(SystemExit) as result:
        cli.main(["polymerge", source, mode, target, "--demangle"])
    assert result.value.code == 2
    assert "cxxfilt" in capsys.readouterr().err


def test_unused_demangling_does_not_require_the_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "cxxfilt", None)
    source = trace_file(tmp_path, "trace.json", ("reader",))
    assert cli.main(["polymerge", source, "--demangle"]) == 0


def test_diff_closes_all_inputs_when_json_decoding_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[TextIO] = []
    open_input = builtins.open

    def record_open(
        path: str | Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> TextIO:
        stream = cast(TextIO, open_input(path, mode, buffering, encoding, errors))
        opened.append(stream)
        return stream

    monkeypatch.setattr(builtins, "open", record_open)
    source = trace_file(tmp_path, "first.json", ("reader",))
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    remaining = trace_file(tmp_path, "remaining.json", ("writer",))
    with pytest.raises(json.JSONDecodeError):
        cli.main(["polymerge", source, "--diff", str(invalid), remaining])
    assert opened
    assert all(stream.closed for stream in opened)


def test_missing_json_input_reports_the_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = trace_file(tmp_path, "first.json", ("reader",))
    missing = tmp_path / "missing.json"

    with pytest.raises(SystemExit) as result:
        cli.main(["polymerge", source, "--diff", str(missing)])

    assert result.value.code == 2
    assert str(missing) in capsys.readouterr().err


def test_diff_reads_the_dash_path_from_standard_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = trace_file(tmp_path, "first.json", ("reader",))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"writer": [0]})))

    with pytest.raises(SystemExit) as result:
        cli.main(["polymerge", source, "--diff", "-"])

    assert result.value.code == 0
    assert set(capsys.readouterr().out.strip().splitlines()) == {"reader", "writer"}
