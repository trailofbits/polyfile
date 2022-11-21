# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class MozillaMar(KaitaiStruct):
    """Mozilla ARchive file is Mozilla's own archive format to distribute software updates.
    Test files can be found on Mozilla's FTP site, for example:
    
    <http://ftp.mozilla.org/pub/firefox/nightly/partials/>
    
    .. seealso::
       Source - https://wiki.mozilla.org/Software_Update:MAR
    """

    class SignatureAlgorithms(Enum):
        rsa_pkcs1_sha1 = 1
        rsa_pkcs1_sha384 = 2

    class BlockIdentifiers(Enum):
        product_information = 1
    SEQ_FIELDS = ["magic", "ofs_index", "file_size", "len_signatures", "signatures", "len_additional_sections", "additional_sections"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x4D\x41\x52\x31":
            raise kaitaistruct.ValidationNotEqualError(b"\x4D\x41\x52\x31", self.magic, self._io, u"/seq/0")
        self._debug['ofs_index']['start'] = self._io.pos()
        self.ofs_index = self._io.read_u4be()
        self._debug['ofs_index']['end'] = self._io.pos()
        self._debug['file_size']['start'] = self._io.pos()
        self.file_size = self._io.read_u8be()
        self._debug['file_size']['end'] = self._io.pos()
        self._debug['len_signatures']['start'] = self._io.pos()
        self.len_signatures = self._io.read_u4be()
        self._debug['len_signatures']['end'] = self._io.pos()
        self._debug['signatures']['start'] = self._io.pos()
        self.signatures = [None] * (self.len_signatures)
        for i in range(self.len_signatures):
            if not 'arr' in self._debug['signatures']:
                self._debug['signatures']['arr'] = []
            self._debug['signatures']['arr'].append({'start': self._io.pos()})
            _t_signatures = MozillaMar.Signature(self._io, self, self._root)
            _t_signatures._read()
            self.signatures[i] = _t_signatures
            self._debug['signatures']['arr'][i]['end'] = self._io.pos()

        self._debug['signatures']['end'] = self._io.pos()
        self._debug['len_additional_sections']['start'] = self._io.pos()
        self.len_additional_sections = self._io.read_u4be()
        self._debug['len_additional_sections']['end'] = self._io.pos()
        self._debug['additional_sections']['start'] = self._io.pos()
        self.additional_sections = [None] * (self.len_additional_sections)
        for i in range(self.len_additional_sections):
            if not 'arr' in self._debug['additional_sections']:
                self._debug['additional_sections']['arr'] = []
            self._debug['additional_sections']['arr'].append({'start': self._io.pos()})
            _t_additional_sections = MozillaMar.AdditionalSection(self._io, self, self._root)
            _t_additional_sections._read()
            self.additional_sections[i] = _t_additional_sections
            self._debug['additional_sections']['arr'][i]['end'] = self._io.pos()

        self._debug['additional_sections']['end'] = self._io.pos()

    class MarIndex(KaitaiStruct):
        SEQ_FIELDS = ["len_index", "index_entries"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_index']['start'] = self._io.pos()
            self.len_index = self._io.read_u4be()
            self._debug['len_index']['end'] = self._io.pos()
            self._debug['index_entries']['start'] = self._io.pos()
            self._raw_index_entries = self._io.read_bytes(self.len_index)
            _io__raw_index_entries = KaitaiStream(BytesIO(self._raw_index_entries))
            self.index_entries = MozillaMar.IndexEntries(_io__raw_index_entries, self, self._root)
            self.index_entries._read()
            self._debug['index_entries']['end'] = self._io.pos()


    class IndexEntries(KaitaiStruct):
        SEQ_FIELDS = ["index_entry"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['index_entry']['start'] = self._io.pos()
            self.index_entry = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['index_entry']:
                    self._debug['index_entry']['arr'] = []
                self._debug['index_entry']['arr'].append({'start': self._io.pos()})
                _t_index_entry = MozillaMar.IndexEntry(self._io, self, self._root)
                _t_index_entry._read()
                self.index_entry.append(_t_index_entry)
                self._debug['index_entry']['arr'][len(self.index_entry) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['index_entry']['end'] = self._io.pos()


    class Signature(KaitaiStruct):
        SEQ_FIELDS = ["algorithm", "len_signature", "signature"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['algorithm']['start'] = self._io.pos()
            self.algorithm = KaitaiStream.resolve_enum(MozillaMar.SignatureAlgorithms, self._io.read_u4be())
            self._debug['algorithm']['end'] = self._io.pos()
            self._debug['len_signature']['start'] = self._io.pos()
            self.len_signature = self._io.read_u4be()
            self._debug['len_signature']['end'] = self._io.pos()
            self._debug['signature']['start'] = self._io.pos()
            self.signature = self._io.read_bytes(self.len_signature)
            self._debug['signature']['end'] = self._io.pos()


    class ProductInformationBlock(KaitaiStruct):
        SEQ_FIELDS = ["mar_channel_name", "product_version"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['mar_channel_name']['start'] = self._io.pos()
            self.mar_channel_name = (KaitaiStream.bytes_terminate(self._io.read_bytes(64), 0, False)).decode(u"UTF-8")
            self._debug['mar_channel_name']['end'] = self._io.pos()
            self._debug['product_version']['start'] = self._io.pos()
            self.product_version = (KaitaiStream.bytes_terminate(self._io.read_bytes(32), 0, False)).decode(u"UTF-8")
            self._debug['product_version']['end'] = self._io.pos()


    class IndexEntry(KaitaiStruct):
        SEQ_FIELDS = ["ofs_content", "len_content", "flags", "file_name"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_content']['start'] = self._io.pos()
            self.ofs_content = self._io.read_u4be()
            self._debug['ofs_content']['end'] = self._io.pos()
            self._debug['len_content']['start'] = self._io.pos()
            self.len_content = self._io.read_u4be()
            self._debug['len_content']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u4be()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['file_name']['start'] = self._io.pos()
            self.file_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self._debug['file_name']['end'] = self._io.pos()

        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body if hasattr(self, '_m_body') else None

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_content)
            self._debug['_m_body']['start'] = io.pos()
            self._m_body = io.read_bytes(self.len_content)
            self._debug['_m_body']['end'] = io.pos()
            io.seek(_pos)
            return self._m_body if hasattr(self, '_m_body') else None


    class AdditionalSection(KaitaiStruct):
        SEQ_FIELDS = ["len_block", "block_identifier", "bytes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_block']['start'] = self._io.pos()
            self.len_block = self._io.read_u4be()
            self._debug['len_block']['end'] = self._io.pos()
            self._debug['block_identifier']['start'] = self._io.pos()
            self.block_identifier = KaitaiStream.resolve_enum(MozillaMar.BlockIdentifiers, self._io.read_u4be())
            self._debug['block_identifier']['end'] = self._io.pos()
            self._debug['bytes']['start'] = self._io.pos()
            _on = self.block_identifier
            if _on == MozillaMar.BlockIdentifiers.product_information:
                self._raw_bytes = self._io.read_bytes(((self.len_block - 4) - 4))
                _io__raw_bytes = KaitaiStream(BytesIO(self._raw_bytes))
                self.bytes = MozillaMar.ProductInformationBlock(_io__raw_bytes, self, self._root)
                self.bytes._read()
            else:
                self.bytes = self._io.read_bytes(((self.len_block - 4) - 4))
            self._debug['bytes']['end'] = self._io.pos()


    @property
    def index(self):
        if hasattr(self, '_m_index'):
            return self._m_index if hasattr(self, '_m_index') else None

        _pos = self._io.pos()
        self._io.seek(self.ofs_index)
        self._debug['_m_index']['start'] = self._io.pos()
        self._m_index = MozillaMar.MarIndex(self._io, self, self._root)
        self._m_index._read()
        self._debug['_m_index']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_index if hasattr(self, '_m_index') else None


