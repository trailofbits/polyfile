# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidNanoappHeader(KaitaiStruct):
    """
    .. seealso::
       Source - https://android.googlesource.com/platform/system/chre/+/a7ff61b9/build/build_template.mk#130
    """
    SEQ_FIELDS = ["header_version", "magic", "app_id", "app_version", "flags", "hub_type", "chre_api_major_version", "chre_api_minor_version", "reserved"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header_version']['start'] = self._io.pos()
        self.header_version = self._io.read_u4le()
        self._debug['header_version']['end'] = self._io.pos()
        if not self.header_version == 1:
            raise kaitaistruct.ValidationNotEqualError(1, self.header_version, self._io, u"/seq/0")
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x4E\x41\x4E\x4F":
            raise kaitaistruct.ValidationNotEqualError(b"\x4E\x41\x4E\x4F", self.magic, self._io, u"/seq/1")
        self._debug['app_id']['start'] = self._io.pos()
        self.app_id = self._io.read_u8le()
        self._debug['app_id']['end'] = self._io.pos()
        self._debug['app_version']['start'] = self._io.pos()
        self.app_version = self._io.read_u4le()
        self._debug['app_version']['end'] = self._io.pos()
        self._debug['flags']['start'] = self._io.pos()
        self.flags = self._io.read_u4le()
        self._debug['flags']['end'] = self._io.pos()
        self._debug['hub_type']['start'] = self._io.pos()
        self.hub_type = self._io.read_u8le()
        self._debug['hub_type']['end'] = self._io.pos()
        self._debug['chre_api_major_version']['start'] = self._io.pos()
        self.chre_api_major_version = self._io.read_u1()
        self._debug['chre_api_major_version']['end'] = self._io.pos()
        self._debug['chre_api_minor_version']['start'] = self._io.pos()
        self.chre_api_minor_version = self._io.read_u1()
        self._debug['chre_api_minor_version']['end'] = self._io.pos()
        self._debug['reserved']['start'] = self._io.pos()
        self.reserved = self._io.read_bytes(6)
        self._debug['reserved']['end'] = self._io.pos()
        if not self.reserved == b"\x00\x00\x00\x00\x00\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00\x00\x00\x00", self.reserved, self._io, u"/seq/8")

    @property
    def is_signed(self):
        if hasattr(self, '_m_is_signed'):
            return self._m_is_signed if hasattr(self, '_m_is_signed') else None

        self._m_is_signed = (self.flags & 1) != 0
        return self._m_is_signed if hasattr(self, '_m_is_signed') else None

    @property
    def is_encrypted(self):
        if hasattr(self, '_m_is_encrypted'):
            return self._m_is_encrypted if hasattr(self, '_m_is_encrypted') else None

        self._m_is_encrypted = (self.flags & 2) != 0
        return self._m_is_encrypted if hasattr(self, '_m_is_encrypted') else None

    @property
    def is_tcm_capable(self):
        if hasattr(self, '_m_is_tcm_capable'):
            return self._m_is_tcm_capable if hasattr(self, '_m_is_tcm_capable') else None

        self._m_is_tcm_capable = (self.flags & 4) != 0
        return self._m_is_tcm_capable if hasattr(self, '_m_is_tcm_capable') else None


