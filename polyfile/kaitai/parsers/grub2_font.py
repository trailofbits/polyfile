# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Grub2Font(KaitaiStruct):
    """Bitmap font format for the GRUB 2 bootloader.
    
    .. seealso::
       Source - https://grub.gibibit.com/New_font_format
    """
    SEQ_FIELDS = ["magic", "sections"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(12)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x46\x49\x4C\x45\x00\x00\x00\x04\x50\x46\x46\x32":
            raise kaitaistruct.ValidationNotEqualError(b"\x46\x49\x4C\x45\x00\x00\x00\x04\x50\x46\x46\x32", self.magic, self._io, u"/seq/0")
        self._debug['sections']['start'] = self._io.pos()
        self.sections = []
        i = 0
        while True:
            if not 'arr' in self._debug['sections']:
                self._debug['sections']['arr'] = []
            self._debug['sections']['arr'].append({'start': self._io.pos()})
            _t_sections = Grub2Font.Section(self._io, self, self._root)
            _t_sections._read()
            _ = _t_sections
            self.sections.append(_)
            self._debug['sections']['arr'][len(self.sections) - 1]['end'] = self._io.pos()
            if _.section_type == u"DATA":
                break
            i += 1
        self._debug['sections']['end'] = self._io.pos()

    class PtszSection(KaitaiStruct):
        SEQ_FIELDS = ["font_point_size"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_point_size']['start'] = self._io.pos()
            self.font_point_size = self._io.read_u2be()
            self._debug['font_point_size']['end'] = self._io.pos()


    class FamiSection(KaitaiStruct):
        SEQ_FIELDS = ["font_family_name"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_family_name']['start'] = self._io.pos()
            self.font_family_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['font_family_name']['end'] = self._io.pos()


    class WeigSection(KaitaiStruct):
        SEQ_FIELDS = ["font_weight"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_weight']['start'] = self._io.pos()
            self.font_weight = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['font_weight']['end'] = self._io.pos()


    class MaxwSection(KaitaiStruct):
        SEQ_FIELDS = ["maximum_character_width"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['maximum_character_width']['start'] = self._io.pos()
            self.maximum_character_width = self._io.read_u2be()
            self._debug['maximum_character_width']['end'] = self._io.pos()


    class DescSection(KaitaiStruct):
        SEQ_FIELDS = ["descent_in_pixels"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['descent_in_pixels']['start'] = self._io.pos()
            self.descent_in_pixels = self._io.read_u2be()
            self._debug['descent_in_pixels']['end'] = self._io.pos()


    class Section(KaitaiStruct):
        SEQ_FIELDS = ["section_type", "len_body", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['section_type']['start'] = self._io.pos()
            self.section_type = (self._io.read_bytes(4)).decode(u"ASCII")
            self._debug['section_type']['end'] = self._io.pos()
            self._debug['len_body']['start'] = self._io.pos()
            self.len_body = self._io.read_u4be()
            self._debug['len_body']['end'] = self._io.pos()
            if self.section_type != u"DATA":
                self._debug['body']['start'] = self._io.pos()
                _on = self.section_type
                if _on == u"MAXH":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.MaxhSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"FAMI":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.FamiSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"PTSZ":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.PtszSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"MAXW":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.MaxwSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"SLAN":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.SlanSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"WEIG":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.WeigSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"CHIX":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.ChixSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"DESC":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.DescSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"NAME":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.NameSection(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == u"ASCE":
                    self._raw_body = self._io.read_bytes(self.len_body)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = Grub2Font.AsceSection(_io__raw_body, self, self._root)
                    self.body._read()
                else:
                    self.body = self._io.read_bytes(self.len_body)
                self._debug['body']['end'] = self._io.pos()



    class AsceSection(KaitaiStruct):
        SEQ_FIELDS = ["ascent_in_pixels"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ascent_in_pixels']['start'] = self._io.pos()
            self.ascent_in_pixels = self._io.read_u2be()
            self._debug['ascent_in_pixels']['end'] = self._io.pos()


    class ChixSection(KaitaiStruct):
        SEQ_FIELDS = ["characters"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['characters']['start'] = self._io.pos()
            self.characters = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['characters']:
                    self._debug['characters']['arr'] = []
                self._debug['characters']['arr'].append({'start': self._io.pos()})
                _t_characters = Grub2Font.ChixSection.Character(self._io, self, self._root)
                _t_characters._read()
                self.characters.append(_t_characters)
                self._debug['characters']['arr'][len(self.characters) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['characters']['end'] = self._io.pos()

        class Character(KaitaiStruct):
            SEQ_FIELDS = ["code_point", "flags", "ofs_definition"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['code_point']['start'] = self._io.pos()
                self.code_point = self._io.read_u4be()
                self._debug['code_point']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u1()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['ofs_definition']['start'] = self._io.pos()
                self.ofs_definition = self._io.read_u4be()
                self._debug['ofs_definition']['end'] = self._io.pos()

            @property
            def definition(self):
                if hasattr(self, '_m_definition'):
                    return self._m_definition if hasattr(self, '_m_definition') else None

                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs_definition)
                self._debug['_m_definition']['start'] = io.pos()
                self._m_definition = Grub2Font.ChixSection.CharacterDefinition(io, self, self._root)
                self._m_definition._read()
                self._debug['_m_definition']['end'] = io.pos()
                io.seek(_pos)
                return self._m_definition if hasattr(self, '_m_definition') else None


        class CharacterDefinition(KaitaiStruct):
            SEQ_FIELDS = ["width", "height", "x_offset", "y_offset", "device_width", "bitmap_data"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['width']['start'] = self._io.pos()
                self.width = self._io.read_u2be()
                self._debug['width']['end'] = self._io.pos()
                self._debug['height']['start'] = self._io.pos()
                self.height = self._io.read_u2be()
                self._debug['height']['end'] = self._io.pos()
                self._debug['x_offset']['start'] = self._io.pos()
                self.x_offset = self._io.read_s2be()
                self._debug['x_offset']['end'] = self._io.pos()
                self._debug['y_offset']['start'] = self._io.pos()
                self.y_offset = self._io.read_s2be()
                self._debug['y_offset']['end'] = self._io.pos()
                self._debug['device_width']['start'] = self._io.pos()
                self.device_width = self._io.read_s2be()
                self._debug['device_width']['end'] = self._io.pos()
                self._debug['bitmap_data']['start'] = self._io.pos()
                self.bitmap_data = self._io.read_bytes(((self.width * self.height) + 7) // 8)
                self._debug['bitmap_data']['end'] = self._io.pos()



    class MaxhSection(KaitaiStruct):
        SEQ_FIELDS = ["maximum_character_height"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['maximum_character_height']['start'] = self._io.pos()
            self.maximum_character_height = self._io.read_u2be()
            self._debug['maximum_character_height']['end'] = self._io.pos()


    class NameSection(KaitaiStruct):
        SEQ_FIELDS = ["font_name"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_name']['start'] = self._io.pos()
            self.font_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['font_name']['end'] = self._io.pos()


    class SlanSection(KaitaiStruct):
        SEQ_FIELDS = ["font_slant"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['font_slant']['start'] = self._io.pos()
            self.font_slant = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['font_slant']['end'] = self._io.pos()



