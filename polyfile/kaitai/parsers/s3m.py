# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class S3m(KaitaiStruct):
    """Scream Tracker 3 module is a tracker music file format that, as all
    tracker music, bundles both sound samples and instructions on which
    notes to play. It originates from a Scream Tracker 3 music editor
    (1994) by Future Crew, derived from original Scream Tracker 2 (.stm)
    module format.
    
    Instrument descriptions in S3M format allow to use either digital
    samples or setup and control AdLib (OPL2) synth.
    
    Music is organized in so called `patterns`. "Pattern" is a generally
    a 64-row long table, which instructs which notes to play on which
    time measure. "Patterns" are played one-by-one in a sequence
    determined by `orders`, which is essentially an array of pattern IDs
    - this way it's possible to reuse certain patterns more than once
    for repetitive musical phrases.
    
    .. seealso::
       Source - http://hackipedia.org/browse.cgi/File%20formats/Music%20tracker/S3M%2c%20ScreamTracker%203/Scream%20Tracker%203.20%20by%20Future%20Crew.txt
    """
    SEQ_FIELDS = ["song_name", "magic1", "file_type", "reserved1", "num_orders", "num_instruments", "num_patterns", "flags", "version", "samples_format", "magic2", "global_volume", "initial_speed", "initial_tempo", "is_stereo", "master_volume", "ultra_click_removal", "has_custom_pan", "reserved2", "ofs_special", "channels", "orders", "instruments", "patterns", "channel_pans"]
    def __init__(self, _io, _parent=None, _root=None):
        super(S3m, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['song_name']['start'] = self._io.pos()
        self.song_name = KaitaiStream.bytes_terminate(self._io.read_bytes(28), 0, False)
        self._debug['song_name']['end'] = self._io.pos()
        self._debug['magic1']['start'] = self._io.pos()
        self.magic1 = self._io.read_bytes(1)
        self._debug['magic1']['end'] = self._io.pos()
        if not self.magic1 == b"\x1A":
            raise kaitaistruct.ValidationNotEqualError(b"\x1A", self.magic1, self._io, u"/seq/1")
        self._debug['file_type']['start'] = self._io.pos()
        self.file_type = self._io.read_u1()
        self._debug['file_type']['end'] = self._io.pos()
        self._debug['reserved1']['start'] = self._io.pos()
        self.reserved1 = self._io.read_bytes(2)
        self._debug['reserved1']['end'] = self._io.pos()
        self._debug['num_orders']['start'] = self._io.pos()
        self.num_orders = self._io.read_u2le()
        self._debug['num_orders']['end'] = self._io.pos()
        self._debug['num_instruments']['start'] = self._io.pos()
        self.num_instruments = self._io.read_u2le()
        self._debug['num_instruments']['end'] = self._io.pos()
        self._debug['num_patterns']['start'] = self._io.pos()
        self.num_patterns = self._io.read_u2le()
        self._debug['num_patterns']['end'] = self._io.pos()
        self._debug['flags']['start'] = self._io.pos()
        self.flags = self._io.read_u2le()
        self._debug['flags']['end'] = self._io.pos()
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u2le()
        self._debug['version']['end'] = self._io.pos()
        self._debug['samples_format']['start'] = self._io.pos()
        self.samples_format = self._io.read_u2le()
        self._debug['samples_format']['end'] = self._io.pos()
        self._debug['magic2']['start'] = self._io.pos()
        self.magic2 = self._io.read_bytes(4)
        self._debug['magic2']['end'] = self._io.pos()
        if not self.magic2 == b"\x53\x43\x52\x4D":
            raise kaitaistruct.ValidationNotEqualError(b"\x53\x43\x52\x4D", self.magic2, self._io, u"/seq/10")
        self._debug['global_volume']['start'] = self._io.pos()
        self.global_volume = self._io.read_u1()
        self._debug['global_volume']['end'] = self._io.pos()
        self._debug['initial_speed']['start'] = self._io.pos()
        self.initial_speed = self._io.read_u1()
        self._debug['initial_speed']['end'] = self._io.pos()
        self._debug['initial_tempo']['start'] = self._io.pos()
        self.initial_tempo = self._io.read_u1()
        self._debug['initial_tempo']['end'] = self._io.pos()
        self._debug['is_stereo']['start'] = self._io.pos()
        self.is_stereo = self._io.read_bits_int_be(1) != 0
        self._debug['is_stereo']['end'] = self._io.pos()
        self._debug['master_volume']['start'] = self._io.pos()
        self.master_volume = self._io.read_bits_int_be(7)
        self._debug['master_volume']['end'] = self._io.pos()
        self._debug['ultra_click_removal']['start'] = self._io.pos()
        self.ultra_click_removal = self._io.read_u1()
        self._debug['ultra_click_removal']['end'] = self._io.pos()
        self._debug['has_custom_pan']['start'] = self._io.pos()
        self.has_custom_pan = self._io.read_u1()
        self._debug['has_custom_pan']['end'] = self._io.pos()
        self._debug['reserved2']['start'] = self._io.pos()
        self.reserved2 = self._io.read_bytes(8)
        self._debug['reserved2']['end'] = self._io.pos()
        self._debug['ofs_special']['start'] = self._io.pos()
        self.ofs_special = self._io.read_u2le()
        self._debug['ofs_special']['end'] = self._io.pos()
        self._debug['channels']['start'] = self._io.pos()
        self._debug['channels']['arr'] = []
        self.channels = []
        for i in range(32):
            self._debug['channels']['arr'].append({'start': self._io.pos()})
            _t_channels = S3m.Channel(self._io, self, self._root)
            try:
                _t_channels._read()
            finally:
                self.channels.append(_t_channels)
            self._debug['channels']['arr'][i]['end'] = self._io.pos()

        self._debug['channels']['end'] = self._io.pos()
        self._debug['orders']['start'] = self._io.pos()
        self.orders = self._io.read_bytes(self.num_orders)
        self._debug['orders']['end'] = self._io.pos()
        self._debug['instruments']['start'] = self._io.pos()
        self._debug['instruments']['arr'] = []
        self.instruments = []
        for i in range(self.num_instruments):
            self._debug['instruments']['arr'].append({'start': self._io.pos()})
            _t_instruments = S3m.InstrumentPtr(self._io, self, self._root)
            try:
                _t_instruments._read()
            finally:
                self.instruments.append(_t_instruments)
            self._debug['instruments']['arr'][i]['end'] = self._io.pos()

        self._debug['instruments']['end'] = self._io.pos()
        self._debug['patterns']['start'] = self._io.pos()
        self._debug['patterns']['arr'] = []
        self.patterns = []
        for i in range(self.num_patterns):
            self._debug['patterns']['arr'].append({'start': self._io.pos()})
            _t_patterns = S3m.PatternPtr(self._io, self, self._root)
            try:
                _t_patterns._read()
            finally:
                self.patterns.append(_t_patterns)
            self._debug['patterns']['arr'][i]['end'] = self._io.pos()

        self._debug['patterns']['end'] = self._io.pos()
        if self.has_custom_pan == 252:
            pass
            self._debug['channel_pans']['start'] = self._io.pos()
            self._debug['channel_pans']['arr'] = []
            self.channel_pans = []
            for i in range(32):
                self._debug['channel_pans']['arr'].append({'start': self._io.pos()})
                _t_channel_pans = S3m.ChannelPan(self._io, self, self._root)
                try:
                    _t_channel_pans._read()
                finally:
                    self.channel_pans.append(_t_channel_pans)
                self._debug['channel_pans']['arr'][i]['end'] = self._io.pos()

            self._debug['channel_pans']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        for i in range(len(self.channels)):
            pass
            self.channels[i]._fetch_instances()

        for i in range(len(self.instruments)):
            pass
            self.instruments[i]._fetch_instances()

        for i in range(len(self.patterns)):
            pass
            self.patterns[i]._fetch_instances()

        if self.has_custom_pan == 252:
            pass
            for i in range(len(self.channel_pans)):
                pass
                self.channel_pans[i]._fetch_instances()



    class Channel(KaitaiStruct):
        SEQ_FIELDS = ["is_disabled", "ch_type"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.Channel, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['is_disabled']['start'] = self._io.pos()
            self.is_disabled = self._io.read_bits_int_be(1) != 0
            self._debug['is_disabled']['end'] = self._io.pos()
            self._debug['ch_type']['start'] = self._io.pos()
            self.ch_type = self._io.read_bits_int_be(7)
            self._debug['ch_type']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class ChannelPan(KaitaiStruct):
        SEQ_FIELDS = ["reserved1", "has_custom_pan", "reserved2", "pan"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.ChannelPan, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['reserved1']['start'] = self._io.pos()
            self.reserved1 = self._io.read_bits_int_be(2)
            self._debug['reserved1']['end'] = self._io.pos()
            self._debug['has_custom_pan']['start'] = self._io.pos()
            self.has_custom_pan = self._io.read_bits_int_be(1) != 0
            self._debug['has_custom_pan']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_bits_int_be(1) != 0
            self._debug['reserved2']['end'] = self._io.pos()
            self._debug['pan']['start'] = self._io.pos()
            self.pan = self._io.read_bits_int_be(4)
            self._debug['pan']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Instrument(KaitaiStruct):

        class InstTypes(IntEnum):
            sample = 1
            melodic = 2
            bass_drum = 3
            snare_drum = 4
            tom = 5
            cymbal = 6
            hihat = 7
        SEQ_FIELDS = ["type", "filename", "body", "tuning_hz", "reserved2", "sample_name", "magic"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.Instrument, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(S3m.Instrument.InstTypes, self._io.read_u1())
            self._debug['type']['end'] = self._io.pos()
            self._debug['filename']['start'] = self._io.pos()
            self.filename = KaitaiStream.bytes_terminate(self._io.read_bytes(12), 0, False)
            self._debug['filename']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == S3m.Instrument.InstTypes.sample:
                pass
                self.body = S3m.Instrument.Sampled(self._io, self, self._root)
                self.body._read()
            else:
                pass
                self.body = S3m.Instrument.Adlib(self._io, self, self._root)
                self.body._read()
            self._debug['body']['end'] = self._io.pos()
            self._debug['tuning_hz']['start'] = self._io.pos()
            self.tuning_hz = self._io.read_u4le()
            self._debug['tuning_hz']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_bytes(12)
            self._debug['reserved2']['end'] = self._io.pos()
            self._debug['sample_name']['start'] = self._io.pos()
            self.sample_name = KaitaiStream.bytes_terminate(self._io.read_bytes(28), 0, False)
            self._debug['sample_name']['end'] = self._io.pos()
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x53\x43\x52\x53":
                raise kaitaistruct.ValidationNotEqualError(b"\x53\x43\x52\x53", self.magic, self._io, u"/types/instrument/seq/6")


        def _fetch_instances(self):
            pass
            _on = self.type
            if _on == S3m.Instrument.InstTypes.sample:
                pass
                self.body._fetch_instances()
            else:
                pass
                self.body._fetch_instances()

        class Adlib(KaitaiStruct):
            SEQ_FIELDS = ["reserved1", "_unnamed1"]
            def __init__(self, _io, _parent=None, _root=None):
                super(S3m.Instrument.Adlib, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved1']['start'] = self._io.pos()
                self.reserved1 = self._io.read_bytes(3)
                self._debug['reserved1']['end'] = self._io.pos()
                if not self.reserved1 == b"\x00\x00\x00":
                    raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00", self.reserved1, self._io, u"/types/instrument/types/adlib/seq/0")
                self._debug['_unnamed1']['start'] = self._io.pos()
                self._unnamed1 = self._io.read_bytes(16)
                self._debug['_unnamed1']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class Sampled(KaitaiStruct):
            SEQ_FIELDS = ["paraptr_sample", "len_sample", "loop_begin", "loop_end", "default_volume", "reserved1", "is_packed", "flags"]
            def __init__(self, _io, _parent=None, _root=None):
                super(S3m.Instrument.Sampled, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['paraptr_sample']['start'] = self._io.pos()
                self.paraptr_sample = S3m.SwappedU3(self._io, self, self._root)
                self.paraptr_sample._read()
                self._debug['paraptr_sample']['end'] = self._io.pos()
                self._debug['len_sample']['start'] = self._io.pos()
                self.len_sample = self._io.read_u4le()
                self._debug['len_sample']['end'] = self._io.pos()
                self._debug['loop_begin']['start'] = self._io.pos()
                self.loop_begin = self._io.read_u4le()
                self._debug['loop_begin']['end'] = self._io.pos()
                self._debug['loop_end']['start'] = self._io.pos()
                self.loop_end = self._io.read_u4le()
                self._debug['loop_end']['end'] = self._io.pos()
                self._debug['default_volume']['start'] = self._io.pos()
                self.default_volume = self._io.read_u1()
                self._debug['default_volume']['end'] = self._io.pos()
                self._debug['reserved1']['start'] = self._io.pos()
                self.reserved1 = self._io.read_u1()
                self._debug['reserved1']['end'] = self._io.pos()
                self._debug['is_packed']['start'] = self._io.pos()
                self.is_packed = self._io.read_u1()
                self._debug['is_packed']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u1()
                self._debug['flags']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                self.paraptr_sample._fetch_instances()
                _ = self.sample
                if hasattr(self, '_m_sample'):
                    pass


            @property
            def sample(self):
                if hasattr(self, '_m_sample'):
                    return self._m_sample

                _pos = self._io.pos()
                self._io.seek(self.paraptr_sample.value * 16)
                self._debug['_m_sample']['start'] = self._io.pos()
                self._m_sample = self._io.read_bytes(self.len_sample)
                self._debug['_m_sample']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_sample', None)



    class InstrumentPtr(KaitaiStruct):
        SEQ_FIELDS = ["paraptr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.InstrumentPtr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['paraptr']['start'] = self._io.pos()
            self.paraptr = self._io.read_u2le()
            self._debug['paraptr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.body
            if hasattr(self, '_m_body'):
                pass
                self._m_body._fetch_instances()


        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body

            _pos = self._io.pos()
            self._io.seek(self.paraptr * 16)
            self._debug['_m_body']['start'] = self._io.pos()
            self._m_body = S3m.Instrument(self._io, self, self._root)
            self._m_body._read()
            self._debug['_m_body']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_body', None)


    class Pattern(KaitaiStruct):
        SEQ_FIELDS = ["size", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.Pattern, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u2le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self._raw_body = self._io.read_bytes(self.size - 2)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = S3m.PatternCells(_io__raw_body, self, self._root)
            self.body._read()
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class PatternCell(KaitaiStruct):
        SEQ_FIELDS = ["has_fx", "has_volume", "has_note_and_instrument", "channel_num", "note", "instrument", "volume", "fx_type", "fx_value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.PatternCell, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['has_fx']['start'] = self._io.pos()
            self.has_fx = self._io.read_bits_int_be(1) != 0
            self._debug['has_fx']['end'] = self._io.pos()
            self._debug['has_volume']['start'] = self._io.pos()
            self.has_volume = self._io.read_bits_int_be(1) != 0
            self._debug['has_volume']['end'] = self._io.pos()
            self._debug['has_note_and_instrument']['start'] = self._io.pos()
            self.has_note_and_instrument = self._io.read_bits_int_be(1) != 0
            self._debug['has_note_and_instrument']['end'] = self._io.pos()
            self._debug['channel_num']['start'] = self._io.pos()
            self.channel_num = self._io.read_bits_int_be(5)
            self._debug['channel_num']['end'] = self._io.pos()
            if self.has_note_and_instrument:
                pass
                self._debug['note']['start'] = self._io.pos()
                self.note = self._io.read_u1()
                self._debug['note']['end'] = self._io.pos()

            if self.has_note_and_instrument:
                pass
                self._debug['instrument']['start'] = self._io.pos()
                self.instrument = self._io.read_u1()
                self._debug['instrument']['end'] = self._io.pos()

            if self.has_volume:
                pass
                self._debug['volume']['start'] = self._io.pos()
                self.volume = self._io.read_u1()
                self._debug['volume']['end'] = self._io.pos()

            if self.has_fx:
                pass
                self._debug['fx_type']['start'] = self._io.pos()
                self.fx_type = self._io.read_u1()
                self._debug['fx_type']['end'] = self._io.pos()

            if self.has_fx:
                pass
                self._debug['fx_value']['start'] = self._io.pos()
                self.fx_value = self._io.read_u1()
                self._debug['fx_value']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.has_note_and_instrument:
                pass

            if self.has_note_and_instrument:
                pass

            if self.has_volume:
                pass

            if self.has_fx:
                pass

            if self.has_fx:
                pass



    class PatternCells(KaitaiStruct):
        SEQ_FIELDS = ["cells"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.PatternCells, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['cells']['start'] = self._io.pos()
            self._debug['cells']['arr'] = []
            self.cells = []
            i = 0
            while not self._io.is_eof():
                self._debug['cells']['arr'].append({'start': self._io.pos()})
                _t_cells = S3m.PatternCell(self._io, self, self._root)
                try:
                    _t_cells._read()
                finally:
                    self.cells.append(_t_cells)
                self._debug['cells']['arr'][len(self.cells) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['cells']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.cells)):
                pass
                self.cells[i]._fetch_instances()



    class PatternPtr(KaitaiStruct):
        SEQ_FIELDS = ["paraptr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.PatternPtr, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['paraptr']['start'] = self._io.pos()
            self.paraptr = self._io.read_u2le()
            self._debug['paraptr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.body
            if hasattr(self, '_m_body'):
                pass
                self._m_body._fetch_instances()


        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body

            _pos = self._io.pos()
            self._io.seek(self.paraptr * 16)
            self._debug['_m_body']['start'] = self._io.pos()
            self._m_body = S3m.Pattern(self._io, self, self._root)
            self._m_body._read()
            self._debug['_m_body']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_body', None)


    class SwappedU3(KaitaiStruct):
        """Custom 3-byte integer, stored in mixed endian manner."""
        SEQ_FIELDS = ["hi", "lo"]
        def __init__(self, _io, _parent=None, _root=None):
            super(S3m.SwappedU3, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['hi']['start'] = self._io.pos()
            self.hi = self._io.read_u1()
            self._debug['hi']['end'] = self._io.pos()
            self._debug['lo']['start'] = self._io.pos()
            self.lo = self._io.read_u2le()
            self._debug['lo']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def value(self):
            if hasattr(self, '_m_value'):
                return self._m_value

            self._m_value = self.lo | self.hi << 16
            return getattr(self, '_m_value', None)



