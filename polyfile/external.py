"""Incremental external decoder execution with optional analysis limits."""

import math
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO, cast

from polyfile.compression import CHUNK_SIZE, DecodeError, OutputBuffer
from polyfile.fileutils import FileStream

DIAGNOSTIC_BYTES = 4096
_Event = tuple[str, bytes | Exception | None]


def _deadline(timeout: float | None) -> float | None:
    if timeout is None:
        return None
    try:
        finite = math.isfinite(timeout)
    except OverflowError as error:
        raise ValueError("helper_timeout must be positive finite seconds or None") from error
    if not finite or timeout <= 0:
        raise ValueError("helper_timeout must be positive finite seconds or None")
    return time.monotonic() + timeout


def _remaining(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DecodeError("external decoder exceeded its helper timeout", status="limited")
    return min(remaining, threading.TIMEOUT_MAX)


def _command(command: tuple[str, ...], max_memory: int | None) -> tuple[str, ...]:
    if not command or not os.path.isabs(command[0]):
        raise ValueError("an external decoder requires an absolute executable path")
    if max_memory is None:
        return command
    if sys.platform != "linux":
        raise DecodeError(
            "a hard external-decoder memory ceiling is supported only on Linux; "
            "omit --max-codec-memory to use this installed decoder",
            status="unsupported",
        )
    launcher = str(Path(__file__).with_name("_helper_launcher.py"))
    return (sys.executable, "-I", launcher, str(max_memory), *command)


def _environment(directory: str, extra: Mapping[str, str] | None) -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
    }
    for name in ("SystemRoot", "SYSTEMROOT", "WINDIR"):
        if name in os.environ:
            environment[name] = os.environ[name]
    if extra is not None:
        environment.update(extra)
    environment.update(TMPDIR=directory, TMP=directory, TEMP=directory)
    return environment


class _Pump:
    def __init__(self, process: subprocess.Popen[bytes], stream: FileStream) -> None:
        self.process = process
        self.stream = stream
        self.events: queue.Queue[_Event] = queue.Queue(maxsize=8)
        self.stopping = threading.Event()
        self.threads = [
            threading.Thread(target=self._work, args=(self._write,), daemon=True),
            threading.Thread(target=self._work, args=(self._stdout,), daemon=True),
            threading.Thread(target=self._work, args=(self._stderr,), daemon=True),
        ]

    def notify(self, event: _Event) -> None:
        while not self.stopping.is_set():
            try:
                self.events.put(event, timeout=0.1)
                return
            except queue.Full:
                continue

    def _work(self, operation: Callable[[], None]) -> None:
        try:
            operation()
        except BrokenPipeError as error:
            self.notify(("broken", error))
        except Exception as error:
            self.notify(("error", error))
        finally:
            self.notify(("done", None))

    def _write(self) -> None:
        with cast(BinaryIO, self.process.stdin) as pipe:
            while not self.stopping.is_set():
                chunk = self.stream.read(CHUNK_SIZE)
                if not chunk:
                    return
                data = memoryview(chunk)
                while data and not self.stopping.is_set():
                    written = pipe.write(data)
                    if not written:
                        raise OSError("external decoder stopped accepting input")
                    data = data[written:]

    def _read(self, pipe: BinaryIO, name: str) -> None:
        with pipe:
            while not self.stopping.is_set():
                data = pipe.read(CHUNK_SIZE)
                if not data:
                    return
                self.notify((name, data))

    def _stdout(self) -> None:
        self._read(cast(BinaryIO, self.process.stdout), "stdout")

    def _stderr(self) -> None:
        self._read(cast(BinaryIO, self.process.stderr), "stderr")

    def start(self) -> None:
        for thread in self.threads:
            thread.start()

    def stop(self) -> None:
        self.stopping.set()
        _terminate(self.process)
        self.process.wait()
        for thread in self.threads:
            if thread.ident is not None:
                thread.join()
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            if pipe is not None and not pipe.closed:
                pipe.close()


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if os.name != "posix":
        if process.poll() is None:
            process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        process.wait()
    except PermissionError:
        process.kill()


def _failure(returncode: int, diagnostic: bytes, max_memory: int | None) -> DecodeError:
    message = diagnostic.decode("utf-8", errors="replace").strip()
    limited = max_memory is not None and (
        returncode == 125
        or re.search(
            r"memoryerror|out of memory|memory exhausted|cannot allocate|failed to map",
            message,
            re.IGNORECASE,
        )
        is not None
    )
    detail = message or f"process exited with status {returncode}"
    return DecodeError(
        f"external decoder failed: {detail}", status="limited" if limited else "invalid"
    )


def _collect(
    pump: _Pump, output: OutputBuffer, deadline: float | None, max_memory: int | None
) -> bytes:
    diagnostic = bytearray()
    completed = 0
    broken: Exception | None = None
    while completed < len(pump.threads):
        try:
            name, value = pump.events.get(timeout=_remaining(deadline))
        except queue.Empty:
            continue
        if name == "done":
            completed += 1
        elif name == "stdout":
            output.append(cast(bytes, value))
        elif name == "stderr":
            diagnostic.extend(cast(bytes, value)[: DIAGNOSTIC_BYTES - len(diagnostic)])
        elif name == "broken":
            broken = cast(Exception, value)
        else:
            raise DecodeError(f"cannot stream external decoder data: {value}")
    return _finish(
        pump.process,
        output,
        deadline,
        max_memory,
        diagnostic=bytes(diagnostic),
        broken=broken,
    )


def _finish(
    process: subprocess.Popen[bytes],
    output: OutputBuffer,
    deadline: float | None,
    max_memory: int | None,
    *,
    diagnostic: bytes,
    broken: Exception | None,
) -> bytes:
    while True:
        try:
            returncode = process.wait(timeout=_remaining(deadline))
            break
        except subprocess.TimeoutExpired:
            _remaining(deadline)
    if returncode:
        raise _failure(returncode, bytes(diagnostic), max_memory)
    if broken is not None:
        raise DecodeError(f"external decoder closed its input prematurely: {broken}")
    return output.finish()


def run_helper(
    stream: FileStream,
    command: tuple[str, ...],
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    helper_timeout: float | None = None,
    environment: Mapping[str, str] | None = None,
) -> bytes:
    """Runs a fixed decoder command while streaming all three standard pipes.

    Args:
        stream: Encoded bytes to send from its current position through EOF.
        command: Fixed argument vector beginning with an absolute executable path.
        max_output: Optional decoded-output allowance, checked before bytes are retained.
        max_memory: Optional hard helper address-space ceiling, supported on Linux.
        helper_timeout: Optional positive timeout in seconds for this invocation.
        environment: Fixed format-specific environment values supplied by the adapter.

    Returns:
        Complete output after the helper exits successfully.

    Raises:
        DecodeError: If the helper is unavailable, invalid, or exceeds a requested limit.
        ValueError: If the command lacks an absolute executable path.
    """
    argv = _command(command, max_memory)
    deadline = _deadline(helper_timeout)
    with TemporaryDirectory(prefix="polyfile-decoder-") as directory:
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                close_fds=True,
                cwd=directory,
                env=_environment(directory, environment),
                start_new_session=os.name == "posix",
            )
        except OSError as error:
            raise DecodeError(
                f"cannot start external decoder {command[0]}: {error}",
                status="unsupported",
            ) from error
        pump = _Pump(process, stream)
        try:
            pump.start()
            return _collect(pump, OutputBuffer(max_output), deadline, max_memory)
        finally:
            pump.stop()
