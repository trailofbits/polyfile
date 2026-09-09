# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class FtlDat(KaitaiStruct):
    SEQ_FIELDS = ["num_files", "files"]
    def __init__(self, _io, _parent=None, _root=None):
        super(FtlDat, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['num_files']['start'] = self._io.pos()
        self.num_files = self._io.read_u4le()
        self._debug['num_files']['end'] = self._io.pos()
        self._debug['files']['start'] = self._io.pos()
        self._debug['files']['arr'] = []
        self.files = []
        for i in range(self.num_files):
            self._debug['files']['arr'].append({'start': self._io.pos()})
            _t_files = FtlDat.File(self._io, self, self._root)
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


    class File(KaitaiStruct):
        SEQ_FIELDS = ["ofs_meta"]
        def __init__(self, _io, _parent=None, _root=None):
            super(FtlDat.File, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_meta']['start'] = self._io.pos()
            self.ofs_meta = self._io.read_u4le()
            self._debug['ofs_meta']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.meta
            if hasattr(self, '_m_meta'):
                pass
                self._m_meta._fetch_instances()


        @property
        def meta(self):
            if hasattr(self, '_m_meta'):
                return self._m_meta

            if self.ofs_meta != 0:
                pass
                _pos = self._io.pos()
                self._io.seek(self.ofs_meta)
                self._debug['_m_meta']['start'] = self._io.pos()
                self._m_meta = FtlDat.Meta(self._io, self, self._root)
                self._m_meta._read()
                self._debug['_m_meta']['end'] = self._io.pos()
                self._io.seek(_pos)

            return getattr(self, '_m_meta', None)


    class Meta(KaitaiStruct):
        SEQ_FIELDS = ["len_file", "len_filename", "filename", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(FtlDat.Meta, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_file']['start'] = self._io.pos()
            self.len_file = self._io.read_u4le()
            self._debug['len_file']['end'] = self._io.pos()
            self._debug['len_filename']['start'] = self._io.pos()
            self.len_filename = self._io.read_u4le()
            self._debug['len_filename']['end'] = self._io.pos()
            self._debug['filename']['start'] = self._io.pos()
            self.filename = (self._io.read_bytes(self.len_filename)).decode(u"UTF-8")
            self._debug['filename']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes(self.len_file)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



