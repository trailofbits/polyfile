# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidSparse(KaitaiStruct):
    """The Android sparse format is a format to more efficiently store files
    for for example firmware updates to save on bandwidth. Files in sparse
    format first have to be converted back to their original format.
    
    A tool to create images for testing can be found in the Android source code tree:
    
    <https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse> - `img2simg.c`
    
    Note: this is not the same as the Android sparse data image format.
    
    .. seealso::
       Source - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse/sparse_format.h
    
    
    .. seealso::
       Source - https://web.archive.org/web/20220322054458/https://source.android.com/devices/bootloader/images#sparse-image-format
    """

    class ChunkTypes(Enum):
        raw = 51905
        fill = 51906
        dont_care = 51907
        crc32 = 51908
    SEQ_FIELDS = ["header_prefix", "header", "chunks"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header_prefix']['start'] = self._io.pos()
        self.header_prefix = AndroidSparse.FileHeaderPrefix(self._io, self, self._root)
        self.header_prefix._read()
        self._debug['header_prefix']['end'] = self._io.pos()
        self._debug['header']['start'] = self._io.pos()
        self._raw_header = self._io.read_bytes((self.header_prefix.len_header - 10))
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = AndroidSparse.FileHeader(_io__raw_header, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['chunks']['start'] = self._io.pos()
        self.chunks = [None] * (self.header.num_chunks)
        for i in range(self.header.num_chunks):
            if not 'arr' in self._debug['chunks']:
                self._debug['chunks']['arr'] = []
            self._debug['chunks']['arr'].append({'start': self._io.pos()})
            _t_chunks = AndroidSparse.Chunk(self._io, self, self._root)
            _t_chunks._read()
            self.chunks[i] = _t_chunks
            self._debug['chunks']['arr'][i]['end'] = self._io.pos()

        self._debug['chunks']['end'] = self._io.pos()

    class FileHeaderPrefix(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version", "len_header"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x3A\xFF\x26\xED":
                raise kaitaistruct.ValidationNotEqualError(b"\x3A\xFF\x26\xED", self.magic, self._io, u"/types/file_header_prefix/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = AndroidSparse.Version(self._io, self, self._root)
            self.version._read()
            self._debug['version']['end'] = self._io.pos()
            self._debug['len_header']['start'] = self._io.pos()
            self.len_header = self._io.read_u2le()
            self._debug['len_header']['end'] = self._io.pos()


    class FileHeader(KaitaiStruct):
        SEQ_FIELDS = ["len_chunk_header", "block_size", "num_blocks", "num_chunks", "checksum"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_chunk_header']['start'] = self._io.pos()
            self.len_chunk_header = self._io.read_u2le()
            self._debug['len_chunk_header']['end'] = self._io.pos()
            self._debug['block_size']['start'] = self._io.pos()
            self.block_size = self._io.read_u4le()
            self._debug['block_size']['end'] = self._io.pos()
            _ = self.block_size
            if not (_ % 4) == 0:
                raise kaitaistruct.ValidationExprError(self.block_size, self._io, u"/types/file_header/seq/1")
            self._debug['num_blocks']['start'] = self._io.pos()
            self.num_blocks = self._io.read_u4le()
            self._debug['num_blocks']['end'] = self._io.pos()
            self._debug['num_chunks']['start'] = self._io.pos()
            self.num_chunks = self._io.read_u4le()
            self._debug['num_chunks']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_u4le()
            self._debug['checksum']['end'] = self._io.pos()

        @property
        def version(self):
            if hasattr(self, '_m_version'):
                return self._m_version if hasattr(self, '_m_version') else None

            self._m_version = self._root.header_prefix.version
            return self._m_version if hasattr(self, '_m_version') else None

        @property
        def len_header(self):
            """size of file header, should be 28."""
            if hasattr(self, '_m_len_header'):
                return self._m_len_header if hasattr(self, '_m_len_header') else None

            self._m_len_header = self._root.header_prefix.len_header
            return self._m_len_header if hasattr(self, '_m_len_header') else None


    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["header", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['header']['start'] = self._io.pos()
            self._raw_header = self._io.read_bytes(self._root.header.len_chunk_header)
            _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
            self.header = AndroidSparse.Chunk.ChunkHeader(_io__raw_header, self, self._root)
            self.header._read()
            self._debug['header']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.header.chunk_type
            if _on == AndroidSparse.ChunkTypes.crc32:
                self.body = self._io.read_u4le()
            else:
                self.body = self._io.read_bytes(self.header.len_body)
            self._debug['body']['end'] = self._io.pos()

        class ChunkHeader(KaitaiStruct):
            SEQ_FIELDS = ["chunk_type", "reserved1", "num_body_blocks", "len_chunk"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['chunk_type']['start'] = self._io.pos()
                self.chunk_type = KaitaiStream.resolve_enum(AndroidSparse.ChunkTypes, self._io.read_u2le())
                self._debug['chunk_type']['end'] = self._io.pos()
                self._debug['reserved1']['start'] = self._io.pos()
                self.reserved1 = self._io.read_u2le()
                self._debug['reserved1']['end'] = self._io.pos()
                self._debug['num_body_blocks']['start'] = self._io.pos()
                self.num_body_blocks = self._io.read_u4le()
                self._debug['num_body_blocks']['end'] = self._io.pos()
                self._debug['len_chunk']['start'] = self._io.pos()
                self.len_chunk = self._io.read_u4le()
                self._debug['len_chunk']['end'] = self._io.pos()
                if not self.len_chunk == ((self._root.header.len_chunk_header + self.len_body_expected) if self.len_body_expected != -1 else self.len_chunk):
                    raise kaitaistruct.ValidationNotEqualError(((self._root.header.len_chunk_header + self.len_body_expected) if self.len_body_expected != -1 else self.len_chunk), self.len_chunk, self._io, u"/types/chunk/types/chunk_header/seq/3")

            @property
            def len_body(self):
                if hasattr(self, '_m_len_body'):
                    return self._m_len_body if hasattr(self, '_m_len_body') else None

                self._m_len_body = (self.len_chunk - self._root.header.len_chunk_header)
                return self._m_len_body if hasattr(self, '_m_len_body') else None

            @property
            def len_body_expected(self):
                """
                .. seealso::
                   Source - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse/sparse_read.cpp#184
                
                
                .. seealso::
                   Source - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse/sparse_read.cpp#215
                
                
                .. seealso::
                   Source - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse/sparse_read.cpp#249
                
                
                .. seealso::
                   Source - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/libsparse/sparse_read.cpp#270
                """
                if hasattr(self, '_m_len_body_expected'):
                    return self._m_len_body_expected if hasattr(self, '_m_len_body_expected') else None

                self._m_len_body_expected = ((self._root.header.block_size * self.num_body_blocks) if self.chunk_type == AndroidSparse.ChunkTypes.raw else (4 if self.chunk_type == AndroidSparse.ChunkTypes.fill else (0 if self.chunk_type == AndroidSparse.ChunkTypes.dont_care else (4 if self.chunk_type == AndroidSparse.ChunkTypes.crc32 else -1))))
                return self._m_len_body_expected if hasattr(self, '_m_len_body_expected') else None



    class Version(KaitaiStruct):
        SEQ_FIELDS = ["major", "minor"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['major']['start'] = self._io.pos()
            self.major = self._io.read_u2le()
            self._debug['major']['end'] = self._io.pos()
            if not self.major == 1:
                raise kaitaistruct.ValidationNotEqualError(1, self.major, self._io, u"/types/version/seq/0")
            self._debug['minor']['start'] = self._io.pos()
            self.minor = self._io.read_u2le()
            self._debug['minor']['end'] = self._io.pos()



