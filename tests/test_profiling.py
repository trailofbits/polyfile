"""Profiler pauses exclude ordinary work once across active parent profilers."""

import pytest

from polyfile import profiling
from polyfile.profiling import Profiler, Unprofiled, unprofiled


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.reads = 0

    def read(self) -> float:
        self.reads += 1
        if self.reads > 100:
            raise RuntimeError("Profiler exceeded the test clock's 100-read traversal budget")
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    result = _Clock()
    monkeypatch.setattr(profiling, "current_time_ms", result.read)
    return result


def test_single_profiler_pause_returns_and_excludes_its_duration(clock: _Clock) -> None:
    profiler = Profiler()
    profiler.start()
    clock.now = 10
    profiler.pause()
    clock.now = 15
    assert profiler.is_paused
    assert profiler.paused_ms == 5
    assert profiler.elapsed_ms == 10

    clock.now = 20
    profiler.unpause()
    assert not profiler.is_paused
    assert profiler.paused_ms == 10
    clock.now = 30
    profiler.stop()
    assert profiler.elapsed_ms == 20


def test_pause_excludes_time_from_each_parent_once(clock: _Clock) -> None:
    outer = Profiler()
    middle = Profiler(outer)
    inner = Profiler(middle)
    outer.start()
    clock.now = 5
    middle.start()
    clock.now = 10
    inner.start()
    clock.now = 20
    inner.pause()
    clock.now = 30
    assert all(profiler.is_paused for profiler in (outer, middle, inner))
    assert [profiler.elapsed_ms for profiler in (outer, middle, inner)] == [20, 15, 10]

    inner.unpause()
    clock.now = 40
    for profiler in (inner, middle, outer):
        assert not profiler.is_paused
        assert profiler.paused_ms == 10
        profiler.stop()
    assert [profiler.elapsed_ms for profiler in (outer, middle, inner)] == [30, 25, 20]


def test_unprofiled_context_pauses_active_nested_profilers(clock: _Clock) -> None:
    with Profiler() as outer:
        clock.now = 5
        with Profiler() as inner:
            clock.now = 10
            with Unprofiled():
                clock.now = 30
                assert outer.elapsed_ms == 10
                assert inner.elapsed_ms == 5
            assert not outer.is_paused
            assert not inner.is_paused
            clock.now = 40
        clock.now = 50
    assert outer.paused_ms == inner.paused_ms == 20
    assert outer.elapsed_ms == 30
    assert inner.elapsed_ms == 15


def test_explicit_unprofiled_context_resumes_after_an_exception(clock: _Clock) -> None:
    profiler = Profiler()
    profiler.start()
    clock.now = 10
    with pytest.raises(ValueError, match="work failed"):
        with Unprofiled(profiler):
            clock.now = 30
            raise ValueError("work failed")
    assert not profiler.is_paused
    clock.now = 40
    profiler.stop()
    assert profiler.paused_ms == 20
    assert profiler.elapsed_ms == 20


def test_unprofiled_decorator_preserves_result_and_excludes_time(clock: _Clock) -> None:
    @unprofiled
    def work(value: int) -> int:
        clock.now = 30
        return value + 1

    with Profiler() as profiler:
        clock.now = 10
        assert work(4) == 5
        clock.now = 40
    assert profiler.paused_ms == 20
    assert profiler.elapsed_ms == 20
    assert work.__name__ == "work"


def test_unprofiled_without_an_active_profiler_returns_normally() -> None:
    @unprofiled
    def work() -> str:
        return "result"

    with Unprofiled():
        assert work() == "result"


@pytest.mark.parametrize("operation", ["pause", "unpause"])
def test_completed_profiler_rejects_pause_operations(clock: _Clock, operation: str) -> None:
    profiler = Profiler()
    profiler.start()
    clock.now = 10
    profiler.stop()
    with pytest.raises(ValueError, match=f"cannot {operation} a completed profiler"):
        getattr(profiler, operation)()


def test_unpause_requires_an_active_pause(clock: _Clock) -> None:
    profiler = Profiler()
    profiler.start()
    with pytest.raises(ValueError, match="not currently paused"):
        profiler.unpause()


def test_paused_profiler_cannot_stop(clock: _Clock) -> None:
    profiler = Profiler()
    profiler.start()
    profiler.pause()
    with pytest.raises(ValueError, match="cannot be stopped while it is paused"):
        profiler.stop()
    profiler.unpause()
    profiler.stop()


def test_elapsed_time_requires_a_started_profiler() -> None:
    with pytest.raises(ValueError, match="has not been started"):
        _ = Profiler().elapsed_ms
