# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Bson(KaitaiStruct):
    """BSON, short for Binary JSON, is a binary-encoded serialization of JSON-like documents. Like JSON, BSON supports the embedding of documents and arrays within other documents and arrays. BSON also contains extensions that allow representation of data types that are not part of the JSON spec. For example, BSON has a Date type and a BinData type. BSON can be compared to binary interchange formats, like Protocol Buffers. BSON is more "schemaless" than Protocol Buffers, which can give it an advantage in flexibility but also a slight disadvantage in space efficiency (BSON has overhead for field names within the serialized data). BSON was designed to have the following three characteristics:
      * Lightweight. Keeping spatial overhead to a minimum is important for any data representation format, especially when used over the network.
      * Traversable. BSON is designed to be traversed easily. This is a vital property in its role as the primary data representation for MongoDB.
      * Efficient. Encoding data to BSON and decoding from BSON can be performed very quickly in most languages due to the use of C data types.
    """
    SEQ_FIELDS = ["len", "fields", "terminator"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Bson, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['len']['start'] = self._io.pos()
        self.len = self._io.read_s4le()
        self._debug['len']['end'] = self._io.pos()
        self._debug['fields']['start'] = self._io.pos()
        self._raw_fields = self._io.read_bytes(self.len - 5)
        _io__raw_fields = KaitaiStream(BytesIO(self._raw_fields))
        self.fields = Bson.ElementsList(_io__raw_fields, self, self._root)
        self.fields._read()
        self._debug['fields']['end'] = self._io.pos()
        self._debug['terminator']['start'] = self._io.pos()
        self.terminator = self._io.read_bytes(1)
        self._debug['terminator']['end'] = self._io.pos()
        if not self.terminator == b"\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x00", self.terminator, self._io, u"/seq/2")


    def _fetch_instances(self):
        pass
        self.fields._fetch_instances()

    class BinData(KaitaiStruct):
        """The BSON "binary" or "BinData" datatype is used to represent arrays of bytes. It is somewhat analogous to the Java notion of a ByteArray. BSON binary values have a subtype. This is used to indicate what kind of data is in the byte array. Subtypes from zero to 127 are predefined or reserved. Subtypes from 128-255 are user-defined."""

        class Subtype(IntEnum):
            generic = 0
            function = 1
            byte_array_deprecated = 2
            uuid_deprecated = 3
            uuid = 4
            md5 = 5
            custom = 128
        SEQ_FIELDS = ["len", "subtype", "content"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.BinData, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_s4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['subtype']['start'] = self._io.pos()
            self.subtype = KaitaiStream.resolve_enum(Bson.BinData.Subtype, self._io.read_u1())
            self._debug['subtype']['end'] = self._io.pos()
            self._debug['content']['start'] = self._io.pos()
            _on = self.subtype
            if _on == Bson.BinData.Subtype.byte_array_deprecated:
                pass
                self._raw_content = self._io.read_bytes(self.len)
                _io__raw_content = KaitaiStream(BytesIO(self._raw_content))
                self.content = Bson.BinData.ByteArrayDeprecated(_io__raw_content, self, self._root)
                self.content._read()
            else:
                pass
                self.content = self._io.read_bytes(self.len)
            self._debug['content']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.subtype
            if _on == Bson.BinData.Subtype.byte_array_deprecated:
                pass
                self.content._fetch_instances()
            else:
                pass

        class ByteArrayDeprecated(KaitaiStruct):
            """The BSON "binary" or "BinData" datatype is used to represent arrays of bytes. It is somewhat analogous to the Java notion of a ByteArray. BSON binary values have a subtype. This is used to indicate what kind of data is in the byte array. Subtypes from zero to 127 are predefined or reserved. Subtypes from 128-255 are user-defined."""
            SEQ_FIELDS = ["len", "content"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Bson.BinData.ByteArrayDeprecated, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['len']['start'] = self._io.pos()
                self.len = self._io.read_s4le()
                self._debug['len']['end'] = self._io.pos()
                self._debug['content']['start'] = self._io.pos()
                self.content = self._io.read_bytes(self.len)
                self._debug['content']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass



    class CodeWithScope(KaitaiStruct):
        SEQ_FIELDS = ["id", "source", "scope"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.CodeWithScope, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_s4le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['source']['start'] = self._io.pos()
            self.source = Bson.String(self._io, self, self._root)
            self.source._read()
            self._debug['source']['end'] = self._io.pos()
            self._debug['scope']['start'] = self._io.pos()
            self.scope = Bson(self._io, self, self._root)
            self.scope._read()
            self._debug['scope']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.source._fetch_instances()
            self.scope._fetch_instances()


    class Cstring(KaitaiStruct):
        SEQ_FIELDS = ["str"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.Cstring, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class DbPointer(KaitaiStruct):
        SEQ_FIELDS = ["namespace", "id"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.DbPointer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['namespace']['start'] = self._io.pos()
            self.namespace = Bson.String(self._io, self, self._root)
            self.namespace._read()
            self._debug['namespace']['end'] = self._io.pos()
            self._debug['id']['start'] = self._io.pos()
            self.id = Bson.ObjectId(self._io, self, self._root)
            self.id._read()
            self._debug['id']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.namespace._fetch_instances()
            self.id._fetch_instances()


    class Element(KaitaiStruct):

        class BsonType(IntEnum):
            min_key = -1
            end_of_object = 0
            number_double = 1
            string = 2
            document = 3
            array = 4
            bin_data = 5
            undefined = 6
            object_id = 7
            boolean = 8
            utc_datetime = 9
            jst_null = 10
            reg_ex = 11
            db_pointer = 12
            javascript = 13
            symbol = 14
            code_with_scope = 15
            number_int = 16
            timestamp = 17
            number_long = 18
            number_decimal = 19
            max_key = 127
        SEQ_FIELDS = ["type_byte", "name", "content"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.Element, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type_byte']['start'] = self._io.pos()
            self.type_byte = KaitaiStream.resolve_enum(Bson.Element.BsonType, self._io.read_u1())
            self._debug['type_byte']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = Bson.Cstring(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['content']['start'] = self._io.pos()
            _on = self.type_byte
            if _on == Bson.Element.BsonType.array:
                pass
                self.content = Bson(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.bin_data:
                pass
                self.content = Bson.BinData(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.boolean:
                pass
                self.content = self._io.read_u1()
            elif _on == Bson.Element.BsonType.code_with_scope:
                pass
                self.content = Bson.CodeWithScope(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.db_pointer:
                pass
                self.content = Bson.DbPointer(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.document:
                pass
                self.content = Bson(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.javascript:
                pass
                self.content = Bson.String(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.number_decimal:
                pass
                self.content = Bson.F16(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.number_double:
                pass
                self.content = self._io.read_f8le()
            elif _on == Bson.Element.BsonType.number_int:
                pass
                self.content = self._io.read_s4le()
            elif _on == Bson.Element.BsonType.number_long:
                pass
                self.content = self._io.read_s8le()
            elif _on == Bson.Element.BsonType.object_id:
                pass
                self.content = Bson.ObjectId(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.reg_ex:
                pass
                self.content = Bson.RegEx(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.string:
                pass
                self.content = Bson.String(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.symbol:
                pass
                self.content = Bson.String(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.timestamp:
                pass
                self.content = Bson.Timestamp(self._io, self, self._root)
                self.content._read()
            elif _on == Bson.Element.BsonType.utc_datetime:
                pass
                self.content = self._io.read_s8le()
            self._debug['content']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            _on = self.type_byte
            if _on == Bson.Element.BsonType.array:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.bin_data:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.boolean:
                pass
            elif _on == Bson.Element.BsonType.code_with_scope:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.db_pointer:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.document:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.javascript:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.number_decimal:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.number_double:
                pass
            elif _on == Bson.Element.BsonType.number_int:
                pass
            elif _on == Bson.Element.BsonType.number_long:
                pass
            elif _on == Bson.Element.BsonType.object_id:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.reg_ex:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.string:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.symbol:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.timestamp:
                pass
                self.content._fetch_instances()
            elif _on == Bson.Element.BsonType.utc_datetime:
                pass


    class ElementsList(KaitaiStruct):
        SEQ_FIELDS = ["elements"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.ElementsList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['elements']['start'] = self._io.pos()
            self._debug['elements']['arr'] = []
            self.elements = []
            i = 0
            while not self._io.is_eof():
                self._debug['elements']['arr'].append({'start': self._io.pos()})
                _t_elements = Bson.Element(self._io, self, self._root)
                try:
                    _t_elements._read()
                finally:
                    self.elements.append(_t_elements)
                self._debug['elements']['arr'][len(self.elements) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['elements']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.elements)):
                pass
                self.elements[i]._fetch_instances()



    class F16(KaitaiStruct):
        """128-bit IEEE 754-2008 decimal floating point."""
        SEQ_FIELDS = ["str", "exponent", "significand_hi", "significand_lo"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.F16, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['str']['start'] = self._io.pos()
            self.str = self._io.read_bits_int_be(1) != 0
            self._debug['str']['end'] = self._io.pos()
            self._debug['exponent']['start'] = self._io.pos()
            self.exponent = self._io.read_bits_int_be(15)
            self._debug['exponent']['end'] = self._io.pos()
            self._debug['significand_hi']['start'] = self._io.pos()
            self.significand_hi = self._io.read_bits_int_be(49)
            self._debug['significand_hi']['end'] = self._io.pos()
            self._debug['significand_lo']['start'] = self._io.pos()
            self.significand_lo = self._io.read_u8le()
            self._debug['significand_lo']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class ObjectId(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.mongodb.com/docs/manual/reference/method/ObjectId/
        """
        SEQ_FIELDS = ["epoch_time", "machine_id", "process_id", "counter"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.ObjectId, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['epoch_time']['start'] = self._io.pos()
            self.epoch_time = self._io.read_u4le()
            self._debug['epoch_time']['end'] = self._io.pos()
            self._debug['machine_id']['start'] = self._io.pos()
            self.machine_id = Bson.U3(self._io, self, self._root)
            self.machine_id._read()
            self._debug['machine_id']['end'] = self._io.pos()
            self._debug['process_id']['start'] = self._io.pos()
            self.process_id = self._io.read_u2le()
            self._debug['process_id']['end'] = self._io.pos()
            self._debug['counter']['start'] = self._io.pos()
            self.counter = Bson.U3(self._io, self, self._root)
            self.counter._read()
            self._debug['counter']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.machine_id._fetch_instances()
            self.counter._fetch_instances()


    class RegEx(KaitaiStruct):
        SEQ_FIELDS = ["pattern", "options"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.RegEx, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['pattern']['start'] = self._io.pos()
            self.pattern = Bson.Cstring(self._io, self, self._root)
            self.pattern._read()
            self._debug['pattern']['end'] = self._io.pos()
            self._debug['options']['start'] = self._io.pos()
            self.options = Bson.Cstring(self._io, self, self._root)
            self.options._read()
            self._debug['options']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.pattern._fetch_instances()
            self.options._fetch_instances()


    class String(KaitaiStruct):
        SEQ_FIELDS = ["len", "str", "terminator"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.String, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_s4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes(self.len - 1)).decode(u"UTF-8")
            self._debug['str']['end'] = self._io.pos()
            self._debug['terminator']['start'] = self._io.pos()
            self.terminator = self._io.read_bytes(1)
            self._debug['terminator']['end'] = self._io.pos()
            if not self.terminator == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.terminator, self._io, u"/types/string/seq/2")


        def _fetch_instances(self):
            pass


    class Timestamp(KaitaiStruct):
        """Special internal type used by MongoDB replication and sharding. First 4 bytes are an increment, second 4 are a timestamp."""
        SEQ_FIELDS = ["increment", "timestamp"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.Timestamp, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['increment']['start'] = self._io.pos()
            self.increment = self._io.read_u4le()
            self._debug['increment']['end'] = self._io.pos()
            self._debug['timestamp']['start'] = self._io.pos()
            self.timestamp = self._io.read_u4le()
            self._debug['timestamp']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class U3(KaitaiStruct):
        """Implements unsigned 24-bit (3 byte) integer.
        """
        SEQ_FIELDS = ["b1", "b2", "b3"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Bson.U3, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['b1']['start'] = self._io.pos()
            self.b1 = self._io.read_u1()
            self._debug['b1']['end'] = self._io.pos()
            self._debug['b2']['start'] = self._io.pos()
            self.b2 = self._io.read_u1()
            self._debug['b2']['end'] = self._io.pos()
            self._debug['b3']['start'] = self._io.pos()
            self.b3 = self._io.read_u1()
            self._debug['b3']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def value(self):
            if hasattr(self, '_m_value'):
                return self._m_value

            self._m_value = (self.b1 | self.b2 << 8) | self.b3 << 16
            return getattr(self, '_m_value', None)



