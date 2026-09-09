# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections
import zlib


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Xar(KaitaiStruct):
    """From [Wikipedia](https://en.wikipedia.org/wiki/Xar_(archiver)):
    
    "XAR (short for eXtensible ARchive format) is an open source file archiver
    and the archiver's file format. It was created within the OpenDarwin project
    and is used in macOS X 10.5 and up for software installation routines, as
    well as browser extensions in Safari 5.0 and up."
    
    .. seealso::
       Source - https://github.com/mackyle/xar/wiki/xarformat
    """

    class ChecksumAlgorithmsApple(IntEnum):
        none = 0
        sha1 = 1
        md5 = 2
        sha256 = 3
        sha512 = 4
    SEQ_FIELDS = ["header_prefix", "header", "toc"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Xar, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header_prefix']['start'] = self._io.pos()
        self.header_prefix = Xar.FileHeaderPrefix(self._io, self, self._root)
        self.header_prefix._read()
        self._debug['header_prefix']['end'] = self._io.pos()
        self._debug['header']['start'] = self._io.pos()
        self._raw_header = self._io.read_bytes(self.header_prefix.len_header - 6)
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = Xar.FileHeader(_io__raw_header, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['toc']['start'] = self._io.pos()
        self._raw__raw_toc = self._io.read_bytes(self.header.len_toc_compressed)
        self._raw_toc = zlib.decompress(self._raw__raw_toc)
        _io__raw_toc = KaitaiStream(BytesIO(self._raw_toc))
        self.toc = Xar.TocType(_io__raw_toc, self, self._root)
        self.toc._read()
        self._debug['toc']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header_prefix._fetch_instances()
        self.header._fetch_instances()
        self.toc._fetch_instances()

    class FileHeader(KaitaiStruct):
        SEQ_FIELDS = ["version", "len_toc_compressed", "toc_length_uncompressed", "checksum_algorithm_int", "checksum_alg_name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Xar.FileHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u2be()
            self._debug['version']['end'] = self._io.pos()
            if not self.version == 1:
                raise kaitaistruct.ValidationNotEqualError(1, self.version, self._io, u"/types/file_header/seq/0")
            self._debug['len_toc_compressed']['start'] = self._io.pos()
            self.len_toc_compressed = self._io.read_u8be()
            self._debug['len_toc_compressed']['end'] = self._io.pos()
            self._debug['toc_length_uncompressed']['start'] = self._io.pos()
            self.toc_length_uncompressed = self._io.read_u8be()
            self._debug['toc_length_uncompressed']['end'] = self._io.pos()
            self._debug['checksum_algorithm_int']['start'] = self._io.pos()
            self.checksum_algorithm_int = self._io.read_u4be()
            self._debug['checksum_algorithm_int']['end'] = self._io.pos()
            if self.has_checksum_alg_name:
                pass
                self._debug['checksum_alg_name']['start'] = self._io.pos()
                self.checksum_alg_name = (KaitaiStream.bytes_terminate(self._io.read_bytes_full(), 0, False)).decode(u"UTF-8")
                self._debug['checksum_alg_name']['end'] = self._io.pos()
                _ = self.checksum_alg_name
                if not  ((_ != u"") and (_ != u"none")) :
                    raise kaitaistruct.ValidationExprError(self.checksum_alg_name, self._io, u"/types/file_header/seq/4")



        def _fetch_instances(self):
            pass
            if self.has_checksum_alg_name:
                pass


        @property
        def checksum_algorithm_name(self):
            """If it is not
            
            * `""` (empty string), indicating an unknown integer value (access
              `checksum_algorithm_int` for debugging purposes to find out
              what that value is), or
            * `"none"`, indicating that the TOC checksum is not provided (in that
              case, the `<checksum>` property or its `style` attribute should be
              missing, or the `style` attribute must be set to `"none"`),
            
            it must exactly match the `style` attribute value of the
            `<checksum>` property in the root node `<toc>`. See
            <https://github.com/mackyle/xar/blob/66d451d/xar/lib/archive.c#L345-L371>
            for reference.
            
            The `xar` (eXtensible ARchiver) program [uses OpenSSL's function
            `EVP_get_digestbyname`](
              https://github.com/mackyle/xar/blob/66d451d/xar/lib/archive.c#L328
            ) to verify this value (if it's not `""` or `"none"`, of course).
            So it's reasonable to assume that this can only have one of the values
            that OpenSSL recognizes.
            """
            if hasattr(self, '_m_checksum_algorithm_name'):
                return self._m_checksum_algorithm_name

            self._m_checksum_algorithm_name = (self.checksum_alg_name if self.has_checksum_alg_name else (u"none" if self.checksum_algorithm_int == int(Xar.ChecksumAlgorithmsApple.none) else (u"sha1" if self.checksum_algorithm_int == int(Xar.ChecksumAlgorithmsApple.sha1) else (u"md5" if self.checksum_algorithm_int == int(Xar.ChecksumAlgorithmsApple.md5) else (u"sha256" if self.checksum_algorithm_int == int(Xar.ChecksumAlgorithmsApple.sha256) else (u"sha512" if self.checksum_algorithm_int == int(Xar.ChecksumAlgorithmsApple.sha512) else u""))))))
            return getattr(self, '_m_checksum_algorithm_name', None)

        @property
        def has_checksum_alg_name(self):
            if hasattr(self, '_m_has_checksum_alg_name'):
                return self._m_has_checksum_alg_name

            self._m_has_checksum_alg_name =  ((self.checksum_algorithm_int == self._root.checksum_algorithm_other) and (self.len_header >= 32) and (self.len_header % 4 == 0)) 
            return getattr(self, '_m_has_checksum_alg_name', None)

        @property
        def len_header(self):
            if hasattr(self, '_m_len_header'):
                return self._m_len_header

            self._m_len_header = self._root.header_prefix.len_header
            return getattr(self, '_m_len_header', None)


    class FileHeaderPrefix(KaitaiStruct):
        SEQ_FIELDS = ["magic", "len_header"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Xar.FileHeaderPrefix, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x78\x61\x72\x21":
                raise kaitaistruct.ValidationNotEqualError(b"\x78\x61\x72\x21", self.magic, self._io, u"/types/file_header_prefix/seq/0")
            self._debug['len_header']['start'] = self._io.pos()
            self.len_header = self._io.read_u2be()
            self._debug['len_header']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class TocType(KaitaiStruct):
        SEQ_FIELDS = ["xml_string"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Xar.TocType, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['xml_string']['start'] = self._io.pos()
            self.xml_string = (self._io.read_bytes_full()).decode(u"UTF-8")
            self._debug['xml_string']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    @property
    def checksum_algorithm_other(self):
        """
        .. seealso::
           Source - https://github.com/mackyle/xar/blob/66d451d/xar/include/xar.h.in#L85
        """
        if hasattr(self, '_m_checksum_algorithm_other'):
            return self._m_checksum_algorithm_other

        self._m_checksum_algorithm_other = 3
        return getattr(self, '_m_checksum_algorithm_other', None)


