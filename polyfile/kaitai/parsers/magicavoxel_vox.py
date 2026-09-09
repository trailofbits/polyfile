# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class MagicavoxelVox(KaitaiStruct):
    """
    .. seealso::
       MagicaVoxel Homepage - https://ephtracy.github.io/
    
    
    .. seealso::
       Format Description - https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt
    """

    class ChunkType(IntEnum):
        main = 1296124238
        matt = 1296127060
        pack = 1346454347
        rgba = 1380401729
        size = 1397316165
        xyzi = 1482250825

    class MaterialType(IntEnum):
        diffuse = 0
        metal = 1
        glass = 2
        emissive = 3

    class PropertyBitsType(IntEnum):
        plastic = 1
        roughness = 2
        specular = 4
        ior = 8
        attenuation = 16
        power = 32
        glow = 64
        is_total_power = 128
    SEQ_FIELDS = ["magic", "version", "main"]
    def __init__(self, _io, _parent=None, _root=None):
        super(MagicavoxelVox, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x56\x4F\x58\x20":
            raise kaitaistruct.ValidationNotEqualError(b"\x56\x4F\x58\x20", self.magic, self._io, u"/seq/0")
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u4le()
        self._debug['version']['end'] = self._io.pos()
        self._debug['main']['start'] = self._io.pos()
        self.main = MagicavoxelVox.Chunk(self._io, self, self._root)
        self.main._read()
        self._debug['main']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.main._fetch_instances()

    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["chunk_id", "num_bytes_of_chunk_content", "num_bytes_of_children_chunks", "chunk_content", "children_chunks"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Chunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['chunk_id']['start'] = self._io.pos()
            self.chunk_id = KaitaiStream.resolve_enum(MagicavoxelVox.ChunkType, self._io.read_u4be())
            self._debug['chunk_id']['end'] = self._io.pos()
            self._debug['num_bytes_of_chunk_content']['start'] = self._io.pos()
            self.num_bytes_of_chunk_content = self._io.read_u4le()
            self._debug['num_bytes_of_chunk_content']['end'] = self._io.pos()
            self._debug['num_bytes_of_children_chunks']['start'] = self._io.pos()
            self.num_bytes_of_children_chunks = self._io.read_u4le()
            self._debug['num_bytes_of_children_chunks']['end'] = self._io.pos()
            if self.num_bytes_of_chunk_content != 0:
                pass
                self._debug['chunk_content']['start'] = self._io.pos()
                _on = self.chunk_id
                if _on == MagicavoxelVox.ChunkType.matt:
                    pass
                    self._raw_chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                    _io__raw_chunk_content = KaitaiStream(BytesIO(self._raw_chunk_content))
                    self.chunk_content = MagicavoxelVox.Matt(_io__raw_chunk_content, self, self._root)
                    self.chunk_content._read()
                elif _on == MagicavoxelVox.ChunkType.pack:
                    pass
                    self._raw_chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                    _io__raw_chunk_content = KaitaiStream(BytesIO(self._raw_chunk_content))
                    self.chunk_content = MagicavoxelVox.Pack(_io__raw_chunk_content, self, self._root)
                    self.chunk_content._read()
                elif _on == MagicavoxelVox.ChunkType.rgba:
                    pass
                    self._raw_chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                    _io__raw_chunk_content = KaitaiStream(BytesIO(self._raw_chunk_content))
                    self.chunk_content = MagicavoxelVox.Rgba(_io__raw_chunk_content, self, self._root)
                    self.chunk_content._read()
                elif _on == MagicavoxelVox.ChunkType.size:
                    pass
                    self._raw_chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                    _io__raw_chunk_content = KaitaiStream(BytesIO(self._raw_chunk_content))
                    self.chunk_content = MagicavoxelVox.Size(_io__raw_chunk_content, self, self._root)
                    self.chunk_content._read()
                elif _on == MagicavoxelVox.ChunkType.xyzi:
                    pass
                    self._raw_chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                    _io__raw_chunk_content = KaitaiStream(BytesIO(self._raw_chunk_content))
                    self.chunk_content = MagicavoxelVox.Xyzi(_io__raw_chunk_content, self, self._root)
                    self.chunk_content._read()
                else:
                    pass
                    self.chunk_content = self._io.read_bytes(self.num_bytes_of_chunk_content)
                self._debug['chunk_content']['end'] = self._io.pos()

            if self.num_bytes_of_children_chunks != 0:
                pass
                self._debug['children_chunks']['start'] = self._io.pos()
                self._debug['children_chunks']['arr'] = []
                self.children_chunks = []
                i = 0
                while not self._io.is_eof():
                    self._debug['children_chunks']['arr'].append({'start': self._io.pos()})
                    _t_children_chunks = MagicavoxelVox.Chunk(self._io, self, self._root)
                    try:
                        _t_children_chunks._read()
                    finally:
                        self.children_chunks.append(_t_children_chunks)
                    self._debug['children_chunks']['arr'][len(self.children_chunks) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['children_chunks']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.num_bytes_of_chunk_content != 0:
                pass
                _on = self.chunk_id
                if _on == MagicavoxelVox.ChunkType.matt:
                    pass
                    self.chunk_content._fetch_instances()
                elif _on == MagicavoxelVox.ChunkType.pack:
                    pass
                    self.chunk_content._fetch_instances()
                elif _on == MagicavoxelVox.ChunkType.rgba:
                    pass
                    self.chunk_content._fetch_instances()
                elif _on == MagicavoxelVox.ChunkType.size:
                    pass
                    self.chunk_content._fetch_instances()
                elif _on == MagicavoxelVox.ChunkType.xyzi:
                    pass
                    self.chunk_content._fetch_instances()
                else:
                    pass

            if self.num_bytes_of_children_chunks != 0:
                pass
                for i in range(len(self.children_chunks)):
                    pass
                    self.children_chunks[i]._fetch_instances()




    class Color(KaitaiStruct):
        SEQ_FIELDS = ["r", "g", "b", "a"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Color, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['r']['start'] = self._io.pos()
            self.r = self._io.read_u1()
            self._debug['r']['end'] = self._io.pos()
            self._debug['g']['start'] = self._io.pos()
            self.g = self._io.read_u1()
            self._debug['g']['end'] = self._io.pos()
            self._debug['b']['start'] = self._io.pos()
            self.b = self._io.read_u1()
            self._debug['b']['end'] = self._io.pos()
            self._debug['a']['start'] = self._io.pos()
            self.a = self._io.read_u1()
            self._debug['a']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Matt(KaitaiStruct):
        SEQ_FIELDS = ["id", "material_type", "material_weight", "property_bits", "plastic", "roughness", "specular", "ior", "attenuation", "power", "glow", "is_total_power"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Matt, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u4le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['material_type']['start'] = self._io.pos()
            self.material_type = KaitaiStream.resolve_enum(MagicavoxelVox.MaterialType, self._io.read_u4le())
            self._debug['material_type']['end'] = self._io.pos()
            self._debug['material_weight']['start'] = self._io.pos()
            self.material_weight = self._io.read_f4le()
            self._debug['material_weight']['end'] = self._io.pos()
            self._debug['property_bits']['start'] = self._io.pos()
            self.property_bits = self._io.read_u4le()
            self._debug['property_bits']['end'] = self._io.pos()
            if self.has_plastic:
                pass
                self._debug['plastic']['start'] = self._io.pos()
                self.plastic = self._io.read_f4le()
                self._debug['plastic']['end'] = self._io.pos()

            if self.has_roughness:
                pass
                self._debug['roughness']['start'] = self._io.pos()
                self.roughness = self._io.read_f4le()
                self._debug['roughness']['end'] = self._io.pos()

            if self.has_specular:
                pass
                self._debug['specular']['start'] = self._io.pos()
                self.specular = self._io.read_f4le()
                self._debug['specular']['end'] = self._io.pos()

            if self.has_ior:
                pass
                self._debug['ior']['start'] = self._io.pos()
                self.ior = self._io.read_f4le()
                self._debug['ior']['end'] = self._io.pos()

            if self.has_attenuation:
                pass
                self._debug['attenuation']['start'] = self._io.pos()
                self.attenuation = self._io.read_f4le()
                self._debug['attenuation']['end'] = self._io.pos()

            if self.has_power:
                pass
                self._debug['power']['start'] = self._io.pos()
                self.power = self._io.read_f4le()
                self._debug['power']['end'] = self._io.pos()

            if self.has_glow:
                pass
                self._debug['glow']['start'] = self._io.pos()
                self.glow = self._io.read_f4le()
                self._debug['glow']['end'] = self._io.pos()

            if self.has_is_total_power:
                pass
                self._debug['is_total_power']['start'] = self._io.pos()
                self.is_total_power = self._io.read_f4le()
                self._debug['is_total_power']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.has_plastic:
                pass

            if self.has_roughness:
                pass

            if self.has_specular:
                pass

            if self.has_ior:
                pass

            if self.has_attenuation:
                pass

            if self.has_power:
                pass

            if self.has_glow:
                pass

            if self.has_is_total_power:
                pass


        @property
        def has_attenuation(self):
            if hasattr(self, '_m_has_attenuation'):
                return self._m_has_attenuation

            self._m_has_attenuation = self.property_bits & 16 != 0
            return getattr(self, '_m_has_attenuation', None)

        @property
        def has_glow(self):
            if hasattr(self, '_m_has_glow'):
                return self._m_has_glow

            self._m_has_glow = self.property_bits & 64 != 0
            return getattr(self, '_m_has_glow', None)

        @property
        def has_ior(self):
            if hasattr(self, '_m_has_ior'):
                return self._m_has_ior

            self._m_has_ior = self.property_bits & 8 != 0
            return getattr(self, '_m_has_ior', None)

        @property
        def has_is_total_power(self):
            if hasattr(self, '_m_has_is_total_power'):
                return self._m_has_is_total_power

            self._m_has_is_total_power = self.property_bits & 128 != 0
            return getattr(self, '_m_has_is_total_power', None)

        @property
        def has_plastic(self):
            if hasattr(self, '_m_has_plastic'):
                return self._m_has_plastic

            self._m_has_plastic = self.property_bits & 1 != 0
            return getattr(self, '_m_has_plastic', None)

        @property
        def has_power(self):
            if hasattr(self, '_m_has_power'):
                return self._m_has_power

            self._m_has_power = self.property_bits & 32 != 0
            return getattr(self, '_m_has_power', None)

        @property
        def has_roughness(self):
            if hasattr(self, '_m_has_roughness'):
                return self._m_has_roughness

            self._m_has_roughness = self.property_bits & 2 != 0
            return getattr(self, '_m_has_roughness', None)

        @property
        def has_specular(self):
            if hasattr(self, '_m_has_specular'):
                return self._m_has_specular

            self._m_has_specular = self.property_bits & 4 != 0
            return getattr(self, '_m_has_specular', None)


    class Pack(KaitaiStruct):
        SEQ_FIELDS = ["num_models"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Pack, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_models']['start'] = self._io.pos()
            self.num_models = self._io.read_u4le()
            self._debug['num_models']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Rgba(KaitaiStruct):
        SEQ_FIELDS = ["colors"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Rgba, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['colors']['start'] = self._io.pos()
            self._debug['colors']['arr'] = []
            self.colors = []
            for i in range(256):
                self._debug['colors']['arr'].append({'start': self._io.pos()})
                _t_colors = MagicavoxelVox.Color(self._io, self, self._root)
                try:
                    _t_colors._read()
                finally:
                    self.colors.append(_t_colors)
                self._debug['colors']['arr'][i]['end'] = self._io.pos()

            self._debug['colors']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.colors)):
                pass
                self.colors[i]._fetch_instances()



    class Size(KaitaiStruct):
        SEQ_FIELDS = ["size_x", "size_y", "size_z"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Size, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size_x']['start'] = self._io.pos()
            self.size_x = self._io.read_u4le()
            self._debug['size_x']['end'] = self._io.pos()
            self._debug['size_y']['start'] = self._io.pos()
            self.size_y = self._io.read_u4le()
            self._debug['size_y']['end'] = self._io.pos()
            self._debug['size_z']['start'] = self._io.pos()
            self.size_z = self._io.read_u4le()
            self._debug['size_z']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Voxel(KaitaiStruct):
        SEQ_FIELDS = ["x", "y", "z", "color_index"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Voxel, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x']['start'] = self._io.pos()
            self.x = self._io.read_u1()
            self._debug['x']['end'] = self._io.pos()
            self._debug['y']['start'] = self._io.pos()
            self.y = self._io.read_u1()
            self._debug['y']['end'] = self._io.pos()
            self._debug['z']['start'] = self._io.pos()
            self.z = self._io.read_u1()
            self._debug['z']['end'] = self._io.pos()
            self._debug['color_index']['start'] = self._io.pos()
            self.color_index = self._io.read_u1()
            self._debug['color_index']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Xyzi(KaitaiStruct):
        SEQ_FIELDS = ["num_voxels", "voxels"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MagicavoxelVox.Xyzi, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_voxels']['start'] = self._io.pos()
            self.num_voxels = self._io.read_u4le()
            self._debug['num_voxels']['end'] = self._io.pos()
            self._debug['voxels']['start'] = self._io.pos()
            self._debug['voxels']['arr'] = []
            self.voxels = []
            for i in range(self.num_voxels):
                self._debug['voxels']['arr'].append({'start': self._io.pos()})
                _t_voxels = MagicavoxelVox.Voxel(self._io, self, self._root)
                try:
                    _t_voxels._read()
                finally:
                    self.voxels.append(_t_voxels)
                self._debug['voxels']['arr'][i]['end'] = self._io.pos()

            self._debug['voxels']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.voxels)):
                pass
                self.voxels[i]._fetch_instances()




