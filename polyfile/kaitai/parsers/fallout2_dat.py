# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections
import zlib


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Fallout2Dat(KaitaiStruct):

    class Compression(IntEnum):
        none = 0
        zlib = 1
    SEQ_FIELDS = []
    def __init__(self, _io, _parent=None, _root=None):
        super(Fallout2Dat, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        pass


    def _fetch_instances(self):
        pass
        _ = self.footer
        if hasattr(self, '_m_footer'):
            pass
            self._m_footer._fetch_instances()

        _ = self.index
        if hasattr(self, '_m_index'):
            pass
            self._m_index._fetch_instances()


    class File(KaitaiStruct):
        SEQ_FIELDS = ["name", "flags", "size_unpacked", "size_packed", "offset"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Fallout2Dat.File, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = Fallout2Dat.Pstr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = KaitaiStream.resolve_enum(Fallout2Dat.Compression, self._io.read_u1())
            self._debug['flags']['end'] = self._io.pos()
            self._debug['size_unpacked']['start'] = self._io.pos()
            self.size_unpacked = self._io.read_u4le()
            self._debug['size_unpacked']['end'] = self._io.pos()
            self._debug['size_packed']['start'] = self._io.pos()
            self.size_packed = self._io.read_u4le()
            self._debug['size_packed']['end'] = self._io.pos()
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u4le()
            self._debug['offset']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            _ = self.contents_raw
            if hasattr(self, '_m_contents_raw'):
                pass

            _ = self.contents_zlib
            if hasattr(self, '_m_contents_zlib'):
                pass


        @property
        def contents(self):
            if hasattr(self, '_m_contents'):
                return self._m_contents

            if  ((self.flags == Fallout2Dat.Compression.zlib) or (self.flags == Fallout2Dat.Compression.none)) :
                pass
                self._m_contents = (self.contents_zlib if self.flags == Fallout2Dat.Compression.zlib else self.contents_raw)

            return getattr(self, '_m_contents', None)

        @property
        def contents_raw(self):
            if hasattr(self, '_m_contents_raw'):
                return self._m_contents_raw

            if self.flags == Fallout2Dat.Compression.none:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.offset)
                self._debug['_m_contents_raw']['start'] = io.pos()
                self._m_contents_raw = io.read_bytes(self.size_unpacked)
                self._debug['_m_contents_raw']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_contents_raw', None)

        @property
        def contents_zlib(self):
            if hasattr(self, '_m_contents_zlib'):
                return self._m_contents_zlib

            if self.flags == Fallout2Dat.Compression.zlib:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.offset)
                self._debug['_m_contents_zlib']['start'] = io.pos()
                self._raw__m_contents_zlib = io.read_bytes(self.size_packed)
                self._m_contents_zlib = zlib.decompress(self._raw__m_contents_zlib)
                self._debug['_m_contents_zlib']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_contents_zlib', None)


    class Footer(KaitaiStruct):
        SEQ_FIELDS = ["index_size", "file_size"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Fallout2Dat.Footer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['index_size']['start'] = self._io.pos()
            self.index_size = self._io.read_u4le()
            self._debug['index_size']['end'] = self._io.pos()
            self._debug['file_size']['start'] = self._io.pos()
            self.file_size = self._io.read_u4le()
            self._debug['file_size']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Index(KaitaiStruct):
        SEQ_FIELDS = ["file_count", "files"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Fallout2Dat.Index, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['file_count']['start'] = self._io.pos()
            self.file_count = self._io.read_u4le()
            self._debug['file_count']['end'] = self._io.pos()
            self._debug['files']['start'] = self._io.pos()
            self._debug['files']['arr'] = []
            self.files = []
            for i in range(self.file_count):
                self._debug['files']['arr'].append({'start': self._io.pos()})
                _t_files = Fallout2Dat.File(self._io, self, self._root)
                try:
                    _t_files._read()
                finally:
                    self.files.append(_t_files)
                self._debug['files']['arr'][i]['end'] = self._io.pos()

            self._debug['files']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.files)):
                pass
                self.files[i]._fetch_instances()



    class Pstr(KaitaiStruct):
        SEQ_FIELDS = ["size", "str"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Fallout2Dat.Pstr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes(self.size)).decode(u"ASCII")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    @property
    def footer(self):
        if hasattr(self, '_m_footer'):
            return self._m_footer

        _pos = self._io.pos()
        self._io.seek(self._io.size() - 8)
        self._debug['_m_footer']['start'] = self._io.pos()
        self._m_footer = Fallout2Dat.Footer(self._io, self, self._root)
        self._m_footer._read()
        self._debug['_m_footer']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_footer', None)

    @property
    def index(self):
        if hasattr(self, '_m_index'):
            return self._m_index

        _pos = self._io.pos()
        self._io.seek((self._io.size() - 8) - self.footer.index_size)
        self._debug['_m_index']['start'] = self._io.pos()
        self._m_index = Fallout2Dat.Index(self._io, self, self._root)
        self._m_index._read()
        self._debug['_m_index']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_index', None)


