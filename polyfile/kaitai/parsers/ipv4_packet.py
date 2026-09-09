# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from polyfile.kaitai.parsers import protocol_body
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Ipv4Packet(KaitaiStruct):
    SEQ_FIELDS = ["b1", "b2", "total_length", "identification", "b67", "ttl", "protocol", "header_checksum", "src_ip_addr", "dst_ip_addr", "options", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Ipv4Packet, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['b1']['start'] = self._io.pos()
        self.b1 = self._io.read_u1()
        self._debug['b1']['end'] = self._io.pos()
        self._debug['b2']['start'] = self._io.pos()
        self.b2 = self._io.read_u1()
        self._debug['b2']['end'] = self._io.pos()
        self._debug['total_length']['start'] = self._io.pos()
        self.total_length = self._io.read_u2be()
        self._debug['total_length']['end'] = self._io.pos()
        self._debug['identification']['start'] = self._io.pos()
        self.identification = self._io.read_u2be()
        self._debug['identification']['end'] = self._io.pos()
        self._debug['b67']['start'] = self._io.pos()
        self.b67 = self._io.read_u2be()
        self._debug['b67']['end'] = self._io.pos()
        self._debug['ttl']['start'] = self._io.pos()
        self.ttl = self._io.read_u1()
        self._debug['ttl']['end'] = self._io.pos()
        self._debug['protocol']['start'] = self._io.pos()
        self.protocol = self._io.read_u1()
        self._debug['protocol']['end'] = self._io.pos()
        self._debug['header_checksum']['start'] = self._io.pos()
        self.header_checksum = self._io.read_u2be()
        self._debug['header_checksum']['end'] = self._io.pos()
        self._debug['src_ip_addr']['start'] = self._io.pos()
        self.src_ip_addr = self._io.read_bytes(4)
        self._debug['src_ip_addr']['end'] = self._io.pos()
        self._debug['dst_ip_addr']['start'] = self._io.pos()
        self.dst_ip_addr = self._io.read_bytes(4)
        self._debug['dst_ip_addr']['end'] = self._io.pos()
        self._debug['options']['start'] = self._io.pos()
        self._raw_options = self._io.read_bytes(self.ihl_bytes - 20)
        _io__raw_options = KaitaiStream(BytesIO(self._raw_options))
        self.options = Ipv4Packet.Ipv4Options(_io__raw_options, self, self._root)
        self.options._read()
        self._debug['options']['end'] = self._io.pos()
        self._debug['body']['start'] = self._io.pos()
        self._raw_body = self._io.read_bytes(self.total_length - self.ihl_bytes)
        _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
        self.body = protocol_body.ProtocolBody(self.protocol, _io__raw_body)
        self.body._read()
        self._debug['body']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.options._fetch_instances()
        self.body._fetch_instances()

    class Ipv4Option(KaitaiStruct):
        SEQ_FIELDS = ["b1", "len", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Ipv4Packet.Ipv4Option, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['b1']['start'] = self._io.pos()
            self.b1 = self._io.read_u1()
            self._debug['b1']['end'] = self._io.pos()
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes((self.len - 2 if self.len > 2 else 0))
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def copy(self):
            if hasattr(self, '_m_copy'):
                return self._m_copy

            self._m_copy = (self.b1 & 128) >> 7
            return getattr(self, '_m_copy', None)

        @property
        def number(self):
            if hasattr(self, '_m_number'):
                return self._m_number

            self._m_number = self.b1 & 31
            return getattr(self, '_m_number', None)

        @property
        def opt_class(self):
            if hasattr(self, '_m_opt_class'):
                return self._m_opt_class

            self._m_opt_class = (self.b1 & 96) >> 5
            return getattr(self, '_m_opt_class', None)


    class Ipv4Options(KaitaiStruct):
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Ipv4Packet.Ipv4Options, self).__init__(_io)
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
                _t_entries = Ipv4Packet.Ipv4Option(self._io, self, self._root)
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



    @property
    def ihl(self):
        if hasattr(self, '_m_ihl'):
            return self._m_ihl

        self._m_ihl = self.b1 & 15
        return getattr(self, '_m_ihl', None)

    @property
    def ihl_bytes(self):
        if hasattr(self, '_m_ihl_bytes'):
            return self._m_ihl_bytes

        self._m_ihl_bytes = self.ihl * 4
        return getattr(self, '_m_ihl_bytes', None)

    @property
    def version(self):
        if hasattr(self, '_m_version'):
            return self._m_version

        self._m_version = (self.b1 & 240) >> 4
        return getattr(self, '_m_version', None)


