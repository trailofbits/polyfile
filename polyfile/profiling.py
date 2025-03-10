from functools import wraps
import time
from typing import Optional
from . import logger

log = logger.getStatusLogger(__file__)


def current_time_ms():
    return time.process_time_ns() / 1000000.0


# Note: This assumes single-threading, but that's basically the case as long as the GIL exists
_PROFILER_STACK: ["Profiler"] = []


class Profiler:
    def __init__(self, parent: Optional["Profiler"] = None):
        self.start_time_ms: Optional[float] = None
        self.end_time_ms: Optional[float] = None
        self.parent: Optional[Profiler] = parent
        self._paused_start_time_ms: [float] = []
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
        profiler = self
        while profiler is not None:
            if profiler.complete:
                raise ValueError("You cannot pause a completed profiler")
            profiler._paused_start_time_ms.append(current_time_ms())

    def unpause(self):
        profiler = self
        while profiler is not None:
            if profiler.complete:
                raise ValueError("You cannot unpause a completed profiler")
            elif not profiler.is_paused:
                raise ValueError("The profiler is not currently paused")
            profiler._paused_ms += current_time_ms() - profiler._paused_start_time_ms[-1]
            profiler._paused_start_time_ms.pop()
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

    def __enter__(self) -> "Profiler":
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
    def __init__(self, profiler: Optional[Profiler] = None):
        self.profiler: Optional[Profiler] = profiler
        self._had_profiler = profiler is not None

    def __enter__(self):
        if not self._had_profiler and _PROFILER_STACK:
            self.profiler = _PROFILER_STACK[-1]
        if self.profiler is not None:
            self.profiler.pause()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.profiler is not None:
            self.profiler.unpause()
            if not self._had_profiler:
                self.profiler = None


def unprofiled(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        with Unprofiled():
            return func(*args, **kwargs)
    return wrapped
