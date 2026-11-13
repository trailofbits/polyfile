"""Logging and terminal status shared by PolyFile's command-line tools."""

import logging
import sys
from collections.abc import Collection, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Any, TextIO, TypeVar

from rich.console import Console, Group, RenderableType
from rich.highlighter import NullHighlighter
from rich.live import Live
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn
from rich.spinner import Spinner
from rich.text import Text

from polyfile.matchtree import Discovery, MatchTree, literal

if TYPE_CHECKING:
    from polyfile.magic import Match as MagicMatch
    from polyfile.polyfile import Match

STATUS = 15
TRACE = 5
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(TRACE, "TRACE")
T = TypeVar("T")


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

    def __init__(
        self, console: Console, *, interactive: bool, show_summary: bool = False
    ):
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
        self.tree = MatchTree()
        self.title = ""
        self.recursive = False
        self.outcome = "Complete"
        self.started = monotonic()
        self.show_summary = show_summary
        self._suspended = 0
        self._closed = False
        self.spinner = Spinner("dots" if console.encoding.startswith("utf") else "line")
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
        if self.title:
            header = Text(
                f"PolyFile  {literal(self.title, encoding=self.console.encoding)}",
                style="bold",
                no_wrap=True,
                overflow="ellipsis",
            )
            summary = Text(
                f"{len(self.tree):,} matches | {monotonic() - self.started:.1f}s",
                style="dim",
            )
            activity = self.spinner if not self._tasks else self._status
            return Group(
                header,
                summary,
                self.tree.render(
                    limit=max(1, self.console.height - 9),
                    encoding=self.console.encoding,
                ),
                activity,
                self.progress,
            )
        return Group(self._status, self.progress)

    def start_scan(self, title: str, *, recursive: bool) -> None:
        """Start a scan without assuming the total recursive work is known."""
        self.title = title
        self.recursive = recursive
        self.started = monotonic()
        self.status("Scanning input")

    def partial(self, outcome: str) -> None:
        """Retain an accurate completion label when analysis stops early."""
        self.outcome = outcome

    def status(self, message: str) -> None:
        """Update the current activity without emitting a permanent log line."""
        self._status = Text(
            literal(message, encoding=self.console.encoding),
            style="cyan",
            no_wrap=True,
            overflow="ellipsis",
        )
        self.spinner.update(text=self._status)
        if self.interactive:
            if message:
                self._start_live()
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
            literal(description, encoding=self.console.encoding),
            total=total,
            unit=literal(unit, encoding=self.console.encoding),
            visible=delay == 0,
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
            elif not self._status and not self.title:
                self.live.stop()

    def _update(self, task: _Task) -> None:
        task.updated = monotonic()
        visible = task.updated - task.started >= task.delay
        self.progress.update(task.identifier, completed=task.completed, visible=visible)
        if visible and self.interactive:
            self._start_live()

    def _start_live(self) -> None:
        if self.interactive and not self._suspended and not self._closed:
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
        self._suspended += 1
        self.live.stop()
        try:
            yield
        finally:
            self._suspended -= 1
            if running:
                self._start_live()

    def close(self) -> None:
        """Restore the terminal before the invocation exits."""
        if self._closed:
            return
        self._closed = True
        self.live.stop()
        if self.title and self.show_summary:
            elapsed = monotonic() - self.started
            title = literal(self.title, encoding=self.console.encoding)
            self.console.print(Text(f"PolyFile  {title}", style="bold"))
            self.console.print(self.tree.render(encoding=self.console.encoding))
            self.console.print(
                Text(
                    f"{self.outcome} | {len(self.tree):,} matches | {elapsed:.2f}s",
                    style="green" if self.outcome == "Complete" else "yellow",
                )
            )


_session: ContextVar[TerminalSession | None] = ContextVar(
    "polyfile_terminal", default=None
)


def start_scan(title: str, *, recursive: bool) -> None:
    """Initialize the active invocation's match display."""
    session = _session.get()
    if session is not None and session.show_summary:
        session.start_scan(title, recursive=recursive)


