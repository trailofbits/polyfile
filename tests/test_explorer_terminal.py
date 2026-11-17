"""Exercise the real terminal lifecycle in a child process with an isolated PTY."""

from collections.abc import Generator
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
from time import monotonic

import pytest

pty = pytest.importorskip("pty", reason="PTY lifecycle checks require a POSIX terminal")
termios = pytest.importorskip("termios", reason="Terminal attributes require POSIX")
fcntl = pytest.importorskip("fcntl", reason="Terminal resizing requires POSIX")


@contextmanager
def terminal_process(
    command: list[str],
) -> Generator[tuple[int, subprocess.Popen[bytes]], None, None]:
    """Keep the slave open so tests can inspect its attributes after the child exits."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
    original = termios.tcgetattr(slave)
    process = subprocess.Popen(
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        start_new_session=True,
        env={**os.environ, "TERM": "xterm-256color", "NO_COLOR": "1"},
    )
    try:
        yield master, process
        assert termios.tcgetattr(slave) == original
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        os.close(master)
        os.close(slave)


def read_until(
    master: int,
    process: subprocess.Popen[bytes],
    output: bytearray,
    marker: bytes,
) -> None:
    """Wait for terminal output with a bounded timeout and no blocking pipe reads."""
    deadline = monotonic() + 20
    while marker not in output:
        if monotonic() >= deadline:
            pytest.fail(f"terminal did not produce {marker!r}: {bytes(output[-1500:])!r}")
        readable, _, _ = select.select([master], [], [], 0.05)
        if readable:
            try:
                chunk = os.read(master, 65_536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                chunk = b""
            output.extend(chunk)
        if process.poll() is not None and not readable:
            pytest.fail(f"terminal exited before {marker!r}: {bytes(output[-1500:])!r}")


@pytest.mark.parametrize(
    ("action", "expected"),
    ((b"q", 0), (b"\x11", 0), (b"\x03", 130), (signal.SIGINT, 130), (signal.SIGTERM, 143)),
)
def test_explorer_restores_terminal_after_quit_or_signal(
    tmp_path: Path,
    action: bytes | signal.Signals,
    expected: int,
) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    with terminal_process(
        [
            sys.executable,
            "-m",
            "polyfile",
            "--quiet",
            "--explore",
            str(path),
        ]
    ) as (master, process):
        output = bytearray()
        read_until(master, process, output, b"\x1b[?1049h")
        if isinstance(action, bytes):
            os.write(master, action)
        else:
            process.send_signal(action)
        read_until(master, process, output, b"\x1b[?1049l")
        assert process.wait(timeout=10) == expected
        assert b"\x1b[?25h" in output


def test_explorer_restores_terminal_after_ui_exception(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    program = """
import sys
from polyfile.__main__ import main
from polyfile.explorer.app import ExplorerApp
def fail(self):
    raise ValueError("test terminal cleanup")
ExplorerApp.on_mount = fail
main(["polyfile", "--quiet", "--explore", sys.argv[1]])
"""
    with terminal_process([sys.executable, "-c", program, str(path)]) as (master, process):
        output = bytearray()
        read_until(master, process, output, b"\x1b[?1049l")
        read_until(master, process, output, b"test terminal cleanup")
        assert process.wait(timeout=10) == 1
        assert b"test terminal cleanup" in output
        assert b"\x1b[?25h" in output


def test_redirected_stderr_is_rejected_before_terminal_mode(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    master, slave = pty.openpty()
    original = termios.tcgetattr(slave)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "polyfile", "--explore", str(path)],
            stdin=slave,
            stdout=slave,
            stderr=subprocess.PIPE,
            timeout=10,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        assert result.returncode == 2
        assert b"requires terminal input and output" in result.stderr
        assert b"\x1b" not in result.stderr
        assert termios.tcgetattr(slave) == original
    finally:
        os.close(master)
        os.close(slave)


def test_explorer_restores_host_signal_handlers(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    program = """
import signal
import sys
from polyfile.explorer.runner import run_explorer
def previous(signum, frame):
    pass
names = ("SIGINT", "SIGTERM", "SIGTSTP", "SIGCONT", "SIGWINCH", "SIGTTIN", "SIGTTOU")
signals = [getattr(signal, name) for name in names if hasattr(signal, name)]
for signum in signals:
    signal.signal(signum, previous)
code = run_explorer(sys.argv[1], [])
assert all(signal.getsignal(signum) is previous for signum in signals)
print("HOST SIGNALS RESTORED", flush=True)
sys.exit(code)
"""
    with terminal_process([sys.executable, "-c", program, str(path)]) as (master, process):
        output = bytearray()
        read_until(master, process, output, b"\x1b[?1049h")
        os.write(master, b"q")
        read_until(master, process, output, b"HOST SIGNALS RESTORED")
        assert process.wait(timeout=10) == 0
