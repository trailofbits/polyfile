# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class RubyMarshal(KaitaiStruct):
    """Ruby's Marshal module allows serialization and deserialization of
    many standard and arbitrary Ruby objects in a compact binary
    format. It is relatively fast, available in stdlibs standard and
    allows conservation of language-specific properties (such as symbols
    or encoding-aware strings).
    
    Feature-wise, it is comparable to other language-specific
    implementations, such as:
    
    * Java's
      [Serializable](https://docs.oracle.com/javase/8/docs/api/java/io/Serializable.html)
    * .NET
      [BinaryFormatter](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.serialization.formatters.binary.binaryformatter?view=net-7.0)
    * Python's
      [marshal](https://docs.python.org/3/library/marshal.html),
      [pickle](https://docs.python.org/3/library/pickle.html) and
      [shelve](https://docs.python.org/3/library/shelve.html)
    
    From internal perspective, serialized stream consists of a simple
    magic header and a record.
    
    .. seealso::
       Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Stream+Format
    """

    class Codes(IntEnum):
        ruby_string = 34
        const_nil = 48
        ruby_symbol = 58
        ruby_symbol_link = 59
        ruby_object_link = 64
        const_false = 70
        instance_var = 73
        ruby_struct = 83
        const_true = 84
        ruby_array = 91
        packed_int = 105
        bignum = 108
        ruby_hash = 123
    SEQ_FIELDS = ["version", "records"]
    def __init__(self, _io, _parent=None, _root=None):
        super(RubyMarshal, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_bytes(2)
        self._debug['version']['end'] = self._io.pos()
        if not self.version == b"\x04\x08":
            raise kaitaistruct.ValidationNotEqualError(b"\x04\x08", self.version, self._io, u"/seq/0")
        self._debug['records']['start'] = self._io.pos()
        self.records = RubyMarshal.Record(self._io, self, self._root)
        self.records._read()
        self._debug['records']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.records._fetch_instances()

    class Bignum(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Bignum
        """
        SEQ_FIELDS = ["sign", "len_div_2", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.Bignum, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['sign']['start'] = self._io.pos()
            self.sign = self._io.read_u1()
            self._debug['sign']['end'] = self._io.pos()
            self._debug['len_div_2']['start'] = self._io.pos()
            self.len_div_2 = RubyMarshal.PackedInt(self._io, self, self._root)
            self.len_div_2._read()
            self._debug['len_div_2']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes(self.len_div_2.value * 2)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.len_div_2._fetch_instances()


    class InstanceVar(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Instance+Variables
        """
        SEQ_FIELDS = ["obj", "num_vars", "vars"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.InstanceVar, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['obj']['start'] = self._io.pos()
            self.obj = RubyMarshal.Record(self._io, self, self._root)
            self.obj._read()
            self._debug['obj']['end'] = self._io.pos()
            self._debug['num_vars']['start'] = self._io.pos()
            self.num_vars = RubyMarshal.PackedInt(self._io, self, self._root)
            self.num_vars._read()
            self._debug['num_vars']['end'] = self._io.pos()
            self._debug['vars']['start'] = self._io.pos()
            self._debug['vars']['arr'] = []
            self.vars = []
            for i in range(self.num_vars.value):
                self._debug['vars']['arr'].append({'start': self._io.pos()})
                _t_vars = RubyMarshal.Pair(self._io, self, self._root)
                try:
                    _t_vars._read()
                finally:
                    self.vars.append(_t_vars)
                self._debug['vars']['arr'][i]['end'] = self._io.pos()

            self._debug['vars']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.obj._fetch_instances()
            self.num_vars._fetch_instances()
            for i in range(len(self.vars)):
                pass
                self.vars[i]._fetch_instances()



    class PackedInt(KaitaiStruct):
        """Ruby uses sophisticated system to pack integers: first `code`
        byte either determines packing scheme or carries encoded
        immediate value (thus allowing smaller values from -123 to 122
        (inclusive) to take only one byte. There are 11 encoding schemes
        in total:
        
        * 0 is encoded specially (as 0)
        * 1..122 are encoded as immediate value with a shift
        * 123..255 are encoded with code of 0x01 and 1 extra byte
        * 0x100..0xffff are encoded with code of 0x02 and 2 extra bytes
        * 0x10000..0xffffff are encoded with code of 0x03 and 3 extra
          bytes
        * 0x1000000..0xffffffff are encoded with code of 0x04 and 4
          extra bytes
        * -123..-1 are encoded as immediate value with another shift
        * -256..-124 are encoded with code of 0xff and 1 extra byte
        * -0x10000..-257 are encoded with code of 0xfe and 2 extra bytes
        * -0x1000000..0x10001 are encoded with code of 0xfd and 3 extra
           bytes
        * -0x40000000..-0x1000001 are encoded with code of 0xfc and 4
           extra bytes
        
        Values beyond that are serialized as bignum (even if they
        technically might be not Bignum class in Ruby implementation,
        i.e. if they fit into 64 bits on a 64-bit platform).
        
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Fixnum+and+long
        """
        SEQ_FIELDS = ["code", "encoded", "encoded2"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.PackedInt, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = self._io.read_u1()
            self._debug['code']['end'] = self._io.pos()
            self._debug['encoded']['start'] = self._io.pos()
            _on = self.code
            if _on == 1:
                pass
                self.encoded = self._io.read_u1()
            elif _on == 2:
                pass
                self.encoded = self._io.read_u2le()
            elif _on == 252:
                pass
                self.encoded = self._io.read_u4le()
            elif _on == 253:
                pass
                self.encoded = self._io.read_u2le()
            elif _on == 254:
                pass
                self.encoded = self._io.read_u2le()
            elif _on == 255:
                pass
                self.encoded = self._io.read_u1()
            elif _on == 3:
                pass
                self.encoded = self._io.read_u2le()
            elif _on == 4:
                pass
                self.encoded = self._io.read_u4le()
            self._debug['encoded']['end'] = self._io.pos()
            self._debug['encoded2']['start'] = self._io.pos()
            _on = self.code
            if _on == 253:
                pass
                self.encoded2 = self._io.read_u1()
            elif _on == 3:
                pass
                self.encoded2 = self._io.read_u1()
            self._debug['encoded2']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.code
            if _on == 1:
                pass
            elif _on == 2:
                pass
            elif _on == 252:
                pass
            elif _on == 253:
                pass
            elif _on == 254:
                pass
            elif _on == 255:
                pass
            elif _on == 3:
                pass
            elif _on == 4:
                pass
            _on = self.code
            if _on == 253:
                pass
            elif _on == 3:
                pass

        @property
        def is_immediate(self):
            if hasattr(self, '_m_is_immediate'):
                return self._m_is_immediate

            self._m_is_immediate =  ((self.code > 4) and (self.code < 252)) 
            return getattr(self, '_m_is_immediate', None)

        @property
        def value(self):
            if hasattr(self, '_m_value'):
                return self._m_value

            self._m_value = ((self.code - 5 if self.code < 128 else 4 - (~(self.code) & 127)) if self.is_immediate else (0 if self.code == 0 else (self.encoded - 256 if self.code == 255 else (self.encoded - 65536 if self.code == 254 else ((self.encoded2 << 16 | self.encoded) - 16777216 if self.code == 253 else (self.encoded2 << 16 | self.encoded if self.code == 3 else self.encoded))))))
            return getattr(self, '_m_value', None)


    class Pair(KaitaiStruct):
        SEQ_FIELDS = ["key", "value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.Pair, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['key']['start'] = self._io.pos()
            self.key = RubyMarshal.Record(self._io, self, self._root)
            self.key._read()
            self._debug['key']['end'] = self._io.pos()
            self._debug['value']['start'] = self._io.pos()
            self.value = RubyMarshal.Record(self._io, self, self._root)
            self.value._read()
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.key._fetch_instances()
            self.value._fetch_instances()


    class Record(KaitaiStruct):
        """Each record starts with a single byte that determines its type
        (`code`) and contents. If necessary, additional info as parsed
        as `body`, to be determined by `code`.
        """
        SEQ_FIELDS = ["code", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.Record, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = KaitaiStream.resolve_enum(RubyMarshal.Codes, self._io.read_u1())
            self._debug['code']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.code
            if _on == RubyMarshal.Codes.bignum:
                pass
                self.body = RubyMarshal.Bignum(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.instance_var:
                pass
                self.body = RubyMarshal.InstanceVar(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.packed_int:
                pass
                self.body = RubyMarshal.PackedInt(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_array:
                pass
                self.body = RubyMarshal.RubyArray(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_hash:
                pass
                self.body = RubyMarshal.RubyHash(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_object_link:
                pass
                self.body = RubyMarshal.PackedInt(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_string:
                pass
                self.body = RubyMarshal.RubyString(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_struct:
                pass
                self.body = RubyMarshal.RubyStruct(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_symbol:
                pass
                self.body = RubyMarshal.RubySymbol(self._io, self, self._root)
                self.body._read()
            elif _on == RubyMarshal.Codes.ruby_symbol_link:
                pass
                self.body = RubyMarshal.PackedInt(self._io, self, self._root)
                self.body._read()
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.code
            if _on == RubyMarshal.Codes.bignum:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.instance_var:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.packed_int:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_array:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_hash:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_object_link:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_string:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_struct:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_symbol:
                pass
                self.body._fetch_instances()
            elif _on == RubyMarshal.Codes.ruby_symbol_link:
                pass
                self.body._fetch_instances()


    class RubyArray(KaitaiStruct):
        SEQ_FIELDS = ["num_elements", "elements"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.RubyArray, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_elements']['start'] = self._io.pos()
            self.num_elements = RubyMarshal.PackedInt(self._io, self, self._root)
            self.num_elements._read()
            self._debug['num_elements']['end'] = self._io.pos()
            self._debug['elements']['start'] = self._io.pos()
            self._debug['elements']['arr'] = []
            self.elements = []
            for i in range(self.num_elements.value):
                self._debug['elements']['arr'].append({'start': self._io.pos()})
                _t_elements = RubyMarshal.Record(self._io, self, self._root)
                try:
                    _t_elements._read()
                finally:
                    self.elements.append(_t_elements)
                self._debug['elements']['arr'][i]['end'] = self._io.pos()

            self._debug['elements']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.num_elements._fetch_instances()
            for i in range(len(self.elements)):
                pass
                self.elements[i]._fetch_instances()



    class RubyHash(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Hash+and+Hash+with+Default+Value
        """
        SEQ_FIELDS = ["num_pairs", "pairs"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.RubyHash, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_pairs']['start'] = self._io.pos()
            self.num_pairs = RubyMarshal.PackedInt(self._io, self, self._root)
            self.num_pairs._read()
            self._debug['num_pairs']['end'] = self._io.pos()
            self._debug['pairs']['start'] = self._io.pos()
            self._debug['pairs']['arr'] = []
            self.pairs = []
            for i in range(self.num_pairs.value):
                self._debug['pairs']['arr'].append({'start': self._io.pos()})
                _t_pairs = RubyMarshal.Pair(self._io, self, self._root)
                try:
                    _t_pairs._read()
                finally:
                    self.pairs.append(_t_pairs)
                self._debug['pairs']['arr'][i]['end'] = self._io.pos()

            self._debug['pairs']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.num_pairs._fetch_instances()
            for i in range(len(self.pairs)):
                pass
                self.pairs[i]._fetch_instances()



    class RubyString(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-String
        """
        SEQ_FIELDS = ["len", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.RubyString, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = RubyMarshal.PackedInt(self._io, self, self._root)
            self.len._read()
            self._debug['len']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes(self.len.value)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.len._fetch_instances()


    class RubyStruct(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Struct
        """
        SEQ_FIELDS = ["name", "num_members", "members"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.RubyStruct, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = RubyMarshal.Record(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['num_members']['start'] = self._io.pos()
            self.num_members = RubyMarshal.PackedInt(self._io, self, self._root)
            self.num_members._read()
            self._debug['num_members']['end'] = self._io.pos()
            self._debug['members']['start'] = self._io.pos()
            self._debug['members']['arr'] = []
            self.members = []
            for i in range(self.num_members.value):
                self._debug['members']['arr'].append({'start': self._io.pos()})
                _t_members = RubyMarshal.Pair(self._io, self, self._root)
                try:
                    _t_members._read()
                finally:
                    self.members.append(_t_members)
                self._debug['members']['arr'][i]['end'] = self._io.pos()

            self._debug['members']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.num_members._fetch_instances()
            for i in range(len(self.members)):
                pass
                self.members[i]._fetch_instances()



    class RubySymbol(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.ruby-lang.org/en/2.4.0/marshal_rdoc.html#label-Symbols+and+Byte+Sequence
        """
        SEQ_FIELDS = ["len", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RubyMarshal.RubySymbol, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = RubyMarshal.PackedInt(self._io, self, self._root)
            self.len._read()
            self._debug['len']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes(self.len.value)).decode(u"UTF-8")
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.len._fetch_instances()



