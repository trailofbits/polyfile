# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidDto(KaitaiStruct):
    """Format for Android DTB/DTBO partitions. It's kind of archive with
    dtb/dtbo files. Used only when there is a separate unique partition
    (dtb, dtbo) on an android device to organize device tree files.
    The format consists of a header with info about size and number
    of device tree entries and the entries themselves. This format
    description could be used to extract device tree entries from a
    partition images and decompile them with dtc (device tree compiler).
    
    .. seealso::
       Source - https://source.android.com/devices/architecture/dto/partitions
    
    
    .. seealso::
       Source - https://android.googlesource.com/platform/system/libufdt/+/refs/tags/android-10.0.0_r47
    """
    SEQ_FIELDS = ["header", "entries"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = AndroidDto.DtTableHeader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['entries']['start'] = self._io.pos()
        self.entries = [None] * (self.header.dt_entry_count)
        for i in range(self.header.dt_entry_count):
            if not 'arr' in self._debug['entries']:
                self._debug['entries']['arr'] = []
            self._debug['entries']['arr'].append({'start': self._io.pos()})
            _t_entries = AndroidDto.DtTableEntry(self._io, self, self._root)
            _t_entries._read()
            self.entries[i] = _t_entries
            self._debug['entries']['arr'][i]['end'] = self._io.pos()

        self._debug['entries']['end'] = self._io.pos()

    class DtTableHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "total_size", "header_size", "dt_entry_size", "dt_entry_count", "dt_entries_offset", "page_size", "version"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
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


    class DtTableEntry(KaitaiStruct):
        SEQ_FIELDS = ["dt_size", "dt_offset", "id", "rev", "custom"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
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
            self.custom = [None] * (4)
            for i in range(4):
                if not 'arr' in self._debug['custom']:
                    self._debug['custom']['arr'] = []
                self._debug['custom']['arr'].append({'start': self._io.pos()})
                self.custom[i] = self._io.read_u4be()
                self._debug['custom']['arr'][i]['end'] = self._io.pos()

            self._debug['custom']['end'] = self._io.pos()

        @property
        def body(self):
            """DTB/DTBO file."""
            if hasattr(self, '_m_body'):
                return self._m_body if hasattr(self, '_m_body') else None

            io = self._root._io
            _pos = io.pos()
            io.seek(self.dt_offset)
            self._debug['_m_body']['start'] = io.pos()
            self._m_body = io.read_bytes(self.dt_size)
            self._debug['_m_body']['end'] = io.pos()
            io.seek(_pos)
            return self._m_body if hasattr(self, '_m_body') else None



