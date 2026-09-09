# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidDto(KaitaiStruct):
    """Format for Android DTB/DTBO partitions. It's kind of archive with
    dtb/dtbo files. Used only when there is a separate unique partition
    (dtb, dtbo) on an android device to organize device tree files.
    The format consists of a header with info about size and number
    of device tree entries and the entries themselves. This format
    description could be used to extract device tree entries from a
    partition images and decompile them with dtc (device tree compiler).
    
    .. seealso::
       Source - https://source.android.com/docs/core/architecture/dto/partitions
    
    
    .. seealso::
       Source - https://android.googlesource.com/platform/system/libufdt/+/refs/tags/android-10.0.0_r47
    """
    SEQ_FIELDS = ["header", "entries"]
    def __init__(self, _io, _parent=None, _root=None):
        super(AndroidDto, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = AndroidDto.DtTableHeader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['entries']['start'] = self._io.pos()
        self._debug['entries']['arr'] = []
        self.entries = []
        for i in range(self.header.dt_entry_count):
            self._debug['entries']['arr'].append({'start': self._io.pos()})
            _t_entries = AndroidDto.DtTableEntry(self._io, self, self._root)
            try:
                _t_entries._read()
            finally:
                self.entries.append(_t_entries)
            self._debug['entries']['arr'][i]['end'] = self._io.pos()

        self._debug['entries']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()
        for i in range(len(self.entries)):
            pass
            self.entries[i]._fetch_instances()


    class DtTableEntry(KaitaiStruct):
        SEQ_FIELDS = ["dt_size", "dt_offset", "id", "rev", "custom"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidDto.DtTableEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['dt_size']['start'] = self._io.pos()
            self.dt_size = self._io.read_u4be()
            self._debug['dt_size']['end'] = self._io.pos()
            self._debug['dt_offset']['start'] = self._io.pos()
            self.dt_offset = self._io.read_u4be()
            self._debug['dt_offset']['end'] = self._io.pos()
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u4be()
            self._debug['id']['end'] = self._io.pos()
            self._debug['rev']['start'] = self._io.pos()
            self.rev = self._io.read_u4be()
            self._debug['rev']['end'] = self._io.pos()
            self._debug['custom']['start'] = self._io.pos()
            self._debug['custom']['arr'] = []
            self.custom = []
            for i in range(4):
                self._debug['custom']['arr'].append({'start': self._io.pos()})
                self.custom.append(self._io.read_u4be())
                self._debug['custom']['arr'][i]['end'] = self._io.pos()

            self._debug['custom']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.custom)):
                pass

            _ = self.body
            if hasattr(self, '_m_body'):
                pass


        @property
        def body(self):
            """DTB/DTBO file."""
            if hasattr(self, '_m_body'):
                return self._m_body

            io = self._root._io
            _pos = io.pos()
            io.seek(self.dt_offset)
            self._debug['_m_body']['start'] = io.pos()
            self._m_body = io.read_bytes(self.dt_size)
            self._debug['_m_body']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_body', None)


    class DtTableHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "total_size", "header_size", "dt_entry_size", "dt_entry_count", "dt_entries_offset", "page_size", "version"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidDto.DtTableHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\xD7\xB7\xAB\x1E":
                raise kaitaistruct.ValidationNotEqualError(b"\xD7\xB7\xAB\x1E", self.magic, self._io, u"/types/dt_table_header/seq/0")
            self._debug['total_size']['start'] = self._io.pos()
            self.total_size = self._io.read_u4be()
            self._debug['total_size']['end'] = self._io.pos()
            self._debug['header_size']['start'] = self._io.pos()
            self.header_size = self._io.read_u4be()
            self._debug['header_size']['end'] = self._io.pos()
            self._debug['dt_entry_size']['start'] = self._io.pos()
            self.dt_entry_size = self._io.read_u4be()
            self._debug['dt_entry_size']['end'] = self._io.pos()
            self._debug['dt_entry_count']['start'] = self._io.pos()
            self.dt_entry_count = self._io.read_u4be()
            self._debug['dt_entry_count']['end'] = self._io.pos()
            self._debug['dt_entries_offset']['start'] = self._io.pos()
            self.dt_entries_offset = self._io.read_u4be()
            self._debug['dt_entries_offset']['end'] = self._io.pos()
            self._debug['page_size']['start'] = self._io.pos()
            self.page_size = self._io.read_u4be()
            self._debug['page_size']['end'] = self._io.pos()
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4be()
            self._debug['version']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



