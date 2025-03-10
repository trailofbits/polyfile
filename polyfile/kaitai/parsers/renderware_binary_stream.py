# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class RenderwareBinaryStream(KaitaiStruct):
    """
    .. seealso::
       Source - https://gtamods.com/wiki/RenderWare_binary_stream_file
    """

    class Sections(Enum):
        struct = 1
        string = 2
        extension = 3
        camera = 5
        texture = 6
        material = 7
        material_list = 8
        atomic_section = 9
        plane_section = 10
        world = 11
        spline = 12
        matrix = 13
        frame_list = 14
        geometry = 15
        clump = 16
        light = 18
        unicode_string = 19
        atomic = 20
        texture_native = 21
        texture_dictionary = 22
        animation_database = 23
        image = 24
        skin_animation = 25
        geometry_list = 26
        anim_animation = 27
        team = 28
        crowd = 29
        delta_morph_animation = 30
        right_to_render = 31
        multitexture_effect_native = 32
        multitexture_effect_dictionary = 33
        team_dictionary = 34
        platform_independent_texture_dictionary = 35
        table_of_contents = 36
        particle_standard_global_data = 37
        altpipe = 38
        platform_independent_peds = 39
        patch_mesh = 40
        chunk_group_start = 41
        chunk_group_end = 42
        uv_animation_dictionary = 43
        coll_tree = 44
        metrics_plg = 257
        spline_plg = 258
        stereo_plg = 259
        vrml_plg = 260
        morph_plg = 261
        pvs_plg = 262
        memory_leak_plg = 263
        animation_plg = 264
        gloss_plg = 265
        logo_plg = 266
        memory_info_plg = 267
        random_plg = 268
        png_image_plg = 269
        bone_plg = 270
        vrml_anim_plg = 271
        sky_mipmap_val = 272
        mrm_plg = 273
        lod_atomic_plg = 274
        me_plg = 275
        lightmap_plg = 276
        refine_plg = 277
        skin_plg = 278
        label_plg = 279
        particles_plg = 280
        geomtx_plg = 281
        synth_core_plg = 282
        stqpp_plg = 283
        part_pp_plg = 284
        collision_plg = 285
        hanim_plg = 286
        user_data_plg = 287
        material_effects_plg = 288
        particle_system_plg = 289
        delta_morph_plg = 290
        patch_plg = 291
        team_plg = 292
        crowd_pp_plg = 293
        mip_split_plg = 294
        anisotropy_plg = 295
        gcn_material_plg = 297
        geometric_pvs_plg = 298
        xbox_material_plg = 299
        multi_texture_plg = 300
        chain_plg = 301
        toon_plg = 302
        ptank_plg = 303
        particle_standard_plg = 304
        pds_plg = 305
        prtadv_plg = 306
        normal_map_plg = 307
        adc_plg = 308
        uv_animation_plg = 309
        character_set_plg = 384
        nohs_world_plg = 385
        import_util_plg = 386
        slerp_plg = 387
        optim_plg = 388
        tl_world_plg = 389
        database_plg = 390
        raytrace_plg = 391
        ray_plg = 392
        library_plg = 393
        plg_2d = 400
        tile_render_plg = 401
        jpeg_image_plg = 402
        tga_image_plg = 403
        gif_image_plg = 404
        quat_plg = 405
        spline_pvs_plg = 406
        mipmap_plg = 407
        mipmapk_plg = 408
        font_2d = 409
        intersection_plg = 410
        tiff_image_plg = 411
        pick_plg = 412
        bmp_image_plg = 413
        ras_image_plg = 414
        skin_fx_plg = 415
        vcat_plg = 416
        path_2d = 417
        brush_2d = 418
        object_2d = 419
        shape_2d = 420
        scene_2d = 421
        pick_region_2d = 422
        object_string_2d = 423
        animation_plg_2d = 424
        animation_2d = 425
        keyframe_2d = 432
        maestro_2d = 433
        barycentric = 434
        platform_independent_texture_dictionary_tk = 435
        toc_tk = 436
        tpl_tk = 437
        altpipe_tk = 438
        animation_tk = 439
        skin_split_tookit = 440
        compressed_key_tk = 441
        geometry_conditioning_plg = 442
        wing_plg = 443
        generic_pipeline_tk = 444
        lightmap_conversion_tk = 445
        filesystem_plg = 446
        dictionary_tk = 447
        uv_animation_linear = 448
        uv_animation_parameter = 449
        bin_mesh_plg = 1294
        native_data_plg = 1296
        zmodeler_lock = 61982
        atomic_visibility_distance = 39055872
        clump_visibility_distance = 39055873
        frame_visibility_distance = 39055874
        pipeline_set = 39056115
        unused_5 = 39056116
        texdictionary_link = 39056117
        specular_material = 39056118
        unused_8 = 39056119
        effect_2d = 39056120
        extra_vert_colour = 39056121
        collision_model = 39056122
        gta_hanim = 39056123
        reflection_material = 39056124
        breakable = 39056125
        frame = 39056126
        unused_16 = 39056127
    SEQ_FIELDS = ["code", "size", "library_id_stamp", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['code']['start'] = self._io.pos()
        self.code = KaitaiStream.resolve_enum(RenderwareBinaryStream.Sections, self._io.read_u4le())
        self._debug['code']['end'] = self._io.pos()
        self._debug['size']['start'] = self._io.pos()
        self.size = self._io.read_u4le()
        self._debug['size']['end'] = self._io.pos()
        self._debug['library_id_stamp']['start'] = self._io.pos()
        self.library_id_stamp = self._io.read_u4le()
        self._debug['library_id_stamp']['end'] = self._io.pos()
        self._debug['body']['start'] = self._io.pos()
        _on = self.code
        if _on == RenderwareBinaryStream.Sections.atomic:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.geometry:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.texture_dictionary:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.geometry_list:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.texture_native:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.clump:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        elif _on == RenderwareBinaryStream.Sections.frame_list:
            self._raw_body = self._io.read_bytes(self.size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = RenderwareBinaryStream.ListWithHeader(_io__raw_body, self, self._root)
            self.body._read()
        else:
            self.body = self._io.read_bytes(self.size)
        self._debug['body']['end'] = self._io.pos()

    class StructClump(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/RpClump
        """
        SEQ_FIELDS = ["num_atomics", "num_lights", "num_cameras"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_atomics']['start'] = self._io.pos()
            self.num_atomics = self._io.read_u4le()
            self._debug['num_atomics']['end'] = self._io.pos()
            if self._parent.version >= 208896:
                self._debug['num_lights']['start'] = self._io.pos()
                self.num_lights = self._io.read_u4le()
                self._debug['num_lights']['end'] = self._io.pos()

            if self._parent.version >= 208896:
                self._debug['num_cameras']['start'] = self._io.pos()
                self.num_cameras = self._io.read_u4le()
                self._debug['num_cameras']['end'] = self._io.pos()



    class StructGeometry(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/RpGeometry
        """
        SEQ_FIELDS = ["format", "num_triangles", "num_vertices", "num_morph_targets", "surf_prop", "geometry", "morph_targets"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['format']['start'] = self._io.pos()
            self.format = self._io.read_u4le()
            self._debug['format']['end'] = self._io.pos()
            self._debug['num_triangles']['start'] = self._io.pos()
            self.num_triangles = self._io.read_u4le()
            self._debug['num_triangles']['end'] = self._io.pos()
            self._debug['num_vertices']['start'] = self._io.pos()
            self.num_vertices = self._io.read_u4le()
            self._debug['num_vertices']['end'] = self._io.pos()
            self._debug['num_morph_targets']['start'] = self._io.pos()
            self.num_morph_targets = self._io.read_u4le()
            self._debug['num_morph_targets']['end'] = self._io.pos()
            if self._parent.version < 212992:
                self._debug['surf_prop']['start'] = self._io.pos()
                self.surf_prop = RenderwareBinaryStream.SurfaceProperties(self._io, self, self._root)
                self.surf_prop._read()
                self._debug['surf_prop']['end'] = self._io.pos()

            if not (self.is_native):
                self._debug['geometry']['start'] = self._io.pos()
                self.geometry = RenderwareBinaryStream.GeometryNonNative(self._io, self, self._root)
                self.geometry._read()
                self._debug['geometry']['end'] = self._io.pos()

            self._debug['morph_targets']['start'] = self._io.pos()
            self.morph_targets = [None] * (self.num_morph_targets)
            for i in range(self.num_morph_targets):
                if not 'arr' in self._debug['morph_targets']:
                    self._debug['morph_targets']['arr'] = []
                self._debug['morph_targets']['arr'].append({'start': self._io.pos()})
                _t_morph_targets = RenderwareBinaryStream.MorphTarget(self._io, self, self._root)
                _t_morph_targets._read()
                self.morph_targets[i] = _t_morph_targets
                self._debug['morph_targets']['arr'][i]['end'] = self._io.pos()

            self._debug['morph_targets']['end'] = self._io.pos()

        @property
        def num_uv_layers_raw(self):
            if hasattr(self, '_m_num_uv_layers_raw'):
                return self._m_num_uv_layers_raw if hasattr(self, '_m_num_uv_layers_raw') else None

            self._m_num_uv_layers_raw = ((self.format & 16711680) >> 16)
            return self._m_num_uv_layers_raw if hasattr(self, '_m_num_uv_layers_raw') else None

        @property
        def is_textured(self):
            if hasattr(self, '_m_is_textured'):
                return self._m_is_textured if hasattr(self, '_m_is_textured') else None

            self._m_is_textured = (self.format & 4) != 0
            return self._m_is_textured if hasattr(self, '_m_is_textured') else None

        @property
        def is_native(self):
            if hasattr(self, '_m_is_native'):
                return self._m_is_native if hasattr(self, '_m_is_native') else None

            self._m_is_native = (self.format & 16777216) != 0
            return self._m_is_native if hasattr(self, '_m_is_native') else None

        @property
        def num_uv_layers(self):
            if hasattr(self, '_m_num_uv_layers'):
                return self._m_num_uv_layers if hasattr(self, '_m_num_uv_layers') else None

            self._m_num_uv_layers = ((2 if self.is_textured2 else (1 if self.is_textured else 0)) if self.num_uv_layers_raw == 0 else self.num_uv_layers_raw)
            return self._m_num_uv_layers if hasattr(self, '_m_num_uv_layers') else None

        @property
        def is_textured2(self):
            if hasattr(self, '_m_is_textured2'):
                return self._m_is_textured2 if hasattr(self, '_m_is_textured2') else None

            self._m_is_textured2 = (self.format & 128) != 0
            return self._m_is_textured2 if hasattr(self, '_m_is_textured2') else None

        @property
        def is_prelit(self):
            if hasattr(self, '_m_is_prelit'):
                return self._m_is_prelit if hasattr(self, '_m_is_prelit') else None

            self._m_is_prelit = (self.format & 8) != 0
            return self._m_is_prelit if hasattr(self, '_m_is_prelit') else None


    class GeometryNonNative(KaitaiStruct):
        SEQ_FIELDS = ["prelit_colors", "uv_layers", "triangles"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if self._parent.is_prelit:
                self._debug['prelit_colors']['start'] = self._io.pos()
                self.prelit_colors = [None] * (self._parent.num_vertices)
                for i in range(self._parent.num_vertices):
                    if not 'arr' in self._debug['prelit_colors']:
                        self._debug['prelit_colors']['arr'] = []
                    self._debug['prelit_colors']['arr'].append({'start': self._io.pos()})
                    _t_prelit_colors = RenderwareBinaryStream.Rgba(self._io, self, self._root)
                    _t_prelit_colors._read()
                    self.prelit_colors[i] = _t_prelit_colors
                    self._debug['prelit_colors']['arr'][i]['end'] = self._io.pos()

                self._debug['prelit_colors']['end'] = self._io.pos()

            self._debug['uv_layers']['start'] = self._io.pos()
            self.uv_layers = [None] * (self._parent.num_uv_layers)
            for i in range(self._parent.num_uv_layers):
                if not 'arr' in self._debug['uv_layers']:
                    self._debug['uv_layers']['arr'] = []
                self._debug['uv_layers']['arr'].append({'start': self._io.pos()})
                _t_uv_layers = RenderwareBinaryStream.UvLayer(self._parent.num_vertices, self._io, self, self._root)
                _t_uv_layers._read()
                self.uv_layers[i] = _t_uv_layers
                self._debug['uv_layers']['arr'][i]['end'] = self._io.pos()

            self._debug['uv_layers']['end'] = self._io.pos()
            self._debug['triangles']['start'] = self._io.pos()
            self.triangles = [None] * (self._parent.num_triangles)
            for i in range(self._parent.num_triangles):
                if not 'arr' in self._debug['triangles']:
                    self._debug['triangles']['arr'] = []
                self._debug['triangles']['arr'].append({'start': self._io.pos()})
                _t_triangles = RenderwareBinaryStream.Triangle(self._io, self, self._root)
                _t_triangles._read()
                self.triangles[i] = _t_triangles
                self._debug['triangles']['arr'][i]['end'] = self._io.pos()

            self._debug['triangles']['end'] = self._io.pos()


    class StructGeometryList(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Geometry_List_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["num_geometries"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_geometries']['start'] = self._io.pos()
            self.num_geometries = self._io.read_u4le()
            self._debug['num_geometries']['end'] = self._io.pos()


    class Rgba(KaitaiStruct):
        SEQ_FIELDS = ["r", "g", "b", "a"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
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


    class Sphere(KaitaiStruct):
        SEQ_FIELDS = ["x", "y", "z", "radius"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x']['start'] = self._io.pos()
            self.x = self._io.read_f4le()
            self._debug['x']['end'] = self._io.pos()
            self._debug['y']['start'] = self._io.pos()
            self.y = self._io.read_f4le()
            self._debug['y']['end'] = self._io.pos()
            self._debug['z']['start'] = self._io.pos()
            self.z = self._io.read_f4le()
            self._debug['z']['end'] = self._io.pos()
            self._debug['radius']['start'] = self._io.pos()
            self.radius = self._io.read_f4le()
            self._debug['radius']['end'] = self._io.pos()


    class MorphTarget(KaitaiStruct):
        SEQ_FIELDS = ["bounding_sphere", "has_vertices", "has_normals", "vertices", "normals"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['bounding_sphere']['start'] = self._io.pos()
            self.bounding_sphere = RenderwareBinaryStream.Sphere(self._io, self, self._root)
            self.bounding_sphere._read()
            self._debug['bounding_sphere']['end'] = self._io.pos()
            self._debug['has_vertices']['start'] = self._io.pos()
            self.has_vertices = self._io.read_u4le()
            self._debug['has_vertices']['end'] = self._io.pos()
            self._debug['has_normals']['start'] = self._io.pos()
            self.has_normals = self._io.read_u4le()
            self._debug['has_normals']['end'] = self._io.pos()
            if self.has_vertices != 0:
                self._debug['vertices']['start'] = self._io.pos()
                self.vertices = [None] * (self._parent.num_vertices)
                for i in range(self._parent.num_vertices):
                    if not 'arr' in self._debug['vertices']:
                        self._debug['vertices']['arr'] = []
                    self._debug['vertices']['arr'].append({'start': self._io.pos()})
                    _t_vertices = RenderwareBinaryStream.Vector3d(self._io, self, self._root)
                    _t_vertices._read()
                    self.vertices[i] = _t_vertices
                    self._debug['vertices']['arr'][i]['end'] = self._io.pos()

                self._debug['vertices']['end'] = self._io.pos()

            if self.has_normals != 0:
                self._debug['normals']['start'] = self._io.pos()
                self.normals = [None] * (self._parent.num_vertices)
                for i in range(self._parent.num_vertices):
                    if not 'arr' in self._debug['normals']:
                        self._debug['normals']['arr'] = []
                    self._debug['normals']['arr'].append({'start': self._io.pos()})
                    _t_normals = RenderwareBinaryStream.Vector3d(self._io, self, self._root)
                    _t_normals._read()
                    self.normals[i] = _t_normals
                    self._debug['normals']['arr'][i]['end'] = self._io.pos()

                self._debug['normals']['end'] = self._io.pos()



    class StructAtomic(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Atomic_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["frame_index", "geometry_index", "flag_render", "_unnamed3", "flag_collision_test", "_unnamed5", "unused"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['frame_index']['start'] = self._io.pos()
            self.frame_index = self._io.read_u4le()
            self._debug['frame_index']['end'] = self._io.pos()
            self._debug['geometry_index']['start'] = self._io.pos()
            self.geometry_index = self._io.read_u4le()
            self._debug['geometry_index']['end'] = self._io.pos()
            self._debug['flag_render']['start'] = self._io.pos()
            self.flag_render = self._io.read_bits_int_le(1) != 0
            self._debug['flag_render']['end'] = self._io.pos()
            self._debug['_unnamed3']['start'] = self._io.pos()
            self._unnamed3 = self._io.read_bits_int_le(1) != 0
            self._debug['_unnamed3']['end'] = self._io.pos()
            self._debug['flag_collision_test']['start'] = self._io.pos()
            self.flag_collision_test = self._io.read_bits_int_le(1) != 0
            self._debug['flag_collision_test']['end'] = self._io.pos()
            self._debug['_unnamed5']['start'] = self._io.pos()
            self._unnamed5 = self._io.read_bits_int_le(29)
            self._debug['_unnamed5']['end'] = self._io.pos()
            self._io.align_to_byte()
            self._debug['unused']['start'] = self._io.pos()
            self.unused = self._io.read_u4le()
            self._debug['unused']['end'] = self._io.pos()


    class SurfaceProperties(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/RpGeometry
        """
        SEQ_FIELDS = ["ambient", "specular", "diffuse"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ambient']['start'] = self._io.pos()
            self.ambient = self._io.read_f4le()
            self._debug['ambient']['end'] = self._io.pos()
            self._debug['specular']['start'] = self._io.pos()
            self.specular = self._io.read_f4le()
            self._debug['specular']['end'] = self._io.pos()
            self._debug['diffuse']['start'] = self._io.pos()
            self.diffuse = self._io.read_f4le()
            self._debug['diffuse']['end'] = self._io.pos()


    class StructFrameList(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Frame_List_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["num_frames", "frames"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_frames']['start'] = self._io.pos()
            self.num_frames = self._io.read_u4le()
            self._debug['num_frames']['end'] = self._io.pos()
            self._debug['frames']['start'] = self._io.pos()
            self.frames = [None] * (self.num_frames)
            for i in range(self.num_frames):
                if not 'arr' in self._debug['frames']:
                    self._debug['frames']['arr'] = []
                self._debug['frames']['arr'].append({'start': self._io.pos()})
                _t_frames = RenderwareBinaryStream.Frame(self._io, self, self._root)
                _t_frames._read()
                self.frames[i] = _t_frames
                self._debug['frames']['arr'][i]['end'] = self._io.pos()

            self._debug['frames']['end'] = self._io.pos()


    class Matrix(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Frame_List_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self.entries = [None] * (3)
            for i in range(3):
                if not 'arr' in self._debug['entries']:
                    self._debug['entries']['arr'] = []
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = RenderwareBinaryStream.Vector3d(self._io, self, self._root)
                _t_entries._read()
                self.entries[i] = _t_entries
                self._debug['entries']['arr'][i]['end'] = self._io.pos()

            self._debug['entries']['end'] = self._io.pos()


    class Vector3d(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Frame_List_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["x", "y", "z"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x']['start'] = self._io.pos()
            self.x = self._io.read_f4le()
            self._debug['x']['end'] = self._io.pos()
            self._debug['y']['start'] = self._io.pos()
            self.y = self._io.read_f4le()
            self._debug['y']['end'] = self._io.pos()
            self._debug['z']['start'] = self._io.pos()
            self.z = self._io.read_f4le()
            self._debug['z']['end'] = self._io.pos()


    class ListWithHeader(KaitaiStruct):
        """Typical structure used by many data types in RenderWare binary
        stream. Substream contains a list of binary stream entries,
        first entry always has type "struct" and carries some specific
        binary data it in, determined by the type of parent. All other
        entries, beside the first one, are normal, self-describing
        records.
        """
        SEQ_FIELDS = ["code", "header_size", "library_id_stamp", "header", "entries"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = self._io.read_bytes(4)
            self._debug['code']['end'] = self._io.pos()
            if not self.code == b"\x01\x00\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x01\x00\x00\x00", self.code, self._io, u"/types/list_with_header/seq/0")
            self._debug['header_size']['start'] = self._io.pos()
            self.header_size = self._io.read_u4le()
            self._debug['header_size']['end'] = self._io.pos()
            self._debug['library_id_stamp']['start'] = self._io.pos()
            self.library_id_stamp = self._io.read_u4le()
            self._debug['library_id_stamp']['end'] = self._io.pos()
            self._debug['header']['start'] = self._io.pos()
            _on = self._parent.code
            if _on == RenderwareBinaryStream.Sections.atomic:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructAtomic(_io__raw_header, self, self._root)
                self.header._read()
            elif _on == RenderwareBinaryStream.Sections.geometry:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructGeometry(_io__raw_header, self, self._root)
                self.header._read()
            elif _on == RenderwareBinaryStream.Sections.texture_dictionary:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructTextureDictionary(_io__raw_header, self, self._root)
                self.header._read()
            elif _on == RenderwareBinaryStream.Sections.geometry_list:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructGeometryList(_io__raw_header, self, self._root)
                self.header._read()
            elif _on == RenderwareBinaryStream.Sections.clump:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructClump(_io__raw_header, self, self._root)
                self.header._read()
            elif _on == RenderwareBinaryStream.Sections.frame_list:
                self._raw_header = self._io.read_bytes(self.header_size)
                _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
                self.header = RenderwareBinaryStream.StructFrameList(_io__raw_header, self, self._root)
                self.header._read()
            else:
                self.header = self._io.read_bytes(self.header_size)
            self._debug['header']['end'] = self._io.pos()
            self._debug['entries']['start'] = self._io.pos()
            self.entries = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['entries']:
                    self._debug['entries']['arr'] = []
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = RenderwareBinaryStream(self._io)
                _t_entries._read()
                self.entries.append(_t_entries)
                self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['entries']['end'] = self._io.pos()

        @property
        def version(self):
            if hasattr(self, '_m_version'):
                return self._m_version if hasattr(self, '_m_version') else None

            self._m_version = (((((self.library_id_stamp >> 14) & 261888) + 196608) | ((self.library_id_stamp >> 16) & 63)) if (self.library_id_stamp & 4294901760) != 0 else (self.library_id_stamp << 8))
            return self._m_version if hasattr(self, '_m_version') else None


    class Triangle(KaitaiStruct):
        SEQ_FIELDS = ["vertex2", "vertex1", "material_id", "vertex3"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['vertex2']['start'] = self._io.pos()
            self.vertex2 = self._io.read_u2le()
            self._debug['vertex2']['end'] = self._io.pos()
            self._debug['vertex1']['start'] = self._io.pos()
            self.vertex1 = self._io.read_u2le()
            self._debug['vertex1']['end'] = self._io.pos()
            self._debug['material_id']['start'] = self._io.pos()
            self.material_id = self._io.read_u2le()
            self._debug['material_id']['end'] = self._io.pos()
            self._debug['vertex3']['start'] = self._io.pos()
            self.vertex3 = self._io.read_u2le()
            self._debug['vertex3']['end'] = self._io.pos()


    class Frame(KaitaiStruct):
        """
        .. seealso::
           Source - https://gtamods.com/wiki/Frame_List_(RW_Section)#Structure
        """
        SEQ_FIELDS = ["rotation_matrix", "position", "cur_frame_idx", "matrix_creation_flags"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['rotation_matrix']['start'] = self._io.pos()
            self.rotation_matrix = RenderwareBinaryStream.Matrix(self._io, self, self._root)
            self.rotation_matrix._read()
            self._debug['rotation_matrix']['end'] = self._io.pos()
            self._debug['position']['start'] = self._io.pos()
            self.position = RenderwareBinaryStream.Vector3d(self._io, self, self._root)
            self.position._read()
            self._debug['position']['end'] = self._io.pos()
            self._debug['cur_frame_idx']['start'] = self._io.pos()
            self.cur_frame_idx = self._io.read_s4le()
            self._debug['cur_frame_idx']['end'] = self._io.pos()
            self._debug['matrix_creation_flags']['start'] = self._io.pos()
            self.matrix_creation_flags = self._io.read_u4le()
            self._debug['matrix_creation_flags']['end'] = self._io.pos()


    class TexCoord(KaitaiStruct):
        SEQ_FIELDS = ["u", "v"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['u']['start'] = self._io.pos()
            self.u = self._io.read_f4le()
            self._debug['u']['end'] = self._io.pos()
            self._debug['v']['start'] = self._io.pos()
            self.v = self._io.read_f4le()
            self._debug['v']['end'] = self._io.pos()


    class UvLayer(KaitaiStruct):
        SEQ_FIELDS = ["tex_coords"]
        def __init__(self, num_vertices, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.num_vertices = num_vertices
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['tex_coords']['start'] = self._io.pos()
            self.tex_coords = [None] * (self.num_vertices)
            for i in range(self.num_vertices):
                if not 'arr' in self._debug['tex_coords']:
                    self._debug['tex_coords']['arr'] = []
                self._debug['tex_coords']['arr'].append({'start': self._io.pos()})
                _t_tex_coords = RenderwareBinaryStream.TexCoord(self._io, self, self._root)
                _t_tex_coords._read()
                self.tex_coords[i] = _t_tex_coords
                self._debug['tex_coords']['arr'][i]['end'] = self._io.pos()

            self._debug['tex_coords']['end'] = self._io.pos()


    class StructTextureDictionary(KaitaiStruct):
        SEQ_FIELDS = ["num_textures"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_textures']['start'] = self._io.pos()
            self.num_textures = self._io.read_u4le()
            self._debug['num_textures']['end'] = self._io.pos()


    @property
    def version(self):
        if hasattr(self, '_m_version'):
            return self._m_version if hasattr(self, '_m_version') else None

        self._m_version = (((((self.library_id_stamp >> 14) & 261888) + 196608) | ((self.library_id_stamp >> 16) & 63)) if (self.library_id_stamp & 4294901760) != 0 else (self.library_id_stamp << 8))
        return self._m_version if hasattr(self, '_m_version') else None


