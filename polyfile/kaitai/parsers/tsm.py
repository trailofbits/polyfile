# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Tsm(KaitaiStruct):
    """InfluxDB is a scalable database optimized for storage of time
    series, real-time application metrics, operations monitoring events,
    etc, written in Go.
    
    Data is stored in .tsm files, which are kept pretty simple
    conceptually. Each .tsm file contains a header and footer, which
    stores offset to an index. Index is used to find a data block for a
    requested time boundary.
    """
    SEQ_FIELDS = ["header"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Tsm, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = Tsm.Header(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()
        _ = self.index
        if hasattr(self, '_m_index'):
            pass
            self._m_index._fetch_instances()


    class Header(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Tsm.Header, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x16\xD1\x16\xD1":
                raise kaitaistruct.ValidationNotEqualError(b"\x16\xD1\x16\xD1", self.magic, self._io, u"/types/header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u1()
            self._debug['version']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Index(KaitaiStruct):
        SEQ_FIELDS = ["offset"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Tsm.Index, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u8be()
            self._debug['offset']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.entries
            if hasattr(self, '_m_entries'):
                pass
                for i in range(len(self._m_entries)):
                    pass
                    self._m_entries[i]._fetch_instances()



        class IndexHeader(KaitaiStruct):
            SEQ_FIELDS = ["key_len", "key", "type", "entry_count", "index_entries"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Tsm.Index.IndexHeader, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['key_len']['start'] = self._io.pos()
                self.key_len = self._io.read_u2be()
                self._debug['key_len']['end'] = self._io.pos()
                self._debug['key']['start'] = self._io.pos()
                self.key = (self._io.read_bytes(self.key_len)).decode(u"UTF-8")
                self._debug['key']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = self._io.read_u1()
                self._debug['type']['end'] = self._io.pos()
                self._debug['entry_count']['start'] = self._io.pos()
                self.entry_count = self._io.read_u2be()
                self._debug['entry_count']['end'] = self._io.pos()
                self._debug['index_entries']['start'] = self._io.pos()
                self._debug['index_entries']['arr'] = []
                self.index_entries = []
                for i in range(self.entry_count):
                    self._debug['index_entries']['arr'].append({'start': self._io.pos()})
                    _t_index_entries = Tsm.Index.IndexHeader.IndexEntry(self._io, self, self._root)
                    try:
                        _t_index_entries._read()
                    finally:
                        self.index_entries.append(_t_index_entries)
                    self._debug['index_entries']['arr'][i]['end'] = self._io.pos()

                self._debug['index_entries']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.index_entries)):
                    pass
                    self.index_entries[i]._fetch_instances()


            class IndexEntry(KaitaiStruct):
                SEQ_FIELDS = ["min_time", "max_time", "block_offset", "block_size"]
                def __init__(self, _io, _parent=None, _root=None):
                    super(Tsm.Index.IndexHeader.IndexEntry, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['min_time']['start'] = self._io.pos()
                    self.min_time = self._io.read_u8be()
                    self._debug['min_time']['end'] = self._io.pos()
                    self._debug['max_time']['start'] = self._io.pos()
                    self.max_time = self._io.read_u8be()
                    self._debug['max_time']['end'] = self._io.pos()
                    self._debug['block_offset']['start'] = self._io.pos()
                    self.block_offset = self._io.read_u8be()
                    self._debug['block_offset']['end'] = self._io.pos()
                    self._debug['block_size']['start'] = self._io.pos()
                    self.block_size = self._io.read_u4be()
                    self._debug['block_size']['end'] = self._io.pos()


                def _fetch_instances(self):
                    pass
                    _ = self.block
                    if hasattr(self, '_m_block'):
                        pass
                        self._m_block._fetch_instances()


                class BlockEntry(KaitaiStruct):
                    SEQ_FIELDS = ["crc32", "data"]
                    def __init__(self, _io, _parent=None, _root=None):
                        super(Tsm.Index.IndexHeader.IndexEntry.BlockEntry, self).__init__(_io)
                        self._parent = _parent
                        self._root = _root
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['crc32']['start'] = self._io.pos()
                        self.crc32 = self._io.read_u4be()
                        self._debug['crc32']['end'] = self._io.pos()
                        self._debug['data']['start'] = self._io.pos()
                        self.data = self._io.read_bytes(self._parent.block_size - 4)
                        self._debug['data']['end'] = self._io.pos()


                    def _fetch_instances(self):
                        pass


                @property
                def block(self):
                    if hasattr(self, '_m_block'):
                        return self._m_block

                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self.block_offset)
                    self._debug['_m_block']['start'] = io.pos()
                    self._m_block = Tsm.Index.IndexHeader.IndexEntry.BlockEntry(io, self, self._root)
                    self._m_block._read()
                    self._debug['_m_block']['end'] = io.pos()
                    io.seek(_pos)
                    return getattr(self, '_m_block', None)



        @property
        def entries(self):
            if hasattr(self, '_m_entries'):
                return self._m_entries

            _pos = self._io.pos()
            self._io.seek(self.offset)
            self._debug['_m_entries']['start'] = self._io.pos()
            self._debug['_m_entries']['arr'] = []
            self._m_entries = []
            i = 0
            while True:
                self._debug['_m_entries']['arr'].append({'start': self._io.pos()})
                _t__m_entries = Tsm.Index.IndexHeader(self._io, self, self._root)
                try:
                    _t__m_entries._read()
                finally:
                    _ = _t__m_entries
                    self._m_entries.append(_)
                self._debug['_m_entries']['arr'][len(self._m_entries) - 1]['end'] = self._io.pos()
                if self._io.pos() == self._io.size() - 8:
                    break
                i += 1
            self._debug['_m_entries']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_entries', None)


    @property
    def index(self):
        if hasattr(self, '_m_index'):
            return self._m_index

        _pos = self._io.pos()
        self._io.seek(self._io.size() - 8)
        self._debug['_m_index']['start'] = self._io.pos()
        self._m_index = Tsm.Index(self._io, self, self._root)
        self._m_index._read()
        self._debug['_m_index']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_index', None)


