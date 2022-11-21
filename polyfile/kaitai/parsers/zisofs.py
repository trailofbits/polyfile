# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Zisofs(KaitaiStruct):
    """zisofs is a compression format for files on ISO9660 file system. It has
    limited support across operating systems, mainly Linux kernel. Typically a
    directory tree is first preprocessed by mkzftree (from the zisofs-tools
    package before being turned into an ISO9660 image by mkisofs, genisoimage
    or similar tool. The data is zlib compressed.
    
    The specification here describes the structure of a file that has been
    preprocessed by mkzftree, not of a full ISO9660 ziso. Data is not
    decompressed, as blocks with length 0 have a special meaning. Decompression
    and deconstruction of this data should be done outside of Kaitai Struct.
    
    .. seealso::
       Source - https://web.archive.org/web/20200612093441/https://dev.lovelyhq.com/libburnia/web/-/wikis/zisofs
    """
    SEQ_FIELDS = ["header", "block_pointers"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self._raw_header = self._io.read_bytes(16)
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = Zisofs.Header(_io__raw_header, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['block_pointers']['start'] = self._io.pos()
        self.block_pointers = [None] * ((self.header.num_blocks + 1))
        for i in range((self.header.num_blocks + 1)):
            if not 'arr' in self._debug['block_pointers']:
                self._debug['block_pointers']['arr'] = []
            self._debug['block_pointers']['arr'].append({'start': self._io.pos()})
            self.block_pointers[i] = self._io.read_u4le()
            self._debug['block_pointers']['arr'][i]['end'] = self._io.pos()

        self._debug['block_pointers']['end'] = self._io.pos()

    class Header(KaitaiStruct):
        SEQ_FIELDS = ["magic", "uncompressed_size", "len_header", "block_size_log2", "reserved"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(8)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x37\xE4\x53\x96\xC9\xDB\xD6\x07":
                raise kaitaistruct.ValidationNotEqualError(b"\x37\xE4\x53\x96\xC9\xDB\xD6\x07", self.magic, self._io, u"/types/header/seq/0")
            self._debug['uncompressed_size']['start'] = self._io.pos()
            self.uncompressed_size = self._io.read_u4le()
            self._debug['uncompressed_size']['end'] = self._io.pos()
            self._debug['len_header']['start'] = self._io.pos()
            self.len_header = self._io.read_u1()
            self._debug['len_header']['end'] = self._io.pos()
            if not self.len_header == 4:
                raise kaitaistruct.ValidationNotEqualError(4, self.len_header, self._io, u"/types/header/seq/2")
            self._debug['block_size_log2']['start'] = self._io.pos()
            self.block_size_log2 = self._io.read_u1()
            self._debug['block_size_log2']['end'] = self._io.pos()
            if not  ((self.block_size_log2 == 15) or (self.block_size_log2 == 16) or (self.block_size_log2 == 17)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.block_size_log2, self._io, u"/types/header/seq/3")
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bytes(2)
            self._debug['reserved']['end'] = self._io.pos()
            if not self.reserved == b"\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00\x00", self.reserved, self._io, u"/types/header/seq/4")

        @property
        def block_size(self):
            if hasattr(self, '_m_block_size'):
                return self._m_block_size if hasattr(self, '_m_block_size') else None

            self._m_block_size = (1 << self.block_size_log2)
            return self._m_block_size if hasattr(self, '_m_block_size') else None

        @property
        def num_blocks(self):
            """ceil(uncompressed_size / block_size)."""
            if hasattr(self, '_m_num_blocks'):
                return self._m_num_blocks if hasattr(self, '_m_num_blocks') else None

            self._m_num_blocks = (self.uncompressed_size // self.block_size + (1 if (self.uncompressed_size % self.block_size) != 0 else 0))
            return self._m_num_blocks if hasattr(self, '_m_num_blocks') else None


    class Block(KaitaiStruct):
        SEQ_FIELDS = []
        def __init__(self, ofs_start, ofs_end, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.ofs_start = ofs_start
            self.ofs_end = ofs_end
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass

        @property
        def len_data(self):
            if hasattr(self, '_m_len_data'):
                return self._m_len_data if hasattr(self, '_m_len_data') else None

            self._m_len_data = (self.ofs_end - self.ofs_start)
            return self._m_len_data if hasattr(self, '_m_len_data') else None

        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data if hasattr(self, '_m_data') else None

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_start)
            self._debug['_m_data']['start'] = io.pos()
            self._m_data = io.read_bytes(self.len_data)
            self._debug['_m_data']['end'] = io.pos()
            io.seek(_pos)
            return self._m_data if hasattr(self, '_m_data') else None


    @property
    def blocks(self):
        if hasattr(self, '_m_blocks'):
            return self._m_blocks if hasattr(self, '_m_blocks') else None

        self._debug['_m_blocks']['start'] = self._io.pos()
        self._m_blocks = [None] * (self.header.num_blocks)
        for i in range(self.header.num_blocks):
            if not 'arr' in self._debug['_m_blocks']:
                self._debug['_m_blocks']['arr'] = []
            self._debug['_m_blocks']['arr'].append({'start': self._io.pos()})
            _t__m_blocks = Zisofs.Block(self.block_pointers[i], self.block_pointers[(i + 1)], self._io, self, self._root)
            _t__m_blocks._read()
            self._m_blocks[i] = _t__m_blocks
            self._debug['_m_blocks']['arr'][i]['end'] = self._io.pos()

        self._debug['_m_blocks']['end'] = self._io.pos()
        return self._m_blocks if hasattr(self, '_m_blocks') else None


