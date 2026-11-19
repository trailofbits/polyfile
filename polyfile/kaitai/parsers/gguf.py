# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Gguf(KaitaiStruct):
    """GGUF is the file format of the [ggml](https://github.com/ggml-org/ggml)
    tensor library for storing machine learning models, used for example by
    [llama.cpp](https://github.com/ggml-org/llama.cpp) for inference. It
    replaced the older GGML, GGMF and GGJT formats.
    
    A GGUF file consists of a header with metadata as key-value pairs (model
    architecture, hyperparameters, tokenizer, etc.), a description of each
    tensor (name, dimensions, type and offset), and finally the tensor data.
    
    .. seealso::
       Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md
    """

    class GgmlType(IntEnum):
        f32 = 0
        f16 = 1
        q4_0 = 2
        q4_1 = 3
        q4_2 = 4
        q4_3 = 5
        q5_0 = 6
        q5_1 = 7
        q8_0 = 8
        q8_1 = 9
        q2_k = 10
        q3_k = 11
        q4_k = 12
        q5_k = 13
        q6_k = 14
        q8_k = 15
        iq2_xxs = 16
        iq2_xs = 17
        iq3_xxs = 18
        iq1_s = 19
        iq4_nl = 20
        iq3_s = 21
        iq2_s = 22
        iq4_xs = 23
        i8 = 24
        i16 = 25
        i32 = 26
        i64 = 27
        f64 = 28
        iq1_m = 29
        bf16 = 30
        q4_0_4_4 = 31
        q4_0_4_8 = 32
        q4_0_8_8 = 33
        tq1_0 = 34
        tq2_0 = 35
        iq4_nl_4_4 = 36
        iq4_nl_4_8 = 37
        iq4_nl_8_8 = 38
        mxfp4 = 39
        nvfp4 = 40
        q1_0 = 41
        q2_0 = 42

    class GgufType(IntEnum):
        uint8 = 0
        int8 = 1
        uint16 = 2
        int16 = 3
        uint32 = 4
        int32 = 5
        float32 = 6
        bool = 7
        string = 8
        array = 9
        uint64 = 10
        int64 = 11
        float64 = 12
    SEQ_FIELDS = ["magic", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Gguf, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x47\x47\x55\x46":
            raise kaitaistruct.ValidationNotEqualError(b"\x47\x47\x55\x46", self.magic, self._io, u"/seq/0")
        self._debug['body']['start'] = self._io.pos()
        self.body = Gguf.GgufBody(self._io, self, self._root)
        self.body._read()
        self._debug['body']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.body._fetch_instances()
        _ = self.version_le
        if hasattr(self, '_m_version_le'):
            pass


    class GgufBody(KaitaiStruct):
        SEQ_FIELDS = ["version", "num_tensor_infos", "num_kv_pairs", "kv_pairs", "tensor_infos", "padding", "_unnamed6"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Gguf.GgufBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            _on = self._root.is_big_endian
            if _on == True:
                pass
                self._is_le = False
            elif _on == False:
                pass
                self._is_le = True
            if not hasattr(self, '_is_le'):
                raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body")
            elif self._is_le == True:
                self._read_le()
            elif self._is_le == False:
                self._read_be()

        def _read_le(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4le()
            self._debug['version']['end'] = self._io.pos()
            if not self.version >= 2:
                raise kaitaistruct.ValidationLessThanError(2, self.version, self._io, u"/types/gguf_body/seq/0")
            if not self.version <= 3:
                raise kaitaistruct.ValidationGreaterThanError(3, self.version, self._io, u"/types/gguf_body/seq/0")
            self._debug['num_tensor_infos']['start'] = self._io.pos()
            self.num_tensor_infos = self._io.read_u8le()
            self._debug['num_tensor_infos']['end'] = self._io.pos()
            self._debug['num_kv_pairs']['start'] = self._io.pos()
            self.num_kv_pairs = self._io.read_u8le()
            self._debug['num_kv_pairs']['end'] = self._io.pos()
            self._debug['kv_pairs']['start'] = self._io.pos()
            self._debug['kv_pairs']['arr'] = []
            self.kv_pairs = []
            for i in range(self.num_kv_pairs):
                self._debug['kv_pairs']['arr'].append({'start': self._io.pos()})
                _t_kv_pairs = Gguf.GgufBody.GgufKv((self.kv_pairs[i - 1].alignment if i != 0 else 32), self._io, self, self._root, self._is_le)
                try:
                    _t_kv_pairs._read()
                finally:
                    self.kv_pairs.append(_t_kv_pairs)
                self._debug['kv_pairs']['arr'][i]['end'] = self._io.pos()

            self._debug['kv_pairs']['end'] = self._io.pos()
            self._debug['tensor_infos']['start'] = self._io.pos()
            self._debug['tensor_infos']['arr'] = []
            self.tensor_infos = []
            for i in range(self.num_tensor_infos):
                self._debug['tensor_infos']['arr'].append({'start': self._io.pos()})
                _t_tensor_infos = Gguf.GgufBody.GgufTensorInfo((self.tensor_infos[i - 1].expected_next_offset if i != 0 else 0), self._io, self, self._root, self._is_le)
                try:
                    _t_tensor_infos._read()
                finally:
                    self.tensor_infos.append(_t_tensor_infos)
                self._debug['tensor_infos']['arr'][i]['end'] = self._io.pos()

            self._debug['tensor_infos']['end'] = self._io.pos()
            if self.num_tensor_infos != 0:
                pass
                self._debug['padding']['start'] = self._io.pos()
                self.padding = self._io.read_bytes((self.alignment - self._io.pos() % self.alignment) % self.alignment)
                self._debug['padding']['end'] = self._io.pos()

            if self.ofs_tensor_data < 0:
                pass
                self._debug['_unnamed6']['start'] = self._io.pos()
                self._unnamed6 = self._io.read_bytes(0)
                self._debug['_unnamed6']['end'] = self._io.pos()


        def _read_be(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4be()
            self._debug['version']['end'] = self._io.pos()
            if not self.version >= 2:
                raise kaitaistruct.ValidationLessThanError(2, self.version, self._io, u"/types/gguf_body/seq/0")
            if not self.version <= 3:
                raise kaitaistruct.ValidationGreaterThanError(3, self.version, self._io, u"/types/gguf_body/seq/0")
            self._debug['num_tensor_infos']['start'] = self._io.pos()
            self.num_tensor_infos = self._io.read_u8be()
            self._debug['num_tensor_infos']['end'] = self._io.pos()
            self._debug['num_kv_pairs']['start'] = self._io.pos()
            self.num_kv_pairs = self._io.read_u8be()
            self._debug['num_kv_pairs']['end'] = self._io.pos()
            self._debug['kv_pairs']['start'] = self._io.pos()
            self._debug['kv_pairs']['arr'] = []
            self.kv_pairs = []
            for i in range(self.num_kv_pairs):
                self._debug['kv_pairs']['arr'].append({'start': self._io.pos()})
                _t_kv_pairs = Gguf.GgufBody.GgufKv((self.kv_pairs[i - 1].alignment if i != 0 else 32), self._io, self, self._root, self._is_le)
                try:
                    _t_kv_pairs._read()
                finally:
                    self.kv_pairs.append(_t_kv_pairs)
                self._debug['kv_pairs']['arr'][i]['end'] = self._io.pos()

            self._debug['kv_pairs']['end'] = self._io.pos()
            self._debug['tensor_infos']['start'] = self._io.pos()
            self._debug['tensor_infos']['arr'] = []
            self.tensor_infos = []
            for i in range(self.num_tensor_infos):
                self._debug['tensor_infos']['arr'].append({'start': self._io.pos()})
                _t_tensor_infos = Gguf.GgufBody.GgufTensorInfo((self.tensor_infos[i - 1].expected_next_offset if i != 0 else 0), self._io, self, self._root, self._is_le)
                try:
                    _t_tensor_infos._read()
                finally:
                    self.tensor_infos.append(_t_tensor_infos)
                self._debug['tensor_infos']['arr'][i]['end'] = self._io.pos()

            self._debug['tensor_infos']['end'] = self._io.pos()
            if self.num_tensor_infos != 0:
                pass
                self._debug['padding']['start'] = self._io.pos()
                self.padding = self._io.read_bytes((self.alignment - self._io.pos() % self.alignment) % self.alignment)
                self._debug['padding']['end'] = self._io.pos()

            if self.ofs_tensor_data < 0:
                pass
                self._debug['_unnamed6']['start'] = self._io.pos()
                self._unnamed6 = self._io.read_bytes(0)
                self._debug['_unnamed6']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            for i in range(len(self.kv_pairs)):
                pass
                self.kv_pairs[i]._fetch_instances()

            for i in range(len(self.tensor_infos)):
                pass
                self.tensor_infos[i]._fetch_instances()

            if self.num_tensor_infos != 0:
                pass

            if self.ofs_tensor_data < 0:
                pass


        class GgufArray(KaitaiStruct):
            """Nested arrays are supported. Although ggml (v0.27.0) doesn't support them,
            they are explicitly allowed by `gguf.md` - see
            <https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md?plain=1#L221>.
            """
            SEQ_FIELDS = ["type", "num_elems", "elems"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufArray, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_array")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgufType, self._io.read_u4le())
                self._debug['type']['end'] = self._io.pos()
                if not isinstance(self.type, Gguf.GgufType):
                    raise kaitaistruct.ValidationNotInEnumError(self.type, self._io, u"/types/gguf_body/types/gguf_array/seq/0")
                self._debug['num_elems']['start'] = self._io.pos()
                self.num_elems = self._io.read_u8le()
                self._debug['num_elems']['end'] = self._io.pos()
                self._debug['elems']['start'] = self._io.pos()
                self._debug['elems']['arr'] = []
                self.elems = []
                for i in range(self.num_elems):
                    self._debug['elems']['arr'].append({'start': self._io.pos()})
                    _t_elems = Gguf.GgufBody.GgufValue(self.type, self._io, self, self._root, self._is_le)
                    try:
                        _t_elems._read()
                    finally:
                        self.elems.append(_t_elems)
                    self._debug['elems']['arr'][i]['end'] = self._io.pos()

                self._debug['elems']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgufType, self._io.read_u4be())
                self._debug['type']['end'] = self._io.pos()
                if not isinstance(self.type, Gguf.GgufType):
                    raise kaitaistruct.ValidationNotInEnumError(self.type, self._io, u"/types/gguf_body/types/gguf_array/seq/0")
                self._debug['num_elems']['start'] = self._io.pos()
                self.num_elems = self._io.read_u8be()
                self._debug['num_elems']['end'] = self._io.pos()
                self._debug['elems']['start'] = self._io.pos()
                self._debug['elems']['arr'] = []
                self.elems = []
                for i in range(self.num_elems):
                    self._debug['elems']['arr'].append({'start': self._io.pos()})
                    _t_elems = Gguf.GgufBody.GgufValue(self.type, self._io, self, self._root, self._is_le)
                    try:
                        _t_elems._read()
                    finally:
                        self.elems.append(_t_elems)
                    self._debug['elems']['arr'][i]['end'] = self._io.pos()

                self._debug['elems']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.elems)):
                    pass
                    self.elems[i]._fetch_instances()



        class GgufBool(KaitaiStruct):
            SEQ_FIELDS = ["value_raw"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufBool, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_bool")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value_raw']['start'] = self._io.pos()
                self.value_raw = self._io.read_u1()
                self._debug['value_raw']['end'] = self._io.pos()
                if not self.value_raw <= 1:
                    raise kaitaistruct.ValidationGreaterThanError(1, self.value_raw, self._io, u"/types/gguf_body/types/gguf_bool/seq/0")

            def _read_be(self):
                self._debug['value_raw']['start'] = self._io.pos()
                self.value_raw = self._io.read_u1()
                self._debug['value_raw']['end'] = self._io.pos()
                if not self.value_raw <= 1:
                    raise kaitaistruct.ValidationGreaterThanError(1, self.value_raw, self._io, u"/types/gguf_body/types/gguf_bool/seq/0")


            def _fetch_instances(self):
                pass

            @property
            def value(self):
                """
                .. seealso::
                   Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/src/gguf.cpp#L321
                """
                if hasattr(self, '_m_value'):
                    return self._m_value

                self._m_value = self.value_raw != 0
                return getattr(self, '_m_value', None)


        class GgufFloat32(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufFloat32, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_float32")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_f4le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_f4be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufFloat64(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufFloat64, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_float64")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_f8le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_f8be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufInt16(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufInt16, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_int16")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s2le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s2be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufInt32(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufInt32, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_int32")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s4le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s4be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufInt64(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufInt64, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_int64")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s8le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s8be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufInt8(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufInt8, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_int8")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s1()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_s1()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufKv(KaitaiStruct):
            """
            .. seealso::
               Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md?plain=1#L262-L275
            """
            SEQ_FIELDS = ["key", "type", "value"]
            def __init__(self, prev_alignment, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufKv, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self.prev_alignment = prev_alignment
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_kv")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['key']['start'] = self._io.pos()
                self.key = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                self.key._read()
                self._debug['key']['end'] = self._io.pos()
                _ = self.key
                if not _.len_value != 0:
                    raise kaitaistruct.ValidationExprError(self.key, self._io, u"/types/gguf_body/types/gguf_kv/seq/0")
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgufType, self._io.read_u4le())
                self._debug['type']['end'] = self._io.pos()
                if not isinstance(self.type, Gguf.GgufType):
                    raise kaitaistruct.ValidationNotInEnumError(self.type, self._io, u"/types/gguf_body/types/gguf_kv/seq/1")
                self._debug['value']['start'] = self._io.pos()
                self.value = Gguf.GgufBody.GgufValue(self.type, self._io, self, self._root, self._is_le)
                self.value._read()
                self._debug['value']['end'] = self._io.pos()
                _ = self.value
                if not ( ((self.type == Gguf.GgufType.uint32) and (_.value.value != 0) and (_.value.value & _.value.value - 1 == 0))  if self.key.value == u"general.alignment" else True):
                    raise kaitaistruct.ValidationExprError(self.value, self._io, u"/types/gguf_body/types/gguf_kv/seq/2")

            def _read_be(self):
                self._debug['key']['start'] = self._io.pos()
                self.key = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                self.key._read()
                self._debug['key']['end'] = self._io.pos()
                _ = self.key
                if not _.len_value != 0:
                    raise kaitaistruct.ValidationExprError(self.key, self._io, u"/types/gguf_body/types/gguf_kv/seq/0")
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgufType, self._io.read_u4be())
                self._debug['type']['end'] = self._io.pos()
                if not isinstance(self.type, Gguf.GgufType):
                    raise kaitaistruct.ValidationNotInEnumError(self.type, self._io, u"/types/gguf_body/types/gguf_kv/seq/1")
                self._debug['value']['start'] = self._io.pos()
                self.value = Gguf.GgufBody.GgufValue(self.type, self._io, self, self._root, self._is_le)
                self.value._read()
                self._debug['value']['end'] = self._io.pos()
                _ = self.value
                if not ( ((self.type == Gguf.GgufType.uint32) and (_.value.value != 0) and (_.value.value & _.value.value - 1 == 0))  if self.key.value == u"general.alignment" else True):
                    raise kaitaistruct.ValidationExprError(self.value, self._io, u"/types/gguf_body/types/gguf_kv/seq/2")


            def _fetch_instances(self):
                pass
                self.key._fetch_instances()
                self.value._fetch_instances()

            @property
            def alignment(self):
                if hasattr(self, '_m_alignment'):
                    return self._m_alignment

                self._m_alignment = (self.value.value.value if self.key.value == u"general.alignment" else self.prev_alignment)
                return getattr(self, '_m_alignment', None)


        class GgufStr(KaitaiStruct):
            """
            .. seealso::
               Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md?plain=1#L232-L237
            """
            SEQ_FIELDS = ["len_value", "value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufStr, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_str")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['len_value']['start'] = self._io.pos()
                self.len_value = self._io.read_u8le()
                self._debug['len_value']['end'] = self._io.pos()
                self._debug['value']['start'] = self._io.pos()
                self.value = (self._io.read_bytes(self.len_value)).decode(u"UTF-8")
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['len_value']['start'] = self._io.pos()
                self.len_value = self._io.read_u8be()
                self._debug['len_value']['end'] = self._io.pos()
                self._debug['value']['start'] = self._io.pos()
                self.value = (self._io.read_bytes(self.len_value)).decode(u"UTF-8")
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufTensorInfo(KaitaiStruct):
            """
            .. seealso::
               Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md?plain=1#L305-L325
            """
            SEQ_FIELDS = ["name", "num_dims", "dims", "type", "offset"]
            def __init__(self, expected_offset, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufTensorInfo, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self.expected_offset = expected_offset
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_tensor_info")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['name']['start'] = self._io.pos()
                self.name = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                self.name._read()
                self._debug['name']['end'] = self._io.pos()
                _ = self.name
                if not _.len_value < 64:
                    raise kaitaistruct.ValidationExprError(self.name, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/0")
                self._debug['num_dims']['start'] = self._io.pos()
                self.num_dims = self._io.read_u4le()
                self._debug['num_dims']['end'] = self._io.pos()
                if not self.num_dims <= 4:
                    raise kaitaistruct.ValidationGreaterThanError(4, self.num_dims, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/1")
                self._debug['dims']['start'] = self._io.pos()
                self._debug['dims']['arr'] = []
                self.dims = []
                for i in range(self.num_dims):
                    self._debug['dims']['arr'].append({'start': self._io.pos()})
                    self.dims.append(self._io.read_s8le())
                    self._debug['dims']['arr'][i]['end'] = self._io.pos()
                    if not self.dims[i] >= 0:
                        raise kaitaistruct.ValidationLessThanError(0, self.dims[i], self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/2")

                self._debug['dims']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgmlType, self._io.read_u4le())
                self._debug['type']['end'] = self._io.pos()
                _ = self.type
                if not  ((int(_) < 43) and (self.num_elements_per_block != 0) and ((self.dims[0] if self.num_dims > 0 else 1) % self.num_elements_per_block == 0)) :
                    raise kaitaistruct.ValidationExprError(self.type, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/3")
                self._debug['offset']['start'] = self._io.pos()
                self.offset = self._io.read_u8le()
                self._debug['offset']['end'] = self._io.pos()
                if not self.offset == self.expected_offset:
                    raise kaitaistruct.ValidationNotEqualError(self.expected_offset, self.offset, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/4")

            def _read_be(self):
                self._debug['name']['start'] = self._io.pos()
                self.name = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                self.name._read()
                self._debug['name']['end'] = self._io.pos()
                _ = self.name
                if not _.len_value < 64:
                    raise kaitaistruct.ValidationExprError(self.name, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/0")
                self._debug['num_dims']['start'] = self._io.pos()
                self.num_dims = self._io.read_u4be()
                self._debug['num_dims']['end'] = self._io.pos()
                if not self.num_dims <= 4:
                    raise kaitaistruct.ValidationGreaterThanError(4, self.num_dims, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/1")
                self._debug['dims']['start'] = self._io.pos()
                self._debug['dims']['arr'] = []
                self.dims = []
                for i in range(self.num_dims):
                    self._debug['dims']['arr'].append({'start': self._io.pos()})
                    self.dims.append(self._io.read_s8be())
                    self._debug['dims']['arr'][i]['end'] = self._io.pos()
                    if not self.dims[i] >= 0:
                        raise kaitaistruct.ValidationLessThanError(0, self.dims[i], self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/2")

                self._debug['dims']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Gguf.GgmlType, self._io.read_u4be())
                self._debug['type']['end'] = self._io.pos()
                _ = self.type
                if not  ((int(_) < 43) and (self.num_elements_per_block != 0) and ((self.dims[0] if self.num_dims > 0 else 1) % self.num_elements_per_block == 0)) :
                    raise kaitaistruct.ValidationExprError(self.type, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/3")
                self._debug['offset']['start'] = self._io.pos()
                self.offset = self._io.read_u8be()
                self._debug['offset']['end'] = self._io.pos()
                if not self.offset == self.expected_offset:
                    raise kaitaistruct.ValidationNotEqualError(self.expected_offset, self.offset, self._io, u"/types/gguf_body/types/gguf_tensor_info/seq/4")


            def _fetch_instances(self):
                pass
                self.name._fetch_instances()
                for i in range(len(self.dims)):
                    pass

                _ = self.data
                if hasattr(self, '_m_data'):
                    pass

                _ = self.padding
                if hasattr(self, '_m_padding'):
                    pass


            @property
            def data(self):
                if hasattr(self, '_m_data'):
                    return self._m_data

                _pos = self._io.pos()
                self._io.seek(self._parent.ofs_tensor_data + self.offset)
                if self._is_le:
                    self._debug['_m_data']['start'] = self._io.pos()
                    self._m_data = self._io.read_bytes(self.len_data)
                    self._debug['_m_data']['end'] = self._io.pos()
                else:
                    self._debug['_m_data']['start'] = self._io.pos()
                    self._m_data = self._io.read_bytes(self.len_data)
                    self._debug['_m_data']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_data', None)

            @property
            def dump_dims(self):
                """`dims` joined with the string `" x "`. This is necessary for
                `-webide-representation`, which cannot format `dims` directly -
                see <https://github.com/kaitai-io/kaitai_struct_webide/issues/160>.
                """
                if hasattr(self, '_m_dump_dims'):
                    return self._m_dump_dims

                self._m_dump_dims = (((str(self.dims[0]) if self.num_dims > 0 else u"") + (u" x " + str(self.dims[1]) if self.num_dims > 1 else u"")) + (u" x " + str(self.dims[2]) if self.num_dims > 2 else u"")) + (u" x " + str(self.dims[3]) if self.num_dims > 3 else u"")
                return getattr(self, '_m_dump_dims', None)

            @property
            def expected_next_offset(self):
                """`offset` that the next tensor must have."""
                if hasattr(self, '_m_expected_next_offset'):
                    return self._m_expected_next_offset

                self._m_expected_next_offset = ((self.offset + self.len_data) + self.len_padding)
                return getattr(self, '_m_expected_next_offset', None)

            @property
            def len_block(self):
                """Size of a block in bytes."""
                if hasattr(self, '_m_len_block'):
                    return self._m_len_block

                self._m_len_block = [4, 2, 18, 20, 0, 0, 22, 24, 34, 36, 84, 110, 144, 176, 210, 292, 66, 74, 98, 50, 18, 110, 82, 136, 1, 2, 4, 8, 8, 56, 2, 0, 0, 0, 54, 66, 0, 0, 0, 17, 36, 18, 18][int(self.type)]
                return getattr(self, '_m_len_block', None)

            @property
            def len_data(self):
                if hasattr(self, '_m_len_data'):
                    return self._m_len_data

                self._m_len_data = (self.len_block * self.num_blocks)
                return getattr(self, '_m_len_data', None)

            @property
            def len_padding(self):
                """Number of padding bytes after the data."""
                if hasattr(self, '_m_len_padding'):
                    return self._m_len_padding

                self._m_len_padding = (self._parent.alignment - self.len_data % self._parent.alignment) % self._parent.alignment
                return getattr(self, '_m_len_padding', None)

            @property
            def num_blocks(self):
                if hasattr(self, '_m_num_blocks'):
                    return self._m_num_blocks

                self._m_num_blocks = (self.num_elements // self.num_elements_per_block)
                return getattr(self, '_m_num_blocks', None)

            @property
            def num_elements(self):
                if hasattr(self, '_m_num_elements'):
                    return self._m_num_elements

                self._m_num_elements = ((((self.dims[0] if self.num_dims > 0 else 1) * (self.dims[1] if self.num_dims > 1 else 1)) * (self.dims[2] if self.num_dims > 2 else 1)) * (self.dims[3] if self.num_dims > 3 else 1))
                return getattr(self, '_m_num_elements', None)

            @property
            def num_elements_per_block(self):
                """Number of elements in a block."""
                if hasattr(self, '_m_num_elements_per_block'):
                    return self._m_num_elements_per_block

                self._m_num_elements_per_block = [1, 1, 32, 32, 0, 0, 32, 32, 32, 32, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 32, 256, 256, 256, 1, 1, 1, 1, 1, 256, 1, 0, 0, 0, 256, 256, 0, 0, 0, 32, 64, 128, 64][int(self.type)]
                return getattr(self, '_m_num_elements_per_block', None)

            @property
            def padding(self):
                """Padding after the data. ggml requires it even after the last tensor
                when reading the tensor data.
                
                .. seealso::
                   Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/src/gguf.cpp#L884-L893
                """
                if hasattr(self, '_m_padding'):
                    return self._m_padding

                _pos = self._io.pos()
                self._io.seek((self._parent.ofs_tensor_data + self.offset) + self.len_data)
                if self._is_le:
                    self._debug['_m_padding']['start'] = self._io.pos()
                    self._m_padding = self._io.read_bytes(self.len_padding)
                    self._debug['_m_padding']['end'] = self._io.pos()
                else:
                    self._debug['_m_padding']['start'] = self._io.pos()
                    self._m_padding = self._io.read_bytes(self.len_padding)
                    self._debug['_m_padding']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_padding', None)


        class GgufUint16(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufUint16, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_uint16")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u2le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u2be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufUint32(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufUint32, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_uint32")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u4le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u4be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufUint64(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufUint64, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_uint64")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u8le()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u8be()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufUint8(KaitaiStruct):
            SEQ_FIELDS = ["value"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufUint8, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_uint8")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u1()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_u1()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class GgufValue(KaitaiStruct):
            """
            .. seealso::
               Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/docs/gguf.md?plain=1#L239-L260
            """
            SEQ_FIELDS = ["value"]
            def __init__(self, type, _io, _parent=None, _root=None, _is_le=None):
                super(Gguf.GgufBody.GgufValue, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self.type = type
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/gguf_body/types/gguf_value")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['value']['start'] = self._io.pos()
                _on = self.type
                if _on == Gguf.GgufType.array:
                    pass
                    self.value = Gguf.GgufBody.GgufArray(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.bool:
                    pass
                    self.value = Gguf.GgufBody.GgufBool(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.float32:
                    pass
                    self.value = Gguf.GgufBody.GgufFloat32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.float64:
                    pass
                    self.value = Gguf.GgufBody.GgufFloat64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int16:
                    pass
                    self.value = Gguf.GgufBody.GgufInt16(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int32:
                    pass
                    self.value = Gguf.GgufBody.GgufInt32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int64:
                    pass
                    self.value = Gguf.GgufBody.GgufInt64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int8:
                    pass
                    self.value = Gguf.GgufBody.GgufInt8(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.string:
                    pass
                    self.value = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint16:
                    pass
                    self.value = Gguf.GgufBody.GgufUint16(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint32:
                    pass
                    self.value = Gguf.GgufBody.GgufUint32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint64:
                    pass
                    self.value = Gguf.GgufBody.GgufUint64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint8:
                    pass
                    self.value = Gguf.GgufBody.GgufUint8(self._io, self, self._root, self._is_le)
                    self.value._read()
                self._debug['value']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['value']['start'] = self._io.pos()
                _on = self.type
                if _on == Gguf.GgufType.array:
                    pass
                    self.value = Gguf.GgufBody.GgufArray(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.bool:
                    pass
                    self.value = Gguf.GgufBody.GgufBool(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.float32:
                    pass
                    self.value = Gguf.GgufBody.GgufFloat32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.float64:
                    pass
                    self.value = Gguf.GgufBody.GgufFloat64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int16:
                    pass
                    self.value = Gguf.GgufBody.GgufInt16(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int32:
                    pass
                    self.value = Gguf.GgufBody.GgufInt32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int64:
                    pass
                    self.value = Gguf.GgufBody.GgufInt64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.int8:
                    pass
                    self.value = Gguf.GgufBody.GgufInt8(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.string:
                    pass
                    self.value = Gguf.GgufBody.GgufStr(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint16:
                    pass
                    self.value = Gguf.GgufBody.GgufUint16(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint32:
                    pass
                    self.value = Gguf.GgufBody.GgufUint32(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint64:
                    pass
                    self.value = Gguf.GgufBody.GgufUint64(self._io, self, self._root, self._is_le)
                    self.value._read()
                elif _on == Gguf.GgufType.uint8:
                    pass
                    self.value = Gguf.GgufBody.GgufUint8(self._io, self, self._root, self._is_le)
                    self.value._read()
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _on = self.type
                if _on == Gguf.GgufType.array:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.bool:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.float32:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.float64:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.int16:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.int32:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.int64:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.int8:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.string:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.uint16:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.uint32:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.uint64:
                    pass
                    self.value._fetch_instances()
                elif _on == Gguf.GgufType.uint8:
                    pass
                    self.value._fetch_instances()


        @property
        def alignment(self):
            """Global alignment - from the `general.alignment` key, or 32 if there's no
            such key.
            
            .. seealso::
               Git tag "v0.27.0" - https://github.com/ggml-org/ggml/blob/a05c9922613c6a2230dbb1d0de679519ecafb4f0/src/gguf.cpp#L622-L630
            """
            if hasattr(self, '_m_alignment'):
                return self._m_alignment

            self._m_alignment = (self.kv_pairs[-1].alignment if len(self.kv_pairs) != 0 else 32)
            return getattr(self, '_m_alignment', None)

        @property
        def ofs_tensor_data(self):
            """Offset of the tensor data. Each tensor's `offset` is relative to this
            position.
            """
            if hasattr(self, '_m_ofs_tensor_data'):
                return self._m_ofs_tensor_data

            self._m_ofs_tensor_data = self._io.pos()
            return getattr(self, '_m_ofs_tensor_data', None)


    @property
    def is_big_endian(self):
        if hasattr(self, '_m_is_big_endian'):
            return self._m_is_big_endian

        self._m_is_big_endian = self.version_le & 65535 == 0
        return getattr(self, '_m_is_big_endian', None)

    @property
    def len_file(self):
        """Length of the file (computed from the header), including the padding after
        the last tensor's data.
        
        This Kaitai Struct implementation stops parsing where the tensor data
        starts (which is read lazily, i.e. only on demand). Without reading the
        tensor data, you can use this expected file size to check whether the file
        has been truncated, to carve the file out of a larger one, etc.
        """
        if hasattr(self, '_m_len_file'):
            return self._m_len_file

        self._m_len_file = (self.body.ofs_tensor_data + (self.body.tensor_infos[-1].expected_next_offset if self.body.num_tensor_infos != 0 else 0))
        return getattr(self, '_m_len_file', None)

    @property
    def version_le(self):
        if hasattr(self, '_m_version_le'):
            return self._m_version_le

        _pos = self._io.pos()
        self._io.seek(4)
        self._debug['_m_version_le']['start'] = self._io.pos()
        self._m_version_le = self._io.read_u4le()
        self._debug['_m_version_le']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_version_le', None)


