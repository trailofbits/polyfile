# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class BroadcomTrx(KaitaiStruct):
    """.trx file format is widely used for distribution of firmware
    updates for Broadcom devices. The most well-known are ASUS routers.
    
    Fundamentally, it includes a footer which acts as a safeguard
    against installing a firmware package on a wrong hardware model or
    version, and a header which list numerous partitions packaged inside
    a single .trx file.
    
    trx files not necessarily contain all these headers.
    
    .. seealso::
       Source - https://github.com/openwrt/openwrt/blob/3f5619f/tools/firmware-utils/src/trx.c
    
    
    .. seealso::
       Source - https://web.archive.org/web/20190127154419/https://openwrt.org/docs/techref/header
    
    
    .. seealso::
       Source - https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/mtd/partitions/brcm,trx.txt
    """
    SEQ_FIELDS = []
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        pass

    class Revision(KaitaiStruct):
        SEQ_FIELDS = ["major", "minor"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['major']['start'] = self._io.pos()
            self.major = self._io.read_u1()
            self._debug['major']['end'] = self._io.pos()
            self._debug['minor']['start'] = self._io.pos()
            self.minor = self._io.read_u1()
            self._debug['minor']['end'] = self._io.pos()


    class Version(KaitaiStruct):
        SEQ_FIELDS = ["major", "minor", "patch", "tweak"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['major']['start'] = self._io.pos()
            self.major = self._io.read_u1()
            self._debug['major']['end'] = self._io.pos()
            self._debug['minor']['start'] = self._io.pos()
            self.minor = self._io.read_u1()
            self._debug['minor']['end'] = self._io.pos()
            self._debug['patch']['start'] = self._io.pos()
            self.patch = self._io.read_u1()
            self._debug['patch']['end'] = self._io.pos()
            self._debug['tweak']['start'] = self._io.pos()
            self.tweak = self._io.read_u1()
            self._debug['tweak']['end'] = self._io.pos()


    class Tail(KaitaiStruct):
        """A safeguard against installation of firmware to an incompatible device."""
        SEQ_FIELDS = ["version", "product_id", "comp_hw", "reserved"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = BroadcomTrx.Version(self._io, self, self._root)
            self.version._read()
            self._debug['version']['end'] = self._io.pos()
            self._debug['product_id']['start'] = self._io.pos()
            self.product_id = (KaitaiStream.bytes_terminate(self._io.read_bytes(12), 0, False)).decode(u"utf-8")
            self._debug['product_id']['end'] = self._io.pos()
            self._debug['comp_hw']['start'] = self._io.pos()
            self.comp_hw = [None] * (4)
            for i in range(4):
                if not 'arr' in self._debug['comp_hw']:
                    self._debug['comp_hw']['arr'] = []
                self._debug['comp_hw']['arr'].append({'start': self._io.pos()})
                _t_comp_hw = BroadcomTrx.Tail.HwCompInfo(self._io, self, self._root)
                _t_comp_hw._read()
                self.comp_hw[i] = _t_comp_hw
                self._debug['comp_hw']['arr'][i]['end'] = self._io.pos()

            self._debug['comp_hw']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bytes(32)
            self._debug['reserved']['end'] = self._io.pos()

        class HwCompInfo(KaitaiStruct):
            SEQ_FIELDS = ["min", "max"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['min']['start'] = self._io.pos()
                self.min = BroadcomTrx.Revision(self._io, self, self._root)
                self.min._read()
                self._debug['min']['end'] = self._io.pos()
                self._debug['max']['start'] = self._io.pos()
                self.max = BroadcomTrx.Revision(self._io, self, self._root)
                self.max._read()
                self._debug['max']['end'] = self._io.pos()



    class Header(KaitaiStruct):
        SEQ_FIELDS = ["magic", "len", "crc32", "version", "flags", "partitions"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x48\x44\x52\x30":
                raise kaitaistruct.ValidationNotEqualError(b"\x48\x44\x52\x30", self.magic, self._io, u"/types/header/seq/0")
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['crc32']['start'] = self._io.pos()
            self.crc32 = self._io.read_u4le()
            self._debug['crc32']['end'] = self._io.pos()
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u2le()
            self._debug['version']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = BroadcomTrx.Header.Flags(self._io, self, self._root)
            self.flags._read()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['partitions']['start'] = self._io.pos()
            self.partitions = []
            i = 0
            while True:
                if not 'arr' in self._debug['partitions']:
                    self._debug['partitions']['arr'] = []
                self._debug['partitions']['arr'].append({'start': self._io.pos()})
                _t_partitions = BroadcomTrx.Header.Partition(i, self._io, self, self._root)
                _t_partitions._read()
                _ = _t_partitions
                self.partitions.append(_)
                self._debug['partitions']['arr'][len(self.partitions) - 1]['end'] = self._io.pos()
                if  ((i >= 4) or (not (_.is_present))) :
                    break
                i += 1
            self._debug['partitions']['end'] = self._io.pos()

        class Partition(KaitaiStruct):
            SEQ_FIELDS = ["ofs_body"]
            def __init__(self, idx, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.idx = idx
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['ofs_body']['start'] = self._io.pos()
                self.ofs_body = self._io.read_u4le()
                self._debug['ofs_body']['end'] = self._io.pos()

            @property
            def is_present(self):
                if hasattr(self, '_m_is_present'):
                    return self._m_is_present if hasattr(self, '_m_is_present') else None

                self._m_is_present = self.ofs_body != 0
                return self._m_is_present if hasattr(self, '_m_is_present') else None

            @property
            def is_last(self):
                if hasattr(self, '_m_is_last'):
                    return self._m_is_last if hasattr(self, '_m_is_last') else None

                if self.is_present:
                    self._m_is_last =  ((self.idx == (len(self._parent.partitions) - 1)) or (not (self._parent.partitions[(self.idx + 1)].is_present))) 

                return self._m_is_last if hasattr(self, '_m_is_last') else None

            @property
            def len_body(self):
                if hasattr(self, '_m_len_body'):
                    return self._m_len_body if hasattr(self, '_m_len_body') else None

                if self.is_present:
                    self._m_len_body = ((self._root._io.size() - self.ofs_body) if self.is_last else self._parent.partitions[(self.idx + 1)].ofs_body)

                return self._m_len_body if hasattr(self, '_m_len_body') else None

            @property
            def body(self):
                if hasattr(self, '_m_body'):
                    return self._m_body if hasattr(self, '_m_body') else None

                if self.is_present:
                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self.ofs_body)
                    self._debug['_m_body']['start'] = io.pos()
                    self._m_body = io.read_bytes(self.len_body)
                    self._debug['_m_body']['end'] = io.pos()
                    io.seek(_pos)

                return self._m_body if hasattr(self, '_m_body') else None


        class Flags(KaitaiStruct):
            SEQ_FIELDS = ["flags"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['flags']['start'] = self._io.pos()
                self.flags = [None] * (16)
                for i in range(16):
                    if not 'arr' in self._debug['flags']:
                        self._debug['flags']['arr'] = []
                    self._debug['flags']['arr'].append({'start': self._io.pos()})
                    self.flags[i] = self._io.read_bits_int_le(1) != 0
                    self._debug['flags']['arr'][i]['end'] = self._io.pos()

                self._debug['flags']['end'] = self._io.pos()



    @property
    def header(self):
        if hasattr(self, '_m_header'):
            return self._m_header if hasattr(self, '_m_header') else None

        _pos = self._io.pos()
        self._io.seek(0)
        self._debug['_m_header']['start'] = self._io.pos()
        self._m_header = BroadcomTrx.Header(self._io, self, self._root)
        self._m_header._read()
        self._debug['_m_header']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_header if hasattr(self, '_m_header') else None

    @property
    def tail(self):
        if hasattr(self, '_m_tail'):
            return self._m_tail if hasattr(self, '_m_tail') else None

        _pos = self._io.pos()
        self._io.seek((self._io.size() - 64))
        self._debug['_m_tail']['start'] = self._io.pos()
        self._m_tail = BroadcomTrx.Tail(self._io, self, self._root)
        self._m_tail._read()
        self._debug['_m_tail']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_tail if hasattr(self, '_m_tail') else None


