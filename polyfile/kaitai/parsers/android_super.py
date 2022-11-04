# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import Enum


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidSuper(KaitaiStruct):
    """The metadata stored by Android at the beginning of a "super" partition, which
    is what it calls a disk partition that holds one or more Dynamic Partitions.
    Dynamic Partitions do more or less the same thing that LVM does on Linux,
    allowing Android to map ranges of non-contiguous extents to a single logical
    device. This metadata holds that mapping.
    
    .. seealso::
       Source - https://source.android.com/devices/tech/ota/dynamic_partitions
    
    
    .. seealso::
       Source - https://android.googlesource.com/platform/system/core/+/refs/tags/android-11.0.0_r8/fs_mgr/liblp/include/liblp/metadata_format.h
    """
    SEQ_FIELDS = []
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        pass

    class Root(KaitaiStruct):
        SEQ_FIELDS = ["primary_geometry", "backup_geometry", "primary_metadata", "backup_metadata"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['primary_geometry']['start'] = self._io.pos()
            self._raw_primary_geometry = self._io.read_bytes(4096)
            _io__raw_primary_geometry = KaitaiStream(BytesIO(self._raw_primary_geometry))
            self.primary_geometry = AndroidSuper.Geometry(_io__raw_primary_geometry, self, self._root)
            self.primary_geometry._read()
            self._debug['primary_geometry']['end'] = self._io.pos()
            self._debug['backup_geometry']['start'] = self._io.pos()
            self._raw_backup_geometry = self._io.read_bytes(4096)
            _io__raw_backup_geometry = KaitaiStream(BytesIO(self._raw_backup_geometry))
            self.backup_geometry = AndroidSuper.Geometry(_io__raw_backup_geometry, self, self._root)
            self.backup_geometry._read()
            self._debug['backup_geometry']['end'] = self._io.pos()
            self._debug['primary_metadata']['start'] = self._io.pos()
            self._raw_primary_metadata = [None] * (self.primary_geometry.metadata_slot_count)
            self.primary_metadata = [None] * (self.primary_geometry.metadata_slot_count)
            for i in range(self.primary_geometry.metadata_slot_count):
                if not 'arr' in self._debug['primary_metadata']:
                    self._debug['primary_metadata']['arr'] = []
                self._debug['primary_metadata']['arr'].append({'start': self._io.pos()})
                self._raw_primary_metadata[i] = self._io.read_bytes(self.primary_geometry.metadata_max_size)
                _io__raw_primary_metadata = KaitaiStream(BytesIO(self._raw_primary_metadata[i]))
                _t_primary_metadata = AndroidSuper.Metadata(_io__raw_primary_metadata, self, self._root)
                _t_primary_metadata._read()
                self.primary_metadata[i] = _t_primary_metadata
                self._debug['primary_metadata']['arr'][i]['end'] = self._io.pos()

            self._debug['primary_metadata']['end'] = self._io.pos()
            self._debug['backup_metadata']['start'] = self._io.pos()
            self._raw_backup_metadata = [None] * (self.primary_geometry.metadata_slot_count)
            self.backup_metadata = [None] * (self.primary_geometry.metadata_slot_count)
            for i in range(self.primary_geometry.metadata_slot_count):
                if not 'arr' in self._debug['backup_metadata']:
                    self._debug['backup_metadata']['arr'] = []
                self._debug['backup_metadata']['arr'].append({'start': self._io.pos()})
                self._raw_backup_metadata[i] = self._io.read_bytes(self.primary_geometry.metadata_max_size)
                _io__raw_backup_metadata = KaitaiStream(BytesIO(self._raw_backup_metadata[i]))
                _t_backup_metadata = AndroidSuper.Metadata(_io__raw_backup_metadata, self, self._root)
                _t_backup_metadata._read()
                self.backup_metadata[i] = _t_backup_metadata
                self._debug['backup_metadata']['arr'][i]['end'] = self._io.pos()

            self._debug['backup_metadata']['end'] = self._io.pos()


    class Geometry(KaitaiStruct):
        SEQ_FIELDS = ["magic", "struct_size", "checksum", "metadata_max_size", "metadata_slot_count", "logical_block_size"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x67\x44\x6C\x61":
                raise kaitaistruct.ValidationNotEqualError(b"\x67\x44\x6C\x61", self.magic, self._io, u"/types/geometry/seq/0")
            self._debug['struct_size']['start'] = self._io.pos()
            self.struct_size = self._io.read_u4le()
            self._debug['struct_size']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_bytes(32)
            self._debug['checksum']['end'] = self._io.pos()
            self._debug['metadata_max_size']['start'] = self._io.pos()
            self.metadata_max_size = self._io.read_u4le()
            self._debug['metadata_max_size']['end'] = self._io.pos()
            self._debug['metadata_slot_count']['start'] = self._io.pos()
            self.metadata_slot_count = self._io.read_u4le()
            self._debug['metadata_slot_count']['end'] = self._io.pos()
            self._debug['logical_block_size']['start'] = self._io.pos()
            self.logical_block_size = self._io.read_u4le()
            self._debug['logical_block_size']['end'] = self._io.pos()


    class Metadata(KaitaiStruct):

        class TableKind(Enum):
            partitions = 0
            extents = 1
            groups = 2
            block_devices = 3
        SEQ_FIELDS = ["magic", "major_version", "minor_version", "header_size", "header_checksum", "tables_size", "tables_checksum", "partitions", "extents", "groups", "block_devices"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x30\x50\x4C\x41":
                raise kaitaistruct.ValidationNotEqualError(b"\x30\x50\x4C\x41", self.magic, self._io, u"/types/metadata/seq/0")
            self._debug['major_version']['start'] = self._io.pos()
            self.major_version = self._io.read_u2le()
            self._debug['major_version']['end'] = self._io.pos()
            self._debug['minor_version']['start'] = self._io.pos()
            self.minor_version = self._io.read_u2le()
            self._debug['minor_version']['end'] = self._io.pos()
            self._debug['header_size']['start'] = self._io.pos()
            self.header_size = self._io.read_u4le()
            self._debug['header_size']['end'] = self._io.pos()
            self._debug['header_checksum']['start'] = self._io.pos()
            self.header_checksum = self._io.read_bytes(32)
            self._debug['header_checksum']['end'] = self._io.pos()
            self._debug['tables_size']['start'] = self._io.pos()
            self.tables_size = self._io.read_u4le()
            self._debug['tables_size']['end'] = self._io.pos()
            self._debug['tables_checksum']['start'] = self._io.pos()
            self.tables_checksum = self._io.read_bytes(32)
            self._debug['tables_checksum']['end'] = self._io.pos()
            self._debug['partitions']['start'] = self._io.pos()
            self.partitions = AndroidSuper.Metadata.TableDescriptor(AndroidSuper.Metadata.TableKind.partitions, self._io, self, self._root)
            self.partitions._read()
            self._debug['partitions']['end'] = self._io.pos()
            self._debug['extents']['start'] = self._io.pos()
            self.extents = AndroidSuper.Metadata.TableDescriptor(AndroidSuper.Metadata.TableKind.extents, self._io, self, self._root)
            self.extents._read()
            self._debug['extents']['end'] = self._io.pos()
            self._debug['groups']['start'] = self._io.pos()
            self.groups = AndroidSuper.Metadata.TableDescriptor(AndroidSuper.Metadata.TableKind.groups, self._io, self, self._root)
            self.groups._read()
            self._debug['groups']['end'] = self._io.pos()
            self._debug['block_devices']['start'] = self._io.pos()
            self.block_devices = AndroidSuper.Metadata.TableDescriptor(AndroidSuper.Metadata.TableKind.block_devices, self._io, self, self._root)
            self.block_devices._read()
            self._debug['block_devices']['end'] = self._io.pos()

        class BlockDevice(KaitaiStruct):
            SEQ_FIELDS = ["first_logical_sector", "alignment", "alignment_offset", "size", "partition_name", "flag_slot_suffixed", "flags_reserved"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['first_logical_sector']['start'] = self._io.pos()
                self.first_logical_sector = self._io.read_u8le()
                self._debug['first_logical_sector']['end'] = self._io.pos()
                self._debug['alignment']['start'] = self._io.pos()
                self.alignment = self._io.read_u4le()
                self._debug['alignment']['end'] = self._io.pos()
                self._debug['alignment_offset']['start'] = self._io.pos()
                self.alignment_offset = self._io.read_u4le()
                self._debug['alignment_offset']['end'] = self._io.pos()
                self._debug['size']['start'] = self._io.pos()
                self.size = self._io.read_u8le()
                self._debug['size']['end'] = self._io.pos()
                self._debug['partition_name']['start'] = self._io.pos()
                self.partition_name = (KaitaiStream.bytes_terminate(self._io.read_bytes(36), 0, False)).decode(u"UTF-8")
                self._debug['partition_name']['end'] = self._io.pos()
                self._debug['flag_slot_suffixed']['start'] = self._io.pos()
                self.flag_slot_suffixed = self._io.read_bits_int_le(1) != 0
                self._debug['flag_slot_suffixed']['end'] = self._io.pos()
                self._debug['flags_reserved']['start'] = self._io.pos()
                self.flags_reserved = self._io.read_bits_int_le(31)
                self._debug['flags_reserved']['end'] = self._io.pos()


        class Extent(KaitaiStruct):

            class TargetType(Enum):
                linear = 0
                zero = 1
            SEQ_FIELDS = ["num_sectors", "target_type", "target_data", "target_source"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['num_sectors']['start'] = self._io.pos()
                self.num_sectors = self._io.read_u8le()
                self._debug['num_sectors']['end'] = self._io.pos()
                self._debug['target_type']['start'] = self._io.pos()
                self.target_type = KaitaiStream.resolve_enum(AndroidSuper.Metadata.Extent.TargetType, self._io.read_u4le())
                self._debug['target_type']['end'] = self._io.pos()
                self._debug['target_data']['start'] = self._io.pos()
                self.target_data = self._io.read_u8le()
                self._debug['target_data']['end'] = self._io.pos()
                self._debug['target_source']['start'] = self._io.pos()
                self.target_source = self._io.read_u4le()
                self._debug['target_source']['end'] = self._io.pos()


        class TableDescriptor(KaitaiStruct):
            SEQ_FIELDS = ["offset", "num_entries", "entry_size"]
            def __init__(self, kind, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.kind = kind
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['offset']['start'] = self._io.pos()
                self.offset = self._io.read_u4le()
                self._debug['offset']['end'] = self._io.pos()
                self._debug['num_entries']['start'] = self._io.pos()
                self.num_entries = self._io.read_u4le()
                self._debug['num_entries']['end'] = self._io.pos()
                self._debug['entry_size']['start'] = self._io.pos()
                self.entry_size = self._io.read_u4le()
                self._debug['entry_size']['end'] = self._io.pos()

            @property
            def table(self):
                if hasattr(self, '_m_table'):
                    return self._m_table if hasattr(self, '_m_table') else None

                _pos = self._io.pos()
                self._io.seek((self._parent.header_size + self.offset))
                self._debug['_m_table']['start'] = self._io.pos()
                self._raw__m_table = [None] * (self.num_entries)
                self._m_table = [None] * (self.num_entries)
                for i in range(self.num_entries):
                    if not 'arr' in self._debug['_m_table']:
                        self._debug['_m_table']['arr'] = []
                    self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                    _on = self.kind
                    if _on == AndroidSuper.Metadata.TableKind.partitions:
                        if not 'arr' in self._debug['_m_table']:
                            self._debug['_m_table']['arr'] = []
                        self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                        self._raw__m_table[i] = self._io.read_bytes(self.entry_size)
                        _io__raw__m_table = KaitaiStream(BytesIO(self._raw__m_table[i]))
                        _t__m_table = AndroidSuper.Metadata.Partition(_io__raw__m_table, self, self._root)
                        _t__m_table._read()
                        self._m_table[i] = _t__m_table
                        self._debug['_m_table']['arr'][i]['end'] = self._io.pos()
                    elif _on == AndroidSuper.Metadata.TableKind.extents:
                        if not 'arr' in self._debug['_m_table']:
                            self._debug['_m_table']['arr'] = []
                        self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                        self._raw__m_table[i] = self._io.read_bytes(self.entry_size)
                        _io__raw__m_table = KaitaiStream(BytesIO(self._raw__m_table[i]))
                        _t__m_table = AndroidSuper.Metadata.Extent(_io__raw__m_table, self, self._root)
                        _t__m_table._read()
                        self._m_table[i] = _t__m_table
                        self._debug['_m_table']['arr'][i]['end'] = self._io.pos()
                    elif _on == AndroidSuper.Metadata.TableKind.groups:
                        if not 'arr' in self._debug['_m_table']:
                            self._debug['_m_table']['arr'] = []
                        self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                        self._raw__m_table[i] = self._io.read_bytes(self.entry_size)
                        _io__raw__m_table = KaitaiStream(BytesIO(self._raw__m_table[i]))
                        _t__m_table = AndroidSuper.Metadata.Group(_io__raw__m_table, self, self._root)
                        _t__m_table._read()
                        self._m_table[i] = _t__m_table
                        self._debug['_m_table']['arr'][i]['end'] = self._io.pos()
                    elif _on == AndroidSuper.Metadata.TableKind.block_devices:
                        if not 'arr' in self._debug['_m_table']:
                            self._debug['_m_table']['arr'] = []
                        self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                        self._raw__m_table[i] = self._io.read_bytes(self.entry_size)
                        _io__raw__m_table = KaitaiStream(BytesIO(self._raw__m_table[i]))
                        _t__m_table = AndroidSuper.Metadata.BlockDevice(_io__raw__m_table, self, self._root)
                        _t__m_table._read()
                        self._m_table[i] = _t__m_table
                        self._debug['_m_table']['arr'][i]['end'] = self._io.pos()
                    else:
                        if not 'arr' in self._debug['_m_table']:
                            self._debug['_m_table']['arr'] = []
                        self._debug['_m_table']['arr'].append({'start': self._io.pos()})
                        self._m_table[i] = self._io.read_bytes(self.entry_size)
                        self._debug['_m_table']['arr'][i]['end'] = self._io.pos()
                    self._debug['_m_table']['arr'][i]['end'] = self._io.pos()

                self._debug['_m_table']['end'] = self._io.pos()
                self._io.seek(_pos)
                return self._m_table if hasattr(self, '_m_table') else None


        class Partition(KaitaiStruct):
            SEQ_FIELDS = ["name", "attr_readonly", "attr_slot_suffixed", "attr_updated", "attr_disabled", "attrs_reserved", "first_extent_index", "num_extents", "group_index"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['name']['start'] = self._io.pos()
                self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(36), 0, False)).decode(u"UTF-8")
                self._debug['name']['end'] = self._io.pos()
                self._debug['attr_readonly']['start'] = self._io.pos()
                self.attr_readonly = self._io.read_bits_int_le(1) != 0
                self._debug['attr_readonly']['end'] = self._io.pos()
                self._debug['attr_slot_suffixed']['start'] = self._io.pos()
                self.attr_slot_suffixed = self._io.read_bits_int_le(1) != 0
                self._debug['attr_slot_suffixed']['end'] = self._io.pos()
                self._debug['attr_updated']['start'] = self._io.pos()
                self.attr_updated = self._io.read_bits_int_le(1) != 0
                self._debug['attr_updated']['end'] = self._io.pos()
                self._debug['attr_disabled']['start'] = self._io.pos()
                self.attr_disabled = self._io.read_bits_int_le(1) != 0
                self._debug['attr_disabled']['end'] = self._io.pos()
                self._debug['attrs_reserved']['start'] = self._io.pos()
                self.attrs_reserved = self._io.read_bits_int_le(28)
                self._debug['attrs_reserved']['end'] = self._io.pos()
                self._io.align_to_byte()
                self._debug['first_extent_index']['start'] = self._io.pos()
                self.first_extent_index = self._io.read_u4le()
                self._debug['first_extent_index']['end'] = self._io.pos()
                self._debug['num_extents']['start'] = self._io.pos()
                self.num_extents = self._io.read_u4le()
                self._debug['num_extents']['end'] = self._io.pos()
                self._debug['group_index']['start'] = self._io.pos()
                self.group_index = self._io.read_u4le()
                self._debug['group_index']['end'] = self._io.pos()


        class Group(KaitaiStruct):
            SEQ_FIELDS = ["name", "flag_slot_suffixed", "flags_reserved", "maximum_size"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['name']['start'] = self._io.pos()
                self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(36), 0, False)).decode(u"UTF-8")
                self._debug['name']['end'] = self._io.pos()
                self._debug['flag_slot_suffixed']['start'] = self._io.pos()
                self.flag_slot_suffixed = self._io.read_bits_int_le(1) != 0
                self._debug['flag_slot_suffixed']['end'] = self._io.pos()
                self._debug['flags_reserved']['start'] = self._io.pos()
                self.flags_reserved = self._io.read_bits_int_le(31)
                self._debug['flags_reserved']['end'] = self._io.pos()
                self._io.align_to_byte()
                self._debug['maximum_size']['start'] = self._io.pos()
                self.maximum_size = self._io.read_u8le()
                self._debug['maximum_size']['end'] = self._io.pos()



    @property
    def root(self):
        if hasattr(self, '_m_root'):
            return self._m_root if hasattr(self, '_m_root') else None

        _pos = self._io.pos()
        self._io.seek(4096)
        self._debug['_m_root']['start'] = self._io.pos()
        self._m_root = AndroidSuper.Root(self._io, self, self._root)
        self._m_root._read()
        self._debug['_m_root']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_root if hasattr(self, '_m_root') else None


