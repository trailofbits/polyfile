# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class FalloutDat(KaitaiStruct):

    class Compression(IntEnum):
        none = 32
        lzss = 64
    SEQ_FIELDS = ["folder_count", "unknown1", "unknown2", "timestamp", "folder_names", "folders"]
    def __init__(self, _io, _parent=None, _root=None):
        super(FalloutDat, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['folder_count']['start'] = self._io.pos()
        self.folder_count = self._io.read_u4be()
        self._debug['folder_count']['end'] = self._io.pos()
        self._debug['unknown1']['start'] = self._io.pos()
        self.unknown1 = self._io.read_u4be()
        self._debug['unknown1']['end'] = self._io.pos()
        self._debug['unknown2']['start'] = self._io.pos()
        self.unknown2 = self._io.read_u4be()
        self._debug['unknown2']['end'] = self._io.pos()
        self._debug['timestamp']['start'] = self._io.pos()
        self.timestamp = self._io.read_u4be()
        self._debug['timestamp']['end'] = self._io.pos()
        self._debug['folder_names']['start'] = self._io.pos()
        self._debug['folder_names']['arr'] = []
        self.folder_names = []
        for i in range(self.folder_count):
            self._debug['folder_names']['arr'].append({'start': self._io.pos()})
            _t_folder_names = FalloutDat.Pstr(self._io, self, self._root)
            try:
                _t_folder_names._read()
            finally:
                self.folder_names.append(_t_folder_names)
            self._debug['folder_names']['arr'][i]['end'] = self._io.pos()

        self._debug['folder_names']['end'] = self._io.pos()
        self._debug['folders']['start'] = self._io.pos()
        self._debug['folders']['arr'] = []
        self.folders = []
        for i in range(self.folder_count):
            self._debug['folders']['arr'].append({'start': self._io.pos()})
            _t_folders = FalloutDat.Folder(self._io, self, self._root)
            try:
                _t_folders._read()
            finally:
                self.folders.append(_t_folders)
            self._debug['folders']['arr'][i]['end'] = self._io.pos()

        self._debug['folders']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.folder_names)):
            pass
            self.folder_names[i]._fetch_instances()

        for i in range(len(self.folders)):
            pass
            self.folders[i]._fetch_instances()


    class File(KaitaiStruct):
        SEQ_FIELDS = ["name", "flags", "offset", "size_unpacked", "size_packed"]
        def __init__(self, _io, _parent=None, _root=None):
            super(FalloutDat.File, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = FalloutDat.Pstr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = KaitaiStream.resolve_enum(FalloutDat.Compression, self._io.read_u4be())
            self._debug['flags']['end'] = self._io.pos()
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u4be()
            self._debug['offset']['end'] = self._io.pos()
            self._debug['size_unpacked']['start'] = self._io.pos()
            self.size_unpacked = self._io.read_u4be()
            self._debug['size_unpacked']['end'] = self._io.pos()
            self._debug['size_packed']['start'] = self._io.pos()
            self.size_packed = self._io.read_u4be()
            self._debug['size_packed']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            _ = self.contents
            if hasattr(self, '_m_contents'):
                pass


        @property
        def contents(self):
            if hasattr(self, '_m_contents'):
                return self._m_contents

            io = self._root._io
            _pos = io.pos()
            io.seek(self.offset)
            self._debug['_m_contents']['start'] = io.pos()
            self._m_contents = io.read_bytes((self.size_unpacked if self.flags == FalloutDat.Compression.none else self.size_packed))
            self._debug['_m_contents']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_contents', None)


    class Folder(KaitaiStruct):
        SEQ_FIELDS = ["file_count", "unknown", "flags", "timestamp", "files"]
        def __init__(self, _io, _parent=None, _root=None):
            super(FalloutDat.Folder, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['file_count']['start'] = self._io.pos()
            self.file_count = self._io.read_u4be()
            self._debug['file_count']['end'] = self._io.pos()
            self._debug['unknown']['start'] = self._io.pos()
            self.unknown = self._io.read_u4be()
            self._debug['unknown']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u4be()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['timestamp']['start'] = self._io.pos()
            self.timestamp = self._io.read_u4be()
            self._debug['timestamp']['end'] = self._io.pos()
            self._debug['files']['start'] = self._io.pos()
            self._debug['files']['arr'] = []
            self.files = []
            for i in range(self.file_count):
                self._debug['files']['arr'].append({'start': self._io.pos()})
                _t_files = FalloutDat.File(self._io, self, self._root)
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
            super(FalloutDat.Pstr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u1()
            self._debug['size']['end'] = self._io.pos()
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes(self.size)).decode(u"ASCII")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



