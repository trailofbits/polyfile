# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class DimeMessage(KaitaiStruct):
    """Direct Internet Message Encapsulation (DIME)
    is an old Microsoft specification for sending and receiving
    SOAP messages along with additional attachments,
    like binary files, XML fragments, and even other
    SOAP messages, using standard transport protocols like HTTP.
    
    Sample file: `curl -LO
    https://github.com/kaitai-io/kaitai_struct_formats/files/5894723/scanner_withoptions.dump.gz
    && gunzip scanner_withoptions.dump.gz`
    
    .. seealso::
       Source - https://tools.ietf.org/html/draft-nielsen-dime-02
    
    
    .. seealso::
       Source - https://docs.microsoft.com/en-us/archive/msdn-magazine/2002/december/sending-files-attachments-and-soap-messages-via-dime
    
    
    .. seealso::
       Source - http://imrannazar.com/Parsing-the-DIME-Message-Format
    """

    class TypeFormats(Enum):
        unchanged = 0
        media_type = 1
        absolute_uri = 2
        unknown = 3
        none = 4
    SEQ_FIELDS = ["records"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['records']['start'] = self._io.pos()
        self.records = []
        i = 0
        while not self._io.is_eof():
            if not 'arr' in self._debug['records']:
                self._debug['records']['arr'] = []
            self._debug['records']['arr'].append({'start': self._io.pos()})
            _t_records = DimeMessage.Record(self._io, self, self._root)
            _t_records._read()
            self.records.append(_t_records)
            self._debug['records']['arr'][len(self.records) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['records']['end'] = self._io.pos()

    class Padding(KaitaiStruct):
        """padding to the next 4-byte boundary."""
        SEQ_FIELDS = ["boundary_padding"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['boundary_padding']['start'] = self._io.pos()
            self.boundary_padding = self._io.read_bytes((-(self._io.pos()) % 4))
            self._debug['boundary_padding']['end'] = self._io.pos()


    class OptionField(KaitaiStruct):
        """the option field of the record."""
        SEQ_FIELDS = ["option_elements"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['option_elements']['start'] = self._io.pos()
            self.option_elements = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['option_elements']:
                    self._debug['option_elements']['arr'] = []
                self._debug['option_elements']['arr'].append({'start': self._io.pos()})
                _t_option_elements = DimeMessage.OptionElement(self._io, self, self._root)
                _t_option_elements._read()
                self.option_elements.append(_t_option_elements)
                self._debug['option_elements']['arr'][len(self.option_elements) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['option_elements']['end'] = self._io.pos()


    class OptionElement(KaitaiStruct):
        """one element of the option field."""
        SEQ_FIELDS = ["element_format", "len_element", "element_data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['element_format']['start'] = self._io.pos()
            self.element_format = self._io.read_u2be()
            self._debug['element_format']['end'] = self._io.pos()
            self._debug['len_element']['start'] = self._io.pos()
            self.len_element = self._io.read_u2be()
            self._debug['len_element']['end'] = self._io.pos()
            self._debug['element_data']['start'] = self._io.pos()
            self.element_data = self._io.read_bytes(self.len_element)
            self._debug['element_data']['end'] = self._io.pos()


    class Record(KaitaiStruct):
        """each individual fragment of the message."""
        SEQ_FIELDS = ["version", "is_first_record", "is_last_record", "is_chunk_record", "type_format", "reserved", "len_options", "len_id", "len_type", "len_data", "options", "options_padding", "id", "id_padding", "type", "type_padding", "data", "data_padding"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_bits_int_be(5)
            self._debug['version']['end'] = self._io.pos()
            self._debug['is_first_record']['start'] = self._io.pos()
            self.is_first_record = self._io.read_bits_int_be(1) != 0
            self._debug['is_first_record']['end'] = self._io.pos()
            self._debug['is_last_record']['start'] = self._io.pos()
            self.is_last_record = self._io.read_bits_int_be(1) != 0
            self._debug['is_last_record']['end'] = self._io.pos()
            self._debug['is_chunk_record']['start'] = self._io.pos()
            self.is_chunk_record = self._io.read_bits_int_be(1) != 0
            self._debug['is_chunk_record']['end'] = self._io.pos()
            self._debug['type_format']['start'] = self._io.pos()
            self.type_format = KaitaiStream.resolve_enum(DimeMessage.TypeFormats, self._io.read_bits_int_be(4))
            self._debug['type_format']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bits_int_be(4)
            self._debug['reserved']['end'] = self._io.pos()
            self._io.align_to_byte()
            self._debug['len_options']['start'] = self._io.pos()
            self.len_options = self._io.read_u2be()
            self._debug['len_options']['end'] = self._io.pos()
            self._debug['len_id']['start'] = self._io.pos()
            self.len_id = self._io.read_u2be()
            self._debug['len_id']['end'] = self._io.pos()
            self._debug['len_type']['start'] = self._io.pos()
            self.len_type = self._io.read_u2be()
            self._debug['len_type']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4be()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['options']['start'] = self._io.pos()
            self._raw_options = self._io.read_bytes(self.len_options)
            _io__raw_options = KaitaiStream(BytesIO(self._raw_options))
            self.options = DimeMessage.OptionField(_io__raw_options, self, self._root)
            self.options._read()
            self._debug['options']['end'] = self._io.pos()
            self._debug['options_padding']['start'] = self._io.pos()
            self.options_padding = DimeMessage.Padding(self._io, self, self._root)
            self.options_padding._read()
            self._debug['options_padding']['end'] = self._io.pos()
            self._debug['id']['start'] = self._io.pos()
            self.id = (self._io.read_bytes(self.len_id)).decode(u"ASCII")
            self._debug['id']['end'] = self._io.pos()
            self._debug['id_padding']['start'] = self._io.pos()
            self.id_padding = DimeMessage.Padding(self._io, self, self._root)
            self.id_padding._read()
            self._debug['id_padding']['end'] = self._io.pos()
            self._debug['type']['start'] = self._io.pos()
            self.type = (self._io.read_bytes(self.len_type)).decode(u"ASCII")
            self._debug['type']['end'] = self._io.pos()
            self._debug['type_padding']['start'] = self._io.pos()
            self.type_padding = DimeMessage.Padding(self._io, self, self._root)
            self.type_padding._read()
            self._debug['type_padding']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()
            self._debug['data_padding']['start'] = self._io.pos()
            self.data_padding = DimeMessage.Padding(self._io, self, self._root)
            self.data_padding._read()
            self._debug['data_padding']['end'] = self._io.pos()



