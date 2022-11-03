# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class DosMz(KaitaiStruct):
    """DOS MZ file format is a traditional format for executables in MS-DOS
    environment. Many modern formats (i.e. Windows PE) still maintain
    compatibility stub with this format.
    
    As opposed to .com file format (which basically sports one 64K code
    segment of raw CPU instructions), DOS MZ .exe file format allowed
    more flexible memory management, loading of larger programs and
    added support for relocations.
    
    .. seealso::
       Source - http://www.delorie.com/djgpp/doc/exe/
    """
    SEQ_FIELDS = ["header", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = DosMz.ExeHeader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['body']['start'] = self._io.pos()
        self.body = self._io.read_bytes(self.header.len_body)
        self._debug['body']['end'] = self._io.pos()

    class ExeHeader(KaitaiStruct):
        SEQ_FIELDS = ["mz", "rest_of_header"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['mz']['start'] = self._io.pos()
            self.mz = DosMz.MzHeader(self._io, self, self._root)
            self.mz._read()
            self._debug['mz']['end'] = self._io.pos()
            self._debug['rest_of_header']['start'] = self._io.pos()
            self.rest_of_header = self._io.read_bytes((self.mz.len_header - 28))
            self._debug['rest_of_header']['end'] = self._io.pos()

        @property
        def len_body(self):
            if hasattr(self, '_m_len_body'):
                return self._m_len_body if hasattr(self, '_m_len_body') else None

            self._m_len_body = (((self.mz.num_pages * 512) if self.mz.last_page_extra_bytes == 0 else (((self.mz.num_pages - 1) * 512) + self.mz.last_page_extra_bytes)) - self.mz.len_header)
            return self._m_len_body if hasattr(self, '_m_len_body') else None


    class MzHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "last_page_extra_bytes", "num_pages", "num_relocations", "header_size", "min_allocation", "max_allocation", "initial_ss", "initial_sp", "checksum", "initial_ip", "initial_cs", "ofs_relocations", "overlay_id"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = (self._io.read_bytes(2)).decode(u"ASCII")
            self._debug['magic']['end'] = self._io.pos()
            if not  ((self.magic == u"MZ") or (self.magic == u"ZM")) :
                raise kaitaistruct.ValidationNotAnyOfError(self.magic, self._io, u"/types/mz_header/seq/0")
            self._debug['last_page_extra_bytes']['start'] = self._io.pos()
            self.last_page_extra_bytes = self._io.read_u2le()
            self._debug['last_page_extra_bytes']['end'] = self._io.pos()
            self._debug['num_pages']['start'] = self._io.pos()
            self.num_pages = self._io.read_u2le()
            self._debug['num_pages']['end'] = self._io.pos()
            self._debug['num_relocations']['start'] = self._io.pos()
            self.num_relocations = self._io.read_u2le()
            self._debug['num_relocations']['end'] = self._io.pos()
            self._debug['header_size']['start'] = self._io.pos()
            self.header_size = self._io.read_u2le()
            self._debug['header_size']['end'] = self._io.pos()
            self._debug['min_allocation']['start'] = self._io.pos()
            self.min_allocation = self._io.read_u2le()
            self._debug['min_allocation']['end'] = self._io.pos()
            self._debug['max_allocation']['start'] = self._io.pos()
            self.max_allocation = self._io.read_u2le()
            self._debug['max_allocation']['end'] = self._io.pos()
            self._debug['initial_ss']['start'] = self._io.pos()
            self.initial_ss = self._io.read_u2le()
            self._debug['initial_ss']['end'] = self._io.pos()
            self._debug['initial_sp']['start'] = self._io.pos()
            self.initial_sp = self._io.read_u2le()
            self._debug['initial_sp']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_u2le()
            self._debug['checksum']['end'] = self._io.pos()
            self._debug['initial_ip']['start'] = self._io.pos()
            self.initial_ip = self._io.read_u2le()
            self._debug['initial_ip']['end'] = self._io.pos()
            self._debug['initial_cs']['start'] = self._io.pos()
            self.initial_cs = self._io.read_u2le()
            self._debug['initial_cs']['end'] = self._io.pos()
            self._debug['ofs_relocations']['start'] = self._io.pos()
            self.ofs_relocations = self._io.read_u2le()
            self._debug['ofs_relocations']['end'] = self._io.pos()
            self._debug['overlay_id']['start'] = self._io.pos()
            self.overlay_id = self._io.read_u2le()
            self._debug['overlay_id']['end'] = self._io.pos()

        @property
        def len_header(self):
            if hasattr(self, '_m_len_header'):
                return self._m_len_header if hasattr(self, '_m_len_header') else None

            self._m_len_header = (self.header_size * 16)
            return self._m_len_header if hasattr(self, '_m_len_header') else None


    class Relocation(KaitaiStruct):
        SEQ_FIELDS = ["ofs", "seg"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs']['start'] = self._io.pos()
            self.ofs = self._io.read_u2le()
            self._debug['ofs']['end'] = self._io.pos()
            self._debug['seg']['start'] = self._io.pos()
            self.seg = self._io.read_u2le()
            self._debug['seg']['end'] = self._io.pos()


    @property
    def relocations(self):
        if hasattr(self, '_m_relocations'):
            return self._m_relocations if hasattr(self, '_m_relocations') else None

        if self.header.mz.ofs_relocations != 0:
            io = self.header._io
            _pos = io.pos()
            io.seek(self.header.mz.ofs_relocations)
            self._debug['_m_relocations']['start'] = io.pos()
            self._m_relocations = [None] * (self.header.mz.num_relocations)
            for i in range(self.header.mz.num_relocations):
                if not 'arr' in self._debug['_m_relocations']:
                    self._debug['_m_relocations']['arr'] = []
                self._debug['_m_relocations']['arr'].append({'start': io.pos()})
                _t__m_relocations = DosMz.Relocation(io, self, self._root)
                _t__m_relocations._read()
                self._m_relocations[i] = _t__m_relocations
                self._debug['_m_relocations']['arr'][i]['end'] = io.pos()

            self._debug['_m_relocations']['end'] = io.pos()
            io.seek(_pos)

        return self._m_relocations if hasattr(self, '_m_relocations') else None


