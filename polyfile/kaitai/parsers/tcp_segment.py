# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class TcpSegment(KaitaiStruct):
    """TCP is one of the core Internet protocols on transport layer (AKA
    OSI layer 4), providing stateful connections with error checking,
    guarantees of delivery, order of segments and avoidance of duplicate
    delivery.
    """
    SEQ_FIELDS = ["src_port", "dst_port", "seq_num", "ack_num", "data_offset", "reserved", "flags", "window_size", "checksum", "urgent_pointer", "options", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        super(TcpSegment, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['src_port']['start'] = self._io.pos()
        self.src_port = self._io.read_u2be()
        self._debug['src_port']['end'] = self._io.pos()
        self._debug['dst_port']['start'] = self._io.pos()
        self.dst_port = self._io.read_u2be()
        self._debug['dst_port']['end'] = self._io.pos()
        self._debug['seq_num']['start'] = self._io.pos()
        self.seq_num = self._io.read_u4be()
        self._debug['seq_num']['end'] = self._io.pos()
        self._debug['ack_num']['start'] = self._io.pos()
        self.ack_num = self._io.read_u4be()
        self._debug['ack_num']['end'] = self._io.pos()
        self._debug['data_offset']['start'] = self._io.pos()
        self.data_offset = self._io.read_bits_int_be(4)
        self._debug['data_offset']['end'] = self._io.pos()
        self._debug['reserved']['start'] = self._io.pos()
        self.reserved = self._io.read_bits_int_be(4)
        self._debug['reserved']['end'] = self._io.pos()
        self._debug['flags']['start'] = self._io.pos()
        self.flags = TcpSegment.Flags(self._io, self, self._root)
        self.flags._read()
        self._debug['flags']['end'] = self._io.pos()
        self._debug['window_size']['start'] = self._io.pos()
        self.window_size = self._io.read_u2be()
        self._debug['window_size']['end'] = self._io.pos()
        self._debug['checksum']['start'] = self._io.pos()
        self.checksum = self._io.read_u2be()
        self._debug['checksum']['end'] = self._io.pos()
        self._debug['urgent_pointer']['start'] = self._io.pos()
        self.urgent_pointer = self._io.read_u2be()
        self._debug['urgent_pointer']['end'] = self._io.pos()
        if self.data_offset * 4 - 20 != 0:
            pass
            self._debug['options']['start'] = self._io.pos()
            self.options = self._io.read_bytes(self.data_offset * 4 - 20)
            self._debug['options']['end'] = self._io.pos()

        self._debug['body']['start'] = self._io.pos()
        self.body = self._io.read_bytes_full()
        self._debug['body']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.flags._fetch_instances()
        if self.data_offset * 4 - 20 != 0:
            pass


    class Flags(KaitaiStruct):
        """TCP header flags as defined "TCP Header Flags" registry.
        """
        SEQ_FIELDS = ["cwr", "ece", "urg", "ack", "psh", "rst", "syn", "fin"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TcpSegment.Flags, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['cwr']['start'] = self._io.pos()
            self.cwr = self._io.read_bits_int_be(1) != 0
            self._debug['cwr']['end'] = self._io.pos()
            self._debug['ece']['start'] = self._io.pos()
            self.ece = self._io.read_bits_int_be(1) != 0
            self._debug['ece']['end'] = self._io.pos()
            self._debug['urg']['start'] = self._io.pos()
            self.urg = self._io.read_bits_int_be(1) != 0
            self._debug['urg']['end'] = self._io.pos()
            self._debug['ack']['start'] = self._io.pos()
            self.ack = self._io.read_bits_int_be(1) != 0
            self._debug['ack']['end'] = self._io.pos()
            self._debug['psh']['start'] = self._io.pos()
            self.psh = self._io.read_bits_int_be(1) != 0
            self._debug['psh']['end'] = self._io.pos()
            self._debug['rst']['start'] = self._io.pos()
            self.rst = self._io.read_bits_int_be(1) != 0
            self._debug['rst']['end'] = self._io.pos()
            self._debug['syn']['start'] = self._io.pos()
            self.syn = self._io.read_bits_int_be(1) != 0
            self._debug['syn']['end'] = self._io.pos()
            self._debug['fin']['start'] = self._io.pos()
            self.fin = self._io.read_bits_int_be(1) != 0
            self._debug['fin']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


        def __str__(self):
            return (((((((u"|CWR" if self.cwr else u"") + (u"|ECE" if self.ece else u"")) + (u"|URG" if self.urg else u"")) + (u"|ACK" if self.ack else u"")) + (u"|PSH" if self.psh else u"")) + (u"|RST" if self.rst else u"")) + (u"|SYN" if self.syn else u"")) + (u"|FIN" if self.fin else u"")


