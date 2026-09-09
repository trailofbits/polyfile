# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Pcx(KaitaiStruct):
    """PCX is a bitmap image format originally used by PC Paintbrush from
    ZSoft Corporation. Originally, it was a relatively simple 128-byte
    header + uncompressed bitmap format, but latest versions introduced
    more complicated palette support and RLE compression.
    
    There's an option to encode 32-bit or 16-bit RGBA pixels, and thus
    it can potentially include transparency. Theoretically, it's
    possible to encode resolution or pixel density in the some of the
    header fields too, but in reality there's no uniform standard for
    these, so different implementations treat these differently.
    
    PCX format was never made a formal standard. "ZSoft Corporation
    Technical Reference Manual" for "Image File (.PCX) Format", last
    updated in 1991, is likely the closest authoritative source.
    
    .. seealso::
       Source - https://web.archive.org/web/20100206055706/http://www.qzx.com/pc-gpe/pcx.txt
    """

    class Encodings(IntEnum):
        rle = 1

    class Versions(IntEnum):
        v2_5 = 0
        v2_8_with_palette = 2
        v2_8_without_palette = 3
        paintbrush_for_windows = 4
        v3_0 = 5
    SEQ_FIELDS = ["hdr"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Pcx, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['hdr']['start'] = self._io.pos()
        self._raw_hdr = self._io.read_bytes(128)
        _io__raw_hdr = KaitaiStream(BytesIO(self._raw_hdr))
        self.hdr = Pcx.Header(_io__raw_hdr, self, self._root)
        self.hdr._read()
        self._debug['hdr']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.hdr._fetch_instances()
        _ = self.palette_256
        if hasattr(self, '_m_palette_256'):
            pass
            self._m_palette_256._fetch_instances()


    class Header(KaitaiStruct):
        """
        .. seealso::
           - "ZSoft .PCX FILE HEADER FORMAT" - https://web.archive.org/web/20100206055706/http://www.qzx.com/pc-gpe/pcx.txt
        """
        SEQ_FIELDS = ["magic", "version", "encoding", "bits_per_pixel", "img_x_min", "img_y_min", "img_x_max", "img_y_max", "hdpi", "vdpi", "palette_16", "reserved", "num_planes", "bytes_per_line", "palette_info", "h_screen_size", "v_screen_size"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Pcx.Header, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(1)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x0A":
                raise kaitaistruct.ValidationNotEqualError(b"\x0A", self.magic, self._io, u"/types/header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = KaitaiStream.resolve_enum(Pcx.Versions, self._io.read_u1())
            self._debug['version']['end'] = self._io.pos()
            self._debug['encoding']['start'] = self._io.pos()
            self.encoding = KaitaiStream.resolve_enum(Pcx.Encodings, self._io.read_u1())
            self._debug['encoding']['end'] = self._io.pos()
            self._debug['bits_per_pixel']['start'] = self._io.pos()
            self.bits_per_pixel = self._io.read_u1()
            self._debug['bits_per_pixel']['end'] = self._io.pos()
            self._debug['img_x_min']['start'] = self._io.pos()
            self.img_x_min = self._io.read_u2le()
            self._debug['img_x_min']['end'] = self._io.pos()
            self._debug['img_y_min']['start'] = self._io.pos()
            self.img_y_min = self._io.read_u2le()
            self._debug['img_y_min']['end'] = self._io.pos()
            self._debug['img_x_max']['start'] = self._io.pos()
            self.img_x_max = self._io.read_u2le()
            self._debug['img_x_max']['end'] = self._io.pos()
            self._debug['img_y_max']['start'] = self._io.pos()
            self.img_y_max = self._io.read_u2le()
            self._debug['img_y_max']['end'] = self._io.pos()
            self._debug['hdpi']['start'] = self._io.pos()
            self.hdpi = self._io.read_u2le()
            self._debug['hdpi']['end'] = self._io.pos()
            self._debug['vdpi']['start'] = self._io.pos()
            self.vdpi = self._io.read_u2le()
            self._debug['vdpi']['end'] = self._io.pos()
            self._debug['palette_16']['start'] = self._io.pos()
            self.palette_16 = self._io.read_bytes(48)
            self._debug['palette_16']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bytes(1)
            self._debug['reserved']['end'] = self._io.pos()
            if not self.reserved == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.reserved, self._io, u"/types/header/seq/11")
            self._debug['num_planes']['start'] = self._io.pos()
            self.num_planes = self._io.read_u1()
            self._debug['num_planes']['end'] = self._io.pos()
            self._debug['bytes_per_line']['start'] = self._io.pos()
            self.bytes_per_line = self._io.read_u2le()
            self._debug['bytes_per_line']['end'] = self._io.pos()
            self._debug['palette_info']['start'] = self._io.pos()
            self.palette_info = self._io.read_u2le()
            self._debug['palette_info']['end'] = self._io.pos()
            self._debug['h_screen_size']['start'] = self._io.pos()
            self.h_screen_size = self._io.read_u2le()
            self._debug['h_screen_size']['end'] = self._io.pos()
            self._debug['v_screen_size']['start'] = self._io.pos()
            self.v_screen_size = self._io.read_u2le()
            self._debug['v_screen_size']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Rgb(KaitaiStruct):
        SEQ_FIELDS = ["r", "g", "b"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Pcx.Rgb, self).__init__(_io)
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


        def _fetch_instances(self):
            pass


    class TPalette256(KaitaiStruct):
        SEQ_FIELDS = ["magic", "colors"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Pcx.TPalette256, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(1)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x0C":
                raise kaitaistruct.ValidationNotEqualError(b"\x0C", self.magic, self._io, u"/types/t_palette_256/seq/0")
            self._debug['colors']['start'] = self._io.pos()
            self._debug['colors']['arr'] = []
            self.colors = []
            for i in range(256):
                self._debug['colors']['arr'].append({'start': self._io.pos()})
                _t_colors = Pcx.Rgb(self._io, self, self._root)
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



    @property
    def palette_256(self):
        """
        .. seealso::
           - "VGA 256 Color Palette Information" - https://web.archive.org/web/20100206055706/http://www.qzx.com/pc-gpe/pcx.txt
        """
        if hasattr(self, '_m_palette_256'):
            return self._m_palette_256

        if  ((self.hdr.version == Pcx.Versions.v3_0) and (self.hdr.bits_per_pixel == 8) and (self.hdr.num_planes == 1)) :
            pass
            _pos = self._io.pos()
            self._io.seek(self._io.size() - 769)
            self._debug['_m_palette_256']['start'] = self._io.pos()
            self._m_palette_256 = Pcx.TPalette256(self._io, self, self._root)
            self._m_palette_256._read()
            self._debug['_m_palette_256']['end'] = self._io.pos()
            self._io.seek(_pos)

        return getattr(self, '_m_palette_256', None)


