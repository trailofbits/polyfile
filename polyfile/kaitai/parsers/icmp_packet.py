# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class IcmpPacket(KaitaiStruct):

    class IcmpTypeEnum(IntEnum):
        echo_reply = 0
        destination_unreachable = 3
        source_quench = 4
        redirect = 5
        echo = 8
        time_exceeded = 11
    SEQ_FIELDS = ["icmp_type", "destination_unreachable", "time_exceeded", "echo"]
    def __init__(self, _io, _parent=None, _root=None):
        super(IcmpPacket, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['icmp_type']['start'] = self._io.pos()
        self.icmp_type = KaitaiStream.resolve_enum(IcmpPacket.IcmpTypeEnum, self._io.read_u1())
        self._debug['icmp_type']['end'] = self._io.pos()
        if self.icmp_type == IcmpPacket.IcmpTypeEnum.destination_unreachable:
            pass
            self._debug['destination_unreachable']['start'] = self._io.pos()
            self.destination_unreachable = IcmpPacket.DestinationUnreachableMsg(self._io, self, self._root)
            self.destination_unreachable._read()
            self._debug['destination_unreachable']['end'] = self._io.pos()

        if self.icmp_type == IcmpPacket.IcmpTypeEnum.time_exceeded:
            pass
            self._debug['time_exceeded']['start'] = self._io.pos()
            self.time_exceeded = IcmpPacket.TimeExceededMsg(self._io, self, self._root)
            self.time_exceeded._read()
            self._debug['time_exceeded']['end'] = self._io.pos()

        if  ((self.icmp_type == IcmpPacket.IcmpTypeEnum.echo) or (self.icmp_type == IcmpPacket.IcmpTypeEnum.echo_reply)) :
            pass
            self._debug['echo']['start'] = self._io.pos()
            self.echo = IcmpPacket.EchoMsg(self._io, self, self._root)
            self.echo._read()
            self._debug['echo']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        if self.icmp_type == IcmpPacket.IcmpTypeEnum.destination_unreachable:
            pass
            self.destination_unreachable._fetch_instances()

        if self.icmp_type == IcmpPacket.IcmpTypeEnum.time_exceeded:
            pass
            self.time_exceeded._fetch_instances()

        if  ((self.icmp_type == IcmpPacket.IcmpTypeEnum.echo) or (self.icmp_type == IcmpPacket.IcmpTypeEnum.echo_reply)) :
            pass
            self.echo._fetch_instances()


    class DestinationUnreachableMsg(KaitaiStruct):

        class DestinationUnreachableCode(IntEnum):
            net_unreachable = 0
            host_unreachable = 1
            protocol_unreachable = 2
            port_unreachable = 3
            fragmentation_needed_and_df_set = 4
            source_route_failed = 5
            dst_net_unknown = 6
            sdt_host_unknown = 7
            src_isolated = 8
            net_prohibited_by_admin = 9
            host_prohibited_by_admin = 10
            net_unreachable_for_tos = 11
            host_unreachable_for_tos = 12
            communication_prohibited_by_admin = 13
            host_precedence_violation = 14
            precedence_cuttoff_in_effect = 15
        SEQ_FIELDS = ["code", "checksum"]
        def __init__(self, _io, _parent=None, _root=None):
            super(IcmpPacket.DestinationUnreachableMsg, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = KaitaiStream.resolve_enum(IcmpPacket.DestinationUnreachableMsg.DestinationUnreachableCode, self._io.read_u1())
            self._debug['code']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_u2be()
            self._debug['checksum']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class EchoMsg(KaitaiStruct):
        SEQ_FIELDS = ["code", "checksum", "identifier", "seq_num", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(IcmpPacket.EchoMsg, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = self._io.read_bytes(1)
            self._debug['code']['end'] = self._io.pos()
            if not self.code == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.code, self._io, u"/types/echo_msg/seq/0")
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_u2be()
            self._debug['checksum']['end'] = self._io.pos()
            self._debug['identifier']['start'] = self._io.pos()
            self.identifier = self._io.read_u2be()
            self._debug['identifier']['end'] = self._io.pos()
            self._debug['seq_num']['start'] = self._io.pos()
            self.seq_num = self._io.read_u2be()
            self._debug['seq_num']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class TimeExceededMsg(KaitaiStruct):

        class TimeExceededCode(IntEnum):
            time_to_live_exceeded_in_transit = 0
            fragment_reassembly_time_exceeded = 1
        SEQ_FIELDS = ["code", "checksum"]
        def __init__(self, _io, _parent=None, _root=None):
            super(IcmpPacket.TimeExceededMsg, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = KaitaiStream.resolve_enum(IcmpPacket.TimeExceededMsg.TimeExceededCode, self._io.read_u1())
            self._debug['code']['end'] = self._io.pos()
            self._debug['checksum']['start'] = self._io.pos()
            self.checksum = self._io.read_u2be()
            self._debug['checksum']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



