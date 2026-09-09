# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class VlqBase128Le(KaitaiStruct):
    """A variable-length unsigned/signed integer using base128 encoding. 1-byte groups
    consist of 1-bit flag of continuation and 7-bit value chunk, and are ordered
    "least significant group first", i.e. in "little-endian" manner.
    
    This particular encoding is specified and used in:
    
    * DWARF debug file format, where it's dubbed "unsigned LEB128" or "ULEB128".
      <https://dwarfstd.org/doc/dwarf-2.0.0.pdf> - page 139
    * Google Protocol Buffers, where it's called "Base 128 Varints".
      <https://protobuf.dev/programming-guides/encoding/#varints>
    * Apache Lucene, where it's called "VInt"
      <https://lucene.apache.org/core/3_5_0/fileformats.html#VInt>
    * Apache Avro uses this as a basis for integer encoding, adding ZigZag on
      top of it for signed ints
      <https://avro.apache.org/docs/1.12.0/specification/#primitive-types-1>
    
    More information on this encoding is available at <https://en.wikipedia.org/wiki/LEB128>
    
    This particular implementation supports integer values up to 64 bits (i.e. the
    maximum unsigned value supported is `2**64 - 1`), which implies that serialized
    values can be up to 10 bytes in length.
    
    If the most significant 10th byte (`groups[9]`) is present, its `has_next`
    must be `false` (otherwise we would have 11 or more bytes, which is not
    supported) and its `value` can be only `0` or `1` (because a 9-byte VLQ can
    represent `9 * 7 = 63` bits already, so the 10th byte can only add 1 bit,
    since only integers up to 64 bits are supported). These restrictions are
    enforced by this implementation. They were inspired by the Protoscope tool,
    see <https://github.com/protocolbuffers/protoscope/blob/8e7a6aafa2c9958527b1e0747e66e1bfff045819/writer.go#L644-L648>.
    """
    SEQ_FIELDS = ["groups"]
    def __init__(self, _io, _parent=None, _root=None):
        super(VlqBase128Le, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['groups']['start'] = self._io.pos()
        self._debug['groups']['arr'] = []
        self.groups = []
        i = 0
        while True:
            self._debug['groups']['arr'].append({'start': self._io.pos()})
            _t_groups = VlqBase128Le.Group(i, (self.groups[i - 1].interm_value if i != 0 else 0), ((9223372036854775808 if i == 9 else self.groups[i - 1].multiplier * 128) if i != 0 else 1), self._io, self, self._root)
            try:
                _t_groups._read()
            finally:
                _ = _t_groups
                self.groups.append(_)
            self._debug['groups']['arr'][len(self.groups) - 1]['end'] = self._io.pos()
            if (not (_.has_next)):
                break
            i += 1
        self._debug['groups']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.groups)):
            pass
            self.groups[i]._fetch_instances()


    class Group(KaitaiStruct):
        """One byte group, clearly divided into 7-bit "value" chunk and 1-bit "continuation" flag.
        """
        SEQ_FIELDS = ["has_next", "value"]
        def __init__(self, idx, prev_interm_value, multiplier, _io, _parent=None, _root=None):
            super(VlqBase128Le.Group, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.idx = idx
            self.prev_interm_value = prev_interm_value
            self.multiplier = multiplier
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['has_next']['start'] = self._io.pos()
            self.has_next = self._io.read_bits_int_be(1) != 0
            self._debug['has_next']['end'] = self._io.pos()
            if not self.has_next == (False if self.idx == 9 else self.has_next):
                raise kaitaistruct.ValidationNotEqualError((False if self.idx == 9 else self.has_next), self.has_next, self._io, u"/types/group/seq/0")
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_bits_int_be(7)
            self._debug['value']['end'] = self._io.pos()
            if not self.value <= (1 if self.idx == 9 else 127):
                raise kaitaistruct.ValidationGreaterThanError((1 if self.idx == 9 else 127), self.value, self._io, u"/types/group/seq/1")


        def _fetch_instances(self):
            pass

        @property
        def interm_value(self):
            if hasattr(self, '_m_interm_value'):
                return self._m_interm_value

            self._m_interm_value = (self.prev_interm_value + self.value * self.multiplier)
            return getattr(self, '_m_interm_value', None)


    @property
    def len(self):
        if hasattr(self, '_m_len'):
            return self._m_len

        self._m_len = len(self.groups)
        return getattr(self, '_m_len', None)

    @property
    def sign_bit(self):
        if hasattr(self, '_m_sign_bit'):
            return self._m_sign_bit

        self._m_sign_bit = (9223372036854775808 if self.len == 10 else self.groups[-1].multiplier * 64)
        return getattr(self, '_m_sign_bit', None)

    @property
    def value(self):
        """Resulting unsigned value as normal integer."""
        if hasattr(self, '_m_value'):
            return self._m_value

        self._m_value = self.groups[-1].interm_value
        return getattr(self, '_m_value', None)

    @property
    def value_signed(self):
        if hasattr(self, '_m_value_signed'):
            return self._m_value_signed

        self._m_value_signed = (-((self.sign_bit - (self.value - self.sign_bit))) if  ((self.sign_bit > 0) and (self.value >= self.sign_bit))  else self.value)
        return getattr(self, '_m_value_signed', None)


