# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class WindowsSystemtime(KaitaiStruct):
    """Microsoft Windows SYSTEMTIME structure, stores individual components
    of date and time as individual fields, up to millisecond precision.
    
    .. seealso::
       Source - https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-systemtime
    """
    SEQ_FIELDS = ["year", "month", "dow", "day", "hour", "min", "sec", "msec"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['year']['start'] = self._io.pos()
        self.year = self._io.read_u2le()
        self._debug['year']['end'] = self._io.pos()
        self._debug['month']['start'] = self._io.pos()
        self.month = self._io.read_u2le()
        self._debug['month']['end'] = self._io.pos()
        self._debug['dow']['start'] = self._io.pos()
        self.dow = self._io.read_u2le()
        self._debug['dow']['end'] = self._io.pos()
        self._debug['day']['start'] = self._io.pos()
        self.day = self._io.read_u2le()
        self._debug['day']['end'] = self._io.pos()
        self._debug['hour']['start'] = self._io.pos()
        self.hour = self._io.read_u2le()
        self._debug['hour']['end'] = self._io.pos()
        self._debug['min']['start'] = self._io.pos()
        self.min = self._io.read_u2le()
        self._debug['min']['end'] = self._io.pos()
        self._debug['sec']['start'] = self._io.pos()
        self.sec = self._io.read_u2le()
        self._debug['sec']['end'] = self._io.pos()
        self._debug['msec']['start'] = self._io.pos()
        self.msec = self._io.read_u2le()
        self._debug['msec']['end'] = self._io.pos()


