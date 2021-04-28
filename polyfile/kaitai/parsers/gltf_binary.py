# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class GltfBinary(KaitaiStruct):
    """glTF is a format for distribution of 3D models optimized for being used in software
    
    .. seealso::
       Source - https://github.com/KhronosGroup/glTF/tree/2354846/specification/2.0#binary-gltf-layout
    """

    class ChunkType(Enum):
        bin = 5130562
        json = 1313821514
    SEQ_FIELDS = ["header", "chunks"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = GltfBinary.Header(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['chunks']['start'] = self._io.pos()
        self.chunks = []
        i = 0
        while not self._io.is_eof():
            if not 'arr' in self._debug['chunks']:
                self._debug['chunks']['arr'] = []
            self._debug['chunks']['arr'].append({'start': self._io.pos()})
            _t_chunks = GltfBinary.Chunk(self._io, self, self._root)
            _t_chunks._read()
            self.chunks.append(_t_chunks)
            self._debug['chunks']['arr'][len(self.chunks) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['chunks']['end'] = self._io.pos()

    class Header(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version", "length"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x67\x6C\x54\x46":
                raise kaitaistruct.ValidationNotEqualError(b"\x67\x6C\x54\x46", self.magic, self._io, u"/types/header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4le()
            self._debug['version']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u4le()
            self._debug['length']['end'] = self._io.pos()


    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["len_data", "type", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(GltfBinary.ChunkType, self._io.read_u4le())
            self._debug['type']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            _on = self.type
            if _on == GltfBinary.ChunkType.json:
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = GltfBinary.Json(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == GltfBinary.ChunkType.bin:
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = GltfBinary.Bin(_io__raw_data, self, self._root)
                self.data._read()
            else:
                self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()


    class Json(KaitaiStruct):
        SEQ_FIELDS = ["data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['data']['start'] = self._io.pos()
            self.data = (self._io.read_bytes_full()).decode(u"UTF-8")
            self._debug['data']['end'] = self._io.pos()


    class Bin(KaitaiStruct):
        SEQ_FIELDS = ["data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()



