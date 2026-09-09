# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class RtcpPayload(KaitaiStruct):
    """RTCP is the Real-Time Control Protocol.
    
    .. seealso::
       Source - https://www.rfc-editor.org/rfc/rfc3550
    """

    class PayloadType(IntEnum):
        fir = 192
        nack = 193
        ij = 195
        sr = 200
        rr = 201
        sdes = 202
        bye = 203
        app = 204
        rtpfb = 205
        psfb = 206
        xr = 207
        avb = 208
        rsi = 209

    class PsfbSubtype(IntEnum):
        pli = 1
        sli = 2
        rpsi = 3
        fir = 4
        tstr = 5
        tstn = 6
        vbcm = 7
        afb = 15

    class RtpfbSubtype(IntEnum):
        nack = 1
        tmmbr = 3
        tmmbn = 4
        rrr = 5
        transport_feedback = 15

    class SdesSubtype(IntEnum):
        pad = 0
        cname = 1
        name = 2
        email = 3
        phone = 4
        loc = 5
        tool = 6
        note = 7
        priv = 8
    SEQ_FIELDS = ["rtcp_packets"]
    def __init__(self, _io, _parent=None, _root=None):
        super(RtcpPayload, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['rtcp_packets']['start'] = self._io.pos()
        self._debug['rtcp_packets']['arr'] = []
        self.rtcp_packets = []
        i = 0
        while not self._io.is_eof():
            self._debug['rtcp_packets']['arr'].append({'start': self._io.pos()})
            _t_rtcp_packets = RtcpPayload.RtcpPacket(self._io, self, self._root)
            try:
                _t_rtcp_packets._read()
            finally:
                self.rtcp_packets.append(_t_rtcp_packets)
            self._debug['rtcp_packets']['arr'][len(self.rtcp_packets) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['rtcp_packets']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.rtcp_packets)):
            pass
            self.rtcp_packets[i]._fetch_instances()


    class PacketStatusChunk(KaitaiStruct):
        SEQ_FIELDS = ["t", "s2", "s1", "rle", "symbol_list"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.PacketStatusChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['t']['start'] = self._io.pos()
            self.t = self._io.read_bits_int_be(1) != 0
            self._debug['t']['end'] = self._io.pos()
            if int(self.t) == 0:
                pass
                self._debug['s2']['start'] = self._io.pos()
                self.s2 = self._io.read_bits_int_be(2)
                self._debug['s2']['end'] = self._io.pos()

            if int(self.t) == 1:
                pass
                self._debug['s1']['start'] = self._io.pos()
                self.s1 = self._io.read_bits_int_be(1) != 0
                self._debug['s1']['end'] = self._io.pos()

            if int(self.t) == 0:
                pass
                self._debug['rle']['start'] = self._io.pos()
                self.rle = self._io.read_bits_int_be(13)
                self._debug['rle']['end'] = self._io.pos()

            if int(self.t) == 1:
                pass
                self._debug['symbol_list']['start'] = self._io.pos()
                self.symbol_list = self._io.read_bits_int_be(14)
                self._debug['symbol_list']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if int(self.t) == 0:
                pass

            if int(self.t) == 1:
                pass

            if int(self.t) == 0:
                pass

            if int(self.t) == 1:
                pass


        @property
        def s(self):
            if hasattr(self, '_m_s'):
                return self._m_s

            self._m_s = (self.s2 if int(self.t) == 0 else (1 if int(self.s1) == 0 else 0))
            return getattr(self, '_m_s', None)


    class PsfbAfbPacket(KaitaiStruct):
        SEQ_FIELDS = ["uid", "contents"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.PsfbAfbPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['uid']['start'] = self._io.pos()
            self.uid = self._io.read_u4be()
            self._debug['uid']['end'] = self._io.pos()
            self._debug['contents']['start'] = self._io.pos()
            _on = self.uid
            if _on == 1380273474:
                pass
                self._raw_contents = self._io.read_bytes_full()
                _io__raw_contents = KaitaiStream(BytesIO(self._raw_contents))
                self.contents = RtcpPayload.PsfbAfbRembPacket(_io__raw_contents, self, self._root)
                self.contents._read()
            else:
                pass
                self.contents = self._io.read_bytes_full()
            self._debug['contents']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.uid
            if _on == 1380273474:
                pass
                self.contents._fetch_instances()
            else:
                pass


    class PsfbAfbRembPacket(KaitaiStruct):
        SEQ_FIELDS = ["num_ssrc", "br_exp", "br_mantissa", "ssrc_list"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.PsfbAfbRembPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_ssrc']['start'] = self._io.pos()
            self.num_ssrc = self._io.read_u1()
            self._debug['num_ssrc']['end'] = self._io.pos()
            self._debug['br_exp']['start'] = self._io.pos()
            self.br_exp = self._io.read_bits_int_be(6)
            self._debug['br_exp']['end'] = self._io.pos()
            self._debug['br_mantissa']['start'] = self._io.pos()
            self.br_mantissa = self._io.read_bits_int_be(18)
            self._debug['br_mantissa']['end'] = self._io.pos()
            self._debug['ssrc_list']['start'] = self._io.pos()
            self._debug['ssrc_list']['arr'] = []
            self.ssrc_list = []
            for i in range(self.num_ssrc):
                self._debug['ssrc_list']['arr'].append({'start': self._io.pos()})
                self.ssrc_list.append(self._io.read_u4be())
                self._debug['ssrc_list']['arr'][i]['end'] = self._io.pos()

            self._debug['ssrc_list']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.ssrc_list)):
                pass


        @property
        def max_total_bitrate(self):
            if hasattr(self, '_m_max_total_bitrate'):
                return self._m_max_total_bitrate

            self._m_max_total_bitrate = self.br_mantissa * (1 << self.br_exp)
            return getattr(self, '_m_max_total_bitrate', None)


    class PsfbPacket(KaitaiStruct):
        SEQ_FIELDS = ["ssrc", "ssrc_media_source", "fci_block"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.PsfbPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc']['start'] = self._io.pos()
            self.ssrc = self._io.read_u4be()
            self._debug['ssrc']['end'] = self._io.pos()
            self._debug['ssrc_media_source']['start'] = self._io.pos()
            self.ssrc_media_source = self._io.read_u4be()
            self._debug['ssrc_media_source']['end'] = self._io.pos()
            self._debug['fci_block']['start'] = self._io.pos()
            _on = self.fmt
            if _on == RtcpPayload.PsfbSubtype.afb:
                pass
                self._raw_fci_block = self._io.read_bytes_full()
                _io__raw_fci_block = KaitaiStream(BytesIO(self._raw_fci_block))
                self.fci_block = RtcpPayload.PsfbAfbPacket(_io__raw_fci_block, self, self._root)
                self.fci_block._read()
            else:
                pass
                self.fci_block = self._io.read_bytes_full()
            self._debug['fci_block']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.fmt
            if _on == RtcpPayload.PsfbSubtype.afb:
                pass
                self.fci_block._fetch_instances()
            else:
                pass

        @property
        def fmt(self):
            if hasattr(self, '_m_fmt'):
                return self._m_fmt

            self._m_fmt = KaitaiStream.resolve_enum(RtcpPayload.PsfbSubtype, self._parent.subtype)
            return getattr(self, '_m_fmt', None)


    class ReportBlock(KaitaiStruct):
        SEQ_FIELDS = ["ssrc_source", "lost_val", "highest_seq_num_received", "interarrival_jitter", "lsr", "dlsr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.ReportBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc_source']['start'] = self._io.pos()
            self.ssrc_source = self._io.read_u4be()
            self._debug['ssrc_source']['end'] = self._io.pos()
            self._debug['lost_val']['start'] = self._io.pos()
            self.lost_val = self._io.read_u1()
            self._debug['lost_val']['end'] = self._io.pos()
            self._debug['highest_seq_num_received']['start'] = self._io.pos()
            self.highest_seq_num_received = self._io.read_u4be()
            self._debug['highest_seq_num_received']['end'] = self._io.pos()
            self._debug['interarrival_jitter']['start'] = self._io.pos()
            self.interarrival_jitter = self._io.read_u4be()
            self._debug['interarrival_jitter']['end'] = self._io.pos()
            self._debug['lsr']['start'] = self._io.pos()
            self.lsr = self._io.read_u4be()
            self._debug['lsr']['end'] = self._io.pos()
            self._debug['dlsr']['start'] = self._io.pos()
            self.dlsr = self._io.read_u4be()
            self._debug['dlsr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def cumulative_packets_lost(self):
            if hasattr(self, '_m_cumulative_packets_lost'):
                return self._m_cumulative_packets_lost

            self._m_cumulative_packets_lost = self.lost_val & 16777215
            return getattr(self, '_m_cumulative_packets_lost', None)

        @property
        def fraction_lost(self):
            if hasattr(self, '_m_fraction_lost'):
                return self._m_fraction_lost

            self._m_fraction_lost = self.lost_val >> 24
            return getattr(self, '_m_fraction_lost', None)


    class RrPacket(KaitaiStruct):
        SEQ_FIELDS = ["ssrc", "report_block"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.RrPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc']['start'] = self._io.pos()
            self.ssrc = self._io.read_u4be()
            self._debug['ssrc']['end'] = self._io.pos()
            self._debug['report_block']['start'] = self._io.pos()
            self._debug['report_block']['arr'] = []
            self.report_block = []
            for i in range(self._parent.subtype):
                self._debug['report_block']['arr'].append({'start': self._io.pos()})
                _t_report_block = RtcpPayload.ReportBlock(self._io, self, self._root)
                try:
                    _t_report_block._read()
                finally:
                    self.report_block.append(_t_report_block)
                self._debug['report_block']['arr'][i]['end'] = self._io.pos()

            self._debug['report_block']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.report_block)):
                pass
                self.report_block[i]._fetch_instances()



    class RtcpPacket(KaitaiStruct):
        SEQ_FIELDS = ["version", "padding", "subtype", "payload_type", "length", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.RtcpPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_bits_int_be(2)
            self._debug['version']['end'] = self._io.pos()
            self._debug['padding']['start'] = self._io.pos()
            self.padding = self._io.read_bits_int_be(1) != 0
            self._debug['padding']['end'] = self._io.pos()
            self._debug['subtype']['start'] = self._io.pos()
            self.subtype = self._io.read_bits_int_be(5)
            self._debug['subtype']['end'] = self._io.pos()
            self._debug['payload_type']['start'] = self._io.pos()
            self.payload_type = KaitaiStream.resolve_enum(RtcpPayload.PayloadType, self._io.read_u1())
            self._debug['payload_type']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u2be()
            self._debug['length']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.payload_type
            if _on == RtcpPayload.PayloadType.psfb:
                pass
                self._raw_body = self._io.read_bytes(4 * self.length)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = RtcpPayload.PsfbPacket(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == RtcpPayload.PayloadType.rr:
                pass
                self._raw_body = self._io.read_bytes(4 * self.length)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = RtcpPayload.RrPacket(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == RtcpPayload.PayloadType.rtpfb:
                pass
                self._raw_body = self._io.read_bytes(4 * self.length)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = RtcpPayload.RtpfbPacket(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == RtcpPayload.PayloadType.sdes:
                pass
                self._raw_body = self._io.read_bytes(4 * self.length)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = RtcpPayload.SdesPacket(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == RtcpPayload.PayloadType.sr:
                pass
                self._raw_body = self._io.read_bytes(4 * self.length)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = RtcpPayload.SrPacket(_io__raw_body, self, self._root)
                self.body._read()
            else:
                pass
                self.body = self._io.read_bytes(4 * self.length)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.payload_type
            if _on == RtcpPayload.PayloadType.psfb:
                pass
                self.body._fetch_instances()
            elif _on == RtcpPayload.PayloadType.rr:
                pass
                self.body._fetch_instances()
            elif _on == RtcpPayload.PayloadType.rtpfb:
                pass
                self.body._fetch_instances()
            elif _on == RtcpPayload.PayloadType.sdes:
                pass
                self.body._fetch_instances()
            elif _on == RtcpPayload.PayloadType.sr:
                pass
                self.body._fetch_instances()
            else:
                pass


    class RtpfbPacket(KaitaiStruct):
        SEQ_FIELDS = ["ssrc", "ssrc_media_source", "fci_block"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.RtpfbPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc']['start'] = self._io.pos()
            self.ssrc = self._io.read_u4be()
            self._debug['ssrc']['end'] = self._io.pos()
            self._debug['ssrc_media_source']['start'] = self._io.pos()
            self.ssrc_media_source = self._io.read_u4be()
            self._debug['ssrc_media_source']['end'] = self._io.pos()
            self._debug['fci_block']['start'] = self._io.pos()
            _on = self.fmt
            if _on == RtcpPayload.RtpfbSubtype.transport_feedback:
                pass
                self._raw_fci_block = self._io.read_bytes_full()
                _io__raw_fci_block = KaitaiStream(BytesIO(self._raw_fci_block))
                self.fci_block = RtcpPayload.RtpfbTransportFeedbackPacket(_io__raw_fci_block, self, self._root)
                self.fci_block._read()
            else:
                pass
                self.fci_block = self._io.read_bytes_full()
            self._debug['fci_block']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.fmt
            if _on == RtcpPayload.RtpfbSubtype.transport_feedback:
                pass
                self.fci_block._fetch_instances()
            else:
                pass

        @property
        def fmt(self):
            if hasattr(self, '_m_fmt'):
                return self._m_fmt

            self._m_fmt = KaitaiStream.resolve_enum(RtcpPayload.RtpfbSubtype, self._parent.subtype)
            return getattr(self, '_m_fmt', None)


    class RtpfbTransportFeedbackPacket(KaitaiStruct):
        SEQ_FIELDS = ["base_sequence_number", "packet_status_count", "b4", "remaining"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.RtpfbTransportFeedbackPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['base_sequence_number']['start'] = self._io.pos()
            self.base_sequence_number = self._io.read_u2be()
            self._debug['base_sequence_number']['end'] = self._io.pos()
            self._debug['packet_status_count']['start'] = self._io.pos()
            self.packet_status_count = self._io.read_u2be()
            self._debug['packet_status_count']['end'] = self._io.pos()
            self._debug['b4']['start'] = self._io.pos()
            self.b4 = self._io.read_u4be()
            self._debug['b4']['end'] = self._io.pos()
            self._debug['remaining']['start'] = self._io.pos()
            self.remaining = self._io.read_bytes_full()
            self._debug['remaining']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.packet_status
            if hasattr(self, '_m_packet_status'):
                pass

            _ = self.recv_delta
            if hasattr(self, '_m_recv_delta'):
                pass


        @property
        def fb_pkt_count(self):
            if hasattr(self, '_m_fb_pkt_count'):
                return self._m_fb_pkt_count

            self._m_fb_pkt_count = self.b4 & 255
            return getattr(self, '_m_fb_pkt_count', None)

        @property
        def packet_status(self):
            if hasattr(self, '_m_packet_status'):
                return self._m_packet_status

            self._debug['_m_packet_status']['start'] = self._io.pos()
            self._m_packet_status = self._io.read_bytes(0)
            self._debug['_m_packet_status']['end'] = self._io.pos()
            return getattr(self, '_m_packet_status', None)

        @property
        def recv_delta(self):
            if hasattr(self, '_m_recv_delta'):
                return self._m_recv_delta

            self._debug['_m_recv_delta']['start'] = self._io.pos()
            self._m_recv_delta = self._io.read_bytes(0)
            self._debug['_m_recv_delta']['end'] = self._io.pos()
            return getattr(self, '_m_recv_delta', None)

        @property
        def reference_time(self):
            if hasattr(self, '_m_reference_time'):
                return self._m_reference_time

            self._m_reference_time = self.b4 >> 8
            return getattr(self, '_m_reference_time', None)


    class SdesPacket(KaitaiStruct):
        SEQ_FIELDS = ["source_chunk"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.SdesPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['source_chunk']['start'] = self._io.pos()
            self._debug['source_chunk']['arr'] = []
            self.source_chunk = []
            for i in range(self.source_count):
                self._debug['source_chunk']['arr'].append({'start': self._io.pos()})
                _t_source_chunk = RtcpPayload.SourceChunk(self._io, self, self._root)
                try:
                    _t_source_chunk._read()
                finally:
                    self.source_chunk.append(_t_source_chunk)
                self._debug['source_chunk']['arr'][i]['end'] = self._io.pos()

            self._debug['source_chunk']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.source_chunk)):
                pass
                self.source_chunk[i]._fetch_instances()


        @property
        def source_count(self):
            if hasattr(self, '_m_source_count'):
                return self._m_source_count

            self._m_source_count = self._parent.subtype
            return getattr(self, '_m_source_count', None)


    class SdesTlv(KaitaiStruct):
        SEQ_FIELDS = ["type", "length", "value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.SdesTlv, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(RtcpPayload.SdesSubtype, self._io.read_u1())
            self._debug['type']['end'] = self._io.pos()
            if self.type != RtcpPayload.SdesSubtype.pad:
                pass
                self._debug['length']['start'] = self._io.pos()
                self.length = self._io.read_u1()
                self._debug['length']['end'] = self._io.pos()

            if self.type != RtcpPayload.SdesSubtype.pad:
                pass
                self._debug['value']['start'] = self._io.pos()
                self.value = self._io.read_bytes(self.length)
                self._debug['value']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.type != RtcpPayload.SdesSubtype.pad:
                pass

            if self.type != RtcpPayload.SdesSubtype.pad:
                pass



    class SourceChunk(KaitaiStruct):
        SEQ_FIELDS = ["ssrc", "sdes_tlv"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.SourceChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc']['start'] = self._io.pos()
            self.ssrc = self._io.read_u4be()
            self._debug['ssrc']['end'] = self._io.pos()
            self._debug['sdes_tlv']['start'] = self._io.pos()
            self._debug['sdes_tlv']['arr'] = []
            self.sdes_tlv = []
            i = 0
            while not self._io.is_eof():
                self._debug['sdes_tlv']['arr'].append({'start': self._io.pos()})
                _t_sdes_tlv = RtcpPayload.SdesTlv(self._io, self, self._root)
                try:
                    _t_sdes_tlv._read()
                finally:
                    self.sdes_tlv.append(_t_sdes_tlv)
                self._debug['sdes_tlv']['arr'][len(self.sdes_tlv) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['sdes_tlv']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.sdes_tlv)):
                pass
                self.sdes_tlv[i]._fetch_instances()



    class SrPacket(KaitaiStruct):
        SEQ_FIELDS = ["ssrc", "ntp_msw", "ntp_lsw", "rtp_timestamp", "sender_packet_count", "sender_octet_count", "report_block"]
        def __init__(self, _io, _parent=None, _root=None):
            super(RtcpPayload.SrPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ssrc']['start'] = self._io.pos()
            self.ssrc = self._io.read_u4be()
            self._debug['ssrc']['end'] = self._io.pos()
            self._debug['ntp_msw']['start'] = self._io.pos()
            self.ntp_msw = self._io.read_u4be()
            self._debug['ntp_msw']['end'] = self._io.pos()
            self._debug['ntp_lsw']['start'] = self._io.pos()
            self.ntp_lsw = self._io.read_u4be()
            self._debug['ntp_lsw']['end'] = self._io.pos()
            self._debug['rtp_timestamp']['start'] = self._io.pos()
            self.rtp_timestamp = self._io.read_u4be()
            self._debug['rtp_timestamp']['end'] = self._io.pos()
            self._debug['sender_packet_count']['start'] = self._io.pos()
            self.sender_packet_count = self._io.read_u4be()
            self._debug['sender_packet_count']['end'] = self._io.pos()
            self._debug['sender_octet_count']['start'] = self._io.pos()
            self.sender_octet_count = self._io.read_u4be()
            self._debug['sender_octet_count']['end'] = self._io.pos()
            self._debug['report_block']['start'] = self._io.pos()
            self._debug['report_block']['arr'] = []
            self.report_block = []
            for i in range(self._parent.subtype):
                self._debug['report_block']['arr'].append({'start': self._io.pos()})
                _t_report_block = RtcpPayload.ReportBlock(self._io, self, self._root)
                try:
                    _t_report_block._read()
                finally:
                    self.report_block.append(_t_report_block)
                self._debug['report_block']['arr'][i]['end'] = self._io.pos()

            self._debug['report_block']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.report_block)):
                pass
                self.report_block[i]._fetch_instances()


        @property
        def ntp(self):
            if hasattr(self, '_m_ntp'):
                return self._m_ntp

            self._m_ntp = self.ntp_msw << 32 & self.ntp_lsw
            return getattr(self, '_m_ntp', None)



