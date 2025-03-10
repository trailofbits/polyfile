# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class ChromePak(KaitaiStruct):
    """Format mostly used by Google Chrome and various Android apps to store
    resources such as translated strings, help messages and images.
    
    .. seealso::
       Source - https://web.archive.org/web/20220126211447/https://dev.chromium.org/developers/design-documents/linuxresourcesandlocalizedstrings
    
    
    .. seealso::
       Source - https://chromium.googlesource.com/chromium/src/tools/grit/+/3c36f27/grit/format/data_pack.py
    
    
    .. seealso::
       Source - https://chromium.googlesource.com/chromium/src/tools/grit/+/8a23eae/grit/format/data_pack.py
    """

    class Encodings(Enum):
        binary = 0
        utf8 = 1
        utf16 = 2
    SEQ_FIELDS = ["version", "num_resources_v4", "encoding", "v5_part", "resources", "aliases"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u4le()
        self._debug['version']['end'] = self._io.pos()
        if not  ((self.version == 4) or (self.version == 5)) :
            raise kaitaistruct.ValidationNotAnyOfError(self.version, self._io, u"/seq/0")
        if self.version == 4:
            self._debug['num_resources_v4']['start'] = self._io.pos()
            self.num_resources_v4 = self._io.read_u4le()
            self._debug['num_resources_v4']['end'] = self._io.pos()

        self._debug['encoding']['start'] = self._io.pos()
        self.encoding = KaitaiStream.resolve_enum(ChromePak.Encodings, self._io.read_u1())
        self._debug['encoding']['end'] = self._io.pos()
        if self.version == 5:
            self._debug['v5_part']['start'] = self._io.pos()
            self.v5_part = ChromePak.HeaderV5Part(self._io, self, self._root)
            self.v5_part._read()
            self._debug['v5_part']['end'] = self._io.pos()

        self._debug['resources']['start'] = self._io.pos()
        self.resources = [None] * ((self.num_resources + 1))
        for i in range((self.num_resources + 1)):
            if not 'arr' in self._debug['resources']:
                self._debug['resources']['arr'] = []
            self._debug['resources']['arr'].append({'start': self._io.pos()})
            _t_resources = ChromePak.Resource(i, i < self.num_resources, self._io, self, self._root)
            _t_resources._read()
            self.resources[i] = _t_resources
            self._debug['resources']['arr'][i]['end'] = self._io.pos()

        self._debug['resources']['end'] = self._io.pos()
        self._debug['aliases']['start'] = self._io.pos()
        self.aliases = [None] * (self.num_aliases)
        for i in range(self.num_aliases):
            if not 'arr' in self._debug['aliases']:
                self._debug['aliases']['arr'] = []
            self._debug['aliases']['arr'].append({'start': self._io.pos()})
            _t_aliases = ChromePak.Alias(self._io, self, self._root)
            _t_aliases._read()
            self.aliases[i] = _t_aliases
            self._debug['aliases']['arr'][i]['end'] = self._io.pos()

        self._debug['aliases']['end'] = self._io.pos()

    class HeaderV5Part(KaitaiStruct):
        SEQ_FIELDS = ["encoding_padding", "num_resources", "num_aliases"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['encoding_padding']['start'] = self._io.pos()
            self.encoding_padding = self._io.read_bytes(3)
            self._debug['encoding_padding']['end'] = self._io.pos()
            self._debug['num_resources']['start'] = self._io.pos()
            self.num_resources = self._io.read_u2le()
            self._debug['num_resources']['end'] = self._io.pos()
            self._debug['num_aliases']['start'] = self._io.pos()
            self.num_aliases = self._io.read_u2le()
            self._debug['num_aliases']['end'] = self._io.pos()


    class Resource(KaitaiStruct):
        SEQ_FIELDS = ["id", "ofs_body"]
        def __init__(self, idx, has_body, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.idx = idx
            self.has_body = has_body
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u2le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['ofs_body']['start'] = self._io.pos()
            self.ofs_body = self._io.read_u4le()
            self._debug['ofs_body']['end'] = self._io.pos()

        @property
        def len_body(self):
            """MUST NOT be accessed until the next `resource` is parsed."""
            if hasattr(self, '_m_len_body'):
                return self._m_len_body if hasattr(self, '_m_len_body') else None

            if self.has_body:
                self._m_len_body = (self._parent.resources[(self.idx + 1)].ofs_body - self.ofs_body)

            return self._m_len_body if hasattr(self, '_m_len_body') else None

        @property
        def body(self):
            """MUST NOT be accessed until the next `resource` is parsed."""
            if hasattr(self, '_m_body'):
                return self._m_body if hasattr(self, '_m_body') else None

            if self.has_body:
                _pos = self._io.pos()
                self._io.seek(self.ofs_body)
                self._debug['_m_body']['start'] = self._io.pos()
                self._m_body = self._io.read_bytes(self.len_body)
                self._debug['_m_body']['end'] = self._io.pos()
                self._io.seek(_pos)

            return self._m_body if hasattr(self, '_m_body') else None


    class Alias(KaitaiStruct):
        SEQ_FIELDS = ["id", "resource_idx"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u2le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['resource_idx']['start'] = self._io.pos()
            self.resource_idx = self._io.read_u2le()
            self._debug['resource_idx']['end'] = self._io.pos()
            if not self.resource_idx <= (self._parent.num_resources - 1):
                raise kaitaistruct.ValidationGreaterThanError((self._parent.num_resources - 1), self.resource_idx, self._io, u"/types/alias/seq/1")

        @property
        def resource(self):
            if hasattr(self, '_m_resource'):
                return self._m_resource if hasattr(self, '_m_resource') else None

            self._m_resource = self._parent.resources[self.resource_idx]
            return self._m_resource if hasattr(self, '_m_resource') else None


    @property
    def num_resources(self):
        if hasattr(self, '_m_num_resources'):
            return self._m_num_resources if hasattr(self, '_m_num_resources') else None

        self._m_num_resources = (self.v5_part.num_resources if self.version == 5 else self.num_resources_v4)
        return self._m_num_resources if hasattr(self, '_m_num_resources') else None

    @property
    def num_aliases(self):
        if hasattr(self, '_m_num_aliases'):
            return self._m_num_aliases if hasattr(self, '_m_num_aliases') else None

        self._m_num_aliases = (self.v5_part.num_aliases if self.version == 5 else 0)
        return self._m_num_aliases if hasattr(self, '_m_num_aliases') else None


