# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class GimpBrush(KaitaiStruct):
    """GIMP brush format is native to the GIMP image editor for storing a brush or a texture.
    It can be used in all [Paint Tools](https://docs.gimp.org/2.10/en/gimp-tools-paint.html),
    for example Pencil and Paintbrush. It works by repeating the brush bitmap as you move
    the tool. The Spacing parameter sets the distance between the brush marks as a percentage
    of brush width. Its default value can be set in the brush file.
    
    You can also use GIMP to create new brushes in this format. Custom brushes can be loaded
    into GIMP for use in the paint tools by copying them into one of the Brush Folders -
    select **Edit** > **Preferences** in the menu bar, expand the **Folders** section
    and choose **Brushes** to see the recognized Brush Folders or to add new ones.
    
    .. seealso::
       Source - https://github.com/GNOME/gimp/blob/441631322b/devel-docs/gbr.txt
    """

    class ColorDepth(Enum):
        grayscale = 1
        rgba = 4
    SEQ_FIELDS = ["len_header", "header"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['len_header']['start'] = self._io.pos()
        self.len_header = self._io.read_u4be()
        self._debug['len_header']['end'] = self._io.pos()
        self._debug['header']['start'] = self._io.pos()
        self._raw_header = self._io.read_bytes((self.len_header - 4))
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = GimpBrush.Header(_io__raw_header, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()

    class Header(KaitaiStruct):
        SEQ_FIELDS = ["version", "width", "height", "bytes_per_pixel", "magic", "spacing", "brush_name"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4be()
            self._debug['version']['end'] = self._io.pos()
            if not self.version == 2:
                raise kaitaistruct.ValidationNotEqualError(2, self.version, self._io, u"/types/header/seq/0")
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_u4be()
            self._debug['width']['end'] = self._io.pos()
            if not self.width >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.width, self._io, u"/types/header/seq/1")
            if not self.width <= 10000:
                raise kaitaistruct.ValidationGreaterThanError(10000, self.width, self._io, u"/types/header/seq/1")
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_u4be()
            self._debug['height']['end'] = self._io.pos()
            if not self.height >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.height, self._io, u"/types/header/seq/2")
            if not self.height <= 10000:
                raise kaitaistruct.ValidationGreaterThanError(10000, self.height, self._io, u"/types/header/seq/2")
            self._debug['bytes_per_pixel']['start'] = self._io.pos()
            self.bytes_per_pixel = KaitaiStream.resolve_enum(GimpBrush.ColorDepth, self._io.read_u4be())
            self._debug['bytes_per_pixel']['end'] = self._io.pos()
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x47\x49\x4D\x50":
                raise kaitaistruct.ValidationNotEqualError(b"\x47\x49\x4D\x50", self.magic, self._io, u"/types/header/seq/4")
            self._debug['spacing']['start'] = self._io.pos()
            self.spacing = self._io.read_u4be()
            self._debug['spacing']['end'] = self._io.pos()
            self._debug['brush_name']['start'] = self._io.pos()
            self.brush_name = (KaitaiStream.bytes_terminate(self._io.read_bytes_full(), 0, False)).decode(u"UTF-8")
            self._debug['brush_name']['end'] = self._io.pos()


    class Bitmap(KaitaiStruct):
        SEQ_FIELDS = ["rows"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['rows']['start'] = self._io.pos()
            self.rows = [None] * (self._root.header.height)
            for i in range(self._root.header.height):
                if not 'arr' in self._debug['rows']:
                    self._debug['rows']['arr'] = []
                self._debug['rows']['arr'].append({'start': self._io.pos()})
                _t_rows = GimpBrush.Row(self._io, self, self._root)
                _t_rows._read()
                self.rows[i] = _t_rows
                self._debug['rows']['arr'][i]['end'] = self._io.pos()

            self._debug['rows']['end'] = self._io.pos()


    class Row(KaitaiStruct):
        SEQ_FIELDS = ["pixels"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['pixels']['start'] = self._io.pos()
            self.pixels = [None] * (self._root.header.width)
            for i in range(self._root.header.width):
                if not 'arr' in self._debug['pixels']:
                    self._debug['pixels']['arr'] = []
                self._debug['pixels']['arr'].append({'start': self._io.pos()})
                _on = self._root.header.bytes_per_pixel
                if _on == GimpBrush.ColorDepth.grayscale:
                    if not 'arr' in self._debug['pixels']:
                        self._debug['pixels']['arr'] = []
                    self._debug['pixels']['arr'].append({'start': self._io.pos()})
                    _t_pixels = GimpBrush.Row.PixelGray(self._io, self, self._root)
                    _t_pixels._read()
                    self.pixels[i] = _t_pixels
                    self._debug['pixels']['arr'][i]['end'] = self._io.pos()
                elif _on == GimpBrush.ColorDepth.rgba:
                    if not 'arr' in self._debug['pixels']:
                        self._debug['pixels']['arr'] = []
                    self._debug['pixels']['arr'].append({'start': self._io.pos()})
                    _t_pixels = GimpBrush.Row.PixelRgba(self._io, self, self._root)
                    _t_pixels._read()
                    self.pixels[i] = _t_pixels
                    self._debug['pixels']['arr'][i]['end'] = self._io.pos()
                self._debug['pixels']['arr'][i]['end'] = self._io.pos()

            self._debug['pixels']['end'] = self._io.pos()

        class PixelGray(KaitaiStruct):
            SEQ_FIELDS = ["gray"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['gray']['start'] = self._io.pos()
                self.gray = self._io.read_u1()
                self._debug['gray']['end'] = self._io.pos()

            @property
            def red(self):
                if hasattr(self, '_m_red'):
                    return self._m_red if hasattr(self, '_m_red') else None

                self._m_red = 0
                return self._m_red if hasattr(self, '_m_red') else None

            @property
            def green(self):
                if hasattr(self, '_m_green'):
                    return self._m_green if hasattr(self, '_m_green') else None

                self._m_green = 0
                return self._m_green if hasattr(self, '_m_green') else None

            @property
            def blue(self):
                if hasattr(self, '_m_blue'):
                    return self._m_blue if hasattr(self, '_m_blue') else None

                self._m_blue = 0
                return self._m_blue if hasattr(self, '_m_blue') else None

            @property
            def alpha(self):
                if hasattr(self, '_m_alpha'):
                    return self._m_alpha if hasattr(self, '_m_alpha') else None

                self._m_alpha = self.gray
                return self._m_alpha if hasattr(self, '_m_alpha') else None


        class PixelRgba(KaitaiStruct):
            SEQ_FIELDS = ["red", "green", "blue", "alpha"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['red']['start'] = self._io.pos()
                self.red = self._io.read_u1()
                self._debug['red']['end'] = self._io.pos()
                self._debug['green']['start'] = self._io.pos()
                self.green = self._io.read_u1()
                self._debug['green']['end'] = self._io.pos()
                self._debug['blue']['start'] = self._io.pos()
                self.blue = self._io.read_u1()
                self._debug['blue']['end'] = self._io.pos()
                self._debug['alpha']['start'] = self._io.pos()
                self.alpha = self._io.read_u1()
                self._debug['alpha']['end'] = self._io.pos()



    @property
    def len_body(self):
        if hasattr(self, '_m_len_body'):
            return self._m_len_body if hasattr(self, '_m_len_body') else None

        self._m_len_body = ((self.header.width * self.header.height) * self.header.bytes_per_pixel.value)
        return self._m_len_body if hasattr(self, '_m_len_body') else None

    @property
    def body(self):
        if hasattr(self, '_m_body'):
            return self._m_body if hasattr(self, '_m_body') else None

        _pos = self._io.pos()
        self._io.seek(self.len_header)
        self._debug['_m_body']['start'] = self._io.pos()
        self._m_body = self._io.read_bytes(self.len_body)
        self._debug['_m_body']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_body if hasattr(self, '_m_body') else None


