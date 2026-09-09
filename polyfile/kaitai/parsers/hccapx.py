# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Hccapx(KaitaiStruct):
    """Native format of Hashcat password "recovery" utility
    
    .. seealso::
       Source - https://hashcat.net/wiki/doku.php?id=hccapx
    """
    SEQ_FIELDS = ["records"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Hccapx, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['records']['start'] = self._io.pos()
        self._debug['records']['arr'] = []
        self.records = []
        i = 0
        while not self._io.is_eof():
            self._debug['records']['arr'].append({'start': self._io.pos()})
            _t_records = Hccapx.HccapxRecord(self._io, self, self._root)
            try:
                _t_records._read()
            finally:
                self.records.append(_t_records)
            self._debug['records']['arr'][len(self.records) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['records']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.records)):
            pass
            self.records[i]._fetch_instances()


    class HccapxRecord(KaitaiStruct):
        SEQ_FIELDS = ["magic", "version", "ignore_replay_counter", "message_pair", "len_essid", "essid", "padding1", "keyver", "keymic", "mac_ap", "nonce_ap", "mac_station", "nonce_station", "len_eapol", "eapol", "padding2"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Hccapx.HccapxRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x48\x43\x50\x58":
                raise kaitaistruct.ValidationNotEqualError(b"\x48\x43\x50\x58", self.magic, self._io, u"/types/hccapx_record/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4le()
            self._debug['version']['end'] = self._io.pos()
            self._debug['ignore_replay_counter']['start'] = self._io.pos()
            self.ignore_replay_counter = self._io.read_bits_int_be(1) != 0
            self._debug['ignore_replay_counter']['end'] = self._io.pos()
            self._debug['message_pair']['start'] = self._io.pos()
            self.message_pair = self._io.read_bits_int_be(7)
            self._debug['message_pair']['end'] = self._io.pos()
            self._debug['len_essid']['start'] = self._io.pos()
            self.len_essid = self._io.read_u1()
            self._debug['len_essid']['end'] = self._io.pos()
            self._debug['essid']['start'] = self._io.pos()
            self.essid = self._io.read_bytes(self.len_essid)
            self._debug['essid']['end'] = self._io.pos()
            self._debug['padding1']['start'] = self._io.pos()
            self.padding1 = self._io.read_bytes(32 - self.len_essid)
            self._debug['padding1']['end'] = self._io.pos()
            self._debug['keyver']['start'] = self._io.pos()
            self.keyver = self._io.read_u1()
            self._debug['keyver']['end'] = self._io.pos()
            self._debug['keymic']['start'] = self._io.pos()
            self.keymic = self._io.read_bytes(16)
            self._debug['keymic']['end'] = self._io.pos()
            self._debug['mac_ap']['start'] = self._io.pos()
            self.mac_ap = self._io.read_bytes(6)
            self._debug['mac_ap']['end'] = self._io.pos()
            self._debug['nonce_ap']['start'] = self._io.pos()
            self.nonce_ap = self._io.read_bytes(32)
            self._debug['nonce_ap']['end'] = self._io.pos()
            self._debug['mac_station']['start'] = self._io.pos()
            self.mac_station = self._io.read_bytes(6)
            self._debug['mac_station']['end'] = self._io.pos()
            self._debug['nonce_station']['start'] = self._io.pos()
            self.nonce_station = self._io.read_bytes(32)
            self._debug['nonce_station']['end'] = self._io.pos()
            self._debug['len_eapol']['start'] = self._io.pos()
            self.len_eapol = self._io.read_u2le()
            self._debug['len_eapol']['end'] = self._io.pos()
            self._debug['eapol']['start'] = self._io.pos()
            self.eapol = self._io.read_bytes(self.len_eapol)
            self._debug['eapol']['end'] = self._io.pos()
            self._debug['padding2']['start'] = self._io.pos()
            self.padding2 = self._io.read_bytes(256 - self.len_eapol)
            self._debug['padding2']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



