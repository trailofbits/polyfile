# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Dtb(KaitaiStruct):
    """Also referred to as Devicetree Blob (DTB). It is a flat binary encoding
    of data (primarily devicetree data, although other data is possible as well).
    The data is internally stored as a tree of named nodes and properties. Nodes
    contain properties and child nodes, while properties are name-value pairs.
    
    The Devicetree Blobs (`.dtb` files) are compiled from the Devicetree Source
    files (`.dts`) through the Devicetree compiler (DTC).
    
    On Linux systems that support this, the blobs can be accessed in
    `/sys/firmware/fdt`:
    
    * <https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-firmware-ofw>
    
    The encoding of strings used in the `strings_block` and `structure_block` is
    actually a subset of ASCII:
    
    <https://devicetree-specification.readthedocs.io/en/v0.3/devicetree-basics.html#node-names>
    
    Example files:
    
    * <https://github.com/qemu/qemu/tree/master/pc-bios>
    
    .. seealso::
       Source - https://devicetree-specification.readthedocs.io/en/v0.3/flattened-format.html
    
    
    .. seealso::
       Source - https://elinux.org/images/f/f4/Elc2013_Fernandes.pdf
    """

    class Fdt(IntEnum):
        begin_node = 1
        end_node = 2
        prop = 3
        nop = 4
        end = 9
    SEQ_FIELDS = ["magic", "total_size", "ofs_structure_block", "ofs_strings_block", "ofs_memory_reservation_block", "version", "min_compatible_version", "boot_cpuid_phys", "len_strings_block", "len_structure_block"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Dtb, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\xD0\x0D\xFE\xED":
            raise kaitaistruct.ValidationNotEqualError(b"\xD0\x0D\xFE\xED", self.magic, self._io, u"/seq/0")
        self._debug['total_size']['start'] = self._io.pos()
        self.total_size = self._io.read_u4be()
        self._debug['total_size']['end'] = self._io.pos()
        self._debug['ofs_structure_block']['start'] = self._io.pos()
        self.ofs_structure_block = self._io.read_u4be()
        self._debug['ofs_structure_block']['end'] = self._io.pos()
        self._debug['ofs_strings_block']['start'] = self._io.pos()
        self.ofs_strings_block = self._io.read_u4be()
        self._debug['ofs_strings_block']['end'] = self._io.pos()
        self._debug['ofs_memory_reservation_block']['start'] = self._io.pos()
        self.ofs_memory_reservation_block = self._io.read_u4be()
        self._debug['ofs_memory_reservation_block']['end'] = self._io.pos()
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u4be()
        self._debug['version']['end'] = self._io.pos()
        self._debug['min_compatible_version']['start'] = self._io.pos()
        self.min_compatible_version = self._io.read_u4be()
        self._debug['min_compatible_version']['end'] = self._io.pos()
        if not self.min_compatible_version <= self.version:
            raise kaitaistruct.ValidationGreaterThanError(self.version, self.min_compatible_version, self._io, u"/seq/6")
        self._debug['boot_cpuid_phys']['start'] = self._io.pos()
        self.boot_cpuid_phys = self._io.read_u4be()
        self._debug['boot_cpuid_phys']['end'] = self._io.pos()
        self._debug['len_strings_block']['start'] = self._io.pos()
        self.len_strings_block = self._io.read_u4be()
        self._debug['len_strings_block']['end'] = self._io.pos()
        self._debug['len_structure_block']['start'] = self._io.pos()
        self.len_structure_block = self._io.read_u4be()
        self._debug['len_structure_block']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        _ = self.memory_reservation_block
        if hasattr(self, '_m_memory_reservation_block'):
            pass
            self._m_memory_reservation_block._fetch_instances()

        _ = self.strings_block
        if hasattr(self, '_m_strings_block'):
            pass
            self._m_strings_block._fetch_instances()

        _ = self.structure_block
        if hasattr(self, '_m_structure_block'):
            pass
            self._m_structure_block._fetch_instances()


    class FdtBeginNode(KaitaiStruct):
        SEQ_FIELDS = ["name", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.FdtBeginNode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['name']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_bytes(-(self._io.pos()) % 4)
            self._debug['padding']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class FdtBlock(KaitaiStruct):
        SEQ_FIELDS = ["nodes"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.FdtBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['nodes']['start'] = self._io.pos()
            self._debug['nodes']['arr'] = []
            self.nodes = []
            i = 0
            while True:
                self._debug['nodes']['arr'].append({'start': self._io.pos()})
                _t_nodes = Dtb.FdtNode(self._io, self, self._root)
                try:
                    _t_nodes._read()
                finally:
                    _ = _t_nodes
                    self.nodes.append(_)
                self._debug['nodes']['arr'][len(self.nodes) - 1]['end'] = self._io.pos()
                if _.type == Dtb.Fdt.end:
                    break
                i += 1
            self._debug['nodes']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.nodes)):
                pass
                self.nodes[i]._fetch_instances()



    class FdtNode(KaitaiStruct):
        SEQ_FIELDS = ["type", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.FdtNode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(Dtb.Fdt, self._io.read_u4be())
            self._debug['type']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == Dtb.Fdt.begin_node:
                pass
                self.body = Dtb.FdtBeginNode(self._io, self, self._root)
                self.body._read()
            elif _on == Dtb.Fdt.prop:
                pass
                self.body = Dtb.FdtProp(self._io, self, self._root)
                self.body._read()
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.type
            if _on == Dtb.Fdt.begin_node:
                pass
                self.body._fetch_instances()
            elif _on == Dtb.Fdt.prop:
                pass
                self.body._fetch_instances()


    class FdtProp(KaitaiStruct):
        SEQ_FIELDS = ["len_property", "ofs_name", "property", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.FdtProp, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_property']['start'] = self._io.pos()
            self.len_property = self._io.read_u4be()
            self._debug['len_property']['end'] = self._io.pos()
            self._debug['ofs_name']['start'] = self._io.pos()
            self.ofs_name = self._io.read_u4be()
            self._debug['ofs_name']['end'] = self._io.pos()
            self._debug['property']['start'] = self._io.pos()
            self.property = self._io.read_bytes(self.len_property)
            self._debug['property']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_bytes(-(self._io.pos()) % 4)
            self._debug['padding']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.name
            if hasattr(self, '_m_name'):
                pass


        @property
        def name(self):
            if hasattr(self, '_m_name'):
                return self._m_name

            io = self._root.strings_block._io
            _pos = io.pos()
            io.seek(self.ofs_name)
            self._debug['_m_name']['start'] = io.pos()
            self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['_m_name']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_name', None)


    class MemoryBlock(KaitaiStruct):
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.MemoryBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self._debug['entries']['arr'] = []
            self.entries = []
            i = 0
            while not self._io.is_eof():
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = Dtb.MemoryBlockEntry(self._io, self, self._root)
                try:
                    _t_entries._read()
                finally:
                    self.entries.append(_t_entries)
                self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['entries']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class MemoryBlockEntry(KaitaiStruct):
        SEQ_FIELDS = ["address", "size"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.MemoryBlockEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['address']['start'] = self._io.pos()
            self.address = self._io.read_u8be()
            self._debug['address']['end'] = self._io.pos()
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u8be()
            self._debug['size']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Strings(KaitaiStruct):
        SEQ_FIELDS = ["strings"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Dtb.Strings, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['strings']['start'] = self._io.pos()
            self._debug['strings']['arr'] = []
            self.strings = []
            i = 0
            while not self._io.is_eof():
                self._debug['strings']['arr'].append({'start': self._io.pos()})
                self.strings.append((self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII"))
                self._debug['strings']['arr'][len(self.strings) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['strings']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.strings)):
                pass



    @property
    def memory_reservation_block(self):
        if hasattr(self, '_m_memory_reservation_block'):
            return self._m_memory_reservation_block

        _pos = self._io.pos()
        self._io.seek(self.ofs_memory_reservation_block)
        self._debug['_m_memory_reservation_block']['start'] = self._io.pos()
        self._raw__m_memory_reservation_block = self._io.read_bytes(self.ofs_structure_block - self.ofs_memory_reservation_block)
        _io__raw__m_memory_reservation_block = KaitaiStream(BytesIO(self._raw__m_memory_reservation_block))
        self._m_memory_reservation_block = Dtb.MemoryBlock(_io__raw__m_memory_reservation_block, self, self._root)
        self._m_memory_reservation_block._read()
        self._debug['_m_memory_reservation_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_memory_reservation_block', None)

    @property
    def strings_block(self):
        if hasattr(self, '_m_strings_block'):
            return self._m_strings_block

        _pos = self._io.pos()
        self._io.seek(self.ofs_strings_block)
        self._debug['_m_strings_block']['start'] = self._io.pos()
        self._raw__m_strings_block = self._io.read_bytes(self.len_strings_block)
        _io__raw__m_strings_block = KaitaiStream(BytesIO(self._raw__m_strings_block))
        self._m_strings_block = Dtb.Strings(_io__raw__m_strings_block, self, self._root)
        self._m_strings_block._read()
        self._debug['_m_strings_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_strings_block', None)

    @property
    def structure_block(self):
        if hasattr(self, '_m_structure_block'):
            return self._m_structure_block

        _pos = self._io.pos()
        self._io.seek(self.ofs_structure_block)
        self._debug['_m_structure_block']['start'] = self._io.pos()
        self._raw__m_structure_block = self._io.read_bytes(self.len_structure_block)
        _io__raw__m_structure_block = KaitaiStream(BytesIO(self._raw__m_structure_block))
        self._m_structure_block = Dtb.FdtBlock(_io__raw__m_structure_block, self, self._root)
        self._m_structure_block._read()
        self._debug['_m_structure_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_structure_block', None)