def partial(outcome: str) -> None:
    """Mark the active scan as incomplete."""
    session = _session.get()
    if session is not None:
        session.partial(outcome)


@contextmanager
def suspend_status() -> Generator[None, None, None]:
    """Suspend animation while writing results or reading an interrupt prompt."""
    session = _session.get()
    if session is None:
        yield
    else:
        with session.suspend():
            yield


def _containing_file(match: "Match") -> tuple["Match | None", str]:
    from polyfile.polyfile import Submatch

    parent = match.parent
    member = ""
    while parent is not None and isinstance(parent, Submatch):
        if parent.display_name != parent.name and not member:
            member = parent.display_name
        if parent.name == "LocalFileHeader" and not member:
            for child in parent.children:
                if child.name == "file_name" and isinstance(child.match, bytes):
                    member = child.match.decode("utf-8", "backslashreplace")
        parent = parent.parent
    return parent, member


def report_match(match: "Match") -> None:
    """Record a parsed file-type verdict without inspecting its lazy magic result."""
    session = _session.get()
    if session is None or not session.show_summary:
        return
    parent, member = _containing_file(match)
    session.tree.add(
        Discovery(
            str(id(match)),
            match.name,
            parent=str(id(parent)) if parent is not None else None,
            member=member,
            offset=match.offset,
            size=match.length,
            source=match.source,
        )
    )


def report_identification(match: "MagicMatch", name: str, description: str) -> None:
    """Record an already-rendered identification without initiating recursive analysis."""
    session = _session.get()
    if session is None or not session.show_summary or session.recursive:
        return
    source = (
        "file"
        if match.context.decoded_from is None
        else (f"decoded text ({match.context.decoded_from})")
    )
    key = f"{source}\0{name}\0{description}"
    session.tree.add(
        Discovery(key, name, member=description, size=len(match.data), source=source)
    )


def report_file_identification(match: "MagicMatch", description: str) -> None:
    """Display an existing file description without resolving additional MIME labels."""
    report_identification(match, description, "")


def report_analysis_status(roots: Collection["Match"]) -> None:
    """Show limitations on parser regions without adding individual fields to the tree."""
    from polyfile.polyfile import Submatch

    session = _session.get()
    if session is None or not session.show_summary:
        return
    stack = [(root, str(id(root))) for root in roots]
    while stack:
        match, owner = stack.pop()
        if not isinstance(match, Submatch):
            owner = str(id(match))
        if match.analysis_status:
            message = f"{match.display_name}: {match.analysis_status}: {match.analysis_message}"
            session.tree.annotate(owner, message)
        stack.extend((child, owner) for child in match.children)


@contextmanager
def scanning_region(parent: "Match | None") -> Generator[None, None, None]:
    """Restore the containing region's activity after a recursive scan returns."""
    session = _session.get()
    if session is None or not session.show_summary:
        yield
        return
    previous = session._status.plain
    if parent is not None:
        container, member = _containing_file(parent)
        name = member or (
            container.name if container is not None else parent.display_name
        )
        session.status(f"Scanning {name} ({parent.source})")
    try:
        yield
    finally:
        session.status(previous)


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

    def render_message(self, record: logging.LogRecord, message: str) -> Text:
        return Text(literal(message, multiline=True, encoding=self.console.encoding))

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
        show_summary=tty and interactive and not quiet,
    )
    handler = _LogHandler(session, quiet=quiet, verbose=level <= logging.DEBUG)
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.CRITICAL + 1 if quiet else level)
    root.addHandler(handler)
    token = _session.set(session)
    try:
        yield session
    except BaseException as error:
        if isinstance(error, SystemExit):
            if error.code not in (0, 127) and session.outcome == "Complete":
                session.partial("Failed")
        else:
            session.partial(
                "Interrupted" if isinstance(error, KeyboardInterrupt) else "Failed"
            )
        raise
    finally:
        try:
            session.close()
        finally:
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
