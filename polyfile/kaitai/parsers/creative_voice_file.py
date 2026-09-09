# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class CreativeVoiceFile(KaitaiStruct):
    """Creative Voice File is a container file format for digital audio
    wave data. Initial revisions were able to support only unsigned
    8-bit PCM and ADPCM data, later versions were revised to add support
    for 16-bit PCM and a-law / u-law formats.
    
    This format was actively used in 1990s, around the advent of
    Creative's sound cards (Sound Blaster family). It was a popular
    choice for a digital sound container in lots of games and multimedia
    software due to simplicity and availability of Creative's recording
    / editing tools.
    
    .. seealso::
       Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice
    """

    class BlockTypes(IntEnum):
        terminator = 0
        sound_data = 1
        sound_data_cont = 2
        silence = 3
        marker = 4
        text = 5
        repeat_start = 6
        repeat_end = 7
        extra_info = 8
        sound_data_new = 9

    class Codecs(IntEnum):
        pcm_8bit_unsigned = 0
        adpcm_4bit = 1
        adpcm_2_6bit = 2
        adpcm_2_bit = 3
        pcm_16bit_signed = 4
        alaw = 6
        ulaw = 7
        adpcm_4_to_16bit = 512
    SEQ_FIELDS = ["magic", "header_size", "version", "checksum", "blocks"]
    def __init__(self, _io, _parent=None, _root=None):
        super(CreativeVoiceFile, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(20)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x43\x72\x65\x61\x74\x69\x76\x65\x20\x56\x6F\x69\x63\x65\x20\x46\x69\x6C\x65\x1A":
            raise kaitaistruct.ValidationNotEqualError(b"\x43\x72\x65\x61\x74\x69\x76\x65\x20\x56\x6F\x69\x63\x65\x20\x46\x69\x6C\x65\x1A", self.magic, self._io, u"/seq/0")
        self._debug['header_size']['start'] = self._io.pos()
        self.header_size = self._io.read_u2le()
        self._debug['header_size']['end'] = self._io.pos()
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u2le()
        self._debug['version']['end'] = self._io.pos()
        self._debug['checksum']['start'] = self._io.pos()
        self.checksum = self._io.read_u2le()
        self._debug['checksum']['end'] = self._io.pos()
        self._debug['blocks']['start'] = self._io.pos()
        self._debug['blocks']['arr'] = []
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            self._debug['blocks']['arr'].append({'start': self._io.pos()})
            _t_blocks = CreativeVoiceFile.Block(self._io, self, self._root)
            try:
                _t_blocks._read()
            finally:
                self.blocks.append(_t_blocks)
            self._debug['blocks']['arr'][len(self.blocks) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['blocks']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.blocks)):
            pass
            self.blocks[i]._fetch_instances()


    class Block(KaitaiStruct):
        SEQ_FIELDS = ["block_type", "body_size1", "body_size2", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.Block, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['block_type']['start'] = self._io.pos()
            self.block_type = KaitaiStream.resolve_enum(CreativeVoiceFile.BlockTypes, self._io.read_u1())
            self._debug['block_type']['end'] = self._io.pos()
            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass
                self._debug['body_size1']['start'] = self._io.pos()
                self.body_size1 = self._io.read_u2le()
                self._debug['body_size1']['end'] = self._io.pos()

            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass
                self._debug['body_size2']['start'] = self._io.pos()
                self.body_size2 = self._io.read_u1()
                self._debug['body_size2']['end'] = self._io.pos()

            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass
                self._debug['body']['start'] = self._io.pos()
                _on = self.block_type
                if _on == CreativeVoiceFile.BlockTypes.extra_info:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockExtraInfo(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == CreativeVoiceFile.BlockTypes.marker:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockMarker(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == CreativeVoiceFile.BlockTypes.repeat_start:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockRepeatStart(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == CreativeVoiceFile.BlockTypes.silence:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockSilence(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == CreativeVoiceFile.BlockTypes.sound_data:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockSoundData(_io__raw_body, self, self._root)
                    self.body._read()
                elif _on == CreativeVoiceFile.BlockTypes.sound_data_new:
                    pass
                    self._raw_body = self._io.read_bytes(self.body_size)
                    _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                    self.body = CreativeVoiceFile.BlockSoundDataNew(_io__raw_body, self, self._root)
                    self.body._read()
                else:
                    pass
                    self.body = self._io.read_bytes(self.body_size)
                self._debug['body']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass

            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass

            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass
                _on = self.block_type
                if _on == CreativeVoiceFile.BlockTypes.extra_info:
                    pass
                    self.body._fetch_instances()
                elif _on == CreativeVoiceFile.BlockTypes.marker:
                    pass
                    self.body._fetch_instances()
                elif _on == CreativeVoiceFile.BlockTypes.repeat_start:
                    pass
                    self.body._fetch_instances()
                elif _on == CreativeVoiceFile.BlockTypes.silence:
                    pass
                    self.body._fetch_instances()
                elif _on == CreativeVoiceFile.BlockTypes.sound_data:
                    pass
                    self.body._fetch_instances()
                elif _on == CreativeVoiceFile.BlockTypes.sound_data_new:
                    pass
                    self.body._fetch_instances()
                else:
                    pass


        @property
        def body_size(self):
            """body_size is a 24-bit little-endian integer, so we're
            emulating that by adding two standard-sized integers
            (body_size1 and body_size2).
            """
            if hasattr(self, '_m_body_size'):
                return self._m_body_size

            if self.block_type != CreativeVoiceFile.BlockTypes.terminator:
                pass
                self._m_body_size = self.body_size1 + (self.body_size2 << 16)

            return getattr(self, '_m_body_size', None)


    class BlockExtraInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x08:_Extra_info
        """
        SEQ_FIELDS = ["freq_div", "codec", "num_channels_1"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockExtraInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['freq_div']['start'] = self._io.pos()
            self.freq_div = self._io.read_u2le()
            self._debug['freq_div']['end'] = self._io.pos()
            self._debug['codec']['start'] = self._io.pos()
            self.codec = KaitaiStream.resolve_enum(CreativeVoiceFile.Codecs, self._io.read_u1())
            self._debug['codec']['end'] = self._io.pos()
            self._debug['num_channels_1']['start'] = self._io.pos()
            self.num_channels_1 = self._io.read_u1()
            self._debug['num_channels_1']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def num_channels(self):
            """Number of channels (1 = mono, 2 = stereo)."""
            if hasattr(self, '_m_num_channels'):
                return self._m_num_channels

            self._m_num_channels = self.num_channels_1 + 1
            return getattr(self, '_m_num_channels', None)

        @property
        def sample_rate(self):
            if hasattr(self, '_m_sample_rate'):
                return self._m_sample_rate

            self._m_sample_rate = 256000000.0 / (self.num_channels * (65536 - self.freq_div))
            return getattr(self, '_m_sample_rate', None)


    class BlockMarker(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x04:_Marker
        """
        SEQ_FIELDS = ["marker_id"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockMarker, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['marker_id']['start'] = self._io.pos()
            self.marker_id = self._io.read_u2le()
            self._debug['marker_id']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class BlockRepeatStart(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x06:_Repeat_start
        """
        SEQ_FIELDS = ["repeat_count_1"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockRepeatStart, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['repeat_count_1']['start'] = self._io.pos()
            self.repeat_count_1 = self._io.read_u2le()
            self._debug['repeat_count_1']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class BlockSilence(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x03:_Silence
        """
        SEQ_FIELDS = ["duration_samples", "freq_div"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockSilence, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['duration_samples']['start'] = self._io.pos()
            self.duration_samples = self._io.read_u2le()
            self._debug['duration_samples']['end'] = self._io.pos()
            self._debug['freq_div']['start'] = self._io.pos()
            self.freq_div = self._io.read_u1()
            self._debug['freq_div']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def duration_sec(self):
            """Duration of silence, in seconds."""
            if hasattr(self, '_m_duration_sec'):
                return self._m_duration_sec

            self._m_duration_sec = self.duration_samples / self.sample_rate
            return getattr(self, '_m_duration_sec', None)

        @property
        def sample_rate(self):
            if hasattr(self, '_m_sample_rate'):
                return self._m_sample_rate

            self._m_sample_rate = 1000000.0 / (256 - self.freq_div)
            return getattr(self, '_m_sample_rate', None)


    class BlockSoundData(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x01:_Sound_data
        """
        SEQ_FIELDS = ["freq_div", "codec", "wave"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockSoundData, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['freq_div']['start'] = self._io.pos()
            self.freq_div = self._io.read_u1()
            self._debug['freq_div']['end'] = self._io.pos()
            self._debug['codec']['start'] = self._io.pos()
            self.codec = KaitaiStream.resolve_enum(CreativeVoiceFile.Codecs, self._io.read_u1())
            self._debug['codec']['end'] = self._io.pos()
            self._debug['wave']['start'] = self._io.pos()
            self.wave = self._io.read_bytes_full()
            self._debug['wave']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def sample_rate(self):
            if hasattr(self, '_m_sample_rate'):
                return self._m_sample_rate

            self._m_sample_rate = 1000000.0 / (256 - self.freq_div)
            return getattr(self, '_m_sample_rate', None)


    class BlockSoundDataNew(KaitaiStruct):
        """
        .. seealso::
           Source - https://wiki.multimedia.cx/index.php?title=Creative_Voice#Block_type_0x09:_Sound_data_.28New_format.29
        """
        SEQ_FIELDS = ["sample_rate", "bits_per_sample", "num_channels", "codec", "reserved", "wave"]
        def __init__(self, _io, _parent=None, _root=None):
            super(CreativeVoiceFile.BlockSoundDataNew, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['sample_rate']['start'] = self._io.pos()
            self.sample_rate = self._io.read_u4le()
            self._debug['sample_rate']['end'] = self._io.pos()
            self._debug['bits_per_sample']['start'] = self._io.pos()
            self.bits_per_sample = self._io.read_u1()
            self._debug['bits_per_sample']['end'] = self._io.pos()
            self._debug['num_channels']['start'] = self._io.pos()
            self.num_channels = self._io.read_u1()
            self._debug['num_channels']['end'] = self._io.pos()
            self._debug['codec']['start'] = self._io.pos()
            self.codec = KaitaiStream.resolve_enum(CreativeVoiceFile.Codecs, self._io.read_u2le())
            self._debug['codec']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_bytes(4)
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['wave']['start'] = self._io.pos()
            self.wave = self._io.read_bytes_full()
            self._debug['wave']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



