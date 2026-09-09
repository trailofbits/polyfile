# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Cramfs(KaitaiStruct):
    SEQ_FIELDS = ["super_block"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Cramfs, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['super_block']['start'] = self._io.pos()
        self.super_block = Cramfs.SuperBlockStruct(self._io, self, self._root)
        self.super_block._read()
        self._debug['super_block']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.super_block._fetch_instances()

    class ChunkedDataInode(KaitaiStruct):
        SEQ_FIELDS = ["block_end_index", "raw_blocks"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Cramfs.ChunkedDataInode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['block_end_index']['start'] = self._io.pos()
            self._debug['block_end_index']['arr'] = []
            self.block_end_index = []
            for i in range(((self._parent.size + self._root.page_size) - 1) // self._root.page_size):
                self._debug['block_end_index']['arr'].append({'start': self._io.pos()})
                self.block_end_index.append(self._io.read_u4le())
                self._debug['block_end_index']['arr'][i]['end'] = self._io.pos()

            self._debug['block_end_index']['end'] = self._io.pos()
            self._debug['raw_blocks']['start'] = self._io.pos()
            self.raw_blocks = self._io.read_bytes_full()
            self._debug['raw_blocks']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.block_end_index)):
                pass



    class DirInode(KaitaiStruct):
        SEQ_FIELDS = ["children"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Cramfs.DirInode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if self._io.size() > 0:
                pass
                self._debug['children']['start'] = self._io.pos()
                self._debug['children']['arr'] = []
                self.children = []
                i = 0
                while not self._io.is_eof():
                    self._debug['children']['arr'].append({'start': self._io.pos()})
                    _t_children = Cramfs.Inode(self._io, self, self._root)
                    try:
                        _t_children._read()
                    finally:
                        self.children.append(_t_children)
                    self._debug['children']['arr'][len(self.children) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['children']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self._io.size() > 0:
                pass
                for i in range(len(self.children)):
                    pass
                    self.children[i]._fetch_instances()




    class Info(KaitaiStruct):
        SEQ_FIELDS = ["crc", "edition", "blocks", "files"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Cramfs.Info, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['crc']['start'] = self._io.pos()
            self.crc = self._io.read_u4le()
            self._debug['crc']['end'] = self._io.pos()
            self._debug['edition']['start'] = self._io.pos()
            self.edition = self._io.read_u4le()
            self._debug['edition']['end'] = self._io.pos()
            self._debug['blocks']['start'] = self._io.pos()
            self.blocks = self._io.read_u4le()
            self._debug['blocks']['end'] = self._io.pos()
            self._debug['files']['start'] = self._io.pos()
            self.files = self._io.read_u4le()
            self._debug['files']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Inode(KaitaiStruct):

        class FileType(IntEnum):
            fifo = 1
            chrdev = 2
            dir = 4
            blkdev = 6
            reg_file = 8
            symlink = 10
            socket = 12
        SEQ_FIELDS = ["mode", "uid", "size_gid", "namelen_offset", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Cramfs.Inode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['mode']['start'] = self._io.pos()
            self.mode = self._io.read_u2le()
            self._debug['mode']['end'] = self._io.pos()
            self._debug['uid']['start'] = self._io.pos()
            self.uid = self._io.read_u2le()
            self._debug['uid']['end'] = self._io.pos()
            self._debug['size_gid']['start'] = self._io.pos()
            self.size_gid = self._io.read_u4le()
            self._debug['size_gid']['end'] = self._io.pos()
            self._debug['namelen_offset']['start'] = self._io.pos()
            self.namelen_offset = self._io.read_u4le()
            self._debug['namelen_offset']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes(self.namelen)).decode(u"UTF-8")
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.as_dir
            if hasattr(self, '_m_as_dir'):
                pass
                self._m_as_dir._fetch_instances()

            _ = self.as_reg_file
            if hasattr(self, '_m_as_reg_file'):
                pass
                self._m_as_reg_file._fetch_instances()

            _ = self.as_symlink
            if hasattr(self, '_m_as_symlink'):
                pass
                self._m_as_symlink._fetch_instances()


        @property
        def as_dir(self):
            if hasattr(self, '_m_as_dir'):
                return self._m_as_dir

            io = self._root._io
            _pos = io.pos()
            io.seek(self.offset)
            self._debug['_m_as_dir']['start'] = io.pos()
            self._raw__m_as_dir = io.read_bytes(self.size)
            _io__raw__m_as_dir = KaitaiStream(BytesIO(self._raw__m_as_dir))
            self._m_as_dir = Cramfs.DirInode(_io__raw__m_as_dir, self, self._root)
            self._m_as_dir._read()
            self._debug['_m_as_dir']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_as_dir', None)

        @property
        def as_reg_file(self):
            if hasattr(self, '_m_as_reg_file'):
                return self._m_as_reg_file

            io = self._root._io
            _pos = io.pos()
            io.seek(self.offset)
            self._debug['_m_as_reg_file']['start'] = io.pos()
            self._m_as_reg_file = Cramfs.ChunkedDataInode(io, self, self._root)
            self._m_as_reg_file._read()
            self._debug['_m_as_reg_file']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_as_reg_file', None)

        @property
        def as_symlink(self):
            if hasattr(self, '_m_as_symlink'):
                return self._m_as_symlink

            io = self._root._io
            _pos = io.pos()
            io.seek(self.offset)
            self._debug['_m_as_symlink']['start'] = io.pos()
            self._m_as_symlink = Cramfs.ChunkedDataInode(io, self, self._root)
            self._m_as_symlink._read()
            self._debug['_m_as_symlink']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_as_symlink', None)

        @property
        def attr(self):
            if hasattr(self, '_m_attr'):
                return self._m_attr

            self._m_attr = self.mode >> 9 & 7
            return getattr(self, '_m_attr', None)

        @property
        def gid(self):
            if hasattr(self, '_m_gid'):
                return self._m_gid

            self._m_gid = self.size_gid >> 24
            return getattr(self, '_m_gid', None)

        @property
        def namelen(self):
            if hasattr(self, '_m_namelen'):
                return self._m_namelen

            self._m_namelen = (self.namelen_offset & 63) << 2
            return getattr(self, '_m_namelen', None)

        @property
        def offset(self):
            if hasattr(self, '_m_offset'):
                return self._m_offset

            self._m_offset = (self.namelen_offset >> 6 & 67108863) << 2
            return getattr(self, '_m_offset', None)

        @property
        def perm_g(self):
            if hasattr(self, '_m_perm_g'):
                return self._m_perm_g

            self._m_perm_g = self.mode >> 3 & 7
            return getattr(self, '_m_perm_g', None)

        @property
        def perm_o(self):
            if hasattr(self, '_m_perm_o'):
                return self._m_perm_o

            self._m_perm_o = self.mode & 7
            return getattr(self, '_m_perm_o', None)

        @property
        def perm_u(self):
            if hasattr(self, '_m_perm_u'):
                return self._m_perm_u

            self._m_perm_u = self.mode >> 6 & 7
            return getattr(self, '_m_perm_u', None)

        @property
        def size(self):
            if hasattr(self, '_m_size'):
                return self._m_size

            self._m_size = self.size_gid & 16777215
            return getattr(self, '_m_size', None)

        @property
        def type(self):
            if hasattr(self, '_m_type'):
                return self._m_type

            self._m_type = KaitaiStream.resolve_enum(Cramfs.Inode.FileType, self.mode >> 12 & 15)
            return getattr(self, '_m_type', None)


    class SuperBlockStruct(KaitaiStruct):
        SEQ_FIELDS = ["magic", "size", "flags", "future", "signature", "fsid", "name", "root"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Cramfs.SuperBlockStruct, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x45\x3D\xCD\x28":
                raise kaitaistruct.ValidationNotEqualError(b"\x45\x3D\xCD\x28", self.magic, self._io, u"/types/super_block_struct/seq/0")
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u4le()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['future']['start'] = self._io.pos()
            self.future = self._io.read_u4le()
            self._debug['future']['end'] = self._io.pos()
            self._debug['signature']['start'] = self._io.pos()
            self.signature = self._io.read_bytes(16)
            self._debug['signature']['end'] = self._io.pos()
            if not self.signature == b"\x43\x6F\x6D\x70\x72\x65\x73\x73\x65\x64\x20\x52\x4F\x4D\x46\x53":
                raise kaitaistruct.ValidationNotEqualError(b"\x43\x6F\x6D\x70\x72\x65\x73\x73\x65\x64\x20\x52\x4F\x4D\x46\x53", self.signature, self._io, u"/types/super_block_struct/seq/4")
            self._debug['fsid']['start'] = self._io.pos()
            self.fsid = Cramfs.Info(self._io, self, self._root)
            self.fsid._read()
            self._debug['fsid']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes(16)).decode(u"ASCII")
            self._debug['name']['end'] = self._io.pos()
            self._debug['root']['start'] = self._io.pos()
            self.root = Cramfs.Inode(self._io, self, self._root)
            self.root._read()
            self._debug['root']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.fsid._fetch_instances()
            self.root._fetch_instances()

        @property
        def flag_fsid_v2(self):
            if hasattr(self, '_m_flag_fsid_v2'):
                return self._m_flag_fsid_v2

            self._m_flag_fsid_v2 = self.flags >> 0 & 1
            return getattr(self, '_m_flag_fsid_v2', None)

        @property
        def flag_holes(self):
            if hasattr(self, '_m_flag_holes'):
                return self._m_flag_holes

            self._m_flag_holes = self.flags >> 8 & 1
            return getattr(self, '_m_flag_holes', None)

        @property
        def flag_shifted_root_offset(self):
            if hasattr(self, '_m_flag_shifted_root_offset'):
                return self._m_flag_shifted_root_offset

            self._m_flag_shifted_root_offset = self.flags >> 10 & 1
            return getattr(self, '_m_flag_shifted_root_offset', None)

        @property
        def flag_sorted_dirs(self):
            if hasattr(self, '_m_flag_sorted_dirs'):
                return self._m_flag_sorted_dirs

            self._m_flag_sorted_dirs = self.flags >> 1 & 1
            return getattr(self, '_m_flag_sorted_dirs', None)

        @property
        def flag_wrong_signature(self):
            if hasattr(self, '_m_flag_wrong_signature'):
                return self._m_flag_wrong_signature

            self._m_flag_wrong_signature = self.flags >> 9 & 1
            return getattr(self, '_m_flag_wrong_signature', None)


    @property
    def page_size(self):
        if hasattr(self, '_m_page_size'):
            return self._m_page_size

        self._m_page_size = 4096
        return getattr(self, '_m_page_size', None)


