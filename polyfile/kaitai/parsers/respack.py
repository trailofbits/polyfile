# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Respack(KaitaiStruct):
    """Resource file found in CPB firmware archives, mostly used on older CoolPad
    phones and/or tablets. The only observed files are called "ResPack.cfg".
    """
    SEQ_FIELDS = ["header", "json"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = Respack.Header(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['json']['start'] = self._io.pos()
        self.json = (self._io.read_bytes(self.header.len_json)).decode(u"UTF-8")
        self._debug['json']['end'] = self._io.pos()

    class Header(KaitaiStruct):
        SEQ_FIELDS = ["magic", "unknown", "len_json", "md5"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(2)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x52\x53":
                raise kaitaistruct.ValidationNotEqualError(b"\x52\x53", self.magic, self._io, u"/types/header/seq/0")
            self._debug['unknown']['start'] = self._io.pos()
            self.unknown = self._io.read_bytes(8)
            self._debug['unknown']['end'] = self._io.pos()
            self._debug['len_json']['start'] = self._io.pos()
            self.len_json = self._io.read_u4le()
            self._debug['len_json']['end'] = self._io.pos()
            self._debug['md5']['start'] = self._io.pos()
            self.md5 = (self._io.read_bytes(32)).decode(u"UTF-8")
            self._debug['md5']['end'] = self._io.pos()



