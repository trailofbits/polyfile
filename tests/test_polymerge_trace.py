"""PolyTracker trace readers preserve empty inputs and iterable taint sources."""

import pytest

from polymerge.polytracker import FunctionInfo, ProgramTrace, parse


@pytest.mark.parametrize("sources", [{}, {"input.bin": [1, 3], "other.bin": [2]}])
def test_function_sources_return_independent_iterators(sources: dict[str, list[int]]) -> None:
    function = FunctionInfo("reader", sources)
    first = iter(function)
    second = iter(function)
    assert first is not second
    assert list(first) == list(sources)
    assert list(second) == list(sources)
    assert list(function.items()) == list(sources.items())
    for source in function:
        assert function[source] == sources[source]


def test_empty_legacy_input_returns_an_empty_program_trace() -> None:
    trace = parse({})
    assert isinstance(trace, ProgramTrace)
    assert trace.polytracker_version == (0, 0, 1)
    assert trace.functions == {}


def test_legacy_trace_preserves_unnamed_input_sources() -> None:
    trace = parse({"reader": [0, 3]})
    assert trace.polytracker_version == (0, 0, 1)
    assert list(trace.functions) == ["reader"]
    function = trace.functions["reader"]
    assert list(function) == [None]
    assert function[None] == [0, 3]


def test_second_legacy_format_preserves_named_sources_and_callers() -> None:
    trace = parse({"reader": {"input_bytes": {"input.bin": [2]}, "called_from": ["main"]}})
    assert trace.polytracker_version == (0, 0, 1, "alpha2.1")
    function = trace.functions["reader"]
    assert list(function) == ["input.bin"]
    assert function["input.bin"] == [2]
    assert function.cmp_bytes == {"input.bin": [2]}
    assert function.called_from == frozenset({"main"})


def test_versioned_trace_keeps_untainted_runtime_functions() -> None:
    trace = parse(
        {
            "version": "1.0.1",
            "tainted_functions": {"reader": {"cmp_bytes": {"input.bin": [2]}}},
            "runtime_cfg": {"reader": ["main"], "main": []},
        }
    )
    assert trace.polytracker_version == ["1", "0", "1"]
    assert set(trace.functions) == {"reader", "main"}
    assert list(trace.functions["reader"]) == ["input.bin"]
    assert list(trace.functions["main"]) == []
