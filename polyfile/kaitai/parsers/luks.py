# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Luks(KaitaiStruct):
    """Linux Unified Key Setup (LUKS) is a format specification for storing disk
    encryption parameters and up to 8 user keys (which can unlock the master key).
    
    .. seealso::
       Source - https://gitlab.com/cryptsetup/cryptsetup/-/wikis/LUKS-standard/on-disk-format.pdf
    """
    SEQ_FIELDS = ["partition_header"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Luks, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['partition_header']['start'] = self._io.pos()
        self.partition_header = Luks.PartitionHeader(self._io, self, self._root)
        self.partition_header._read()
        self._debug['partition_header']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.partition_header._fetch_instances()
        _ = self.payload
        if hasattr(self, '_m_payload'):
            pass


    class PartitionHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version", "cipher_name_specification", "cipher_mode_specification", "hash_specification", "payload_offset", "number_of_key_bytes", "master_key_checksum", "master_key_salt_parameter", "master_key_iterations_parameter", "uuid", "key_slots"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Luks.PartitionHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(6)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x4C\x55\x4B\x53\xBA\xBE":
                raise kaitaistruct.ValidationNotEqualError(b"\x4C\x55\x4B\x53\xBA\xBE", self.magic, self._io, u"/types/partition_header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_bytes(2)
            self._debug['version']['end'] = self._io.pos()
            if not self.version == b"\x00\x01":
                raise kaitaistruct.ValidationNotEqualError(b"\x00\x01", self.version, self._io, u"/types/partition_header/seq/1")
            self._debug['cipher_name_specification']['start'] = self._io.pos()
            self.cipher_name_specification = (self._io.read_bytes(32)).decode(u"ASCII")
            self._debug['cipher_name_specification']['end'] = self._io.pos()
            self._debug['cipher_mode_specification']['start'] = self._io.pos()
            self.cipher_mode_specification = (self._io.read_bytes(32)).decode(u"ASCII")
            self._debug['cipher_mode_specification']['end'] = self._io.pos()
            self._debug['hash_specification']['start'] = self._io.pos()
            self.hash_specification = (self._io.read_bytes(32)).decode(u"ASCII")
            self._debug['hash_specification']['end'] = self._io.pos()
            self._debug['payload_offset']['start'] = self._io.pos()
            self.payload_offset = self._io.read_u4be()
            self._debug['payload_offset']['end'] = self._io.pos()
            self._debug['number_of_key_bytes']['start'] = self._io.pos()
            self.number_of_key_bytes = self._io.read_u4be()
            self._debug['number_of_key_bytes']['end'] = self._io.pos()
            self._debug['master_key_checksum']['start'] = self._io.pos()
            self.master_key_checksum = self._io.read_bytes(20)
            self._debug['master_key_checksum']['end'] = self._io.pos()
            self._debug['master_key_salt_parameter']['start'] = self._io.pos()
            self.master_key_salt_parameter = self._io.read_bytes(32)
            self._debug['master_key_salt_parameter']['end'] = self._io.pos()
            self._debug['master_key_iterations_parameter']['start'] = self._io.pos()
            self.master_key_iterations_parameter = self._io.read_u4be()
            self._debug['master_key_iterations_parameter']['end'] = self._io.pos()
            self._debug['uuid']['start'] = self._io.pos()
            self.uuid = (self._io.read_bytes(40)).decode(u"ASCII")
            self._debug['uuid']['end'] = self._io.pos()
            self._debug['key_slots']['start'] = self._io.pos()
            self._debug['key_slots']['arr'] = []
            self.key_slots = []
            for i in range(8):
                self._debug['key_slots']['arr'].append({'start': self._io.pos()})
                _t_key_slots = Luks.PartitionHeader.KeySlot(self._io, self, self._root)
                try:
                    _t_key_slots._read()
                finally:
                    self.key_slots.append(_t_key_slots)
                self._debug['key_slots']['arr'][i]['end'] = self._io.pos()

            self._debug['key_slots']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.key_slots)):
                pass
                self.key_slots[i]._fetch_instances()


        class KeySlot(KaitaiStruct):

            class KeySlotStates(IntEnum):
                disabled_key_slot = 57005
                enabled_key_slot = 11301363
            SEQ_FIELDS = ["state_of_key_slot", "iteration_parameter", "salt_parameter", "start_sector_of_key_material", "number_of_anti_forensic_stripes"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Luks.PartitionHeader.KeySlot, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['state_of_key_slot']['start'] = self._io.pos()
                self.state_of_key_slot = KaitaiStream.resolve_enum(Luks.PartitionHeader.KeySlot.KeySlotStates, self._io.read_u4be())
                self._debug['state_of_key_slot']['end'] = self._io.pos()
                self._debug['iteration_parameter']['start'] = self._io.pos()
                self.iteration_parameter = self._io.read_u4be()
                self._debug['iteration_parameter']['end'] = self._io.pos()
                self._debug['salt_parameter']['start'] = self._io.pos()
                self.salt_parameter = self._io.read_bytes(32)
                self._debug['salt_parameter']['end'] = self._io.pos()
                self._debug['start_sector_of_key_material']['start'] = self._io.pos()
                self.start_sector_of_key_material = self._io.read_u4be()
                self._debug['start_sector_of_key_material']['end'] = self._io.pos()
                self._debug['number_of_anti_forensic_stripes']['start'] = self._io.pos()
                self.number_of_anti_forensic_stripes = self._io.read_u4be()
                self._debug['number_of_anti_forensic_stripes']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _ = self.key_material
                if hasattr(self, '_m_key_material'):
                    pass


            @property
            def key_material(self):
                if hasattr(self, '_m_key_material'):
                    return self._m_key_material

                _pos = self._io.pos()
                self._io.seek(self.start_sector_of_key_material * 512)
                self._debug['_m_key_material']['start'] = self._io.pos()
                self._m_key_material = self._io.read_bytes(self._parent.number_of_key_bytes * self.number_of_anti_forensic_stripes)
                self._debug['_m_key_material']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_key_material', None)



    @property
    def payload(self):
        if hasattr(self, '_m_payload'):
            return self._m_payload

        _pos = self._io.pos()
        self._io.seek(self.partition_header.payload_offset * 512)
        self._debug['_m_payload']['start'] = self._io.pos()
        self._m_payload = self._io.read_bytes_full()
        self._debug['_m_payload']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_payload', None)


