# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Msgpack(KaitaiStruct):
    """MessagePack (msgpack) is a system to serialize arbitrary structured
    data into a compact binary stream.
    
    .. seealso::
       Source - https://github.com/msgpack/msgpack/blob/master/spec.md
    """
    SEQ_FIELDS = ["b1", "int_extra", "float_32_value", "float_64_value", "str_len_8", "str_len_16", "str_len_32", "str_value", "num_array_elements_16", "num_array_elements_32", "array_elements", "num_map_elements_16", "num_map_elements_32", "map_elements"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Msgpack, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['b1']['start'] = self._io.pos()
        self.b1 = self._io.read_u1()
        self._debug['b1']['end'] = self._io.pos()
        self._debug['int_extra']['start'] = self._io.pos()
        _on = self.b1
        if _on == 204:
            pass
            self.int_extra = self._io.read_u1()
        elif _on == 205:
            pass
            self.int_extra = self._io.read_u2be()
        elif _on == 206:
            pass
            self.int_extra = self._io.read_u4be()
        elif _on == 207:
            pass
            self.int_extra = self._io.read_u8be()
        elif _on == 208:
            pass
            self.int_extra = self._io.read_s1()
        elif _on == 209:
            pass
            self.int_extra = self._io.read_s2be()
        elif _on == 210:
            pass
            self.int_extra = self._io.read_s4be()
        elif _on == 211:
            pass
            self.int_extra = self._io.read_s8be()
        self._debug['int_extra']['end'] = self._io.pos()
        if self.is_float_32:
            pass
            self._debug['float_32_value']['start'] = self._io.pos()
            self.float_32_value = self._io.read_f4be()
            self._debug['float_32_value']['end'] = self._io.pos()

        if self.is_float_64:
            pass
            self._debug['float_64_value']['start'] = self._io.pos()
            self.float_64_value = self._io.read_f8be()
            self._debug['float_64_value']['end'] = self._io.pos()

        if self.is_str_8:
            pass
            self._debug['str_len_8']['start'] = self._io.pos()
            self.str_len_8 = self._io.read_u1()
            self._debug['str_len_8']['end'] = self._io.pos()

        if self.is_str_16:
            pass
            self._debug['str_len_16']['start'] = self._io.pos()
            self.str_len_16 = self._io.read_u2be()
            self._debug['str_len_16']['end'] = self._io.pos()

        if self.is_str_32:
            pass
            self._debug['str_len_32']['start'] = self._io.pos()
            self.str_len_32 = self._io.read_u4be()
            self._debug['str_len_32']['end'] = self._io.pos()

        if self.is_str:
            pass
            self._debug['str_value']['start'] = self._io.pos()
            self.str_value = (self._io.read_bytes(self.str_len)).decode(u"UTF-8")
            self._debug['str_value']['end'] = self._io.pos()

        if self.is_array_16:
            pass
            self._debug['num_array_elements_16']['start'] = self._io.pos()
            self.num_array_elements_16 = self._io.read_u2be()
            self._debug['num_array_elements_16']['end'] = self._io.pos()

        if self.is_array_32:
            pass
            self._debug['num_array_elements_32']['start'] = self._io.pos()
            self.num_array_elements_32 = self._io.read_u4be()
            self._debug['num_array_elements_32']['end'] = self._io.pos()

        if self.is_array:
            pass
            self._debug['array_elements']['start'] = self._io.pos()
            self._debug['array_elements']['arr'] = []
            self.array_elements = []
            for i in range(self.num_array_elements):
                self._debug['array_elements']['arr'].append({'start': self._io.pos()})
                _t_array_elements = Msgpack(self._io, self, self._root)
                try:
                    _t_array_elements._read()
                finally:
                    self.array_elements.append(_t_array_elements)
                self._debug['array_elements']['arr'][i]['end'] = self._io.pos()

            self._debug['array_elements']['end'] = self._io.pos()

        if self.is_map_16:
            pass
            self._debug['num_map_elements_16']['start'] = self._io.pos()
            self.num_map_elements_16 = self._io.read_u2be()
            self._debug['num_map_elements_16']['end'] = self._io.pos()

        if self.is_map_32:
            pass
            self._debug['num_map_elements_32']['start'] = self._io.pos()
            self.num_map_elements_32 = self._io.read_u4be()
            self._debug['num_map_elements_32']['end'] = self._io.pos()

        if self.is_map:
            pass
            self._debug['map_elements']['start'] = self._io.pos()
            self._debug['map_elements']['arr'] = []
            self.map_elements = []
            for i in range(self.num_map_elements):
                self._debug['map_elements']['arr'].append({'start': self._io.pos()})
                _t_map_elements = Msgpack.MapTuple(self._io, self, self._root)
                try:
                    _t_map_elements._read()
                finally:
                    self.map_elements.append(_t_map_elements)
                self._debug['map_elements']['arr'][i]['end'] = self._io.pos()

            self._debug['map_elements']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        _on = self.b1
        if _on == 204:
            pass
        elif _on == 205:
            pass
        elif _on == 206:
            pass
        elif _on == 207:
            pass
        elif _on == 208:
            pass
        elif _on == 209:
            pass
        elif _on == 210:
            pass
        elif _on == 211:
            pass
        if self.is_float_32:
            pass

        if self.is_float_64:
            pass

        if self.is_str_8:
            pass

        if self.is_str_16:
            pass

        if self.is_str_32:
            pass

        if self.is_str:
            pass

        if self.is_array_16:
            pass

        if self.is_array_32:
            pass

        if self.is_array:
            pass
            for i in range(len(self.array_elements)):
                pass
                self.array_elements[i]._fetch_instances()


        if self.is_map_16:
            pass

        if self.is_map_32:
            pass

        if self.is_map:
            pass
            for i in range(len(self.map_elements)):
                pass
                self.map_elements[i]._fetch_instances()



    class MapTuple(KaitaiStruct):
        SEQ_FIELDS = ["key", "value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Msgpack.MapTuple, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['key']['start'] = self._io.pos()
            self.key = Msgpack(self._io, self, self._root)
            self.key._read()
            self._debug['key']['end'] = self._io.pos()
            self._debug['value']['start'] = self._io.pos()
            self.value = Msgpack(self._io, self, self._root)
            self.value._read()
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.key._fetch_instances()
            self.value._fetch_instances()


    @property
    def bool_value(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-bool
        """
        if hasattr(self, '_m_bool_value'):
            return self._m_bool_value

        if self.is_bool:
            pass
            self._m_bool_value = self.b1 == 195

        return getattr(self, '_m_bool_value', None)

    @property
    def float_value(self):
        if hasattr(self, '_m_float_value'):
            return self._m_float_value

        if self.is_float:
            pass
            self._m_float_value = (self.float_32_value if self.is_float_32 else self.float_64_value)

        return getattr(self, '_m_float_value', None)

    @property
    def int_value(self):
        if hasattr(self, '_m_int_value'):
            return self._m_int_value

        if self.is_int:
            pass
            self._m_int_value = (self.pos_int7_value if self.is_pos_int7 else (self.neg_int5_value if self.is_neg_int5 else 4919))

        return getattr(self, '_m_int_value', None)

    @property
    def is_array(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-array
        """
        if hasattr(self, '_m_is_array'):
            return self._m_is_array

        self._m_is_array =  ((self.is_fix_array) or (self.is_array_16) or (self.is_array_32)) 
        return getattr(self, '_m_is_array', None)

    @property
    def is_array_16(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-array
        """
        if hasattr(self, '_m_is_array_16'):
            return self._m_is_array_16

        self._m_is_array_16 = self.b1 == 220
        return getattr(self, '_m_is_array_16', None)

    @property
    def is_array_32(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-array
        """
        if hasattr(self, '_m_is_array_32'):
            return self._m_is_array_32

        self._m_is_array_32 = self.b1 == 221
        return getattr(self, '_m_is_array_32', None)

    @property
    def is_bool(self):
        if hasattr(self, '_m_is_bool'):
            return self._m_is_bool

        self._m_is_bool =  ((self.b1 == 194) or (self.b1 == 195)) 
        return getattr(self, '_m_is_bool', None)

    @property
    def is_fix_array(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-array
        """
        if hasattr(self, '_m_is_fix_array'):
            return self._m_is_fix_array

        self._m_is_fix_array = self.b1 & 240 == 144
        return getattr(self, '_m_is_fix_array', None)

    @property
    def is_fix_map(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-map
        """
        if hasattr(self, '_m_is_fix_map'):
            return self._m_is_fix_map

        self._m_is_fix_map = self.b1 & 240 == 128
        return getattr(self, '_m_is_fix_map', None)

    @property
    def is_fix_str(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-str
        """
        if hasattr(self, '_m_is_fix_str'):
            return self._m_is_fix_str

        self._m_is_fix_str = self.b1 & 224 == 160
        return getattr(self, '_m_is_fix_str', None)

    @property
    def is_float(self):
        if hasattr(self, '_m_is_float'):
            return self._m_is_float

        self._m_is_float =  ((self.is_float_32) or (self.is_float_64)) 
        return getattr(self, '_m_is_float', None)

    @property
    def is_float_32(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-float
        """
        if hasattr(self, '_m_is_float_32'):
            return self._m_is_float_32

        self._m_is_float_32 = self.b1 == 202
        return getattr(self, '_m_is_float_32', None)

    @property
    def is_float_64(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-float
        """
        if hasattr(self, '_m_is_float_64'):
            return self._m_is_float_64

        self._m_is_float_64 = self.b1 == 203
        return getattr(self, '_m_is_float_64', None)

    @property
    def is_int(self):
        if hasattr(self, '_m_is_int'):
            return self._m_is_int

        self._m_is_int =  ((self.is_pos_int7) or (self.is_neg_int5)) 
        return getattr(self, '_m_is_int', None)

    @property
    def is_map(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-map
        """
        if hasattr(self, '_m_is_map'):
            return self._m_is_map

        self._m_is_map =  ((self.is_fix_map) or (self.is_map_16) or (self.is_map_32)) 
        return getattr(self, '_m_is_map', None)

    @property
    def is_map_16(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-map
        """
        if hasattr(self, '_m_is_map_16'):
            return self._m_is_map_16

        self._m_is_map_16 = self.b1 == 222
        return getattr(self, '_m_is_map_16', None)

    @property
    def is_map_32(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-map
        """
        if hasattr(self, '_m_is_map_32'):
            return self._m_is_map_32

        self._m_is_map_32 = self.b1 == 223
        return getattr(self, '_m_is_map_32', None)

    @property
    def is_neg_int5(self):
        if hasattr(self, '_m_is_neg_int5'):
            return self._m_is_neg_int5

        self._m_is_neg_int5 = self.b1 & 224 == 224
        return getattr(self, '_m_is_neg_int5', None)

    @property
    def is_nil(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-nil
        """
        if hasattr(self, '_m_is_nil'):
            return self._m_is_nil

        self._m_is_nil = self.b1 == 192
        return getattr(self, '_m_is_nil', None)

    @property
    def is_pos_int7(self):
        if hasattr(self, '_m_is_pos_int7'):
            return self._m_is_pos_int7

        self._m_is_pos_int7 = self.b1 & 128 == 0
        return getattr(self, '_m_is_pos_int7', None)

    @property
    def is_str(self):
        if hasattr(self, '_m_is_str'):
            return self._m_is_str

        self._m_is_str =  ((self.is_fix_str) or (self.is_str_8) or (self.is_str_16) or (self.is_str_32)) 
        return getattr(self, '_m_is_str', None)

    @property
    def is_str_16(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-str
        """
        if hasattr(self, '_m_is_str_16'):
            return self._m_is_str_16

        self._m_is_str_16 = self.b1 == 218
        return getattr(self, '_m_is_str_16', None)

    @property
    def is_str_32(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-str
        """
        if hasattr(self, '_m_is_str_32'):
            return self._m_is_str_32

        self._m_is_str_32 = self.b1 == 219
        return getattr(self, '_m_is_str_32', None)

    @property
    def is_str_8(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-str
        """
        if hasattr(self, '_m_is_str_8'):
            return self._m_is_str_8

        self._m_is_str_8 = self.b1 == 217
        return getattr(self, '_m_is_str_8', None)

    @property
    def neg_int5_value(self):
        if hasattr(self, '_m_neg_int5_value'):
            return self._m_neg_int5_value

        if self.is_neg_int5:
            pass
            self._m_neg_int5_value = -(self.b1 & 31)

        return getattr(self, '_m_neg_int5_value', None)

    @property
    def num_array_elements(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-array
        """
        if hasattr(self, '_m_num_array_elements'):
            return self._m_num_array_elements

        if self.is_array:
            pass
            self._m_num_array_elements = (self.b1 & 15 if self.is_fix_array else (self.num_array_elements_16 if self.is_array_16 else self.num_array_elements_32))

        return getattr(self, '_m_num_array_elements', None)

    @property
    def num_map_elements(self):
        """
        .. seealso::
           Source - https://github.com/msgpack/msgpack/blob/master/spec.md#formats-map
        """
        if hasattr(self, '_m_num_map_elements'):
            return self._m_num_map_elements

        if self.is_map:
            pass
            self._m_num_map_elements = (self.b1 & 15 if self.is_fix_map else (self.num_map_elements_16 if self.is_map_16 else self.num_map_elements_32))

        return getattr(self, '_m_num_map_elements', None)

    @property
    def pos_int7_value(self):
        if hasattr(self, '_m_pos_int7_value'):
            return self._m_pos_int7_value

        if self.is_pos_int7:
            pass
            self._m_pos_int7_value = self.b1

        return getattr(self, '_m_pos_int7_value', None)

    @property
    def str_len(self):
        if hasattr(self, '_m_str_len'):
            return self._m_str_len

        if self.is_str:
            pass
            self._m_str_len = (self.b1 & 31 if self.is_fix_str else (self.str_len_8 if self.is_str_8 else (self.str_len_16 if self.is_str_16 else self.str_len_32)))

        return getattr(self, '_m_str_len', None)


