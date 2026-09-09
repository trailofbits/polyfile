# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Webp(KaitaiStruct):
    """
    .. seealso::
       Source - https://developers.google.com/speed/webp/docs/riff_container
    """

    class ChunkNames(IntEnum):
        xmp_var = 5262680
        vp8 = 540561494
        xmp = 542133592
        exif = 1179211845
        anmf = 1179471425
        alph = 1213221953
        vp8l = 1278758998
        frgm = 1296519750
        anim = 1296649793
        iccp = 1346585417
        vp8x = 1480085590

    class CompressionMethod(IntEnum):
        none = 0
        webp_lossless = 1

    class FilteringMethod(IntEnum):
        none = 0
        horizontal = 1
        vertical = 2
        gradient = 3

    class Preprocessing(IntEnum):
        none = 0
        level_reduction = 1
    SEQ_FIELDS = ["magic", "len_data", "webp", "payload"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Webp, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x52\x49\x46\x46":
            raise kaitaistruct.ValidationNotEqualError(b"\x52\x49\x46\x46", self.magic, self._io, u"/seq/0")
        self._debug['len_data']['start'] = self._io.pos()
        self.len_data = self._io.read_u4le()
        self._debug['len_data']['end'] = self._io.pos()
        self._debug['webp']['start'] = self._io.pos()
        self.webp = self._io.read_bytes(4)
        self._debug['webp']['end'] = self._io.pos()
        if not self.webp == b"\x57\x45\x42\x50":
            raise kaitaistruct.ValidationNotEqualError(b"\x57\x45\x42\x50", self.webp, self._io, u"/seq/2")
        self._debug['payload']['start'] = self._io.pos()
        self._raw_payload = self._io.read_bytes(self.len_data - 4)
        _io__raw_payload = KaitaiStream(BytesIO(self._raw_payload))
        self.payload = Webp.Chunks(_io__raw_payload, self, self._root)
        self.payload._read()
        self._debug['payload']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.payload._fetch_instances()

    class Alph(KaitaiStruct):
        SEQ_FIELDS = ["reserved", "preprocessing", "filtering", "compression", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Alph, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bits_int_be(2)
            self._debug['reserved']['end'] = self._io.pos()
            if not self.reserved == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.reserved, self._io, u"/types/alph/seq/0")
            self._debug['preprocessing']['start'] = self._io.pos()
            self.preprocessing = KaitaiStream.resolve_enum(Webp.Preprocessing, self._io.read_bits_int_be(2))
            self._debug['preprocessing']['end'] = self._io.pos()
            if not isinstance(self.preprocessing, Webp.Preprocessing):
                raise kaitaistruct.ValidationNotInEnumError(self.preprocessing, self._io, u"/types/alph/seq/1")
            self._debug['filtering']['start'] = self._io.pos()
            self.filtering = KaitaiStream.resolve_enum(Webp.FilteringMethod, self._io.read_bits_int_be(2))
            self._debug['filtering']['end'] = self._io.pos()
            self._debug['compression']['start'] = self._io.pos()
            self.compression = KaitaiStream.resolve_enum(Webp.CompressionMethod, self._io.read_bits_int_be(2))
            self._debug['compression']['end'] = self._io.pos()
            if not isinstance(self.compression, Webp.CompressionMethod):
                raise kaitaistruct.ValidationNotInEnumError(self.compression, self._io, u"/types/alph/seq/3")
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Anim(KaitaiStruct):
        """
        .. seealso::
           Source - https://developers.google.com/speed/webp/docs/riff_container#animation
        """
        SEQ_FIELDS = ["background_color", "loop_count"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Anim, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['background_color']['start'] = self._io.pos()
            self.background_color = Webp.Anim.BgColor(self._io, self, self._root)
            self.background_color._read()
            self._debug['background_color']['end'] = self._io.pos()
            self._debug['loop_count']['start'] = self._io.pos()
            self.loop_count = self._io.read_u2le()
            self._debug['loop_count']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.background_color._fetch_instances()

        class BgColor(KaitaiStruct):
            SEQ_FIELDS = ["blue", "green", "red", "alpha"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Webp.Anim.BgColor, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['blue']['start'] = self._io.pos()
                self.blue = self._io.read_u1()
                self._debug['blue']['end'] = self._io.pos()
                self._debug['green']['start'] = self._io.pos()
                self.green = self._io.read_u1()
                self._debug['green']['end'] = self._io.pos()
                self._debug['red']['start'] = self._io.pos()
                self.red = self._io.read_u1()
                self._debug['red']['end'] = self._io.pos()
                self._debug['alpha']['start'] = self._io.pos()
                self.alpha = self._io.read_u1()
                self._debug['alpha']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass



    class Anmf(KaitaiStruct):
        SEQ_FIELDS = ["frame_x_div_2", "frame_y_div_2", "frame_width_minus_1", "frame_height_minus_1", "duration", "reserved", "blending_method", "disposal_method", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Anmf, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['frame_x_div_2']['start'] = self._io.pos()
            self.frame_x_div_2 = self._io.read_bits_int_le(24)
            self._debug['frame_x_div_2']['end'] = self._io.pos()
            self._debug['frame_y_div_2']['start'] = self._io.pos()
            self.frame_y_div_2 = self._io.read_bits_int_le(24)
            self._debug['frame_y_div_2']['end'] = self._io.pos()
            self._debug['frame_width_minus_1']['start'] = self._io.pos()
            self.frame_width_minus_1 = self._io.read_bits_int_le(24)
            self._debug['frame_width_minus_1']['end'] = self._io.pos()
            self._debug['frame_height_minus_1']['start'] = self._io.pos()
            self.frame_height_minus_1 = self._io.read_bits_int_le(24)
            self._debug['frame_height_minus_1']['end'] = self._io.pos()
            self._debug['duration']['start'] = self._io.pos()
            self.duration = self._io.read_bits_int_le(24)
            self._debug['duration']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bits_int_be(6)
            self._debug['reserved']['end'] = self._io.pos()
            if not self.reserved == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.reserved, self._io, u"/types/anmf/seq/5")
            self._debug['blending_method']['start'] = self._io.pos()
            self.blending_method = self._io.read_bits_int_be(1) != 0
            self._debug['blending_method']['end'] = self._io.pos()
            self._debug['disposal_method']['start'] = self._io.pos()
            self.disposal_method = self._io.read_bits_int_be(1) != 0
            self._debug['disposal_method']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def frame_height(self):
            if hasattr(self, '_m_frame_height'):
                return self._m_frame_height

            self._m_frame_height = self.frame_height_minus_1 + 1
            return getattr(self, '_m_frame_height', None)

        @property
        def frame_width(self):
            if hasattr(self, '_m_frame_width'):
                return self._m_frame_width

            self._m_frame_width = self.frame_width_minus_1 + 1
            return getattr(self, '_m_frame_width', None)

        @property
        def frame_x(self):
            if hasattr(self, '_m_frame_x'):
                return self._m_frame_x

            self._m_frame_x = self.frame_x_div_2 * 2
            return getattr(self, '_m_frame_x', None)

        @property
        def frame_y(self):
            if hasattr(self, '_m_frame_y'):
                return self._m_frame_y

            self._m_frame_y = self.frame_y_div_2 * 2
            return getattr(self, '_m_frame_y', None)


    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["name", "len_data", "data", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Chunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = KaitaiStream.resolve_enum(Webp.ChunkNames, self._io.read_u4le())
            self._debug['name']['end'] = self._io.pos()
            if not isinstance(self.name, Webp.ChunkNames):
                raise kaitaistruct.ValidationNotInEnumError(self.name, self._io, u"/types/chunk/seq/0")
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            _on = self.name
            if _on == Webp.ChunkNames.alph:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Alph(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.anim:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Anim(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.anmf:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Anmf(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.vp8:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Vp8(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.vp8l:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Vp8l(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.vp8x:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Vp8x(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.xmp:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Xmp(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Webp.ChunkNames.xmp_var:
                pass
                self._raw_data = self._io.read_bytes(self.len_data)
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Webp.Xmp(_io__raw_data, self, self._root)
                self.data._read()
            else:
                pass
                self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()
            if self.len_data % 2 != 0:
                pass
                self._debug['padding']['start'] = self._io.pos()
                self.padding = self._io.read_bytes(1)
                self._debug['padding']['end'] = self._io.pos()
                if not self.padding == b"\x00":
                    raise kaitaistruct.ValidationNotEqualError(b"\x00", self.padding, self._io, u"/types/chunk/seq/3")



        def _fetch_instances(self):
            pass
            _on = self.name
            if _on == Webp.ChunkNames.alph:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.anim:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.anmf:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.vp8:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.vp8l:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.vp8x:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.xmp:
                pass
                self.data._fetch_instances()
            elif _on == Webp.ChunkNames.xmp_var:
                pass
                self.data._fetch_instances()
            else:
                pass
            if self.len_data % 2 != 0:
                pass



    class Chunks(KaitaiStruct):
        SEQ_FIELDS = ["chunks"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Chunks, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['chunks']['start'] = self._io.pos()
            self._debug['chunks']['arr'] = []
            self.chunks = []
            i = 0
            while not self._io.is_eof():
                self._debug['chunks']['arr'].append({'start': self._io.pos()})
                _t_chunks = Webp.Chunk(self._io, self, self._root)
                try:
                    _t_chunks._read()
                finally:
                    self.chunks.append(_t_chunks)
                self._debug['chunks']['arr'][len(self.chunks) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['chunks']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.chunks)):
                pass
                self.chunks[i]._fetch_instances()



    class Vp8(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.rfc-editor.org/rfc/rfc6386#section-9.1
        """
        SEQ_FIELDS = ["frame_type", "version", "show_frame", "len_first_partition", "start_code", "width", "horizontal_scale", "height", "vertical_scale", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Vp8, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['frame_type']['start'] = self._io.pos()
            self.frame_type = self._io.read_bits_int_le(1) != 0
            self._debug['frame_type']['end'] = self._io.pos()
            if not self.frame_type == False:
                raise kaitaistruct.ValidationNotEqualError(False, self.frame_type, self._io, u"/types/vp8/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_bits_int_le(3)
            self._debug['version']['end'] = self._io.pos()
            if not self.version <= 3:
                raise kaitaistruct.ValidationGreaterThanError(3, self.version, self._io, u"/types/vp8/seq/1")
            self._debug['show_frame']['start'] = self._io.pos()
            self.show_frame = self._io.read_bits_int_le(1) != 0
            self._debug['show_frame']['end'] = self._io.pos()
            self._debug['len_first_partition']['start'] = self._io.pos()
            self.len_first_partition = self._io.read_bits_int_le(19)
            self._debug['len_first_partition']['end'] = self._io.pos()
            self._debug['start_code']['start'] = self._io.pos()
            self.start_code = self._io.read_bytes(3)
            self._debug['start_code']['end'] = self._io.pos()
            if not self.start_code == b"\x9D\x01\x2A":
                raise kaitaistruct.ValidationNotEqualError(b"\x9D\x01\x2A", self.start_code, self._io, u"/types/vp8/seq/4")
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_bits_int_le(14)
            self._debug['width']['end'] = self._io.pos()
            self._debug['horizontal_scale']['start'] = self._io.pos()
            self.horizontal_scale = self._io.read_bits_int_le(2)
            self._debug['horizontal_scale']['end'] = self._io.pos()
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_bits_int_le(14)
            self._debug['height']['end'] = self._io.pos()
            self._debug['vertical_scale']['start'] = self._io.pos()
            self.vertical_scale = self._io.read_bits_int_le(2)
            self._debug['vertical_scale']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Vp8l(KaitaiStruct):
        """
        .. seealso::
           Source - https://developers.google.com/speed/webp/docs/webp_lossless_bitstream_specification
        """
        SEQ_FIELDS = ["signature", "image_width_minus_1", "image_height_minus_1", "alpha_is_used", "version_number", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Vp8l, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['signature']['start'] = self._io.pos()
            self.signature = self._io.read_u1()
            self._debug['signature']['end'] = self._io.pos()
            if not self.signature == 47:
                raise kaitaistruct.ValidationNotEqualError(47, self.signature, self._io, u"/types/vp8l/seq/0")
            self._debug['image_width_minus_1']['start'] = self._io.pos()
            self.image_width_minus_1 = self._io.read_bits_int_le(14)
            self._debug['image_width_minus_1']['end'] = self._io.pos()
            self._debug['image_height_minus_1']['start'] = self._io.pos()
            self.image_height_minus_1 = self._io.read_bits_int_le(14)
            self._debug['image_height_minus_1']['end'] = self._io.pos()
            self._debug['alpha_is_used']['start'] = self._io.pos()
            self.alpha_is_used = self._io.read_bits_int_le(1) != 0
            self._debug['alpha_is_used']['end'] = self._io.pos()
            self._debug['version_number']['start'] = self._io.pos()
            self.version_number = self._io.read_bits_int_le(3)
            self._debug['version_number']['end'] = self._io.pos()
            if not self.version_number == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.version_number, self._io, u"/types/vp8l/seq/4")
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def image_height(self):
            if hasattr(self, '_m_image_height'):
                return self._m_image_height

            self._m_image_height = self.image_height_minus_1 + 1
            return getattr(self, '_m_image_height', None)

        @property
        def image_width(self):
            if hasattr(self, '_m_image_width'):
                return self._m_image_width

            self._m_image_width = self.image_width_minus_1 + 1
            return getattr(self, '_m_image_width', None)


    class Vp8x(KaitaiStruct):
        SEQ_FIELDS = ["reserved1", "icc_profile", "alpha", "exif", "xmp", "animation", "reserved2", "reserved3", "canvas_width_minus_1", "canvas_height_minus_1"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Vp8x, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['reserved1']['start'] = self._io.pos()
            self.reserved1 = self._io.read_bits_int_be(2)
            self._debug['reserved1']['end'] = self._io.pos()
            if not self.reserved1 == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.reserved1, self._io, u"/types/vp8x/seq/0")
            self._debug['icc_profile']['start'] = self._io.pos()
            self.icc_profile = self._io.read_bits_int_be(1) != 0
            self._debug['icc_profile']['end'] = self._io.pos()
            self._debug['alpha']['start'] = self._io.pos()
            self.alpha = self._io.read_bits_int_be(1) != 0
            self._debug['alpha']['end'] = self._io.pos()
            self._debug['exif']['start'] = self._io.pos()
            self.exif = self._io.read_bits_int_be(1) != 0
            self._debug['exif']['end'] = self._io.pos()
            self._debug['xmp']['start'] = self._io.pos()
            self.xmp = self._io.read_bits_int_be(1) != 0
            self._debug['xmp']['end'] = self._io.pos()
            self._debug['animation']['start'] = self._io.pos()
            self.animation = self._io.read_bits_int_be(1) != 0
            self._debug['animation']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_bits_int_be(1) != 0
            self._debug['reserved2']['end'] = self._io.pos()
            if not self.reserved2 == False:
                raise kaitaistruct.ValidationNotEqualError(False, self.reserved2, self._io, u"/types/vp8x/seq/6")
            self._debug['reserved3']['start'] = self._io.pos()
            self.reserved3 = self._io.read_bits_int_be(24)
            self._debug['reserved3']['end'] = self._io.pos()
            if not self.reserved3 == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.reserved3, self._io, u"/types/vp8x/seq/7")
            self._debug['canvas_width_minus_1']['start'] = self._io.pos()
            self.canvas_width_minus_1 = self._io.read_bits_int_le(24)
            self._debug['canvas_width_minus_1']['end'] = self._io.pos()
            self._debug['canvas_height_minus_1']['start'] = self._io.pos()
            self.canvas_height_minus_1 = self._io.read_bits_int_le(24)
            self._debug['canvas_height_minus_1']['end'] = self._io.pos()
            if not self.canvas_height_minus_1 <= 4294967295 // self.canvas_width - 1:
                raise kaitaistruct.ValidationGreaterThanError(4294967295 // self.canvas_width - 1, self.canvas_height_minus_1, self._io, u"/types/vp8x/seq/9")


        def _fetch_instances(self):
            pass

        @property
        def canvas_height(self):
            if hasattr(self, '_m_canvas_height'):
                return self._m_canvas_height

            self._m_canvas_height = self.canvas_height_minus_1 + 1
            return getattr(self, '_m_canvas_height', None)

        @property
        def canvas_width(self):
            if hasattr(self, '_m_canvas_width'):
                return self._m_canvas_width

            self._m_canvas_width = self.canvas_width_minus_1 + 1
            return getattr(self, '_m_canvas_width', None)


    class Xmp(KaitaiStruct):
        SEQ_FIELDS = ["data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Webp.Xmp, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['data']['start'] = self._io.pos()
            self.data = (self._io.read_bytes_full()).decode(u"UTF-8")
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



