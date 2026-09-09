# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class TrDosImage(KaitaiStruct):
    """.trd file is a raw dump of TR-DOS (ZX-Spectrum) floppy. .trd files are
    headerless and contain consequent "logical tracks", each logical track
    consists of 16 256-byte sectors.
    
    Logical tracks are defined the same way as used by TR-DOS: for single-side
    floppies it's just a physical track number, for two-side floppies sides are
    interleaved, i.e. logical_track_num = (physical_track_num << 1) | side
    
    So, this format definition is more for TR-DOS filesystem than for .trd files,
    which are formatless.
    
    Strings (file names, disk label, disk password) are padded with spaces and use
    ZX Spectrum character set, including UDGs, block drawing chars and Basic
    tokens. ASCII range is mostly standard ASCII, with few characters (^, `, DEL)
    replaced with (up arrow, pound, copyright symbol).
    
    .trd file can be smaller than actual floppy disk, if last logical tracks are
    empty (contain no file data) they can be omitted.
    """

    class DiskType(IntEnum):
        type_80_tracks_double_side = 22
        type_40_tracks_double_side = 23
        type_80_tracks_single_side = 24
        type_40_tracks_single_side = 25
    SEQ_FIELDS = ["files"]
    def __init__(self, _io, _parent=None, _root=None):
        super(TrDosImage, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['files']['start'] = self._io.pos()
        self._debug['files']['arr'] = []
        self.files = []
        i = 0
        while True:
            self._debug['files']['arr'].append({'start': self._io.pos()})
            _t_files = TrDosImage.File(self._io, self, self._root)
            try:
                _t_files._read()
            finally:
                _ = _t_files
                self.files.append(_)
            self._debug['files']['arr'][len(self.files) - 1]['end'] = self._io.pos()
            if _.is_terminator:
                break
            i += 1
        self._debug['files']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.files)):
            pass
            self.files[i]._fetch_instances()

        _ = self.volume_info
        if hasattr(self, '_m_volume_info'):
            pass
            self._m_volume_info._fetch_instances()


    class File(KaitaiStruct):
        SEQ_FIELDS = ["name", "extension", "position_and_length", "length_sectors", "starting_sector", "starting_track"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.File, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self._raw_name = self._io.read_bytes(8)
            _io__raw_name = KaitaiStream(BytesIO(self._raw_name))
            self.name = TrDosImage.Filename(_io__raw_name, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['extension']['start'] = self._io.pos()
            self.extension = self._io.read_u1()
            self._debug['extension']['end'] = self._io.pos()
            self._debug['position_and_length']['start'] = self._io.pos()
            _on = self.extension
            if _on == 35:
                pass
                self.position_and_length = TrDosImage.PositionAndLengthPrint(self._io, self, self._root)
                self.position_and_length._read()
            elif _on == 66:
                pass
                self.position_and_length = TrDosImage.PositionAndLengthBasic(self._io, self, self._root)
                self.position_and_length._read()
            elif _on == 67:
                pass
                self.position_and_length = TrDosImage.PositionAndLengthCode(self._io, self, self._root)
                self.position_and_length._read()
            else:
                pass
                self.position_and_length = TrDosImage.PositionAndLengthGeneric(self._io, self, self._root)
                self.position_and_length._read()
            self._debug['position_and_length']['end'] = self._io.pos()
            self._debug['length_sectors']['start'] = self._io.pos()
            self.length_sectors = self._io.read_u1()
            self._debug['length_sectors']['end'] = self._io.pos()
            self._debug['starting_sector']['start'] = self._io.pos()
            self.starting_sector = self._io.read_u1()
            self._debug['starting_sector']['end'] = self._io.pos()
            self._debug['starting_track']['start'] = self._io.pos()
            self.starting_track = self._io.read_u1()
            self._debug['starting_track']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            _on = self.extension
            if _on == 35:
                pass
                self.position_and_length._fetch_instances()
            elif _on == 66:
                pass
                self.position_and_length._fetch_instances()
            elif _on == 67:
                pass
                self.position_and_length._fetch_instances()
            else:
                pass
                self.position_and_length._fetch_instances()
            _ = self.contents
            if hasattr(self, '_m_contents'):
                pass


        @property
        def contents(self):
            if hasattr(self, '_m_contents'):
                return self._m_contents

            _pos = self._io.pos()
            self._io.seek((self.starting_track * 256) * 16 + self.starting_sector * 256)
            self._debug['_m_contents']['start'] = self._io.pos()
            self._m_contents = self._io.read_bytes(self.length_sectors * 256)
            self._debug['_m_contents']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_contents', None)

        @property
        def is_deleted(self):
            if hasattr(self, '_m_is_deleted'):
                return self._m_is_deleted

            self._m_is_deleted = self.name.first_byte == 1
            return getattr(self, '_m_is_deleted', None)

        @property
        def is_terminator(self):
            if hasattr(self, '_m_is_terminator'):
                return self._m_is_terminator

            self._m_is_terminator = self.name.first_byte == 0
            return getattr(self, '_m_is_terminator', None)


    class Filename(KaitaiStruct):
        SEQ_FIELDS = ["name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.Filename, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = self._io.read_bytes(8)
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.first_byte
            if hasattr(self, '_m_first_byte'):
                pass


        @property
        def first_byte(self):
            if hasattr(self, '_m_first_byte'):
                return self._m_first_byte

            _pos = self._io.pos()
            self._io.seek(0)
            self._debug['_m_first_byte']['start'] = self._io.pos()
            self._m_first_byte = self._io.read_u1()
            self._debug['_m_first_byte']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_first_byte', None)


    class PositionAndLengthBasic(KaitaiStruct):
        SEQ_FIELDS = ["program_and_data_length", "program_length"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.PositionAndLengthBasic, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['program_and_data_length']['start'] = self._io.pos()
            self.program_and_data_length = self._io.read_u2le()
            self._debug['program_and_data_length']['end'] = self._io.pos()
            self._debug['program_length']['start'] = self._io.pos()
            self.program_length = self._io.read_u2le()
            self._debug['program_length']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class PositionAndLengthCode(KaitaiStruct):
        SEQ_FIELDS = ["start_address", "length"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.PositionAndLengthCode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['start_address']['start'] = self._io.pos()
            self.start_address = self._io.read_u2le()
            self._debug['start_address']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u2le()
            self._debug['length']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class PositionAndLengthGeneric(KaitaiStruct):
        SEQ_FIELDS = ["reserved", "length"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.PositionAndLengthGeneric, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_u2le()
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u2le()
            self._debug['length']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class PositionAndLengthPrint(KaitaiStruct):
        SEQ_FIELDS = ["extent_no", "reserved", "length"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.PositionAndLengthPrint, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['extent_no']['start'] = self._io.pos()
            self.extent_no = self._io.read_u1()
            self._debug['extent_no']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_u1()
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u2le()
            self._debug['length']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class VolumeInfo(KaitaiStruct):
        SEQ_FIELDS = ["catalog_end", "unused", "first_free_sector_sector", "first_free_sector_track", "disk_type", "num_files", "num_free_sectors", "tr_dos_id", "unused_2", "password", "unused_3", "num_deleted_files", "label", "unused_4"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TrDosImage.VolumeInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['catalog_end']['start'] = self._io.pos()
            self.catalog_end = self._io.read_bytes(1)
            self._debug['catalog_end']['end'] = self._io.pos()
            if not self.catalog_end == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.catalog_end, self._io, u"/types/volume_info/seq/0")
            self._debug['unused']['start'] = self._io.pos()
            self.unused = self._io.read_bytes(224)
            self._debug['unused']['end'] = self._io.pos()
            self._debug['first_free_sector_sector']['start'] = self._io.pos()
            self.first_free_sector_sector = self._io.read_u1()
            self._debug['first_free_sector_sector']['end'] = self._io.pos()
            self._debug['first_free_sector_track']['start'] = self._io.pos()
            self.first_free_sector_track = self._io.read_u1()
            self._debug['first_free_sector_track']['end'] = self._io.pos()
            self._debug['disk_type']['start'] = self._io.pos()
            self.disk_type = KaitaiStream.resolve_enum(TrDosImage.DiskType, self._io.read_u1())
            self._debug['disk_type']['end'] = self._io.pos()
            self._debug['num_files']['start'] = self._io.pos()
            self.num_files = self._io.read_u1()
            self._debug['num_files']['end'] = self._io.pos()
            self._debug['num_free_sectors']['start'] = self._io.pos()
            self.num_free_sectors = self._io.read_u2le()
            self._debug['num_free_sectors']['end'] = self._io.pos()
            self._debug['tr_dos_id']['start'] = self._io.pos()
            self.tr_dos_id = self._io.read_bytes(1)
            self._debug['tr_dos_id']['end'] = self._io.pos()
            if not self.tr_dos_id == b"\x10":
                raise kaitaistruct.ValidationNotEqualError(b"\x10", self.tr_dos_id, self._io, u"/types/volume_info/seq/7")
            self._debug['unused_2']['start'] = self._io.pos()
            self.unused_2 = self._io.read_bytes(2)
            self._debug['unused_2']['end'] = self._io.pos()
            self._debug['password']['start'] = self._io.pos()
            self.password = self._io.read_bytes(9)
            self._debug['password']['end'] = self._io.pos()
            self._debug['unused_3']['start'] = self._io.pos()
            self.unused_3 = self._io.read_bytes(1)
            self._debug['unused_3']['end'] = self._io.pos()
            self._debug['num_deleted_files']['start'] = self._io.pos()
            self.num_deleted_files = self._io.read_u1()
            self._debug['num_deleted_files']['end'] = self._io.pos()
            self._debug['label']['start'] = self._io.pos()
            self.label = self._io.read_bytes(8)
            self._debug['label']['end'] = self._io.pos()
            self._debug['unused_4']['start'] = self._io.pos()
            self.unused_4 = self._io.read_bytes(3)
            self._debug['unused_4']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def num_sides(self):
            if hasattr(self, '_m_num_sides'):
                return self._m_num_sides

            self._m_num_sides = (1 if int(self.disk_type) & 8 != 0 else 2)
            return getattr(self, '_m_num_sides', None)

        @property
        def num_tracks(self):
            if hasattr(self, '_m_num_tracks'):
                return self._m_num_tracks

            self._m_num_tracks = (40 if int(self.disk_type) & 1 != 0 else 80)
            return getattr(self, '_m_num_tracks', None)


    @property
    def volume_info(self):
        if hasattr(self, '_m_volume_info'):
            return self._m_volume_info

        _pos = self._io.pos()
        self._io.seek(2048)
        self._debug['_m_volume_info']['start'] = self._io.pos()
        self._m_volume_info = TrDosImage.VolumeInfo(self._io, self, self._root)
        self._m_volume_info._read()
        self._debug['_m_volume_info']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_volume_info', None)


