from contextlib import nullcontext
import logging
import sys
from typing import Collection, Iterable, TypeVar, Union

from rich.console import Console, ConsoleRenderable, RichCast, Style
from rich.progress import track
from rich.status import Status


STATUS = 15
TRACE = 5


class StatusLogHandler(logging.StreamHandler):
    def __init__(self, stream=sys.stderr.buffer):
        super().__init__(stream=stream)  # type: ignore
        self._status: bytes = b''

    def print(self, text):
        if self._status and self.stream.isatty():
            self.stream.write(f"\r{' ' * len(self._status)}\r".encode('utf-8'))
            self.stream.flush()
            sys.stdout.write(str(text))
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.stream.write(self._status)
            self.stream.flush()
        else:
            sys.stdout.write(str(text))
            sys.stdout.write("\n")

    def emit(self, record):
        isatty = self.stream.isatty()
        if self._status and isatty:
            self.stream.write(f"\r{' ' * len(self._status)}\r".encode('utf-8'))
        msg = record.getMessage()
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        if record.levelno == STATUS and isatty:
            self._status = msg
        else:
            self.stream.write(msg)
            self.stream.write(b'\n')
        if self._status and isatty:
            self.stream.write(self._status)
        self.stream.flush()


logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(TRACE, "TRACE")

DEFAULT_STATUS_LOG_HANDLER = StatusLogHandler()


T = TypeVar("T")


class StatusLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.console: Console = Console(log_path=False, file=sys.stderr)
        # self.addHandler(DEFAULT_STATUS_LOG_HANDLER)

    def status(self,
               msg: Union[ConsoleRenderable, RichCast, str],
               *,
               spinner: str = "dots",
               spinner_style: str | Style = "status.spinner",
               speed: float = 1.0,
               refresh_per_second: float = 12.5
    ) -> Union[Status, nullcontext]:
        if self.isEnabledFor(STATUS):
            return self.console.status(msg, spinner=spinner, spinner_style=spinner_style, speed=speed,
                                       refresh_per_second=refresh_per_second)
        else:
            return nullcontext()

    def range(
            self,
            iterable: Collection[T],
            desc: str = "",
            update_interval: float = 0.1,
            transient: bool = False
    ) -> Iterable[T]:
        return track(sequence=iterable, description=desc, console=self.console, transient=transient,
                     update_period=update_interval)

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    def clear_status(self):
        self.status("")


logging.setLoggerClass(StatusLogger)


def getStatusLogger(name) -> StatusLogger:
    return logging.getLogger(name)  # type: ignore


def get_root_logger() -> logging.Logger:
    logger: logging.Logger = getStatusLogger(__name__)
    while logger.parent:
        logger = logger.parent
    return logger


def setLevel(levelno):
    get_root_logger().setLevel(levelno)
