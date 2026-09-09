# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class GptPartitionTable(KaitaiStruct):
    """
    .. seealso::
       Source - https://en.wikipedia.org/wiki/GUID_Partition_Table
    """
    SEQ_FIELDS = []
    def __init__(self, _io, _parent=None, _root=None):
        super(GptPartitionTable, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        pass


    def _fetch_instances(self):
        pass
        _ = self.backup
        if hasattr(self, '_m_backup'):
            pass
            self._m_backup._fetch_instances()

        _ = self.primary
        if hasattr(self, '_m_primary'):
            pass
            self._m_primary._fetch_instances()


    class PartitionEntry(KaitaiStruct):
        SEQ_FIELDS = ["type_guid", "guid", "first_lba", "last_lba", "attributes", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(GptPartitionTable.PartitionEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type_guid']['start'] = self._io.pos()
            self.type_guid = self._io.read_bytes(16)
            self._debug['type_guid']['end'] = self._io.pos()
            self._debug['guid']['start'] = self._io.pos()
            self.guid = self._io.read_bytes(16)
            self._debug['guid']['end'] = self._io.pos()
            self._debug['first_lba']['start'] = self._io.pos()
            self.first_lba = self._io.read_u8le()
            self._debug['first_lba']['end'] = self._io.pos()
            self._debug['last_lba']['start'] = self._io.pos()
            self.last_lba = self._io.read_u8le()
            self._debug['last_lba']['end'] = self._io.pos()
            self._debug['attributes']['start'] = self._io.pos()
            self.attributes = self._io.read_u8le()
            self._debug['attributes']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes(72)).decode(u"UTF-16LE")
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class PartitionHeader(KaitaiStruct):
        SEQ_FIELDS = ["signature", "revision", "header_size", "crc32_header", "reserved", "current_lba", "backup_lba", "first_usable_lba", "last_usable_lba", "disk_guid", "entries_start", "entries_count", "entries_size", "crc32_array"]
        def __init__(self, _io, _parent=None, _root=None):
            super(GptPartitionTable.PartitionHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['signature']['start'] = self._io.pos()
            self.signature = self._io.read_bytes(8)
            self._debug['signature']['end'] = self._io.pos()
            if not self.signature == b"\x45\x46\x49\x20\x50\x41\x52\x54":
                raise kaitaistruct.ValidationNotEqualError(b"\x45\x46\x49\x20\x50\x41\x52\x54", self.signature, self._io, u"/types/partition_header/seq/0")
            self._debug['revision']['start'] = self._io.pos()
            self.revision = self._io.read_u4le()
            self._debug['revision']['end'] = self._io.pos()
            self._debug['header_size']['start'] = self._io.pos()
            self.header_size = self._io.read_u4le()
            self._debug['header_size']['end'] = self._io.pos()
            self._debug['crc32_header']['start'] = self._io.pos()
            self.crc32_header = self._io.read_u4le()
            self._debug['crc32_header']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_u4le()
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['current_lba']['start'] = self._io.pos()
            self.current_lba = self._io.read_u8le()
            self._debug['current_lba']['end'] = self._io.pos()
            self._debug['backup_lba']['start'] = self._io.pos()
            self.backup_lba = self._io.read_u8le()
            self._debug['backup_lba']['end'] = self._io.pos()
            self._debug['first_usable_lba']['start'] = self._io.pos()
            self.first_usable_lba = self._io.read_u8le()
            self._debug['first_usable_lba']['end'] = self._io.pos()
            self._debug['last_usable_lba']['start'] = self._io.pos()
            self.last_usable_lba = self._io.read_u8le()
            self._debug['last_usable_lba']['end'] = self._io.pos()
            self._debug['disk_guid']['start'] = self._io.pos()
            self.disk_guid = self._io.read_bytes(16)
            self._debug['disk_guid']['end'] = self._io.pos()
            self._debug['entries_start']['start'] = self._io.pos()
            self.entries_start = self._io.read_u8le()
            self._debug['entries_start']['end'] = self._io.pos()
            self._debug['entries_count']['start'] = self._io.pos()
            self.entries_count = self._io.read_u4le()
            self._debug['entries_count']['end'] = self._io.pos()
            self._debug['entries_size']['start'] = self._io.pos()
            self.entries_size = self._io.read_u4le()
            self._debug['entries_size']['end'] = self._io.pos()
            self._debug['crc32_array']['start'] = self._io.pos()
            self.crc32_array = self._io.read_u4le()
            self._debug['crc32_array']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.entries
            if hasattr(self, '_m_entries'):
                pass
                for i in range(len(self._m_entries)):
                    pass
                    self._m_entries[i]._fetch_instances()



        @property
        def entries(self):
            if hasattr(self, '_m_entries'):
                return self._m_entries

            io = self._root._io
            _pos = io.pos()
            io.seek(self.entries_start * self._root.sector_size)
            self._debug['_m_entries']['start'] = io.pos()
            self._debug['_m_entries']['arr'] = []
            self._raw__m_entries = []
            self._m_entries = []
            for i in range(self.entries_count):
                self._debug['_m_entries']['arr'].append({'start': io.pos()})
                self._raw__m_entries.append(io.read_bytes(self.entries_size))
                _io__raw__m_entries = KaitaiStream(BytesIO(self._raw__m_entries[i]))
                _t__m_entries = GptPartitionTable.PartitionEntry(_io__raw__m_entries, self, self._root)
                try:
                    _t__m_entries._read()
                finally:
                    self._m_entries.append(_t__m_entries)
                self._debug['_m_entries']['arr'][i]['end'] = io.pos()

            self._debug['_m_entries']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_entries', None)


    @property
    def backup(self):
        if hasattr(self, '_m_backup'):
            return self._m_backup

        io = self._root._io
        _pos = io.pos()
        io.seek(self._io.size() - self._root.sector_size)
        self._debug['_m_backup']['start'] = io.pos()
        self._m_backup = GptPartitionTable.PartitionHeader(io, self, self._root)
        self._m_backup._read()
        self._debug['_m_backup']['end'] = io.pos()
        io.seek(_pos)
        return getattr(self, '_m_backup', None)

    @property
    def primary(self):
        if hasattr(self, '_m_primary'):
            return self._m_primary

        io = self._root._io
        _pos = io.pos()
        io.seek(self._root.sector_size)
        self._debug['_m_primary']['start'] = io.pos()
        self._m_primary = GptPartitionTable.PartitionHeader(io, self, self._root)
        self._m_primary._read()
        self._debug['_m_primary']['end'] = io.pos()
        io.seek(_pos)
        return getattr(self, '_m_primary', None)

    @property
    def sector_size(self):
        if hasattr(self, '_m_sector_size'):
            return self._m_sector_size

        self._m_sector_size = 512
        return getattr(self, '_m_sector_size', None)


