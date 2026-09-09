# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Mcap(KaitaiStruct):
    """MCAP is a modular container format and logging library for pub/sub messages with
    arbitrary message serialization. It is primarily intended for use in robotics
    applications, and works well under various workloads, resource constraints, and
    durability requirements.
    
    Time values (`log_time`, `publish_time`, `create_time`) are represented in
    nanoseconds since a user-understood epoch (i.e. Unix epoch, robot boot time,
    etc.)
    
    .. seealso::
       Source - https://github.com/foxglove/mcap/tree/c1cc51d/docs/specification#readme
    """

    class Opcode(IntEnum):
        header = 1
        footer = 2
        schema = 3
        channel = 4
        message = 5
        chunk = 6
        message_index = 7
        chunk_index = 8
        attachment = 9
        attachment_index = 10
        statistics = 11
        metadata = 12
        metadata_index = 13
        summary_offset = 14
        data_end = 15
    SEQ_FIELDS = ["header_magic", "records", "footer_magic"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Mcap, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header_magic']['start'] = self._io.pos()
        self.header_magic = Mcap.Magic(self._io, self, self._root)
        self.header_magic._read()
        self._debug['header_magic']['end'] = self._io.pos()
        self._debug['records']['start'] = self._io.pos()
        self._debug['records']['arr'] = []
        self.records = []
        i = 0
        while True:
            self._debug['records']['arr'].append({'start': self._io.pos()})
            _t_records = Mcap.Record(self._io, self, self._root)
            try:
                _t_records._read()
            finally:
                _ = _t_records
                self.records.append(_)
            self._debug['records']['arr'][len(self.records) - 1]['end'] = self._io.pos()
            if _.op == Mcap.Opcode.footer:
                break
            i += 1
        self._debug['records']['end'] = self._io.pos()
        self._debug['footer_magic']['start'] = self._io.pos()
        self.footer_magic = Mcap.Magic(self._io, self, self._root)
        self.footer_magic._read()
        self._debug['footer_magic']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header_magic._fetch_instances()
        for i in range(len(self.records)):
            pass
            self.records[i]._fetch_instances()

        self.footer_magic._fetch_instances()
        _ = self.footer
        if hasattr(self, '_m_footer'):
            pass
            self._m_footer._fetch_instances()


    class Attachment(KaitaiStruct):
        SEQ_FIELDS = ["log_time", "create_time", "name", "content_type", "len_data", "data", "invoke_crc32_input_end", "crc32"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Attachment, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['log_time']['start'] = self._io.pos()
            self.log_time = self._io.read_u8le()
            self._debug['log_time']['end'] = self._io.pos()
            self._debug['create_time']['start'] = self._io.pos()
            self.create_time = self._io.read_u8le()
            self._debug['create_time']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = Mcap.PrefixedStr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['content_type']['start'] = self._io.pos()
            self.content_type = Mcap.PrefixedStr(self._io, self, self._root)
            self.content_type._read()
            self._debug['content_type']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u8le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()
            if self.crc32_input_end >= 0:
                pass
                self._debug['invoke_crc32_input_end']['start'] = self._io.pos()
                self.invoke_crc32_input_end = self._io.read_bytes(0)
                self._debug['invoke_crc32_input_end']['end'] = self._io.pos()

            self._debug['crc32']['start'] = self._io.pos()
            self.crc32 = self._io.read_u4le()
            self._debug['crc32']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.content_type._fetch_instances()
            if self.crc32_input_end >= 0:
                pass

            _ = self.crc32_input
            if hasattr(self, '_m_crc32_input'):
                pass


        @property
        def crc32_input(self):
            if hasattr(self, '_m_crc32_input'):
                return self._m_crc32_input

            _pos = self._io.pos()
            self._io.seek(0)
            self._debug['_m_crc32_input']['start'] = self._io.pos()
            self._m_crc32_input = self._io.read_bytes(self.crc32_input_end)
            self._debug['_m_crc32_input']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_crc32_input', None)

        @property
        def crc32_input_end(self):
            if hasattr(self, '_m_crc32_input_end'):
                return self._m_crc32_input_end

            self._m_crc32_input_end = self._io.pos()
            return getattr(self, '_m_crc32_input_end', None)


    class AttachmentIndex(KaitaiStruct):
        SEQ_FIELDS = ["ofs_attachment", "len_attachment", "log_time", "create_time", "data_size", "name", "content_type"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.AttachmentIndex, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_attachment']['start'] = self._io.pos()
            self.ofs_attachment = self._io.read_u8le()
            self._debug['ofs_attachment']['end'] = self._io.pos()
            self._debug['len_attachment']['start'] = self._io.pos()
            self.len_attachment = self._io.read_u8le()
            self._debug['len_attachment']['end'] = self._io.pos()
            self._debug['log_time']['start'] = self._io.pos()
            self.log_time = self._io.read_u8le()
            self._debug['log_time']['end'] = self._io.pos()
            self._debug['create_time']['start'] = self._io.pos()
            self.create_time = self._io.read_u8le()
            self._debug['create_time']['end'] = self._io.pos()
            self._debug['data_size']['start'] = self._io.pos()
            self.data_size = self._io.read_u8le()
            self._debug['data_size']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = Mcap.PrefixedStr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['content_type']['start'] = self._io.pos()
            self.content_type = Mcap.PrefixedStr(self._io, self, self._root)
            self.content_type._read()
            self._debug['content_type']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.content_type._fetch_instances()
            _ = self.attachment
            if hasattr(self, '_m_attachment'):
                pass
                self._m_attachment._fetch_instances()


        @property
        def attachment(self):
            if hasattr(self, '_m_attachment'):
                return self._m_attachment

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_attachment)
            self._debug['_m_attachment']['start'] = io.pos()
            self._raw__m_attachment = io.read_bytes(self.len_attachment)
            _io__raw__m_attachment = KaitaiStream(BytesIO(self._raw__m_attachment))
            self._m_attachment = Mcap.Record(_io__raw__m_attachment, self, self._root)
            self._m_attachment._read()
            self._debug['_m_attachment']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_attachment', None)


    class Channel(KaitaiStruct):
        SEQ_FIELDS = ["id", "schema_id", "topic", "message_encoding", "metadata"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Channel, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u2le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['schema_id']['start'] = self._io.pos()
            self.schema_id = self._io.read_u2le()
            self._debug['schema_id']['end'] = self._io.pos()
            self._debug['topic']['start'] = self._io.pos()
            self.topic = Mcap.PrefixedStr(self._io, self, self._root)
            self.topic._read()
            self._debug['topic']['end'] = self._io.pos()
            self._debug['message_encoding']['start'] = self._io.pos()
            self.message_encoding = Mcap.PrefixedStr(self._io, self, self._root)
            self.message_encoding._read()
            self._debug['message_encoding']['end'] = self._io.pos()
            self._debug['metadata']['start'] = self._io.pos()
            self.metadata = Mcap.MapStrStr(self._io, self, self._root)
            self.metadata._read()
            self._debug['metadata']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.topic._fetch_instances()
            self.message_encoding._fetch_instances()
            self.metadata._fetch_instances()


    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["message_start_time", "message_end_time", "uncompressed_size", "uncompressed_crc32", "compression", "len_records", "records"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Chunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['message_start_time']['start'] = self._io.pos()
            self.message_start_time = self._io.read_u8le()
            self._debug['message_start_time']['end'] = self._io.pos()
            self._debug['message_end_time']['start'] = self._io.pos()
            self.message_end_time = self._io.read_u8le()
            self._debug['message_end_time']['end'] = self._io.pos()
            self._debug['uncompressed_size']['start'] = self._io.pos()
            self.uncompressed_size = self._io.read_u8le()
            self._debug['uncompressed_size']['end'] = self._io.pos()
            self._debug['uncompressed_crc32']['start'] = self._io.pos()
            self.uncompressed_crc32 = self._io.read_u4le()
            self._debug['uncompressed_crc32']['end'] = self._io.pos()
            self._debug['compression']['start'] = self._io.pos()
            self.compression = Mcap.PrefixedStr(self._io, self, self._root)
            self.compression._read()
            self._debug['compression']['end'] = self._io.pos()
            self._debug['len_records']['start'] = self._io.pos()
            self.len_records = self._io.read_u8le()
            self._debug['len_records']['end'] = self._io.pos()
            self._debug['records']['start'] = self._io.pos()
            _on = self.compression.str
            if _on == u"":
                pass
                self._raw_records = self._io.read_bytes(self.len_records)
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records))
                self.records = Mcap.Records(_io__raw_records, self, self._root)
                self.records._read()
            else:
                pass
                self.records = self._io.read_bytes(self.len_records)
            self._debug['records']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.compression._fetch_instances()
            _on = self.compression.str
            if _on == u"":
                pass
                self.records._fetch_instances()
            else:
                pass


    class ChunkIndex(KaitaiStruct):
        SEQ_FIELDS = ["message_start_time", "message_end_time", "ofs_chunk", "len_chunk", "len_message_index_offsets", "message_index_offsets", "message_index_length", "compression", "compressed_size", "uncompressed_size"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.ChunkIndex, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['message_start_time']['start'] = self._io.pos()
            self.message_start_time = self._io.read_u8le()
            self._debug['message_start_time']['end'] = self._io.pos()
            self._debug['message_end_time']['start'] = self._io.pos()
            self.message_end_time = self._io.read_u8le()
            self._debug['message_end_time']['end'] = self._io.pos()
            self._debug['ofs_chunk']['start'] = self._io.pos()
            self.ofs_chunk = self._io.read_u8le()
            self._debug['ofs_chunk']['end'] = self._io.pos()
            self._debug['len_chunk']['start'] = self._io.pos()
            self.len_chunk = self._io.read_u8le()
            self._debug['len_chunk']['end'] = self._io.pos()
            self._debug['len_message_index_offsets']['start'] = self._io.pos()
            self.len_message_index_offsets = self._io.read_u4le()
            self._debug['len_message_index_offsets']['end'] = self._io.pos()
            self._debug['message_index_offsets']['start'] = self._io.pos()
            self._raw_message_index_offsets = self._io.read_bytes(self.len_message_index_offsets)
            _io__raw_message_index_offsets = KaitaiStream(BytesIO(self._raw_message_index_offsets))
            self.message_index_offsets = Mcap.ChunkIndex.MessageIndexOffsets(_io__raw_message_index_offsets, self, self._root)
            self.message_index_offsets._read()
            self._debug['message_index_offsets']['end'] = self._io.pos()
            self._debug['message_index_length']['start'] = self._io.pos()
            self.message_index_length = self._io.read_u8le()
            self._debug['message_index_length']['end'] = self._io.pos()
            self._debug['compression']['start'] = self._io.pos()
            self.compression = Mcap.PrefixedStr(self._io, self, self._root)
            self.compression._read()
            self._debug['compression']['end'] = self._io.pos()
            self._debug['compressed_size']['start'] = self._io.pos()
            self.compressed_size = self._io.read_u8le()
            self._debug['compressed_size']['end'] = self._io.pos()
            self._debug['uncompressed_size']['start'] = self._io.pos()
            self.uncompressed_size = self._io.read_u8le()
            self._debug['uncompressed_size']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.message_index_offsets._fetch_instances()
            self.compression._fetch_instances()
            _ = self.chunk
            if hasattr(self, '_m_chunk'):
                pass
                self._m_chunk._fetch_instances()


        class MessageIndexOffset(KaitaiStruct):
            SEQ_FIELDS = ["channel_id", "offset"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.ChunkIndex.MessageIndexOffset, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['channel_id']['start'] = self._io.pos()
                self.channel_id = self._io.read_u2le()
                self._debug['channel_id']['end'] = self._io.pos()
                self._debug['offset']['start'] = self._io.pos()
                self.offset = self._io.read_u8le()
                self._debug['offset']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class MessageIndexOffsets(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.ChunkIndex.MessageIndexOffsets, self).__init__(_io)
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
                    _t_entries = Mcap.ChunkIndex.MessageIndexOffset(self._io, self, self._root)
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
        def chunk(self):
            if hasattr(self, '_m_chunk'):
                return self._m_chunk

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_chunk)
            self._debug['_m_chunk']['start'] = io.pos()
            self._raw__m_chunk = io.read_bytes(self.len_chunk)
            _io__raw__m_chunk = KaitaiStream(BytesIO(self._raw__m_chunk))
            self._m_chunk = Mcap.Record(_io__raw__m_chunk, self, self._root)
            self._m_chunk._read()
            self._debug['_m_chunk']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_chunk', None)


    class DataEnd(KaitaiStruct):
        SEQ_FIELDS = ["data_section_crc32"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.DataEnd, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['data_section_crc32']['start'] = self._io.pos()
            self.data_section_crc32 = self._io.read_u4le()
            self._debug['data_section_crc32']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Footer(KaitaiStruct):
        SEQ_FIELDS = ["ofs_summary_section", "ofs_summary_offset_section", "summary_crc32"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Footer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_summary_section']['start'] = self._io.pos()
            self.ofs_summary_section = self._io.read_u8le()
            self._debug['ofs_summary_section']['end'] = self._io.pos()
            self._debug['ofs_summary_offset_section']['start'] = self._io.pos()
            self.ofs_summary_offset_section = self._io.read_u8le()
            self._debug['ofs_summary_offset_section']['end'] = self._io.pos()
            self._debug['summary_crc32']['start'] = self._io.pos()
            self.summary_crc32 = self._io.read_u4le()
            self._debug['summary_crc32']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.summary_crc32_input
            if hasattr(self, '_m_summary_crc32_input'):
                pass

            _ = self.summary_offset_section
            if hasattr(self, '_m_summary_offset_section'):
                pass
                self._m_summary_offset_section._fetch_instances()

            _ = self.summary_section
            if hasattr(self, '_m_summary_section'):
                pass
                self._m_summary_section._fetch_instances()


        @property
        def ofs_summary_crc32_input(self):
            if hasattr(self, '_m_ofs_summary_crc32_input'):
                return self._m_ofs_summary_crc32_input

            self._m_ofs_summary_crc32_input = (self.ofs_summary_section if self.ofs_summary_section != 0 else self._root.ofs_footer)
            return getattr(self, '_m_ofs_summary_crc32_input', None)

        @property
        def summary_crc32_input(self):
            if hasattr(self, '_m_summary_crc32_input'):
                return self._m_summary_crc32_input

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_summary_crc32_input)
            self._debug['_m_summary_crc32_input']['start'] = io.pos()
            self._m_summary_crc32_input = io.read_bytes(((self._root._io.size() - self.ofs_summary_crc32_input) - 8) - 4)
            self._debug['_m_summary_crc32_input']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_summary_crc32_input', None)

        @property
        def summary_offset_section(self):
            if hasattr(self, '_m_summary_offset_section'):
                return self._m_summary_offset_section

            if self.ofs_summary_offset_section != 0:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs_summary_offset_section)
                self._debug['_m_summary_offset_section']['start'] = io.pos()
                self._raw__m_summary_offset_section = io.read_bytes(self._root.ofs_footer - self.ofs_summary_offset_section)
                _io__raw__m_summary_offset_section = KaitaiStream(BytesIO(self._raw__m_summary_offset_section))
                self._m_summary_offset_section = Mcap.Records(_io__raw__m_summary_offset_section, self, self._root)
                self._m_summary_offset_section._read()
                self._debug['_m_summary_offset_section']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_summary_offset_section', None)

        @property
        def summary_section(self):
            if hasattr(self, '_m_summary_section'):
                return self._m_summary_section

            if self.ofs_summary_section != 0:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs_summary_section)
                self._debug['_m_summary_section']['start'] = io.pos()
                self._raw__m_summary_section = io.read_bytes((self.ofs_summary_offset_section if self.ofs_summary_offset_section != 0 else self._root.ofs_footer) - self.ofs_summary_section)
                _io__raw__m_summary_section = KaitaiStream(BytesIO(self._raw__m_summary_section))
                self._m_summary_section = Mcap.Records(_io__raw__m_summary_section, self, self._root)
                self._m_summary_section._read()
                self._debug['_m_summary_section']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_summary_section', None)


    class Header(KaitaiStruct):
        SEQ_FIELDS = ["profile", "library"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Header, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['profile']['start'] = self._io.pos()
            self.profile = Mcap.PrefixedStr(self._io, self, self._root)
            self.profile._read()
            self._debug['profile']['end'] = self._io.pos()
            self._debug['library']['start'] = self._io.pos()
            self.library = Mcap.PrefixedStr(self._io, self, self._root)
            self.library._read()
            self._debug['library']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.profile._fetch_instances()
            self.library._fetch_instances()


    class Magic(KaitaiStruct):
        SEQ_FIELDS = ["magic"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Magic, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(8)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x89\x4D\x43\x41\x50\x30\x0D\x0A":
                raise kaitaistruct.ValidationNotEqualError(b"\x89\x4D\x43\x41\x50\x30\x0D\x0A", self.magic, self._io, u"/types/magic/seq/0")


        def _fetch_instances(self):
            pass


    class MapStrStr(KaitaiStruct):
        SEQ_FIELDS = ["len_entries", "entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.MapStrStr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_entries']['start'] = self._io.pos()
            self.len_entries = self._io.read_u4le()
            self._debug['len_entries']['end'] = self._io.pos()
            self._debug['entries']['start'] = self._io.pos()
            self._raw_entries = self._io.read_bytes(self.len_entries)
            _io__raw_entries = KaitaiStream(BytesIO(self._raw_entries))
            self.entries = Mcap.MapStrStr.Entries(_io__raw_entries, self, self._root)
            self.entries._read()
            self._debug['entries']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.entries._fetch_instances()

        class Entries(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.MapStrStr.Entries, self).__init__(_io)
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
                    _t_entries = Mcap.TupleStrStr(self._io, self, self._root)
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




    class Message(KaitaiStruct):
        SEQ_FIELDS = ["channel_id", "sequence", "log_time", "publish_time", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Message, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['channel_id']['start'] = self._io.pos()
            self.channel_id = self._io.read_u2le()
            self._debug['channel_id']['end'] = self._io.pos()
            self._debug['sequence']['start'] = self._io.pos()
            self.sequence = self._io.read_u4le()
            self._debug['sequence']['end'] = self._io.pos()
            self._debug['log_time']['start'] = self._io.pos()
            self.log_time = self._io.read_u8le()
            self._debug['log_time']['end'] = self._io.pos()
            self._debug['publish_time']['start'] = self._io.pos()
            self.publish_time = self._io.read_u8le()
            self._debug['publish_time']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class MessageIndex(KaitaiStruct):
        SEQ_FIELDS = ["channel_id", "len_records", "records"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.MessageIndex, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['channel_id']['start'] = self._io.pos()
            self.channel_id = self._io.read_u2le()
            self._debug['channel_id']['end'] = self._io.pos()
            self._debug['len_records']['start'] = self._io.pos()
            self.len_records = self._io.read_u4le()
            self._debug['len_records']['end'] = self._io.pos()
            self._debug['records']['start'] = self._io.pos()
            self._raw_records = self._io.read_bytes(self.len_records)
            _io__raw_records = KaitaiStream(BytesIO(self._raw_records))
            self.records = Mcap.MessageIndex.MessageIndexEntries(_io__raw_records, self, self._root)
            self.records._read()
            self._debug['records']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.records._fetch_instances()

        class MessageIndexEntries(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.MessageIndex.MessageIndexEntries, self).__init__(_io)
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
                    _t_entries = Mcap.MessageIndex.MessageIndexEntry(self._io, self, self._root)
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



        class MessageIndexEntry(KaitaiStruct):
            SEQ_FIELDS = ["log_time", "offset"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.MessageIndex.MessageIndexEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['log_time']['start'] = self._io.pos()
                self.log_time = self._io.read_u8le()
                self._debug['log_time']['end'] = self._io.pos()
                self._debug['offset']['start'] = self._io.pos()
                self.offset = self._io.read_u8le()
                self._debug['offset']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass



    class Metadata(KaitaiStruct):
        SEQ_FIELDS = ["name", "metadata"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Metadata, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = Mcap.PrefixedStr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['metadata']['start'] = self._io.pos()
            self.metadata = Mcap.MapStrStr(self._io, self, self._root)
            self.metadata._read()
            self._debug['metadata']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.metadata._fetch_instances()


    class MetadataIndex(KaitaiStruct):
        SEQ_FIELDS = ["ofs_metadata", "len_metadata", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.MetadataIndex, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_metadata']['start'] = self._io.pos()
            self.ofs_metadata = self._io.read_u8le()
            self._debug['ofs_metadata']['end'] = self._io.pos()
            self._debug['len_metadata']['start'] = self._io.pos()
            self.len_metadata = self._io.read_u8le()
            self._debug['len_metadata']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = Mcap.PrefixedStr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            _ = self.metadata
            if hasattr(self, '_m_metadata'):
                pass
                self._m_metadata._fetch_instances()


        @property
        def metadata(self):
            if hasattr(self, '_m_metadata'):
                return self._m_metadata

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_metadata)
            self._debug['_m_metadata']['start'] = io.pos()
            self._raw__m_metadata = io.read_bytes(self.len_metadata)
            _io__raw__m_metadata = KaitaiStream(BytesIO(self._raw__m_metadata))
            self._m_metadata = Mcap.Record(_io__raw__m_metadata, self, self._root)
            self._m_metadata._read()
            self._debug['_m_metadata']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_metadata', None)


    class PrefixedStr(KaitaiStruct):
        SEQ_FIELDS = ["len_str", "str"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.PrefixedStr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_str']['start'] = self._io.pos()
            self.len_str = self._io.read_u4le()
            self._debug['len_str']['end'] = self._io.pos()
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes(self.len_str)).decode(u"UTF-8")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Record(KaitaiStruct):
        SEQ_FIELDS = ["op", "len_body", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Record, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['op']['start'] = self._io.pos()
            self.op = KaitaiStream.resolve_enum(Mcap.Opcode, self._io.read_u1())
            self._debug['op']['end'] = self._io.pos()
            self._debug['len_body']['start'] = self._io.pos()
            self.len_body = self._io.read_u8le()
            self._debug['len_body']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.op
            if _on == Mcap.Opcode.attachment:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Attachment(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.attachment_index:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.AttachmentIndex(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.channel:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Channel(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.chunk:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Chunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.chunk_index:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.ChunkIndex(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.data_end:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.DataEnd(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.footer:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Footer(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.header:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Header(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.message:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Message(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.message_index:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.MessageIndex(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.metadata:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Metadata(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.metadata_index:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.MetadataIndex(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.schema:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Schema(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.statistics:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.Statistics(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == Mcap.Opcode.summary_offset:
                pass
                self._raw_body = self._io.read_bytes(self.len_body)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Mcap.SummaryOffset(_io__raw_body, self, self._root)
                self.body._read()
            else:
                pass
                self.body = self._io.read_bytes(self.len_body)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.op
            if _on == Mcap.Opcode.attachment:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.attachment_index:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.channel:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.chunk:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.chunk_index:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.data_end:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.footer:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.header:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.message:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.message_index:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.metadata:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.metadata_index:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.schema:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.statistics:
                pass
                self.body._fetch_instances()
            elif _on == Mcap.Opcode.summary_offset:
                pass
                self.body._fetch_instances()
            else:
                pass


    class Records(KaitaiStruct):
        SEQ_FIELDS = ["records"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Records, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['records']['start'] = self._io.pos()
            self._debug['records']['arr'] = []
            self.records = []
            i = 0
            while not self._io.is_eof():
                self._debug['records']['arr'].append({'start': self._io.pos()})
                _t_records = Mcap.Record(self._io, self, self._root)
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



    class Schema(KaitaiStruct):
        SEQ_FIELDS = ["id", "name", "encoding", "len_data", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Schema, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['id']['start'] = self._io.pos()
            self.id = self._io.read_u2le()
            self._debug['id']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = Mcap.PrefixedStr(self._io, self, self._root)
            self.name._read()
            self._debug['name']['end'] = self._io.pos()
            self._debug['encoding']['start'] = self._io.pos()
            self.encoding = Mcap.PrefixedStr(self._io, self, self._root)
            self.encoding._read()
            self._debug['encoding']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.encoding._fetch_instances()


    class Statistics(KaitaiStruct):
        SEQ_FIELDS = ["message_count", "schema_count", "channel_count", "attachment_count", "metadata_count", "chunk_count", "message_start_time", "message_end_time", "len_channel_message_counts", "channel_message_counts"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.Statistics, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['message_count']['start'] = self._io.pos()
            self.message_count = self._io.read_u8le()
            self._debug['message_count']['end'] = self._io.pos()
            self._debug['schema_count']['start'] = self._io.pos()
            self.schema_count = self._io.read_u2le()
            self._debug['schema_count']['end'] = self._io.pos()
            self._debug['channel_count']['start'] = self._io.pos()
            self.channel_count = self._io.read_u4le()
            self._debug['channel_count']['end'] = self._io.pos()
            self._debug['attachment_count']['start'] = self._io.pos()
            self.attachment_count = self._io.read_u4le()
            self._debug['attachment_count']['end'] = self._io.pos()
            self._debug['metadata_count']['start'] = self._io.pos()
            self.metadata_count = self._io.read_u4le()
            self._debug['metadata_count']['end'] = self._io.pos()
            self._debug['chunk_count']['start'] = self._io.pos()
            self.chunk_count = self._io.read_u4le()
            self._debug['chunk_count']['end'] = self._io.pos()
            self._debug['message_start_time']['start'] = self._io.pos()
            self.message_start_time = self._io.read_u8le()
            self._debug['message_start_time']['end'] = self._io.pos()
            self._debug['message_end_time']['start'] = self._io.pos()
            self.message_end_time = self._io.read_u8le()
            self._debug['message_end_time']['end'] = self._io.pos()
            self._debug['len_channel_message_counts']['start'] = self._io.pos()
            self.len_channel_message_counts = self._io.read_u4le()
            self._debug['len_channel_message_counts']['end'] = self._io.pos()
            self._debug['channel_message_counts']['start'] = self._io.pos()
            self._raw_channel_message_counts = self._io.read_bytes(self.len_channel_message_counts)
            _io__raw_channel_message_counts = KaitaiStream(BytesIO(self._raw_channel_message_counts))
            self.channel_message_counts = Mcap.Statistics.ChannelMessageCounts(_io__raw_channel_message_counts, self, self._root)
            self.channel_message_counts._read()
            self._debug['channel_message_counts']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.channel_message_counts._fetch_instances()

        class ChannelMessageCount(KaitaiStruct):
            SEQ_FIELDS = ["channel_id", "message_count"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.Statistics.ChannelMessageCount, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['channel_id']['start'] = self._io.pos()
                self.channel_id = self._io.read_u2le()
                self._debug['channel_id']['end'] = self._io.pos()
                self._debug['message_count']['start'] = self._io.pos()
                self.message_count = self._io.read_u8le()
                self._debug['message_count']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class ChannelMessageCounts(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None):
                super(Mcap.Statistics.ChannelMessageCounts, self).__init__(_io)
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
                    _t_entries = Mcap.Statistics.ChannelMessageCount(self._io, self, self._root)
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




    class SummaryOffset(KaitaiStruct):
        SEQ_FIELDS = ["group_opcode", "ofs_group", "len_group"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.SummaryOffset, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['group_opcode']['start'] = self._io.pos()
            self.group_opcode = KaitaiStream.resolve_enum(Mcap.Opcode, self._io.read_u1())
            self._debug['group_opcode']['end'] = self._io.pos()
            self._debug['ofs_group']['start'] = self._io.pos()
            self.ofs_group = self._io.read_u8le()
            self._debug['ofs_group']['end'] = self._io.pos()
            self._debug['len_group']['start'] = self._io.pos()
            self.len_group = self._io.read_u8le()
            self._debug['len_group']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.group
            if hasattr(self, '_m_group'):
                pass
                self._m_group._fetch_instances()


        @property
        def group(self):
            if hasattr(self, '_m_group'):
                return self._m_group

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_group)
            self._debug['_m_group']['start'] = io.pos()
            self._raw__m_group = io.read_bytes(self.len_group)
            _io__raw__m_group = KaitaiStream(BytesIO(self._raw__m_group))
            self._m_group = Mcap.Records(_io__raw__m_group, self, self._root)
            self._m_group._read()
            self._debug['_m_group']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_group', None)


    class TupleStrStr(KaitaiStruct):
        SEQ_FIELDS = ["key", "value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Mcap.TupleStrStr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['key']['start'] = self._io.pos()
            self.key = Mcap.PrefixedStr(self._io, self, self._root)
            self.key._read()
            self._debug['key']['end'] = self._io.pos()
            self._debug['value']['start'] = self._io.pos()
            self.value = Mcap.PrefixedStr(self._io, self, self._root)
            self.value._read()
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.key._fetch_instances()
            self.value._fetch_instances()


    @property
    def footer(self):
        if hasattr(self, '_m_footer'):
            return self._m_footer

        _pos = self._io.pos()
        self._io.seek(self.ofs_footer)
        self._debug['_m_footer']['start'] = self._io.pos()
        self._raw__m_footer = self._io.read_bytes_full()
        _io__raw__m_footer = KaitaiStream(BytesIO(self._raw__m_footer))
        self._m_footer = Mcap.Record(_io__raw__m_footer, self, self._root)
        self._m_footer._read()
        self._debug['_m_footer']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_footer', None)

    @property
    def ofs_footer(self):
        if hasattr(self, '_m_ofs_footer'):
            return self._m_ofs_footer

        self._m_ofs_footer = (((self._io.size() - 1) - 8) - 20) - 8
        return getattr(self, '_m_ofs_footer', None)


