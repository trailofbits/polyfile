import logging
import sys


STATUS = 15


class StatusLogHandler(logging.StreamHandler):
    def __init__(self, stream=sys.stderr.buffer):
        super().__init__(stream=stream)
        self._status = b''

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

DEFAULT_STATUS_LOG_HANDLER = StatusLogHandler()

_debug_nesting = 0


class DebugNester:
    def __init__(self, status_logger):
        self.logger = status_logger

    def __enter__(self):
        self.logger.push_debug_nesting()
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.pop_debug_nesting()


class StatusLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.addHandler(DEFAULT_STATUS_LOG_HANDLER)

    def status(self, msg, *args, **kwargs):
        if self.isEnabledFor(STATUS):
            self._log(STATUS, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        global _debug_nesting
        msg = '    ' * _debug_nesting + msg
        super().debug(msg, *args, **kwargs)

    @staticmethod
    def push_debug_nesting():
        global _debug_nesting
        _debug_nesting += 1

    def pop_debug_nesting(self):
        global _debug_nesting
        _debug_nesting = _debug_nesting - 1
        if _debug_nesting < 0:
            self.warn("Unbalanced debug nesting")
            _debug_nesting = 0

    def debug_nesting(self):
        return DebugNester(self)

    def clear_status(self):
        self.status('')


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
