# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Utf16WithBom(KaitaiStruct):
    """A simple wrapper which allows to read a UTF-16 encoded string that starts
    with a byte order mark (BOM). The BOM indicates the endianness of the UTF-16
    encoding, which can be either big-endian (BE) or little-endian (LE).
    
    Use:
    
    * `value` to get the string value with BOM stripped, regardless of endianness.
    * `is_be` and `is_le` to check the endianness indicated by the BOM.
    * `bom` to check the raw byte order mark.
    
    .. seealso::
       - https://en.wikipedia.org/wiki/Byte_order_mark
    """
    SEQ_FIELDS = ["bom", "str_be", "str_le"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Utf16WithBom, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['bom']['start'] = self._io.pos()
        self.bom = self._io.read_bytes(2)
        self._debug['bom']['end'] = self._io.pos()
        if not  ((self.bom == b"\xFE\xFF") or (self.bom == b"\xFF\xFE")) :
            raise kaitaistruct.ValidationNotAnyOfError(self.bom, self._io, u"/seq/0")
        if self.is_be:
            pass
            self._debug['str_be']['start'] = self._io.pos()
            self.str_be = (self._io.read_bytes_full()).decode(u"UTF-16BE")
            self._debug['str_be']['end'] = self._io.pos()

        if self.is_le:
            pass
            self._debug['str_le']['start'] = self._io.pos()
            self.str_le = (self._io.read_bytes_full()).decode(u"UTF-16LE")
            self._debug['str_le']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        if self.is_be:
            pass

        if self.is_le:
            pass


    @property
    def is_be(self):
        """True if the byte order mark indicates big-endian UTF-16 encoding."""
        if hasattr(self, '_m_is_be'):
            return self._m_is_be

        self._m_is_be = self.bom == b"\xFE\xFF"
        return getattr(self, '_m_is_be', None)

    @property
    def is_le(self):
        """True if the byte order mark indicates little-endian UTF-16 encoding."""
        if hasattr(self, '_m_is_le'):
            return self._m_is_le

        self._m_is_le = self.bom == b"\xFF\xFE"
        return getattr(self, '_m_is_le', None)

    @property
    def value(self):
        """The string value with BOM stripped, regardless of endianness."""
        if hasattr(self, '_m_value'):
            return self._m_value

        self._m_value = (self.str_be if self.is_be else self.str_le)
        return getattr(self, '_m_value', None)


