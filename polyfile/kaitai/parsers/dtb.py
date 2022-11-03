# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

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

    class Fdt(Enum):
        begin_node = 1
        end_node = 2
        prop = 3
        nop = 4
        end = 9
    SEQ_FIELDS = ["magic", "total_size", "ofs_structure_block", "ofs_strings_block", "ofs_memory_reservation_block", "version", "min_compatible_version", "boot_cpuid_phys", "len_strings_block", "len_structure_block"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
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

    class MemoryBlock(KaitaiStruct):
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self.entries = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['entries']:
                    self._debug['entries']['arr'] = []
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = Dtb.MemoryBlockEntry(self._io, self, self._root)
                _t_entries._read()
                self.entries.append(_t_entries)
                self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['entries']['end'] = self._io.pos()


    class FdtBlock(KaitaiStruct):
        SEQ_FIELDS = ["nodes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['nodes']['start'] = self._io.pos()
            self.nodes = []
            i = 0
            while True:
                if not 'arr' in self._debug['nodes']:
                    self._debug['nodes']['arr'] = []
                self._debug['nodes']['arr'].append({'start': self._io.pos()})
                _t_nodes = Dtb.FdtNode(self._io, self, self._root)
                _t_nodes._read()
                _ = _t_nodes
                self.nodes.append(_)
                self._debug['nodes']['arr'][len(self.nodes) - 1]['end'] = self._io.pos()
                if _.type == Dtb.Fdt.end:
                    break
                i += 1
            self._debug['nodes']['end'] = self._io.pos()


    class MemoryBlockEntry(KaitaiStruct):
        SEQ_FIELDS = ["address", "size"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['address']['start'] = self._io.pos()
            self.address = self._io.read_u8be()
            self._debug['address']['end'] = self._io.pos()
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u8be()
            self._debug['size']['end'] = self._io.pos()


    class Strings(KaitaiStruct):
        SEQ_FIELDS = ["strings"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['strings']['start'] = self._io.pos()
            self.strings = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['strings']:
                    self._debug['strings']['arr'] = []
                self._debug['strings']['arr'].append({'start': self._io.pos()})
                self.strings.append((self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII"))
                self._debug['strings']['arr'][len(self.strings) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['strings']['end'] = self._io.pos()


    class FdtProp(KaitaiStruct):
        SEQ_FIELDS = ["len_property", "ofs_name", "property", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
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
            self.padding = self._io.read_bytes((-(self._io.pos()) % 4))
            self._debug['padding']['end'] = self._io.pos()

        @property
        def name(self):
            if hasattr(self, '_m_name'):
                return self._m_name if hasattr(self, '_m_name') else None

            io = self._root.strings_block._io
            _pos = io.pos()
            io.seek(self.ofs_name)
            self._debug['_m_name']['start'] = io.pos()
            self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['_m_name']['end'] = io.pos()
            io.seek(_pos)
            return self._m_name if hasattr(self, '_m_name') else None


    class FdtNode(KaitaiStruct):
        SEQ_FIELDS = ["type", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(Dtb.Fdt, self._io.read_u4be())
            self._debug['type']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == Dtb.Fdt.begin_node:
                self.body = Dtb.FdtBeginNode(self._io, self, self._root)
                self.body._read()
            elif _on == Dtb.Fdt.prop:
                self.body = Dtb.FdtProp(self._io, self, self._root)
                self.body._read()
            self._debug['body']['end'] = self._io.pos()


    class FdtBeginNode(KaitaiStruct):
        SEQ_FIELDS = ["name", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['name']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_bytes((-(self._io.pos()) % 4))
            self._debug['padding']['end'] = self._io.pos()


    @property
    def memory_reservation_block(self):
        if hasattr(self, '_m_memory_reservation_block'):
            return self._m_memory_reservation_block if hasattr(self, '_m_memory_reservation_block') else None

        _pos = self._io.pos()
        self._io.seek(self.ofs_memory_reservation_block)
        self._debug['_m_memory_reservation_block']['start'] = self._io.pos()
        self._raw__m_memory_reservation_block = self._io.read_bytes((self.ofs_structure_block - self.ofs_memory_reservation_block))
        _io__raw__m_memory_reservation_block = KaitaiStream(BytesIO(self._raw__m_memory_reservation_block))
        self._m_memory_reservation_block = Dtb.MemoryBlock(_io__raw__m_memory_reservation_block, self, self._root)
        self._m_memory_reservation_block._read()
        self._debug['_m_memory_reservation_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_memory_reservation_block if hasattr(self, '_m_memory_reservation_block') else None

    @property
    def structure_block(self):
        if hasattr(self, '_m_structure_block'):
            return self._m_structure_block if hasattr(self, '_m_structure_block') else None

        _pos = self._io.pos()
        self._io.seek(self.ofs_structure_block)
        self._debug['_m_structure_block']['start'] = self._io.pos()
        self._raw__m_structure_block = self._io.read_bytes(self.len_structure_block)
        _io__raw__m_structure_block = KaitaiStream(BytesIO(self._raw__m_structure_block))
        self._m_structure_block = Dtb.FdtBlock(_io__raw__m_structure_block, self, self._root)
        self._m_structure_block._read()
        self._debug['_m_structure_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_structure_block if hasattr(self, '_m_structure_block') else None

    @property
    def strings_block(self):
        if hasattr(self, '_m_strings_block'):
            return self._m_strings_block if hasattr(self, '_m_strings_block') else None

        _pos = self._io.pos()
        self._io.seek(self.ofs_strings_block)
        self._debug['_m_strings_block']['start'] = self._io.pos()
        self._raw__m_strings_block = self._io.read_bytes(self.len_strings_block)
        _io__raw__m_strings_block = KaitaiStream(BytesIO(self._raw__m_strings_block))
        self._m_strings_block = Dtb.Strings(_io__raw__m_strings_block, self, self._root)
        self._m_strings_block._read()
        self._debug['_m_strings_block']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_strings_block if hasattr(self, '_m_strings_block') else None


