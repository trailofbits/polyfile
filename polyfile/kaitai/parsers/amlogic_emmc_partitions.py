# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class AmlogicEmmcPartitions(KaitaiStruct):
    """This is an unnamed and undocumented partition table format implemented by
    the bootloader and kernel that Amlogic provides for their Linux SoCs (Meson
    series at least, and probably others). They appear to use this rather than GPT,
    the industry standard, because their BootROM loads and executes the next stage
    loader from offset 512 (0x200) on the eMMC, which is exactly where the GPT
    header would have to start. So instead of changing their BootROM, Amlogic
    devised this partition table, which lives at an offset of 36MiB (0x240_0000)
    on the eMMC and so doesn't conflict. This parser expects as input just the
    partition table from that offset. The maximum number of partitions in a table
    is 32, which corresponds to a maximum table size of 1304 bytes (0x518).
    
    .. seealso::
       Source - http://aml-code.amlogic.com/kernel/common.git/tree/include/linux/mmc/emmc_partitions.h?id=18a4a87072ababf76ea08c8539e939b5b8a440ef
    
    
    .. seealso::
       Source - http://aml-code.amlogic.com/kernel/common.git/tree/drivers/amlogic/mmc/emmc_partitions.c?id=18a4a87072ababf76ea08c8539e939b5b8a440ef
    """
    SEQ_FIELDS = ["magic", "version", "num_partitions", "checksum", "partitions"]
    def __init__(self, _io, _parent=None, _root=None):
        super(AmlogicEmmcPartitions, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x4D\x50\x54\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x4D\x50\x54\x00", self.magic, self._io, u"/seq/0")
        self._debug['version']['start'] = self._io.pos()
        self.version = (KaitaiStream.bytes_terminate(self._io.read_bytes(12), 0, False)).decode(u"UTF-8")
        self._debug['version']['end'] = self._io.pos()
        self._debug['num_partitions']['start'] = self._io.pos()
        self.num_partitions = self._io.read_s4le()
        self._debug['num_partitions']['end'] = self._io.pos()
        if not self.num_partitions >= 1:
            raise kaitaistruct.ValidationLessThanError(1, self.num_partitions, self._io, u"/seq/2")
        if not self.num_partitions <= 32:
            raise kaitaistruct.ValidationGreaterThanError(32, self.num_partitions, self._io, u"/seq/2")
        self._debug['checksum']['start'] = self._io.pos()
        self.checksum = self._io.read_u4le()
        self._debug['checksum']['end'] = self._io.pos()
        self._debug['partitions']['start'] = self._io.pos()
        self._debug['partitions']['arr'] = []
        self.partitions = []
        for i in range(self.num_partitions):
            self._debug['partitions']['arr'].append({'start': self._io.pos()})
            _t_partitions = AmlogicEmmcPartitions.Partition(self._io, self, self._root)
            try:
                _t_partitions._read()
            finally:
                self.partitions.append(_t_partitions)
            self._debug['partitions']['arr'][i]['end'] = self._io.pos()

        self._debug['partitions']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.partitions)):
            pass
            self.partitions[i]._fetch_instances()


    class Partition(KaitaiStruct):
        SEQ_FIELDS = ["name", "size", "offset", "flags", "padding"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AmlogicEmmcPartitions.Partition, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(16), 0, False)).decode(u"UTF-8")
            self._debug['name']['end'] = self._io.pos()
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u8le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u8le()
            self._debug['offset']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self._raw_flags = self._io.read_bytes(4)
            _io__raw_flags = KaitaiStream(BytesIO(self._raw_flags))
            self.flags = AmlogicEmmcPartitions.Partition.PartFlags(_io__raw_flags, self, self._root)
            self.flags._read()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_bytes(4)
            self._debug['padding']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.flags._fetch_instances()

        class PartFlags(KaitaiStruct):
            SEQ_FIELDS = ["is_code", "is_cache", "is_data"]
            def __init__(self, _io, _parent=None, _root=None):
                super(AmlogicEmmcPartitions.Partition.PartFlags, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['is_code']['start'] = self._io.pos()
                self.is_code = self._io.read_bits_int_le(1) != 0
                self._debug['is_code']['end'] = self._io.pos()
                self._debug['is_cache']['start'] = self._io.pos()
                self.is_cache = self._io.read_bits_int_le(1) != 0
                self._debug['is_cache']['end'] = self._io.pos()
                self._debug['is_data']['start'] = self._io.pos()
                self.is_data = self._io.read_bits_int_le(1) != 0
                self._debug['is_data']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass




