# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Xwd(KaitaiStruct):
    """xwd is a file format written by eponymous X11 screen capture
    application (xwd stands for "X Window Dump"). Typically, an average
    user transforms xwd format into something more widespread by any of
    `xwdtopnm` and `pnmto...` utilities right away.
    
    xwd format itself provides a raw uncompressed bitmap with some
    metainformation, like pixel format, width, height, bit depth,
    etc. Note that technically format includes machine-dependent fields
    and thus is probably a poor choice for true cross-platform usage.
    """

    class ByteOrder(IntEnum):
        le = 0
        be = 1

    class PixmapFormat(IntEnum):
        x_y_bitmap = 0
        x_y_pixmap = 1
        z_pixmap = 2

    class VisualClass(IntEnum):
        static_gray = 0
        gray_scale = 1
        static_color = 2
        pseudo_color = 3
        true_color = 4
        direct_color = 5
    SEQ_FIELDS = ["len_header", "hdr", "color_map"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Xwd, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['len_header']['start'] = self._io.pos()
        self.len_header = self._io.read_u4be()
        self._debug['len_header']['end'] = self._io.pos()
        self._debug['hdr']['start'] = self._io.pos()
        self._raw_hdr = self._io.read_bytes(self.len_header - 4)
        _io__raw_hdr = KaitaiStream(BytesIO(self._raw_hdr))
        self.hdr = Xwd.Header(_io__raw_hdr, self, self._root)
        self.hdr._read()
        self._debug['hdr']['end'] = self._io.pos()
        self._debug['color_map']['start'] = self._io.pos()
        self._debug['color_map']['arr'] = []
        self._raw_color_map = []
        self.color_map = []
        for i in range(self.hdr.color_map_entries):
            self._debug['color_map']['arr'].append({'start': self._io.pos()})
            self._raw_color_map.append(self._io.read_bytes(12))
            _io__raw_color_map = KaitaiStream(BytesIO(self._raw_color_map[i]))
            _t_color_map = Xwd.ColorMapEntry(_io__raw_color_map, self, self._root)
            try:
                _t_color_map._read()
            finally:
                self.color_map.append(_t_color_map)
            self._debug['color_map']['arr'][i]['end'] = self._io.pos()

        self._debug['color_map']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.hdr._fetch_instances()
        for i in range(len(self.color_map)):
            pass
            self.color_map[i]._fetch_instances()


    class ColorMapEntry(KaitaiStruct):
        SEQ_FIELDS = ["entry_number", "red", "green", "blue", "flags", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Xwd.ColorMapEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entry_number']['start'] = self._io.pos()
            self.entry_number = self._io.read_u4be()
            self._debug['entry_number']['end'] = self._io.pos()
            self._debug['red']['start'] = self._io.pos()
            self.red = self._io.read_u2be()
            self._debug['red']['end'] = self._io.pos()
            self._debug['green']['start'] = self._io.pos()
            self.green = self._io.read_u2be()
            self._debug['green']['end'] = self._io.pos()
            self._debug['blue']['start'] = self._io.pos()
            self.blue = self._io.read_u2be()
            self._debug['blue']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u1()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_u1()
            self._debug['padding']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Header(KaitaiStruct):
        SEQ_FIELDS = ["file_version", "pixmap_format", "pixmap_depth", "pixmap_width", "pixmap_height", "x_offset", "byte_order", "bitmap_unit", "bitmap_bit_order", "bitmap_pad", "bits_per_pixel", "bytes_per_line", "visual_class", "red_mask", "green_mask", "blue_mask", "bits_per_rgb", "number_of_colors", "color_map_entries", "window_width", "window_height", "window_x", "window_y", "window_border_width", "creator"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Xwd.Header, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['file_version']['start'] = self._io.pos()
            self.file_version = self._io.read_u4be()
            self._debug['file_version']['end'] = self._io.pos()
            self._debug['pixmap_format']['start'] = self._io.pos()
            self.pixmap_format = KaitaiStream.resolve_enum(Xwd.PixmapFormat, self._io.read_u4be())
            self._debug['pixmap_format']['end'] = self._io.pos()
            self._debug['pixmap_depth']['start'] = self._io.pos()
            self.pixmap_depth = self._io.read_u4be()
            self._debug['pixmap_depth']['end'] = self._io.pos()
            self._debug['pixmap_width']['start'] = self._io.pos()
            self.pixmap_width = self._io.read_u4be()
            self._debug['pixmap_width']['end'] = self._io.pos()
            self._debug['pixmap_height']['start'] = self._io.pos()
            self.pixmap_height = self._io.read_u4be()
            self._debug['pixmap_height']['end'] = self._io.pos()
            self._debug['x_offset']['start'] = self._io.pos()
            self.x_offset = self._io.read_u4be()
            self._debug['x_offset']['end'] = self._io.pos()
            self._debug['byte_order']['start'] = self._io.pos()
            self.byte_order = KaitaiStream.resolve_enum(Xwd.ByteOrder, self._io.read_u4be())
            self._debug['byte_order']['end'] = self._io.pos()
            self._debug['bitmap_unit']['start'] = self._io.pos()
            self.bitmap_unit = self._io.read_u4be()
            self._debug['bitmap_unit']['end'] = self._io.pos()
            self._debug['bitmap_bit_order']['start'] = self._io.pos()
            self.bitmap_bit_order = self._io.read_u4be()
            self._debug['bitmap_bit_order']['end'] = self._io.pos()
            self._debug['bitmap_pad']['start'] = self._io.pos()
            self.bitmap_pad = self._io.read_u4be()
            self._debug['bitmap_pad']['end'] = self._io.pos()
            self._debug['bits_per_pixel']['start'] = self._io.pos()
            self.bits_per_pixel = self._io.read_u4be()
            self._debug['bits_per_pixel']['end'] = self._io.pos()
            self._debug['bytes_per_line']['start'] = self._io.pos()
            self.bytes_per_line = self._io.read_u4be()
            self._debug['bytes_per_line']['end'] = self._io.pos()
            self._debug['visual_class']['start'] = self._io.pos()
            self.visual_class = KaitaiStream.resolve_enum(Xwd.VisualClass, self._io.read_u4be())
            self._debug['visual_class']['end'] = self._io.pos()
            self._debug['red_mask']['start'] = self._io.pos()
            self.red_mask = self._io.read_u4be()
            self._debug['red_mask']['end'] = self._io.pos()
            self._debug['green_mask']['start'] = self._io.pos()
            self.green_mask = self._io.read_u4be()
            self._debug['green_mask']['end'] = self._io.pos()
            self._debug['blue_mask']['start'] = self._io.pos()
            self.blue_mask = self._io.read_u4be()
            self._debug['blue_mask']['end'] = self._io.pos()
            self._debug['bits_per_rgb']['start'] = self._io.pos()
            self.bits_per_rgb = self._io.read_u4be()
            self._debug['bits_per_rgb']['end'] = self._io.pos()
            self._debug['number_of_colors']['start'] = self._io.pos()
            self.number_of_colors = self._io.read_u4be()
            self._debug['number_of_colors']['end'] = self._io.pos()
            self._debug['color_map_entries']['start'] = self._io.pos()
            self.color_map_entries = self._io.read_u4be()
            self._debug['color_map_entries']['end'] = self._io.pos()
            self._debug['window_width']['start'] = self._io.pos()
            self.window_width = self._io.read_u4be()
            self._debug['window_width']['end'] = self._io.pos()
            self._debug['window_height']['start'] = self._io.pos()
            self.window_height = self._io.read_u4be()
            self._debug['window_height']['end'] = self._io.pos()
            self._debug['window_x']['start'] = self._io.pos()
            self.window_x = self._io.read_s4be()
            self._debug['window_x']['end'] = self._io.pos()
            self._debug['window_y']['start'] = self._io.pos()
            self.window_y = self._io.read_s4be()
            self._debug['window_y']['end'] = self._io.pos()
            self._debug['window_border_width']['start'] = self._io.pos()
            self.window_border_width = self._io.read_u4be()
            self._debug['window_border_width']['end'] = self._io.pos()
            self._debug['creator']['start'] = self._io.pos()
            self.creator = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self._debug['creator']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



