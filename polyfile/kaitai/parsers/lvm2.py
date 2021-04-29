# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import Enum


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Lvm2(KaitaiStruct):
    """### Building a test file
    
    ```
    dd if=/dev/zero of=image.img bs=512 count=$(( 4 * 1024 * 2 ))
    sudo losetup /dev/loop1 image.img
    sudo pvcreate /dev/loop1
    sudo vgcreate vg_test /dev/loop1
    sudo lvcreate --name lv_test1 vg_test
    sudo losetup -d /dev/loop1
    ```
    
    .. seealso::
       Source - https://github.com/libyal/libvslvm/blob/master/documentation/Logical%20Volume%20Manager%20(LVM)%20format.asciidoc
    """
    SEQ_FIELDS = ["pv"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['pv']['start'] = self._io.pos()
        self.pv = Lvm2.PhysicalVolume(self._io, self, self._root)
        self.pv._read()
        self._debug['pv']['end'] = self._io.pos()

    class PhysicalVolume(KaitaiStruct):
        SEQ_FIELDS = ["empty_sector", "label"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['empty_sector']['start'] = self._io.pos()
            self.empty_sector = self._io.read_bytes(self._root.sector_size)
            self._debug['empty_sector']['end'] = self._io.pos()
            self._debug['label']['start'] = self._io.pos()
            self.label = Lvm2.PhysicalVolume.Label(self._io, self, self._root)
            self.label._read()
            self._debug['label']['end'] = self._io.pos()

        class Label(KaitaiStruct):
            SEQ_FIELDS = ["label_header", "volume_header"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['label_header']['start'] = self._io.pos()
                self.label_header = Lvm2.PhysicalVolume.Label.LabelHeader(self._io, self, self._root)
                self.label_header._read()
                self._debug['label_header']['end'] = self._io.pos()
                self._debug['volume_header']['start'] = self._io.pos()
                self.volume_header = Lvm2.PhysicalVolume.Label.VolumeHeader(self._io, self, self._root)
                self.volume_header._read()
                self._debug['volume_header']['end'] = self._io.pos()

            class LabelHeader(KaitaiStruct):
                SEQ_FIELDS = ["signature", "sector_number", "checksum", "label_header_"]
                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['signature']['start'] = self._io.pos()
                    self.signature = self._io.read_bytes(8)
                    self._debug['signature']['end'] = self._io.pos()
                    if not self.signature == b"\x4C\x41\x42\x45\x4C\x4F\x4E\x45":
                        raise kaitaistruct.ValidationNotEqualError(b"\x4C\x41\x42\x45\x4C\x4F\x4E\x45", self.signature, self._io, u"/types/physical_volume/types/label/types/label_header/seq/0")
                    self._debug['sector_number']['start'] = self._io.pos()
                    self.sector_number = self._io.read_u8le()
                    self._debug['sector_number']['end'] = self._io.pos()
                    self._debug['checksum']['start'] = self._io.pos()
                    self.checksum = self._io.read_u4le()
                    self._debug['checksum']['end'] = self._io.pos()
                    self._debug['label_header_']['start'] = self._io.pos()
                    self.label_header_ = Lvm2.PhysicalVolume.Label.LabelHeader.LabelHeader(self._io, self, self._root)
                    self.label_header_._read()
                    self._debug['label_header_']['end'] = self._io.pos()

                class LabelHeader(KaitaiStruct):
                    SEQ_FIELDS = ["data_offset", "type_indicator"]
                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['data_offset']['start'] = self._io.pos()
                        self.data_offset = self._io.read_u4le()
                        self._debug['data_offset']['end'] = self._io.pos()
                        self._debug['type_indicator']['start'] = self._io.pos()
                        self.type_indicator = self._io.read_bytes(8)
                        self._debug['type_indicator']['end'] = self._io.pos()
                        if not self.type_indicator == b"\x4C\x56\x4D\x32\x20\x30\x30\x31":
                            raise kaitaistruct.ValidationNotEqualError(b"\x4C\x56\x4D\x32\x20\x30\x30\x31", self.type_indicator, self._io, u"/types/physical_volume/types/label/types/label_header/types/label_header_/seq/1")



            class VolumeHeader(KaitaiStruct):
                SEQ_FIELDS = ["id", "size", "data_area_descriptors", "metadata_area_descriptors"]
                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['id']['start'] = self._io.pos()
                    self.id = (self._io.read_bytes(32)).decode(u"ascii")
                    self._debug['id']['end'] = self._io.pos()
                    self._debug['size']['start'] = self._io.pos()
                    self.size = self._io.read_u8le()
                    self._debug['size']['end'] = self._io.pos()
                    self._debug['data_area_descriptors']['start'] = self._io.pos()
                    self.data_area_descriptors = []
                    i = 0
                    while True:
                        if not 'arr' in self._debug['data_area_descriptors']:
                            self._debug['data_area_descriptors']['arr'] = []
                        self._debug['data_area_descriptors']['arr'].append({'start': self._io.pos()})
                        _t_data_area_descriptors = Lvm2.PhysicalVolume.Label.VolumeHeader.DataAreaDescriptor(self._io, self, self._root)
                        _t_data_area_descriptors._read()
                        _ = _t_data_area_descriptors
                        self.data_area_descriptors.append(_)
                        self._debug['data_area_descriptors']['arr'][len(self.data_area_descriptors) - 1]['end'] = self._io.pos()
                        if  ((_.size != 0) and (_.offset != 0)) :
                            break
                        i += 1
                    self._debug['data_area_descriptors']['end'] = self._io.pos()
                    self._debug['metadata_area_descriptors']['start'] = self._io.pos()
                    self.metadata_area_descriptors = []
                    i = 0
                    while True:
                        if not 'arr' in self._debug['metadata_area_descriptors']:
                            self._debug['metadata_area_descriptors']['arr'] = []
                        self._debug['metadata_area_descriptors']['arr'].append({'start': self._io.pos()})
                        _t_metadata_area_descriptors = Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataAreaDescriptor(self._io, self, self._root)
                        _t_metadata_area_descriptors._read()
                        _ = _t_metadata_area_descriptors
                        self.metadata_area_descriptors.append(_)
                        self._debug['metadata_area_descriptors']['arr'][len(self.metadata_area_descriptors) - 1]['end'] = self._io.pos()
                        if  ((_.size != 0) and (_.offset != 0)) :
                            break
                        i += 1
                    self._debug['metadata_area_descriptors']['end'] = self._io.pos()

                class DataAreaDescriptor(KaitaiStruct):
                    SEQ_FIELDS = ["offset", "size"]
                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['offset']['start'] = self._io.pos()
                        self.offset = self._io.read_u8le()
                        self._debug['offset']['end'] = self._io.pos()
                        self._debug['size']['start'] = self._io.pos()
                        self.size = self._io.read_u8le()
                        self._debug['size']['end'] = self._io.pos()

                    @property
                    def data(self):
                        if hasattr(self, '_m_data'):
                            return self._m_data if hasattr(self, '_m_data') else None

                        if self.size != 0:
                            _pos = self._io.pos()
                            self._io.seek(self.offset)
                            self._debug['_m_data']['start'] = self._io.pos()
                            self._m_data = (self._io.read_bytes(self.size)).decode(u"ascii")
                            self._debug['_m_data']['end'] = self._io.pos()
                            self._io.seek(_pos)

                        return self._m_data if hasattr(self, '_m_data') else None


                class MetadataAreaDescriptor(KaitaiStruct):
                    SEQ_FIELDS = ["offset", "size"]
                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['offset']['start'] = self._io.pos()
                        self.offset = self._io.read_u8le()
                        self._debug['offset']['end'] = self._io.pos()
                        self._debug['size']['start'] = self._io.pos()
                        self.size = self._io.read_u8le()
                        self._debug['size']['end'] = self._io.pos()

                    @property
                    def data(self):
                        if hasattr(self, '_m_data'):
                            return self._m_data if hasattr(self, '_m_data') else None

                        if self.size != 0:
                            _pos = self._io.pos()
                            self._io.seek(self.offset)
                            self._debug['_m_data']['start'] = self._io.pos()
                            self._raw__m_data = self._io.read_bytes(self.size)
                            _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                            self._m_data = Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataArea(_io__raw__m_data, self, self._root)
                            self._m_data._read()
                            self._debug['_m_data']['end'] = self._io.pos()
                            self._io.seek(_pos)

                        return self._m_data if hasattr(self, '_m_data') else None


                class MetadataArea(KaitaiStruct):
                    """According to `[REDHAT]` the metadata area is a circular buffer. New metadata is appended to the old metadata and then the pointer to the start of it is updated. The metadata area, therefore, can contain copies of older versions of the metadata."""
                    SEQ_FIELDS = ["header"]
                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['header']['start'] = self._io.pos()
                        self.header = Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataArea.MetadataAreaHeader(self._io, self, self._root)
                        self.header._read()
                        self._debug['header']['end'] = self._io.pos()

                    class MetadataAreaHeader(KaitaiStruct):
                        SEQ_FIELDS = ["checksum", "signature", "version", "metadata_area_offset", "metadata_area_size", "raw_location_descriptors"]
                        def __init__(self, _io, _parent=None, _root=None):
                            self._io = _io
                            self._parent = _parent
                            self._root = _root if _root else self
                            self._debug = collections.defaultdict(dict)

                        def _read(self):
                            self._debug['checksum']['start'] = self._io.pos()
                            self.checksum = Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataArea.MetadataAreaHeader(self._io, self, self._root)
                            self.checksum._read()
                            self._debug['checksum']['end'] = self._io.pos()
                            self._debug['signature']['start'] = self._io.pos()
                            self.signature = self._io.read_bytes(16)
                            self._debug['signature']['end'] = self._io.pos()
                            if not self.signature == b"\x20\x4C\x56\x4D\x32\x20\x78\x5B\x35\x41\x25\x72\x30\x4E\x2A\x3E":
                                raise kaitaistruct.ValidationNotEqualError(b"\x20\x4C\x56\x4D\x32\x20\x78\x5B\x35\x41\x25\x72\x30\x4E\x2A\x3E", self.signature, self._io, u"/types/physical_volume/types/label/types/volume_header/types/metadata_area/types/metadata_area_header/seq/1")
                            self._debug['version']['start'] = self._io.pos()
                            self.version = self._io.read_u4le()
                            self._debug['version']['end'] = self._io.pos()
                            self._debug['metadata_area_offset']['start'] = self._io.pos()
                            self.metadata_area_offset = self._io.read_u8le()
                            self._debug['metadata_area_offset']['end'] = self._io.pos()
                            self._debug['metadata_area_size']['start'] = self._io.pos()
                            self.metadata_area_size = self._io.read_u8le()
                            self._debug['metadata_area_size']['end'] = self._io.pos()
                            self._debug['raw_location_descriptors']['start'] = self._io.pos()
                            self.raw_location_descriptors = []
                            i = 0
                            while True:
                                if not 'arr' in self._debug['raw_location_descriptors']:
                                    self._debug['raw_location_descriptors']['arr'] = []
                                self._debug['raw_location_descriptors']['arr'].append({'start': self._io.pos()})
                                _t_raw_location_descriptors = Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataArea.MetadataAreaHeader.RawLocationDescriptor(self._io, self, self._root)
                                _t_raw_location_descriptors._read()
                                _ = _t_raw_location_descriptors
                                self.raw_location_descriptors.append(_)
                                self._debug['raw_location_descriptors']['arr'][len(self.raw_location_descriptors) - 1]['end'] = self._io.pos()
                                if  ((_.offset != 0) and (_.size != 0) and (_.checksum != 0)) :
                                    break
                                i += 1
                            self._debug['raw_location_descriptors']['end'] = self._io.pos()

                        class RawLocationDescriptor(KaitaiStruct):
                            """The data area size can be 0. It is assumed it represents the remaining  available data."""

                            class RawLocationDescriptorFlags(Enum):
                                raw_location_ignored = 1
                            SEQ_FIELDS = ["offset", "size", "checksum", "flags"]
                            def __init__(self, _io, _parent=None, _root=None):
                                self._io = _io
                                self._parent = _parent
                                self._root = _root if _root else self
                                self._debug = collections.defaultdict(dict)

                            def _read(self):
                                self._debug['offset']['start'] = self._io.pos()
                                self.offset = self._io.read_u8le()
                                self._debug['offset']['end'] = self._io.pos()
                                self._debug['size']['start'] = self._io.pos()
                                self.size = self._io.read_u8le()
                                self._debug['size']['end'] = self._io.pos()
                                self._debug['checksum']['start'] = self._io.pos()
                                self.checksum = self._io.read_u4le()
                                self._debug['checksum']['end'] = self._io.pos()
                                self._debug['flags']['start'] = self._io.pos()
                                self.flags = KaitaiStream.resolve_enum(Lvm2.PhysicalVolume.Label.VolumeHeader.MetadataArea.MetadataAreaHeader.RawLocationDescriptor.RawLocationDescriptorFlags, self._io.read_u4le())
                                self._debug['flags']['end'] = self._io.pos()


                        @property
                        def metadata(self):
                            if hasattr(self, '_m_metadata'):
                                return self._m_metadata if hasattr(self, '_m_metadata') else None

                            _pos = self._io.pos()
                            self._io.seek(self.metadata_area_offset)
                            self._debug['_m_metadata']['start'] = self._io.pos()
                            self._m_metadata = self._io.read_bytes(self.metadata_area_size)
                            self._debug['_m_metadata']['end'] = self._io.pos()
                            self._io.seek(_pos)
                            return self._m_metadata if hasattr(self, '_m_metadata') else None






    @property
    def sector_size(self):
        if hasattr(self, '_m_sector_size'):
            return self._m_sector_size if hasattr(self, '_m_sector_size') else None

        self._m_sector_size = 512
        return self._m_sector_size if hasattr(self, '_m_sector_size') else None


