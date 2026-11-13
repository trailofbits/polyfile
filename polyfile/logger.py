"""Logging and terminal status shared by PolyFile's command-line tools."""

import logging
import sys
from collections.abc import Collection, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
from dataclasses import dataclass
from time import monotonic
from typing import Any, TextIO, TypeVar

from rich.console import Console, Group, RenderableType
from rich.highlighter import NullHighlighter
from rich.live import Live
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn
from rich.text import Text

STATUS = 15
TRACE = 5
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(TRACE, "TRACE")
T = TypeVar("T")


def literal(value: object, *, multiline: bool = False) -> str:
    """Escape terminal controls without interpreting markup in input-derived text."""
    return "".join(
        char
        if (char.isprintable() or (multiline and char == "\n"))
        else ascii(char)[1:-1]
        for char in str(value)
    )


@dataclass
class _Task:
    identifier: TaskID
    started: float
    delay: float
    interval: float
    completed: int = 0
    updated: float = 0.0


class TerminalSession:
    """Own one invocation's console and live rendering lifecycle."""

    def __init__(self, console: Console, *, interactive: bool):
        self.console = console
        self.interactive = interactive
        self.progress = Progress(
            TextColumn("{task.description}", markup=False),
            BarColumn(),
            TextColumn(
                "{task.completed:.0f}/{task.total:.0f}{task.fields[unit]}", markup=False
            ),
            TimeElapsedColumn(),
            console=console,
            auto_refresh=False,
        )
        self._tasks: list[_Task] = []
        self._status = Text()
        self.live = Live(
            console=console,
            get_renderable=self.render,
            refresh_per_second=4,
            transient=True,
            redirect_stdout=False,
            redirect_stderr=False,
        )

    def render(self) -> RenderableType:
        """Build the current status frame."""
        return Group(self._status, self.progress)

    def status(self, message: str) -> None:
        """Update the current activity without emitting a permanent log line."""
        self._status = Text(literal(message), style="cyan")
        if self.interactive:
            if message:
                self.live.start()
            else:
                self.live.stop()

    @contextmanager
    def task(
        self, description: str, total: int, unit: str, *, delay: float, interval: float
    ) -> Generator[_Task, None, None]:
        """Track a bounded unit of work and remove it even when iteration stops early."""
        for current in self._tasks:
            self.progress.update(current.identifier, visible=False)
        identifier = self.progress.add_task(
            literal(description), total=total, unit=literal(unit), visible=delay == 0
        )
        task = _Task(identifier, monotonic(), delay, interval)
        self._tasks.append(task)
        self._update(task)
        try:
            yield task
        finally:
            self._tasks.remove(task)
            self.progress.remove_task(identifier)
            if self._tasks:
                self._update(self._tasks[-1])
            elif not self._status:
                self.live.stop()

    def _update(self, task: _Task) -> None:
        task.updated = monotonic()
        visible = task.updated - task.started >= task.delay
        self.progress.update(task.identifier, completed=task.completed, visible=visible)
        if visible and self.interactive:
            self.live.start()

    def advance(self, task: _Task) -> None:
        """Count an item only after its consumer has processed it."""
        task.completed += 1
        if monotonic() - task.updated >= task.interval:
            self._update(task)

    @contextmanager
    def suspend(self) -> Generator[None, None, None]:
        """Clear the live frame while another stream writes or a prompt reads."""
        running = self.live.is_started
        self.live.stop()
        try:
            yield
        finally:
            if running:
                self.live.start()

    def close(self) -> None:
        """Restore the terminal before the invocation exits."""
        self.live.stop()


_session: ContextVar[TerminalSession | None] = ContextVar(
    "polyfile_terminal", default=None
)


class _LogHandler(RichHandler):
    def __init__(self, session: TerminalSession, *, quiet: bool, verbose: bool):
        super().__init__(
            console=session.console,
            show_time=False,
            show_path=False,
            highlighter=NullHighlighter(),
            markup=False,
        )
        self.session = session
        self.quiet = quiet
        self.verbose = verbose

    def emit(self, record: logging.LogRecord) -> None:
        if self.quiet:
            return
        if record.levelno == STATUS:
            self.session.status(record.getMessage())
            return
        if (
            not self.console.is_terminal
            and not self.verbose
            and record.levelno < logging.WARNING
        ):
            return
        record = copy(record)
        record.msg = literal(record.getMessage(), multiline=True)
        record.args = ()
        super().emit(record)


@contextmanager
def logging_context(
    level: int = STATUS,
    *,
    quiet: bool = False,
    interactive: bool = True,
    stream: TextIO | None = None,
) -> Generator[TerminalSession, None, None]:
    """Configure stderr logging for one invocation and restore the host's logging state.

    Args:
        level: Minimum diagnostic level, including STATUS and TRACE.
        quiet: Suppress every logger message and live update.
        interactive: Allow cursor movement; disable for interactive debuggers.
        stream: Stderr destination, resolved at invocation time when omitted.

    Yields:
        The invocation's terminal session.
    """
    stream = sys.stderr if stream is None else stream
    tty = stream.isatty()
    console = Console(
        file=stream,
        force_terminal=None if tty else False,
        force_jupyter=False,
        markup=False,
        highlight=False,
    )
    session = TerminalSession(
        console,
        interactive=tty and console.is_interactive and interactive and not quiet,
    )
    handler = _LogHandler(session, quiet=quiet, verbose=level <= logging.DEBUG)
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.CRITICAL + 1 if quiet else level)
    root.addHandler(handler)
    token = _session.set(session)
    try:
        yield session
    finally:
        session.close()
        _session.reset(token)
        root.removeHandler(handler)
        handler.close()
        root.setLevel(previous_level)


class StatusLogger(logging.LoggerAdapter):
    """Add status and trace helpers to a standard Python logger."""

    def __init__(self, name: str):
        super().__init__(logging.getLogger(name), {})

    def status(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Set the current terminal activity."""
        self.log(STATUS, msg, *args, **kwargs)

    def trace(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Emit extra-verbose diagnostic output."""
        self.log(TRACE, msg, *args, **kwargs)

    def clear_status(self) -> None:
        """Clear the current terminal activity."""
        self.status("")

    def range(
        self,
        iterable: Collection[T],
        desc: str = "",
        unit: str = "",
        *,
        delay: float = 0.0,
        update_interval: float = 0.5,
    ) -> Generator[T, None, None]:
        """Yield items while tracking completed work on an interactive terminal."""
        session = _session.get()
        if (
            session is None
            or not session.interactive
            or not iterable
            or not self.isEnabledFor(STATUS)
        ):
            yield from iterable
            return
        with session.task(
            desc, len(iterable), unit, delay=delay, interval=update_interval
        ) as task:
            for item in iterable:
                yield item
                session.advance(task)


def getStatusLogger(name: str) -> StatusLogger:
    """Return a status adapter without changing Python's global logger class."""
    return StatusLogger(name)


def get_root_logger() -> logging.Logger:
    """Return the standard root logger."""
    return logging.getLogger()


def setLevel(levelno: int) -> None:
    """Set the root diagnostic threshold."""
    get_root_logger().setLevel(levelno)
