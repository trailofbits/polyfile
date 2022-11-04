# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

from polyfile.kaitai.parsers import mach_o
class MachOFat(KaitaiStruct):
    """This is a simple container format that encapsulates multiple Mach-O files,
    each generally for a different architecture. XNU can execute these files just
    like single-arch Mach-Os and will pick the appropriate entry.
    
    .. seealso::
       Source - https://opensource.apple.com/source/xnu/xnu-7195.121.3/EXTERNAL_HEADERS/mach-o/fat.h.auto.html
    """
    SEQ_FIELDS = ["magic", "num_fat_arch", "fat_archs"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\xCA\xFE\xBA\xBE":
            raise kaitaistruct.ValidationNotEqualError(b"\xCA\xFE\xBA\xBE", self.magic, self._io, u"/seq/0")
        self._debug['num_fat_arch']['start'] = self._io.pos()
        self.num_fat_arch = self._io.read_u4be()
        self._debug['num_fat_arch']['end'] = self._io.pos()
        self._debug['fat_archs']['start'] = self._io.pos()
        self.fat_archs = [None] * (self.num_fat_arch)
        for i in range(self.num_fat_arch):
            if not 'arr' in self._debug['fat_archs']:
                self._debug['fat_archs']['arr'] = []
            self._debug['fat_archs']['arr'].append({'start': self._io.pos()})
            _t_fat_archs = MachOFat.FatArch(self._io, self, self._root)
            _t_fat_archs._read()
            self.fat_archs[i] = _t_fat_archs
            self._debug['fat_archs']['arr'][i]['end'] = self._io.pos()

        self._debug['fat_archs']['end'] = self._io.pos()

    class FatArch(KaitaiStruct):
        SEQ_FIELDS = ["cpu_type", "cpu_subtype", "ofs_object", "len_object", "align"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['cpu_type']['start'] = self._io.pos()
            self.cpu_type = KaitaiStream.resolve_enum(MachO.CpuType, self._io.read_u4be())
            self._debug['cpu_type']['end'] = self._io.pos()
            self._debug['cpu_subtype']['start'] = self._io.pos()
            self.cpu_subtype = self._io.read_u4be()
            self._debug['cpu_subtype']['end'] = self._io.pos()
            self._debug['ofs_object']['start'] = self._io.pos()
            self.ofs_object = self._io.read_u4be()
            self._debug['ofs_object']['end'] = self._io.pos()
            self._debug['len_object']['start'] = self._io.pos()
            self.len_object = self._io.read_u4be()
            self._debug['len_object']['end'] = self._io.pos()
            self._debug['align']['start'] = self._io.pos()
            self.align = self._io.read_u4be()
            self._debug['align']['end'] = self._io.pos()

        @property
        def object(self):
            if hasattr(self, '_m_object'):
                return self._m_object if hasattr(self, '_m_object') else None

            _pos = self._io.pos()
            self._io.seek(self.ofs_object)
            self._debug['_m_object']['start'] = self._io.pos()
            self._raw__m_object = self._io.read_bytes(self.len_object)
            _io__raw__m_object = KaitaiStream(BytesIO(self._raw__m_object))
            self._m_object = mach_o.MachO(_io__raw__m_object)
            self._m_object._read()
            self._debug['_m_object']['end'] = self._io.pos()
            self._io.seek(_pos)
            return self._m_object if hasattr(self, '_m_object') else None



