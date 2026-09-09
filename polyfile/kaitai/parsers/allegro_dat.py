# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class AllegroDat(KaitaiStruct):
    """Allegro library for C (mostly used for game and multimedia apps
    programming) used its own container file format.
    
    In general, it allows storage of arbitrary binary data blocks
    bundled together with some simple key-value style metadata
    ("properties") for every block. Allegro also pre-defines some simple
    formats for bitmaps, fonts, MIDI music, sound samples and
    palettes. Allegro library v4.0+ also support LZSS compression.
    
    This spec applies to Allegro data files for library versions 2.2 up
    to 4.4.
    
    .. seealso::
       Source - https://liballeg.org/stabledocs/en/datafile.html
    """

    class PackEnum(IntEnum):
        unpacked = 1936484398
    SEQ_FIELDS = ["pack_magic", "dat_magic", "num_objects", "objects"]
    def __init__(self, _io, _parent=None, _root=None):
        super(AllegroDat, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['pack_magic']['start'] = self._io.pos()
        self.pack_magic = KaitaiStream.resolve_enum(AllegroDat.PackEnum, self._io.read_u4be())
        self._debug['pack_magic']['end'] = self._io.pos()
        self._debug['dat_magic']['start'] = self._io.pos()
        self.dat_magic = self._io.read_bytes(4)
        self._debug['dat_magic']['end'] = self._io.pos()
        if not self.dat_magic == b"\x41\x4C\x4C\x2E":
            raise kaitaistruct.ValidationNotEqualError(b"\x41\x4C\x4C\x2E", self.dat_magic, self._io, u"/seq/1")
        self._debug['num_objects']['start'] = self._io.pos()
        self.num_objects = self._io.read_u4be()
        self._debug['num_objects']['end'] = self._io.pos()
        self._debug['objects']['start'] = self._io.pos()
        self._debug['objects']['arr'] = []
        self.objects = []
        for i in range(self.num_objects):
            self._debug['objects']['arr'].append({'start': self._io.pos()})
            _t_objects = AllegroDat.DatObject(self._io, self, self._root)
            try:
                _t_objects._read()
            finally:
                self.objects.append(_t_objects)
            self._debug['objects']['arr'][i]['end'] = self._io.pos()

        self._debug['objects']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.objects)):
            pass
            self.objects[i]._fetch_instances()


    class DatBitmap(KaitaiStruct):
        SEQ_FIELDS = ["bits_per_pixel", "width", "height", "image"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatBitmap, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['bits_per_pixel']['start'] = self._io.pos()
            self.bits_per_pixel = self._io.read_s2be()
            self._debug['bits_per_pixel']['end'] = self._io.pos()
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_u2be()
            self._debug['width']['end'] = self._io.pos()
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_u2be()
            self._debug['height']['end'] = self._io.pos()
            self._debug['image']['start'] = self._io.pos()
            self.image = self._io.read_bytes_full()
            self._debug['image']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class DatFont(KaitaiStruct):
        SEQ_FIELDS = ["font_size", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatFont, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_size']['start'] = self._io.pos()
            self.font_size = self._io.read_s2be()
            self._debug['font_size']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.font_size
            if _on == 0:
                pass
                self.body = AllegroDat.DatFont39(self._io, self, self._root)
                self.body._read()
            elif _on == 16:
                pass
                self.body = AllegroDat.DatFont16(self._io, self, self._root)
                self.body._read()
            elif _on == 8:
                pass
                self.body = AllegroDat.DatFont8(self._io, self, self._root)
                self.body._read()
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.font_size
            if _on == 0:
                pass
                self.body._fetch_instances()
            elif _on == 16:
                pass
                self.body._fetch_instances()
            elif _on == 8:
                pass
                self.body._fetch_instances()


    class DatFont16(KaitaiStruct):
        """Simple monochrome monospaced font, 95 characters, 8x16 px
        characters.
        """
        SEQ_FIELDS = ["chars"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatFont16, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['chars']['start'] = self._io.pos()
            self._debug['chars']['arr'] = []
            self.chars = []
            for i in range(95):
                self._debug['chars']['arr'].append({'start': self._io.pos()})
                self.chars.append(self._io.read_bytes(16))
                self._debug['chars']['arr'][i]['end'] = self._io.pos()

            self._debug['chars']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.chars)):
                pass



    class DatFont39(KaitaiStruct):
        """New bitmap font format introduced since Allegro 3.9: allows
        flexible designation of character ranges, 8-bit colored
        characters, etc.
        """
        SEQ_FIELDS = ["num_ranges", "ranges"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatFont39, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_ranges']['start'] = self._io.pos()
            self.num_ranges = self._io.read_s2be()
            self._debug['num_ranges']['end'] = self._io.pos()
            self._debug['ranges']['start'] = self._io.pos()
            self._debug['ranges']['arr'] = []
            self.ranges = []
            for i in range(self.num_ranges):
                self._debug['ranges']['arr'].append({'start': self._io.pos()})
                _t_ranges = AllegroDat.DatFont39.Range(self._io, self, self._root)
                try:
                    _t_ranges._read()
                finally:
                    self.ranges.append(_t_ranges)
                self._debug['ranges']['arr'][i]['end'] = self._io.pos()

            self._debug['ranges']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.ranges)):
                pass
                self.ranges[i]._fetch_instances()


        class FontChar(KaitaiStruct):
            SEQ_FIELDS = ["width", "height", "body"]
            def __init__(self, _io, _parent=None, _root=None):
                super(AllegroDat.DatFont39.FontChar, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['width']['start'] = self._io.pos()
                self.width = self._io.read_u2be()
                self._debug['width']['end'] = self._io.pos()
                self._debug['height']['start'] = self._io.pos()
                self.height = self._io.read_u2be()
                self._debug['height']['end'] = self._io.pos()
                self._debug['body']['start'] = self._io.pos()
                self.body = self._io.read_bytes(self.width * self.height)
                self._debug['body']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class Range(KaitaiStruct):
            SEQ_FIELDS = ["mono", "start_char", "end_char", "chars"]
            def __init__(self, _io, _parent=None, _root=None):
                super(AllegroDat.DatFont39.Range, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['mono']['start'] = self._io.pos()
                self.mono = self._io.read_u1()
                self._debug['mono']['end'] = self._io.pos()
                self._debug['start_char']['start'] = self._io.pos()
                self.start_char = self._io.read_u4be()
                self._debug['start_char']['end'] = self._io.pos()
                self._debug['end_char']['start'] = self._io.pos()
                self.end_char = self._io.read_u4be()
                self._debug['end_char']['end'] = self._io.pos()
                self._debug['chars']['start'] = self._io.pos()
                self._debug['chars']['arr'] = []
                self.chars = []
                for i in range((self.end_char - self.start_char) + 1):
                    self._debug['chars']['arr'].append({'start': self._io.pos()})
                    _t_chars = AllegroDat.DatFont39.FontChar(self._io, self, self._root)
                    try:
                        _t_chars._read()
                    finally:
                        self.chars.append(_t_chars)
                    self._debug['chars']['arr'][i]['end'] = self._io.pos()

                self._debug['chars']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.chars)):
                    pass
                    self.chars[i]._fetch_instances()




    class DatFont8(KaitaiStruct):
        """Simple monochrome monospaced font, 95 characters, 8x8 px
        characters.
        """
        SEQ_FIELDS = ["chars"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatFont8, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['chars']['start'] = self._io.pos()
            self._debug['chars']['arr'] = []
            self.chars = []
            for i in range(95):
                self._debug['chars']['arr'].append({'start': self._io.pos()})
                self.chars.append(self._io.read_bytes(8))
                self._debug['chars']['arr'][i]['end'] = self._io.pos()

            self._debug['chars']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.chars)):
                pass



    class DatObject(KaitaiStruct):
        SEQ_FIELDS = ["properties", "len_compressed", "len_uncompressed", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatObject, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['properties']['start'] = self._io.pos()
            self._debug['properties']['arr'] = []
            self.properties = []
            i = 0
            while True:
                self._debug['properties']['arr'].append({'start': self._io.pos()})
                _t_properties = AllegroDat.Property(self._io, self, self._root)
                try:
                    _t_properties._read()
                finally:
                    _ = _t_properties
                    self.properties.append(_)
                self._debug['properties']['arr'][len(self.properties) - 1]['end'] = self._io.pos()
                if (not (_.is_valid)):
                    break
                i += 1
            self._debug['properties']['end'] = self._io.pos()
            self._debug['len_compressed']['start'] = self._io.pos()
            self.len_compressed = self._io.read_s4be()
            self._debug['len_compressed']['end'] = self._io.pos()
            self._debug['len_uncompressed']['start'] = self._io.pos()
            self.len_uncompressed = self._io.read_s4be()
            self._debug['len_uncompressed']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == u"BMP ":
                pass
                self._raw_body = self._io.read_bytes(self.len_compressed)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = AllegroDat.DatBitmap(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"FONT":
                pass
                self._raw_body = self._io.read_bytes(self.len_compressed)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = AllegroDat.DatFont(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"RLE ":
                pass
                self._raw_body = self._io.read_bytes(self.len_compressed)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = AllegroDat.DatRleSprite(_io__raw_body, self, self._root)
                self.body._read()
            else:
                pass
                self.body = self._io.read_bytes(self.len_compressed)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.properties)):
                pass
                self.properties[i]._fetch_instances()

            _on = self.type
            if _on == u"BMP ":
                pass
                self.body._fetch_instances()
            elif _on == u"FONT":
                pass
                self.body._fetch_instances()
            elif _on == u"RLE ":
                pass
                self.body._fetch_instances()
            else:
                pass

        @property
        def type(self):
            if hasattr(self, '_m_type'):
                return self._m_type

            self._m_type = self.properties[-1].magic
            return getattr(self, '_m_type', None)


    class DatRleSprite(KaitaiStruct):
        SEQ_FIELDS = ["bits_per_pixel", "width", "height", "len_image", "image"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.DatRleSprite, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['bits_per_pixel']['start'] = self._io.pos()
            self.bits_per_pixel = self._io.read_s2be()
            self._debug['bits_per_pixel']['end'] = self._io.pos()
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_u2be()
            self._debug['width']['end'] = self._io.pos()
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_u2be()
            self._debug['height']['end'] = self._io.pos()
            self._debug['len_image']['start'] = self._io.pos()
            self.len_image = self._io.read_u4be()
            self._debug['len_image']['end'] = self._io.pos()
            self._debug['image']['start'] = self._io.pos()
            self.image = self._io.read_bytes_full()
            self._debug['image']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Property(KaitaiStruct):
        SEQ_FIELDS = ["magic", "type", "len_body", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AllegroDat.Property, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = (self._io.read_bytes(4)).decode(u"UTF-8")
            self._debug['magic']['end'] = self._io.pos()
            if self.is_valid:
                pass
                self._debug['type']['start'] = self._io.pos()
                self.type = (self._io.read_bytes(4)).decode(u"UTF-8")
                self._debug['type']['end'] = self._io.pos()

            if self.is_valid:
                pass
                self._debug['len_body']['start'] = self._io.pos()
                self.len_body = self._io.read_u4be()
                self._debug['len_body']['end'] = self._io.pos()

            if self.is_valid:
                pass
                self._debug['body']['start'] = self._io.pos()
                self.body = (self._io.read_bytes(self.len_body)).decode(u"UTF-8")
                self._debug['body']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.is_valid:
                pass

            if self.is_valid:
                pass

            if self.is_valid:
                pass


        @property
        def is_valid(self):
            if hasattr(self, '_m_is_valid'):
                return self._m_is_valid

            self._m_is_valid = self.magic == u"prop"
            return getattr(self, '_m_is_valid', None)



