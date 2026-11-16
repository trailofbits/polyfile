from functools import wraps
import time
from collections.abc import Callable
from typing import ParamSpec, Self, TypeVar
from polyfile import logger

log = logger.getStatusLogger(__file__)


def current_time_ms() -> float:
    return time.process_time_ns() / 1000000.0


# Note: This assumes single-threading, but that's basically the case as long as the GIL exists
_PROFILER_STACK: list["Profiler"] = []
P = ParamSpec("P")
ResultT = TypeVar("ResultT")


class Profiler:
    def __init__(self, parent: 'Profiler | None' = None):
        self.start_time_ms: float | None = None
        self.end_time_ms: float | None = None
        self.parent: Profiler | None = parent
        self._paused_start_time_ms: list[float] = []
        self._paused_ms: float = 0.0

    @property
    def complete(self) -> bool:
        return self.end_time_ms is not None

    @property
    def is_paused(self) -> bool:
        return bool(self._paused_start_time_ms)

    @property
    def paused_ms(self) -> float:
        if self.complete or not self.is_paused:
            return self._paused_ms
        return self._paused_ms + current_time_ms() - self._paused_start_time_ms[0]

    def pause(self):
        """Pause this profiler and each active parent."""
        profiler: Profiler | None = self
        while profiler is not None:
            if profiler.complete:
                raise ValueError("You cannot pause a completed profiler")
            profiler._paused_start_time_ms.append(current_time_ms())
            profiler = profiler.parent

    def unpause(self) -> None:
        """End one pause on this profiler and each parent, counting overlapping time once."""
        profiler: Profiler | None = self
        while profiler is not None:
            if profiler.complete:
                raise ValueError("You cannot unpause a completed profiler")
            elif not profiler.is_paused:
                raise ValueError("The profiler is not currently paused")
            paused_start_time_ms = profiler._paused_start_time_ms.pop()
            if not profiler.is_paused:
                profiler._paused_ms += current_time_ms() - paused_start_time_ms
            profiler = profiler.parent

    @property
    def elapsed_ms(self) -> float:
        if self.start_time_ms is None:
            raise ValueError("the profiler has not been started yet")
        if self.end_time_ms is None:
            end_time_ms = current_time_ms()
        else:
            end_time_ms = self.end_time_ms
        return end_time_ms - self.start_time_ms - self.paused_ms

    def start(self):
        self.start_time_ms = current_time_ms()
        self.end_time_ms = None

    def stop(self):
        if self._paused_start_time_ms:
            raise ValueError("A profiler cannot be stopped while it is paused")
        self.end_time_ms = current_time_ms()

    def __enter__(self) -> Self:
        self.start()
        if self.parent is None and _PROFILER_STACK:
            self.parent = _PROFILER_STACK[-1]
        _PROFILER_STACK.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if _PROFILER_STACK[-1] is not self:
            log.warning(f"Profiler {self!r} stopped before its children stopped!")
            _PROFILER_STACK.remove(self)
        else:
            _PROFILER_STACK.pop()


class Unprofiled:
    """Exclude work from explicit or active profilers, including reentrant contexts."""

    def __init__(self, profiler: Profiler | None = None):
        self.profiler: Profiler | None = profiler
        self._had_profiler = profiler is not None
        self._previous_profilers: list[Profiler | None] = []

    def __enter__(self) -> None:
        profiler = self.profiler
        if not self._had_profiler and _PROFILER_STACK:
            profiler = _PROFILER_STACK[-1]
        if profiler is not None:
            profiler.pause()
        self._previous_profilers.append(self.profiler)
        self.profiler = profiler

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.profiler is not None:
            self.profiler.unpause()
        self.profiler = self._previous_profilers.pop()


def unprofiled(func: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        with Unprofiled():
            return func(*args, **kwargs)
    return wrapped
