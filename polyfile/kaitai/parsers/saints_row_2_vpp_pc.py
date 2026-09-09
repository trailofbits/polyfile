# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SaintsRow2VppPc(KaitaiStruct):
    SEQ_FIELDS = ["magic", "pad1", "num_files", "container_size", "len_offsets", "len_filenames", "len_extensions", "smth5", "smth6", "smth7", "smth8", "smth9"]
    def __init__(self, _io, _parent=None, _root=None):
        super(SaintsRow2VppPc, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(5)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\xCE\x0A\x89\x51\x04":
            raise kaitaistruct.ValidationNotEqualError(b"\xCE\x0A\x89\x51\x04", self.magic, self._io, u"/seq/0")
        self._debug['pad1']['start'] = self._io.pos()
        self.pad1 = self._io.read_bytes(335)
        self._debug['pad1']['end'] = self._io.pos()
        self._debug['num_files']['start'] = self._io.pos()
        self.num_files = self._io.read_s4le()
        self._debug['num_files']['end'] = self._io.pos()
        self._debug['container_size']['start'] = self._io.pos()
        self.container_size = self._io.read_s4le()
        self._debug['container_size']['end'] = self._io.pos()
        self._debug['len_offsets']['start'] = self._io.pos()
        self.len_offsets = self._io.read_s4le()
        self._debug['len_offsets']['end'] = self._io.pos()
        self._debug['len_filenames']['start'] = self._io.pos()
        self.len_filenames = self._io.read_s4le()
        self._debug['len_filenames']['end'] = self._io.pos()
        self._debug['len_extensions']['start'] = self._io.pos()
        self.len_extensions = self._io.read_s4le()
        self._debug['len_extensions']['end'] = self._io.pos()
        self._debug['smth5']['start'] = self._io.pos()
        self.smth5 = self._io.read_s4le()
        self._debug['smth5']['end'] = self._io.pos()
        self._debug['smth6']['start'] = self._io.pos()
        self.smth6 = self._io.read_s4le()
        self._debug['smth6']['end'] = self._io.pos()
        self._debug['smth7']['start'] = self._io.pos()
        self.smth7 = self._io.read_s4le()
        self._debug['smth7']['end'] = self._io.pos()
        self._debug['smth8']['start'] = self._io.pos()
        self.smth8 = self._io.read_s4le()
        self._debug['smth8']['end'] = self._io.pos()
        self._debug['smth9']['start'] = self._io.pos()
        self.smth9 = self._io.read_s4le()
        self._debug['smth9']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        _ = self.extensions
        if hasattr(self, '_m_extensions'):
            pass
            self._m_extensions._fetch_instances()

        _ = self.filenames
        if hasattr(self, '_m_filenames'):
            pass
            self._m_filenames._fetch_instances()

        _ = self.files
        if hasattr(self, '_m_files'):
            pass
            self._m_files._fetch_instances()


    class Offsets(KaitaiStruct):
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(SaintsRow2VppPc.Offsets, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self._debug['entries']['arr'] = []
            self.entries = []
            i = 0
            while not self._io.is_eof():
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = SaintsRow2VppPc.Offsets.Offset(self._io, self, self._root)
                try:
                    _t_entries._read()
                finally:
                    self.entries.append(_t_entries)
                self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['entries']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()


        class Offset(KaitaiStruct):
            SEQ_FIELDS = ["name_ofs", "ext_ofs", "smth2", "ofs_body", "len_body", "always_minus_1", "always_zero"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SaintsRow2VppPc.Offsets.Offset, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['name_ofs']['start'] = self._io.pos()
                self.name_ofs = self._io.read_u4le()
                self._debug['name_ofs']['end'] = self._io.pos()
                self._debug['ext_ofs']['start'] = self._io.pos()
                self.ext_ofs = self._io.read_u4le()
                self._debug['ext_ofs']['end'] = self._io.pos()
                self._debug['smth2']['start'] = self._io.pos()
                self.smth2 = self._io.read_s4le()
                self._debug['smth2']['end'] = self._io.pos()
                self._debug['ofs_body']['start'] = self._io.pos()
                self.ofs_body = self._io.read_s4le()
                self._debug['ofs_body']['end'] = self._io.pos()
                self._debug['len_body']['start'] = self._io.pos()
                self.len_body = self._io.read_s4le()
                self._debug['len_body']['end'] = self._io.pos()
                self._debug['always_minus_1']['start'] = self._io.pos()
                self.always_minus_1 = self._io.read_s4le()
                self._debug['always_minus_1']['end'] = self._io.pos()
                self._debug['always_zero']['start'] = self._io.pos()
                self.always_zero = self._io.read_s4le()
                self._debug['always_zero']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _ = self.body
                if hasattr(self, '_m_body'):
                    pass

                _ = self.ext
                if hasattr(self, '_m_ext'):
                    pass

                _ = self.filename
                if hasattr(self, '_m_filename'):
                    pass


            @property
            def body(self):
                if hasattr(self, '_m_body'):
                    return self._m_body

                io = self._root._io
                _pos = io.pos()
                io.seek(self._root.data_start + self.ofs_body)
                self._debug['_m_body']['start'] = io.pos()
                self._m_body = io.read_bytes(self.len_body)
                self._debug['_m_body']['end'] = io.pos()
                io.seek(_pos)
                return getattr(self, '_m_body', None)

            @property
            def ext(self):
                if hasattr(self, '_m_ext'):
                    return self._m_ext

                io = self._root.extensions._io
                _pos = io.pos()
                io.seek(self.ext_ofs)
                self._debug['_m_ext']['start'] = io.pos()
                self._m_ext = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                self._debug['_m_ext']['end'] = io.pos()
                io.seek(_pos)
                return getattr(self, '_m_ext', None)

            @property
            def filename(self):
                if hasattr(self, '_m_filename'):
                    return self._m_filename

                io = self._root.filenames._io
                _pos = io.pos()
                io.seek(self.name_ofs)
                self._debug['_m_filename']['start'] = io.pos()
                self._m_filename = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                self._debug['_m_filename']['end'] = io.pos()
                io.seek(_pos)
                return getattr(self, '_m_filename', None)



    class Strings(KaitaiStruct):
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(SaintsRow2VppPc.Strings, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self._debug['entries']['arr'] = []
            self.entries = []
            i = 0
            while not self._io.is_eof():
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                self.entries.append((self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8"))
                self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['entries']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass



    @property
    def data_start(self):
        if hasattr(self, '_m_data_start'):
            return self._m_data_start

        self._m_data_start = (self.ofs_extensions + self.len_extensions & 4294965248) + 2048
        return getattr(self, '_m_data_start', None)

    @property
    def extensions(self):
        if hasattr(self, '_m_extensions'):
            return self._m_extensions

        _pos = self._io.pos()
        self._io.seek(self.ofs_extensions)
        self._debug['_m_extensions']['start'] = self._io.pos()
        self._raw__m_extensions = self._io.read_bytes(self.len_extensions)
        _io__raw__m_extensions = KaitaiStream(BytesIO(self._raw__m_extensions))
        self._m_extensions = SaintsRow2VppPc.Strings(_io__raw__m_extensions, self, self._root)
        self._m_extensions._read()
        self._debug['_m_extensions']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_extensions', None)

    @property
    def filenames(self):
        if hasattr(self, '_m_filenames'):
            return self._m_filenames

        _pos = self._io.pos()
        self._io.seek(self.ofs_filenames)
        self._debug['_m_filenames']['start'] = self._io.pos()
        self._raw__m_filenames = self._io.read_bytes(self.len_filenames)
        _io__raw__m_filenames = KaitaiStream(BytesIO(self._raw__m_filenames))
        self._m_filenames = SaintsRow2VppPc.Strings(_io__raw__m_filenames, self, self._root)
        self._m_filenames._read()
        self._debug['_m_filenames']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_filenames', None)

    @property
    def files(self):
        if hasattr(self, '_m_files'):
            return self._m_files

        _pos = self._io.pos()
        self._io.seek(2048)
        self._debug['_m_files']['start'] = self._io.pos()
        self._raw__m_files = self._io.read_bytes(self.len_offsets)
        _io__raw__m_files = KaitaiStream(BytesIO(self._raw__m_files))
        self._m_files = SaintsRow2VppPc.Offsets(_io__raw__m_files, self, self._root)
        self._m_files._read()
        self._debug['_m_files']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_files', None)

    @property
    def ofs_extensions(self):
        if hasattr(self, '_m_ofs_extensions'):
            return self._m_ofs_extensions

        self._m_ofs_extensions = (self.ofs_filenames + self.len_filenames & 4294965248) + 2048
        return getattr(self, '_m_ofs_extensions', None)

    @property
    def ofs_filenames(self):
        if hasattr(self, '_m_ofs_filenames'):
            return self._m_ofs_filenames

        self._m_ofs_filenames = (2048 + self.len_offsets & 4294965248) + 2048
        return getattr(self, '_m_ofs_filenames', None)


