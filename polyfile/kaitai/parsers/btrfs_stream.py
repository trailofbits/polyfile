# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class BtrfsStream(KaitaiStruct):
    """Btrfs is a copy on write file system based on B-trees focusing on fault tolerance, repair and easy
    administration. Btrfs is intended to address the lack of pooling, snapshots, checksums, and
    integral multi-device spanning in Linux file systems.
    Given any pair of subvolumes (or snapshots), Btrfs can generate a binary diff between them by
    using the `btrfs send` command that can be replayed later by using `btrfs receive`, possibly on a
    different Btrfs file system. The `btrfs send` command creates a set of data modifications required
    for converting one subvolume into another.
    This spec can be used to disassemble the binary diff created by the `btrfs send` command.
    If you want a text representation you may want to checkout `btrfs receive --dump` instead.
    
    .. seealso::
       Source - https://archive.kernel.org/oldwiki/btrfs.wiki.kernel.org/index.php/Design_notes_on_Send/Receive.html
    """

    class Attribute(IntEnum):
        unspec = 0
        uuid = 1
        ctransid = 2
        ino = 3
        size = 4
        mode = 5
        uid = 6
        gid = 7
        rdev = 8
        ctime = 9
        mtime = 10
        atime = 11
        otime = 12
        xattr_name = 13
        xattr_data = 14
        path = 15
        path_to = 16
        path_link = 17
        file_offset = 18
        data = 19
        clone_uuid = 20
        clone_ctransid = 21
        clone_path = 22
        clone_offset = 23
        clone_len = 24

    class Command(IntEnum):
        unspec = 0
        subvol = 1
        snapshot = 2
        mkfile = 3
        mkdir = 4
        mknod = 5
        mkfifo = 6
        mksock = 7
        symlink = 8
        rename = 9
        link = 10
        unlink = 11
        rmdir = 12
        set_xattr = 13
        remove_xattr = 14
        write = 15
        clone = 16
        truncate = 17
        chmod = 18
        chown = 19
        utimes = 20
        end = 21
        update_extent = 22
    SEQ_FIELDS = ["header", "commands"]
    def __init__(self, _io, _parent=None, _root=None):
        super(BtrfsStream, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = BtrfsStream.SendStreamHeader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['commands']['start'] = self._io.pos()
        self._debug['commands']['arr'] = []
        self.commands = []
        i = 0
        while not self._io.is_eof():
            self._debug['commands']['arr'].append({'start': self._io.pos()})
            _t_commands = BtrfsStream.SendCommand(self._io, self, self._root)
            try:
                _t_commands._read()
            finally:
                self.commands.append(_t_commands)
            self._debug['commands']['arr'][len(self.commands) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['commands']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()
        for i in range(len(self.commands)):
            pass
            self.commands[i]._fetch_instances()


    class SendCommand(KaitaiStruct):
        SEQ_FIELDS = ["len_data", "type", "checksum", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(BtrfsStream.SendCommand, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(BtrfsStream.Command, self._io.read_u2le())
            self._debug['type']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_bytes(4)
            self._debug['checksum']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self._raw_data = self._io.read_bytes(self.len_data)
            _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
            self.data = BtrfsStream.SendCommand.Tlvs(_io__raw_data, self, self._root)
            self.data._read()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.data._fetch_instances()

        class String(KaitaiStruct):
            SEQ_FIELDS = ["string"]
            def __init__(self, _io, _parent=None, _root=None):
                super(BtrfsStream.SendCommand.String, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['string']['start'] = self._io.pos()
                self.string = (self._io.read_bytes_full()).decode(u"UTF-8")
                self._debug['string']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class Timespec(KaitaiStruct):
            SEQ_FIELDS = ["ts_sec", "ts_nsec"]
            def __init__(self, _io, _parent=None, _root=None):
                super(BtrfsStream.SendCommand.Timespec, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['ts_sec']['start'] = self._io.pos()
                self.ts_sec = self._io.read_s8le()
                self._debug['ts_sec']['end'] = self._io.pos()
                self._debug['ts_nsec']['start'] = self._io.pos()
                self.ts_nsec = self._io.read_s4le()
                self._debug['ts_nsec']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class Tlv(KaitaiStruct):
            SEQ_FIELDS = ["type", "length", "value"]
            def __init__(self, _io, _parent=None, _root=None):
                super(BtrfsStream.SendCommand.Tlv, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(BtrfsStream.Attribute, self._io.read_u2le())
                self._debug['type']['end'] = self._io.pos()
                self._debug['length']['start'] = self._io.pos()
                self.length = self._io.read_u2le()
                self._debug['length']['end'] = self._io.pos()
                self._debug['value']['start'] = self._io.pos()
                _on = self.type
                if _on == BtrfsStream.Attribute.atime:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Timespec(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.clone_ctransid:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.clone_len:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.clone_offset:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.clone_path:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.String(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.clone_uuid:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Uuid(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.ctime:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Timespec(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.ctransid:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.file_offset:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.gid:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.mode:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.mtime:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Timespec(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.otime:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Timespec(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.path:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.String(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.path_link:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.String(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.path_to:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.String(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.rdev:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.size:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.uid:
                    pass
                    self.value = self._io.read_u8le()
                elif _on == BtrfsStream.Attribute.uuid:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.Uuid(_io__raw_value, self, self._root)
                    self.value._read()
                elif _on == BtrfsStream.Attribute.xattr_name:
                    pass
                    self._raw_value = self._io.read_bytes(self.length)
                    _io__raw_value = KaitaiStream(BytesIO(self._raw_value))
                    self.value = BtrfsStream.SendCommand.String(_io__raw_value, self, self._root)
                    self.value._read()
                else:
                    pass
                    self.value = self._io.read_bytes(self.length)
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _on = self.type
                if _on == BtrfsStream.Attribute.atime:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.clone_ctransid:
                    pass
                elif _on == BtrfsStream.Attribute.clone_len:
                    pass
                elif _on == BtrfsStream.Attribute.clone_offset:
                    pass
                elif _on == BtrfsStream.Attribute.clone_path:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.clone_uuid:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.ctime:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.ctransid:
                    pass
                elif _on == BtrfsStream.Attribute.file_offset:
                    pass
                elif _on == BtrfsStream.Attribute.gid:
                    pass
                elif _on == BtrfsStream.Attribute.mode:
                    pass
                elif _on == BtrfsStream.Attribute.mtime:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.otime:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.path:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.path_link:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.path_to:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.rdev:
                    pass
                elif _on == BtrfsStream.Attribute.size:
                    pass
                elif _on == BtrfsStream.Attribute.uid:
                    pass
                elif _on == BtrfsStream.Attribute.uuid:
                    pass
                    self.value._fetch_instances()
                elif _on == BtrfsStream.Attribute.xattr_name:
                    pass
                    self.value._fetch_instances()
                else:
                    pass


        class Tlvs(KaitaiStruct):
            SEQ_FIELDS = ["tlv"]
            def __init__(self, _io, _parent=None, _root=None):
                super(BtrfsStream.SendCommand.Tlvs, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['tlv']['start'] = self._io.pos()
                self._debug['tlv']['arr'] = []
                self.tlv = []
                i = 0
                while not self._io.is_eof():
                    self._debug['tlv']['arr'].append({'start': self._io.pos()})
                    _t_tlv = BtrfsStream.SendCommand.Tlv(self._io, self, self._root)
                    try:
                        _t_tlv._read()
                    finally:
                        self.tlv.append(_t_tlv)
                    self._debug['tlv']['arr'][len(self.tlv) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['tlv']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.tlv)):
                    pass
                    self.tlv[i]._fetch_instances()



        class Uuid(KaitaiStruct):
            SEQ_FIELDS = ["uuid"]
            def __init__(self, _io, _parent=None, _root=None):
                super(BtrfsStream.SendCommand.Uuid, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['uuid']['start'] = self._io.pos()
                self.uuid = self._io.read_bytes(16)
                self._debug['uuid']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass



    class SendStreamHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version"]
        def __init__(self, _io, _parent=None, _root=None):
            super(BtrfsStream.SendStreamHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(13)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x62\x74\x72\x66\x73\x2D\x73\x74\x72\x65\x61\x6D\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x62\x74\x72\x66\x73\x2D\x73\x74\x72\x65\x61\x6D\x00", self.magic, self._io, u"/types/send_stream_header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4le()
            self._debug['version']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



