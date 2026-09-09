# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Dune2Pak(KaitaiStruct):
    """
    .. seealso::
       Source - https://moddingwiki.shikadi.net/wiki/PAK_Format_(Westwood)
    """
    SEQ_FIELDS = ["dir"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Dune2Pak, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['dir']['start'] = self._io.pos()
        self._raw_dir = self._io.read_bytes(self.dir_size)
        _io__raw_dir = KaitaiStream(BytesIO(self._raw_dir))
        self.dir = Dune2Pak.Files(_io__raw_dir, self, self._root)
        self.dir._read()
        self._debug['dir']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.dir._fetch_instances()
        _ = self.dir_size
        if hasattr(self, '_m_dir_size'):
            pass


    class File(KaitaiStruct):
        SEQ_FIELDS = ["ofs", "file_name"]
        def __init__(self, idx, _io, _parent=None, _root=None):
            super(Dune2Pak.File, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.idx = idx
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs']['start'] = self._io.pos()
            self.ofs = self._io.read_u4le()
            self._debug['ofs']['end'] = self._io.pos()
            if self.ofs != 0:
                pass
                self._debug['file_name']['start'] = self._io.pos()
                self.file_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                self._debug['file_name']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.ofs != 0:
                pass

            _ = self.body
            if hasattr(self, '_m_body'):
                pass


        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body

            if self.ofs != 0:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs)
                self._debug['_m_body']['start'] = io.pos()
                self._m_body = io.read_bytes(self.next_ofs - self.ofs)
                self._debug['_m_body']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_body', None)

        @property
        def next_ofs(self):
            if hasattr(self, '_m_next_ofs'):
                return self._m_next_ofs

            if self.ofs != 0:
                pass
                self._m_next_ofs = (self._root._io.size() if self.next_ofs0 == 0 else self.next_ofs0)

            return getattr(self, '_m_next_ofs', None)

        @property
        def next_ofs0(self):
            if hasattr(self, '_m_next_ofs0'):
                return self._m_next_ofs0

            if self.ofs != 0:
                pass
                self._m_next_ofs0 = self._root.dir.files[self.idx + 1].ofs

            return getattr(self, '_m_next_ofs0', None)


    class Files(KaitaiStruct):
        SEQ_FIELDS = ["files"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dune2Pak.Files, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['files']['start'] = self._io.pos()
            self._debug['files']['arr'] = []
            self.files = []
            i = 0
            while not self._io.is_eof():
                self._debug['files']['arr'].append({'start': self._io.pos()})
                _t_files = Dune2Pak.File(i, self._io, self, self._root)
                try:
                    _t_files._read()
                finally:
                    self.files.append(_t_files)
                self._debug['files']['arr'][len(self.files) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['files']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.files)):
                pass
                self.files[i]._fetch_instances()



    @property
    def dir_size(self):
        if hasattr(self, '_m_dir_size'):
            return self._m_dir_size

        _pos = self._io.pos()
        self._io.seek(0)
        self._debug['_m_dir_size']['start'] = self._io.pos()
        self._m_dir_size = self._io.read_u4le()
        self._debug['_m_dir_size']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_dir_size', None)


