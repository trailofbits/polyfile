# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Utf8String(KaitaiStruct):
    """UTF-8 is a popular character encoding scheme that allows to
    represent strings as sequence of code points defined in Unicode
    standard. Its features are:
    
    * variable width (i.e. one code point might be represented by 1 to 4
      bytes)
    * backward compatiblity with ASCII
    * basic validity checking (and thus distinguishing from other legacy
      8-bit encodings)
    * maintaining sort order of codepoints if sorted as a byte array
    
    WARNING: For the vast majority of practical purposes of format
    definitions in Kaitai Struct, you'd likely NOT want to use this and
    rather just use `type: str` with `encoding: utf-8`. That will use
    native string implementations, which are most likely more efficient
    and will give you native language strings, rather than an array of
    individual codepoints.  This format definition is provided mostly
    for educational / research purposes.
    """
    SEQ_FIELDS = ["codepoints"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['codepoints']['start'] = self._io.pos()
        self.codepoints = []
        i = 0
        while not self._io.is_eof():
            if not 'arr' in self._debug['codepoints']:
                self._debug['codepoints']['arr'] = []
            self._debug['codepoints']['arr'].append({'start': self._io.pos()})
            _t_codepoints = Utf8String.Utf8Codepoint(self._io.pos(), self._io, self, self._root)
            _t_codepoints._read()
            self.codepoints.append(_t_codepoints)
            self._debug['codepoints']['arr'][len(self.codepoints) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['codepoints']['end'] = self._io.pos()

    class Utf8Codepoint(KaitaiStruct):
        SEQ_FIELDS = ["bytes"]
        def __init__(self, ofs, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.ofs = ofs
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['bytes']['start'] = self._io.pos()
            self.bytes = self._io.read_bytes(self.len_bytes)
            self._debug['bytes']['end'] = self._io.pos()

        @property
        def raw1(self):
            if hasattr(self, '_m_raw1'):
                return self._m_raw1 if hasattr(self, '_m_raw1') else None

            if self.len_bytes >= 2:
                self._m_raw1 = (KaitaiStream.byte_array_index(self.bytes, 1) & 63)

            return self._m_raw1 if hasattr(self, '_m_raw1') else None

        @property
        def len_bytes(self):
            if hasattr(self, '_m_len_bytes'):
                return self._m_len_bytes if hasattr(self, '_m_len_bytes') else None

            self._m_len_bytes = (1 if (self.byte0 & 128) == 0 else (2 if (self.byte0 & 224) == 192 else (3 if (self.byte0 & 240) == 224 else (4 if (self.byte0 & 248) == 240 else -1))))
            return self._m_len_bytes if hasattr(self, '_m_len_bytes') else None

        @property
        def raw3(self):
            if hasattr(self, '_m_raw3'):
                return self._m_raw3 if hasattr(self, '_m_raw3') else None

            if self.len_bytes >= 4:
                self._m_raw3 = (KaitaiStream.byte_array_index(self.bytes, 3) & 63)

            return self._m_raw3 if hasattr(self, '_m_raw3') else None

        @property
        def value_as_int(self):
            if hasattr(self, '_m_value_as_int'):
                return self._m_value_as_int if hasattr(self, '_m_value_as_int') else None

            self._m_value_as_int = (self.raw0 if self.len_bytes == 1 else (((self.raw0 << 6) | self.raw1) if self.len_bytes == 2 else ((((self.raw0 << 12) | (self.raw1 << 6)) | self.raw2) if self.len_bytes == 3 else (((((self.raw0 << 18) | (self.raw1 << 12)) | (self.raw2 << 6)) | self.raw3) if self.len_bytes == 4 else -1))))
            return self._m_value_as_int if hasattr(self, '_m_value_as_int') else None

        @property
        def raw0(self):
            if hasattr(self, '_m_raw0'):
                return self._m_raw0 if hasattr(self, '_m_raw0') else None

            self._m_raw0 = (KaitaiStream.byte_array_index(self.bytes, 0) & (127 if self.len_bytes == 1 else (31 if self.len_bytes == 2 else (15 if self.len_bytes == 3 else (7 if self.len_bytes == 4 else 0)))))
            return self._m_raw0 if hasattr(self, '_m_raw0') else None

        @property
        def byte0(self):
            if hasattr(self, '_m_byte0'):
                return self._m_byte0 if hasattr(self, '_m_byte0') else None

            _pos = self._io.pos()
            self._io.seek(self.ofs)
            self._debug['_m_byte0']['start'] = self._io.pos()
            self._m_byte0 = self._io.read_u1()
            self._debug['_m_byte0']['end'] = self._io.pos()
            self._io.seek(_pos)
            return self._m_byte0 if hasattr(self, '_m_byte0') else None

        @property
        def raw2(self):
            if hasattr(self, '_m_raw2'):
                return self._m_raw2 if hasattr(self, '_m_raw2') else None

            if self.len_bytes >= 3:
                self._m_raw2 = (KaitaiStream.byte_array_index(self.bytes, 2) & 63)

            return self._m_raw2 if hasattr(self, '_m_raw2') else None



