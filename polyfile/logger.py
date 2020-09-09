import logging
import sys


STATUS = 15


class StatusLogHandler(logging.StreamHandler):
    def __init__(self, stream=sys.stderr):
        super().__init__(stream=stream)
        self._status: str = ''

    def emit(self, record):
        isatty = self.stream.isatty()
        if self._status and isatty:
            self.stream.write(f"\r{' ' * len(self._status)}\r")
        msg = record.getMessage()
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')
        if record.levelno == STATUS and isatty:
            self._status = msg
        else:
            self.stream.write(msg)
            self.stream.write('\n')
        if self._status and isatty:
            self.stream.write(self._status)
        self.stream.flush()


logging.addLevelName(STATUS, "STATUS")

DEFAULT_STATUS_LOG_HANDLER = StatusLogHandler()


class StatusLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.addHandler(DEFAULT_STATUS_LOG_HANDLER)

    def status(self, msg, *args, **kwargs):
        if self.isEnabledFor(STATUS):
            self._log(STATUS, msg, args, **kwargs)

    def clear_status(self):
        self.status('')


logging.setLoggerClass(StatusLogger)


def getStatusLogger(name):
    return logging.getLogger(name)


def get_root_logger():
    l = getStatusLogger(__name__)
    while l.parent:
        l = l.parent
    return l


def setLevel(levelno):
    get_root_logger().setLevel(levelno)
