"""Own the explorer's signal lifecycle while Textual owns the terminal."""

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
import signal
from types import FrameType

from polyfile.explorer.app import ExplorerApp
from polyfile.explorer.model import ExplorerModel
from polyfile.polyfile import Match


@contextmanager
def explorer_signals(app: ExplorerApp) -> Generator[None, None, None]:
    """Schedule orderly UI shutdown and restore the caller's signal handlers."""

    def interrupt(signum: int, frame: FrameType | None) -> None:
        code = 128 + signum
        app.call_later(app.exit, code, return_code=code)

    names = ("SIGINT", "SIGTERM", "SIGTSTP", "SIGCONT", "SIGWINCH", "SIGTTIN", "SIGTTOU")
    previous = {
        getattr(signal, name): signal.getsignal(getattr(signal, name))
        for name in names
        if hasattr(signal, name)
    }
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, interrupt)
        yield
    finally:
        for signum, handler in previous.items():
            if handler is not None:
                signal.signal(signum, handler)


def run_explorer(
    path: str | Path,
    matches: Sequence[Match],
    *,
    partial: bool = False,
    terminated: Callable[[], bool] | None = None,
) -> int:
    """Explore an existing analysis and return its terminal application's exit code.

    Args:
        path: Original input, kept available for bounded byte reads.
        matches: Completed or explicitly retained top-level match trees.
        partial: Whether scanning stopped before the analysis was complete.
        terminated: Whether SIGTERM arrived during the scan-to-UI handoff.

    Returns:
        Zero on normal exit, 130 for SIGINT, 143 for SIGTERM, or Textual's error code.
    """
    app = ExplorerApp(ExplorerModel(path, matches, partial=partial))
    with explorer_signals(app):
        if terminated is not None and terminated():
            return 128 + signal.SIGTERM
        result = app.run()
    return result or app.return_code or 0
