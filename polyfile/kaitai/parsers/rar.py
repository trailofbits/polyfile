# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

from polyfile.kaitai.parsers import dos_datetime
class Rar(KaitaiStruct):
    """RAR is a archive format used by popular proprietary RAR archiver,
    created by Eugene Roshal. There are two major versions of format
    (v1.5-4.0 and RAR v5+).
    
    File format essentially consists of a linear sequence of
    blocks. Each block has fixed header and custom body (that depends on
    block type), so it's possible to skip block even if one doesn't know
    how to process a certain block type.
    
    .. seealso::
       Source - http://acritum.com/winrar/rar-format
    """

    class BlockTypes(Enum):
        marker = 114
        archive_header = 115
        file_header = 116
        old_style_comment_header = 117
        old_style_authenticity_info_76 = 118
        old_style_subblock = 119
        old_style_recovery_record = 120
        old_style_authenticity_info_79 = 121
        subblock = 122
        terminator = 123

    class Oses(Enum):
        ms_dos = 0
        os_2 = 1
        windows = 2
        unix = 3
        mac_os = 4
        beos = 5

    class Methods(Enum):
        store = 48
        fastest = 49
        fast = 50
        normal = 51
        good = 52
        best = 53
    SEQ_FIELDS = ["magic", "blocks"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = Rar.MagicSignature(self._io, self, self._root)
        self.magic._read()
        self._debug['magic']['end'] = self._io.pos()
        self._debug['blocks']['start'] = self._io.pos()
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            if not 'arr' in self._debug['blocks']:
                self._debug['blocks']['arr'] = []
            self._debug['blocks']['arr'].append({'start': self._io.pos()})
            _on = self.magic.version
            if _on == 0:
                if not 'arr' in self._debug['blocks']:
                    self._debug['blocks']['arr'] = []
                self._debug['blocks']['arr'].append({'start': self._io.pos()})
                _t_blocks = Rar.Block(self._io, self, self._root)
                _t_blocks._read()
                self.blocks.append(_t_blocks)
                self._debug['blocks']['arr'][len(self.blocks) - 1]['end'] = self._io.pos()
            elif _on == 1:
                if not 'arr' in self._debug['blocks']:
                    self._debug['blocks']['arr'] = []
                self._debug['blocks']['arr'].append({'start': self._io.pos()})
                _t_blocks = Rar.BlockV5(self._io, self, self._root)
                _t_blocks._read()
                self.blocks.append(_t_blocks)
                self._debug['blocks']['arr'][len(self.blocks) - 1]['end'] = self._io.pos()
            self._debug['blocks']['arr'][len(self.blocks) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['blocks']['end'] = self._io.pos()

    class MagicSignature(KaitaiStruct):
        """RAR uses either 7-byte magic for RAR versions 1.5 to 4.0, and
        8-byte magic (and pretty different block format) for v5+. This
        type would parse and validate both versions of signature. Note
        that actually this signature is a valid RAR "block": in theory,
        one can omit signature reading at all, and read this normally,
        as a block, if exact RAR version is known (and thus it's
        possible to choose correct block format).
        """
        SEQ_FIELDS = ["magic1", "version", "magic3"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic1']['start'] = self._io.pos()
            self.magic1 = self._io.read_bytes(6)
            self._debug['magic1']['end'] = self._io.pos()
            if not self.magic1 == b"\x52\x61\x72\x21\x1A\x07":
                raise kaitaistruct.ValidationNotEqualError(b"\x52\x61\x72\x21\x1A\x07", self.magic1, self._io, u"/types/magic_signature/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u1()
            self._debug['version']['end'] = self._io.pos()
            if self.version == 1:
                self._debug['magic3']['start'] = self._io.pos()
                self.magic3 = self._io.read_bytes(1)
                self._debug['magic3']['end'] = self._io.pos()
                if not self.magic3 == b"\x00":
                    raise kaitaistruct.ValidationNotEqualError(b"\x00", self.magic3, self._io, u"/types/magic_signature/seq/2")



    class Block(KaitaiStruct):
        """Basic block that RAR files consist of. There are several block
        types (see `block_type`), which have different `body` and
        `add_body`.
        """
        SEQ_FIELDS = ["crc16", "block_type", "flags", "block_size", "add_size", "body", "add_body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['crc16']['start'] = self._io.pos()
            self.crc16 = self._io.read_u2le()
            self._debug['crc16']['end'] = self._io.pos()
            self._debug['block_type']['start'] = self._io.pos()
            self.block_type = KaitaiStream.resolve_enum(Rar.BlockTypes, self._io.read_u1())
            self._debug['block_type']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u2le()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['block_size']['start'] = self._io.pos()
            self.block_size = self._io.read_u2le()
            self._debug['block_size']['end'] = self._io.pos()
            if self.has_add:
                self._debug['add_size']['start'] = self._io.pos()
                self.add_size = self._io.read_u4le()
                self._debug['add_size']['end'] = self._io.pos()

            self._debug['body']['start'] = self._io.pos()
            _on = self.block_type
            if _on == Rar.BlockTypes.file_header:
                self._raw_body = self._io.read_bytes(self.body_size)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Rar.BlockFileHeader(_io__raw_body, self, self._root)
                self.body._read()
            else:
                self.body = self._io.read_bytes(self.body_size)
            self._debug['body']['end'] = self._io.pos()
            if self.has_add:
                self._debug['add_body']['start'] = self._io.pos()
                self.add_body = self._io.read_bytes(self.add_size)
                self._debug['add_body']['end'] = self._io.pos()


        @property
        def has_add(self):
            """True if block has additional content attached to it."""
            if hasattr(self, '_m_has_add'):
                return self._m_has_add if hasattr(self, '_m_has_add') else None

            self._m_has_add = (self.flags & 32768) != 0
            return self._m_has_add if hasattr(self, '_m_has_add') else None

        @property
        def header_size(self):
            if hasattr(self, '_m_header_size'):
                return self._m_header_size if hasattr(self, '_m_header_size') else None

            self._m_header_size = (11 if self.has_add else 7)
            return self._m_header_size if hasattr(self, '_m_header_size') else None

        @property
        def body_size(self):
            if hasattr(self, '_m_body_size'):
                return self._m_body_size if hasattr(self, '_m_body_size') else None

            self._m_body_size = (self.block_size - self.header_size)
            return self._m_body_size if hasattr(self, '_m_body_size') else None


    class BlockFileHeader(KaitaiStruct):
        SEQ_FIELDS = ["low_unp_size", "host_os", "file_crc32", "file_time", "rar_version", "method", "name_size", "attr", "high_pack_size", "file_name", "salt"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['low_unp_size']['start'] = self._io.pos()
            self.low_unp_size = self._io.read_u4le()
            self._debug['low_unp_size']['end'] = self._io.pos()
            self._debug['host_os']['start'] = self._io.pos()
            self.host_os = KaitaiStream.resolve_enum(Rar.Oses, self._io.read_u1())
            self._debug['host_os']['end'] = self._io.pos()
            self._debug['file_crc32']['start'] = self._io.pos()
            self.file_crc32 = self._io.read_u4le()
            self._debug['file_crc32']['end'] = self._io.pos()
            self._debug['file_time']['start'] = self._io.pos()
            self._raw_file_time = self._io.read_bytes(4)
            _io__raw_file_time = KaitaiStream(BytesIO(self._raw_file_time))
            self.file_time = dos_datetime.DosDatetime(_io__raw_file_time)
            self.file_time._read()
            self._debug['file_time']['end'] = self._io.pos()
            self._debug['rar_version']['start'] = self._io.pos()
            self.rar_version = self._io.read_u1()
            self._debug['rar_version']['end'] = self._io.pos()
            self._debug['method']['start'] = self._io.pos()
            self.method = KaitaiStream.resolve_enum(Rar.Methods, self._io.read_u1())
            self._debug['method']['end'] = self._io.pos()
            self._debug['name_size']['start'] = self._io.pos()
            self.name_size = self._io.read_u2le()
            self._debug['name_size']['end'] = self._io.pos()
            self._debug['attr']['start'] = self._io.pos()
            self.attr = self._io.read_u4le()
            self._debug['attr']['end'] = self._io.pos()
            if (self._parent.flags & 256) != 0:
                self._debug['high_pack_size']['start'] = self._io.pos()
                self.high_pack_size = self._io.read_u4le()
                self._debug['high_pack_size']['end'] = self._io.pos()

            self._debug['file_name']['start'] = self._io.pos()
            self.file_name = self._io.read_bytes(self.name_size)
            self._debug['file_name']['end'] = self._io.pos()
            if (self._parent.flags & 1024) != 0:
                self._debug['salt']['start'] = self._io.pos()
                self.salt = self._io.read_u8le()
                self._debug['salt']['end'] = self._io.pos()



    class BlockV5(KaitaiStruct):
        SEQ_FIELDS = []
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass



