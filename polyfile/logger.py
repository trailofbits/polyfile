import logging
import sys
from time import time
from typing import Collection, Iterator, Optional, TypeVar


STATUS = 15
TRACE = 5


class StatusLogHandler(logging.StreamHandler):
    def __init__(self, stream=sys.stderr.buffer):
        super().__init__(stream=stream)
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
        self.addHandler(DEFAULT_STATUS_LOG_HANDLER)

    def status(self, msg, *args, **kwargs):
        if self.isEnabledFor(STATUS):
            self._log(STATUS, msg, args, **kwargs)

    def print(self, text: str):
        DEFAULT_STATUS_LOG_HANDLER.print(text)

    def range(
            self,
            iterable: Collection[T],
            desc: str = "",
            unit: str = "",
            delay: float = 0.0,
            update_interval: float = 0.5
    ) -> Iterator[T]:
        if not self.isEnabledFor(STATUS) or len(iterable) == 0:
            yield from iterable
            return
        size = len(iterable)
        start_time = time()
        last_update_time: float = 0.0
        last_percent: float = -1.0
        def print_msg(percent: float, item: int):
            msg = desc.strip()
            if msg:
                msg = f"{msg} "
            bar = "=" * int(30 * percent)
            if bar and percent < 1.0:
                bar = f"{bar[:-1]}>"
            bar = f"|{bar}{'-' * (30 - len(bar))}|"
            pct = f"{percent * 100.0:.1f}%"
            pct_pos = (len(bar) - len(pct)) // 2
            bar = f"{bar[:pct_pos]}{pct}{bar[pct_pos + len(pct):]}"
            msg = f"{msg}{bar} {item}/{size}{unit}"
            self.status(msg)
        if delay == 0.0:
            print_msg(0.0, 0)
        for i, obj in enumerate(iterable):
            current_time = time()
            elapsed_time = current_time - start_time
            if size == 1:
                new_percent = 1.0
            else:
                new_percent = i / (size - 1)
            if (elapsed_time >= delay and (
                    current_time - last_update_time >= update_interval or new_percent >= last_percent + 0.1
            )) or i == size - 1:
                last_update_time = current_time
                last_percent = new_percent
                print_msg(new_percent, i + 1)
            yield obj

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    def clear_status(self):
        self.status("")


logging.setLoggerClass(StatusLogger)


def getStatusLogger(name) -> StatusLogger:
    return logging.getLogger(name)


def get_root_logger():
    l = getStatusLogger(__name__)
    while l.parent:
        l = l.parent
    return l


def setLevel(levelno):
    get_root_logger().setLevel(levelno)
