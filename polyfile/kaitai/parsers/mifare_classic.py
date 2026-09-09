# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class MifareClassic(KaitaiStruct):
    """You can get a dump for testing from this link:
    <https://github.com/zhovner/mfdread/raw/master/dump.mfd>
    
    .. seealso::
       Source - https://github.com/nfc-tools/libnfc
       https://www.nxp.com/docs/en/data-sheet/MF1S70YYX_V1.pdf
    """
    SEQ_FIELDS = ["sectors"]
    def __init__(self, _io, _parent=None, _root=None):
        super(MifareClassic, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['sectors']['start'] = self._io.pos()
        self._debug['sectors']['arr'] = []
        self._raw_sectors = []
        self.sectors = []
        i = 0
        while not self._io.is_eof():
            self._debug['sectors']['arr'].append({'start': self._io.pos()})
            self._raw_sectors.append(self._io.read_bytes(((4 if i >= 32 else 1) * 4) * 16))
            _io__raw_sectors = KaitaiStream(BytesIO(self._raw_sectors[-1]))
            _t_sectors = MifareClassic.Sector(i == 0, _io__raw_sectors, self, self._root)
            try:
                _t_sectors._read()
            finally:
                self.sectors.append(_t_sectors)
            self._debug['sectors']['arr'][len(self.sectors) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['sectors']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.sectors)):
            pass
            self.sectors[i]._fetch_instances()


    class Key(KaitaiStruct):
        SEQ_FIELDS = ["key"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MifareClassic.Key, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['key']['start'] = self._io.pos()
            self.key = self._io.read_bytes(6)
            self._debug['key']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Manufacturer(KaitaiStruct):
        SEQ_FIELDS = ["nuid", "bcc", "sak", "atqa", "manufacturer"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MifareClassic.Manufacturer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['nuid']['start'] = self._io.pos()
            self.nuid = self._io.read_u4le()
            self._debug['nuid']['end'] = self._io.pos()
            self._debug['bcc']['start'] = self._io.pos()
            self.bcc = self._io.read_u1()
            self._debug['bcc']['end'] = self._io.pos()
            self._debug['sak']['start'] = self._io.pos()
            self.sak = self._io.read_u1()
            self._debug['sak']['end'] = self._io.pos()
            self._debug['atqa']['start'] = self._io.pos()
            self.atqa = self._io.read_u2le()
            self._debug['atqa']['end'] = self._io.pos()
            self._debug['manufacturer']['start'] = self._io.pos()
            self.manufacturer = self._io.read_bytes(8)
            self._debug['manufacturer']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Sector(KaitaiStruct):
        SEQ_FIELDS = ["manufacturer", "data_filler", "trailer"]
        def __init__(self, has_manufacturer, _io, _parent=None, _root=None):
            super(MifareClassic.Sector, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.has_manufacturer = has_manufacturer
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if self.has_manufacturer:
                pass
                self._debug['manufacturer']['start'] = self._io.pos()
                self.manufacturer = MifareClassic.Manufacturer(self._io, self, self._root)
                self.manufacturer._read()
                self._debug['manufacturer']['end'] = self._io.pos()

            self._debug['data_filler']['start'] = self._io.pos()
            self._raw_data_filler = self._io.read_bytes((self._io.size() - self._io.pos()) - 16)
            _io__raw_data_filler = KaitaiStream(BytesIO(self._raw_data_filler))
            self.data_filler = MifareClassic.Sector.Filler(_io__raw_data_filler, self, self._root)
            self.data_filler._read()
            self._debug['data_filler']['end'] = self._io.pos()
            self._debug['trailer']['start'] = self._io.pos()
            self.trailer = MifareClassic.Trailer(self._io, self, self._root)
            self.trailer._read()
            self._debug['trailer']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            if self.has_manufacturer:
                pass
                self.manufacturer._fetch_instances()

            self.data_filler._fetch_instances()
            self.trailer._fetch_instances()
            _ = self.blocks
            if hasattr(self, '_m_blocks'):
                pass
                for i in range(len(self._m_blocks)):
                    pass


            _ = self.values
            if hasattr(self, '_m_values'):
                pass
                self._m_values._fetch_instances()


        class Filler(KaitaiStruct):
            """only to create _io."""
            SEQ_FIELDS = ["data"]
            def __init__(self, _io, _parent=None, _root=None):
                super(MifareClassic.Sector.Filler, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['data']['start'] = self._io.pos()
                self.data = self._io.read_bytes(self._io.size())
                self._debug['data']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class Values(KaitaiStruct):
            SEQ_FIELDS = ["values"]
            def __init__(self, _io, _parent=None, _root=None):
                super(MifareClassic.Sector.Values, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['values']['start'] = self._io.pos()
                self._debug['values']['arr'] = []
                self.values = []
                i = 0
                while not self._io.is_eof():
                    self._debug['values']['arr'].append({'start': self._io.pos()})
                    _t_values = MifareClassic.Sector.Values.ValueBlock(self._io, self, self._root)
                    try:
                        _t_values._read()
                    finally:
                        self.values.append(_t_values)
                    self._debug['values']['arr'][len(self.values) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['values']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.values)):
                    pass
                    self.values[i]._fetch_instances()


            class ValueBlock(KaitaiStruct):
                SEQ_FIELDS = ["valuez", "addrz"]
                def __init__(self, _io, _parent=None, _root=None):
                    super(MifareClassic.Sector.Values.ValueBlock, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['valuez']['start'] = self._io.pos()
                    self._debug['valuez']['arr'] = []
                    self.valuez = []
                    for i in range(3):
                        self._debug['valuez']['arr'].append({'start': self._io.pos()})
                        self.valuez.append(self._io.read_u4le())
                        self._debug['valuez']['arr'][i]['end'] = self._io.pos()

                    self._debug['valuez']['end'] = self._io.pos()
                    self._debug['addrz']['start'] = self._io.pos()
                    self._debug['addrz']['arr'] = []
                    self.addrz = []
                    for i in range(4):
                        self._debug['addrz']['arr'].append({'start': self._io.pos()})
                        self.addrz.append(self._io.read_u1())
                        self._debug['addrz']['arr'][i]['end'] = self._io.pos()

                    self._debug['addrz']['end'] = self._io.pos()


                def _fetch_instances(self):
                    pass
                    for i in range(len(self.valuez)):
                        pass

                    for i in range(len(self.addrz)):
                        pass


                @property
                def addr(self):
                    if hasattr(self, '_m_addr'):
                        return self._m_addr

                    if self.valid:
                        pass
                        self._m_addr = self.addrz[0]

                    return getattr(self, '_m_addr', None)

                @property
                def addr_valid(self):
                    if hasattr(self, '_m_addr_valid'):
                        return self._m_addr_valid

                    self._m_addr_valid =  ((self.addrz[0] == ~(self.addrz[1])) and (self.addrz[0] == self.addrz[2]) and (self.addrz[1] == self.addrz[3])) 
                    return getattr(self, '_m_addr_valid', None)

                @property
                def valid(self):
                    if hasattr(self, '_m_valid'):
                        return self._m_valid

                    self._m_valid =  ((self.value_valid) and (self.addr_valid)) 
                    return getattr(self, '_m_valid', None)

                @property
                def value(self):
                    if hasattr(self, '_m_value'):
                        return self._m_value

                    if self.valid:
                        pass
                        self._m_value = self.valuez[0]

                    return getattr(self, '_m_value', None)

                @property
                def value_valid(self):
                    if hasattr(self, '_m_value_valid'):
                        return self._m_value_valid

                    self._m_value_valid =  ((self.valuez[0] == ~(self.valuez[1])) and (self.valuez[0] == self.valuez[2])) 
                    return getattr(self, '_m_value_valid', None)



        @property
        def block_size(self):
            if hasattr(self, '_m_block_size'):
                return self._m_block_size

            self._m_block_size = 16
            return getattr(self, '_m_block_size', None)

        @property
        def blocks(self):
            if hasattr(self, '_m_blocks'):
                return self._m_blocks

            io = self.data_filler._io
            _pos = io.pos()
            io.seek(0)
            self._debug['_m_blocks']['start'] = io.pos()
            self._debug['_m_blocks']['arr'] = []
            self._m_blocks = []
            i = 0
            while not io.is_eof():
                self._debug['_m_blocks']['arr'].append({'start': io.pos()})
                self._m_blocks.append(io.read_bytes(self.block_size))
                self._debug['_m_blocks']['arr'][len(self._m_blocks) - 1]['end'] = io.pos()
                i += 1

            self._debug['_m_blocks']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_blocks', None)

        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data

            self._m_data = self.data_filler.data
            return getattr(self, '_m_data', None)

        @property
        def values(self):
            if hasattr(self, '_m_values'):
                return self._m_values

            io = self.data_filler._io
            _pos = io.pos()
            io.seek(0)
            self._debug['_m_values']['start'] = io.pos()
            self._m_values = MifareClassic.Sector.Values(io, self, self._root)
            self._m_values._read()
            self._debug['_m_values']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_values', None)


    class Trailer(KaitaiStruct):
        SEQ_FIELDS = ["key_a", "access_bits", "user_byte", "key_b"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MifareClassic.Trailer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['key_a']['start'] = self._io.pos()
            self.key_a = MifareClassic.Key(self._io, self, self._root)
            self.key_a._read()
            self._debug['key_a']['end'] = self._io.pos()
            self._debug['access_bits']['start'] = self._io.pos()
            self._raw_access_bits = self._io.read_bytes(3)
            _io__raw_access_bits = KaitaiStream(BytesIO(self._raw_access_bits))
            self.access_bits = MifareClassic.Trailer.AccessConditions(_io__raw_access_bits, self, self._root)
            self.access_bits._read()
            self._debug['access_bits']['end'] = self._io.pos()
            self._debug['user_byte']['start'] = self._io.pos()
            self.user_byte = self._io.read_u1()
            self._debug['user_byte']['end'] = self._io.pos()
            self._debug['key_b']['start'] = self._io.pos()
            self.key_b = MifareClassic.Key(self._io, self, self._root)
            self.key_b._read()
            self._debug['key_b']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.key_a._fetch_instances()
            self.access_bits._fetch_instances()
            self.key_b._fetch_instances()

        class AccessConditions(KaitaiStruct):
            SEQ_FIELDS = ["raw_chunks"]
            def __init__(self, _io, _parent=None, _root=None):
                super(MifareClassic.Trailer.AccessConditions, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['raw_chunks']['start'] = self._io.pos()
                self._debug['raw_chunks']['arr'] = []
                self.raw_chunks = []
                for i in range(self._parent.ac_count_of_chunks):
                    self._debug['raw_chunks']['arr'].append({'start': self._io.pos()})
                    self.raw_chunks.append(self._io.read_bits_int_be(4))
                    self._debug['raw_chunks']['arr'][i]['end'] = self._io.pos()

                self._debug['raw_chunks']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.raw_chunks)):
                    pass

                _ = self.acs_raw
                if hasattr(self, '_m_acs_raw'):
                    pass
                    for i in range(len(self._m_acs_raw)):
                        pass
                        self._m_acs_raw[i]._fetch_instances()


                _ = self.chunks
                if hasattr(self, '_m_chunks'):
                    pass
                    for i in range(len(self._m_chunks)):
                        pass
                        self._m_chunks[i]._fetch_instances()


                _ = self.data_acs
                if hasattr(self, '_m_data_acs'):
                    pass
                    for i in range(len(self._m_data_acs)):
                        pass
                        self._m_data_acs[i]._fetch_instances()


                _ = self.remaps
                if hasattr(self, '_m_remaps'):
                    pass
                    for i in range(len(self._m_remaps)):
                        pass
                        self._m_remaps[i]._fetch_instances()


                _ = self.trailer_ac
                if hasattr(self, '_m_trailer_ac'):
                    pass
                    self._m_trailer_ac._fetch_instances()


            class Ac(KaitaiStruct):
                SEQ_FIELDS = []
                def __init__(self, index, _io, _parent=None, _root=None):
                    super(MifareClassic.Trailer.AccessConditions.Ac, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self.index = index
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    pass


                def _fetch_instances(self):
                    pass
                    _ = self.bits
                    if hasattr(self, '_m_bits'):
                        pass
                        for i in range(len(self._m_bits)):
                            pass
                            self._m_bits[i]._fetch_instances()



                class AcBit(KaitaiStruct):
                    SEQ_FIELDS = []
                    def __init__(self, i, chunk, _io, _parent=None, _root=None):
                        super(MifareClassic.Trailer.AccessConditions.Ac.AcBit, self).__init__(_io)
                        self._parent = _parent
                        self._root = _root
                        self.i = i
                        self.chunk = chunk
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        pass


                    def _fetch_instances(self):
                        pass

                    @property
                    def b(self):
                        if hasattr(self, '_m_b'):
                            return self._m_b

                        self._m_b = self.n == 1
                        return getattr(self, '_m_b', None)

                    @property
                    def n(self):
                        if hasattr(self, '_m_n'):
                            return self._m_n

                        self._m_n = self.chunk >> self.i & 1
                        return getattr(self, '_m_n', None)


                @property
                def bits(self):
                    if hasattr(self, '_m_bits'):
                        return self._m_bits

                    _pos = self._io.pos()
                    self._io.seek(0)
                    self._debug['_m_bits']['start'] = self._io.pos()
                    self._debug['_m_bits']['arr'] = []
                    self._m_bits = []
                    for i in range(self._parent._parent.ac_bits):
                        self._debug['_m_bits']['arr'].append({'start': self._io.pos()})
                        _t__m_bits = MifareClassic.Trailer.AccessConditions.Ac.AcBit(self.index, self._parent.chunks[i].chunk, self._io, self, self._root)
                        try:
                            _t__m_bits._read()
                        finally:
                            self._m_bits.append(_t__m_bits)
                        self._debug['_m_bits']['arr'][i]['end'] = self._io.pos()

                    self._debug['_m_bits']['end'] = self._io.pos()
                    self._io.seek(_pos)
                    return getattr(self, '_m_bits', None)

                @property
                def inv_shift_val(self):
                    if hasattr(self, '_m_inv_shift_val'):
                        return self._m_inv_shift_val

                    self._m_inv_shift_val = (self.bits[0].n << 2 | self.bits[1].n << 1) | self.bits[2].n
                    return getattr(self, '_m_inv_shift_val', None)

                @property
                def val(self):
                    """c3 c2 c1."""
                    if hasattr(self, '_m_val'):
                        return self._m_val

                    self._m_val = (self.bits[2].n << 2 | self.bits[1].n << 1) | self.bits[0].n
                    return getattr(self, '_m_val', None)


            class ChunkBitRemap(KaitaiStruct):
                SEQ_FIELDS = []
                def __init__(self, bit_no, _io, _parent=None, _root=None):
                    super(MifareClassic.Trailer.AccessConditions.ChunkBitRemap, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self.bit_no = bit_no
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    pass


                def _fetch_instances(self):
                    pass

                @property
                def chunk_no(self):
                    if hasattr(self, '_m_chunk_no'):
                        return self._m_chunk_no

                    self._m_chunk_no = ((self.inv_chunk_no + self.shift_value) + self._parent._parent.ac_count_of_chunks) % self._parent._parent.ac_count_of_chunks
                    return getattr(self, '_m_chunk_no', None)

                @property
                def inv_chunk_no(self):
                    if hasattr(self, '_m_inv_chunk_no'):
                        return self._m_inv_chunk_no

                    self._m_inv_chunk_no = self.bit_no + self.shift_value
                    return getattr(self, '_m_inv_chunk_no', None)

                @property
                def shift_value(self):
                    if hasattr(self, '_m_shift_value'):
                        return self._m_shift_value

                    self._m_shift_value = (-1 if self.bit_no == 1 else 1)
                    return getattr(self, '_m_shift_value', None)


            class DataAc(KaitaiStruct):
                SEQ_FIELDS = []
                def __init__(self, ac, _io, _parent=None, _root=None):
                    super(MifareClassic.Trailer.AccessConditions.DataAc, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self.ac = ac
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    pass


                def _fetch_instances(self):
                    pass

                @property
                def decrement_available(self):
                    if hasattr(self, '_m_decrement_available'):
                        return self._m_decrement_available

                    self._m_decrement_available =  (( ((self.ac.bits[1].b) or ((not (self.ac.bits[0].b)))) ) and ((not (self.ac.bits[2].b)))) 
                    return getattr(self, '_m_decrement_available', None)

                @property
                def increment_available(self):
                    if hasattr(self, '_m_increment_available'):
                        return self._m_increment_available

                    self._m_increment_available =  (( (((not (self.ac.bits[0].b))) and ((not (self.read_key_a_required))) and ((not (self.read_key_b_required)))) ) or ( (((not (self.ac.bits[0].b))) and (self.read_key_a_required) and (self.read_key_b_required)) )) 
                    return getattr(self, '_m_increment_available', None)

                @property
                def read_key_a_required(self):
                    if hasattr(self, '_m_read_key_a_required'):
                        return self._m_read_key_a_required

                    self._m_read_key_a_required = self.ac.val <= 4
                    return getattr(self, '_m_read_key_a_required', None)

                @property
                def read_key_b_required(self):
                    if hasattr(self, '_m_read_key_b_required'):
                        return self._m_read_key_b_required

                    self._m_read_key_b_required = self.ac.val <= 6
                    return getattr(self, '_m_read_key_b_required', None)

                @property
                def write_key_a_required(self):
                    if hasattr(self, '_m_write_key_a_required'):
                        return self._m_write_key_a_required

                    self._m_write_key_a_required = self.ac.val == 0
                    return getattr(self, '_m_write_key_a_required', None)

                @property
                def write_key_b_required(self):
                    if hasattr(self, '_m_write_key_b_required'):
                        return self._m_write_key_b_required

                    self._m_write_key_b_required =  (( (((not (self.read_key_a_required))) or (self.read_key_b_required)) ) and ((not (self.ac.bits[0].b)))) 
                    return getattr(self, '_m_write_key_b_required', None)


            class TrailerAc(KaitaiStruct):
                SEQ_FIELDS = []
                def __init__(self, ac, _io, _parent=None, _root=None):
                    super(MifareClassic.Trailer.AccessConditions.TrailerAc, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self.ac = ac
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    pass


                def _fetch_instances(self):
                    pass

                @property
                def can_read_key_b(self):
                    """key A is required."""
                    if hasattr(self, '_m_can_read_key_b'):
                        return self._m_can_read_key_b

                    self._m_can_read_key_b = self.ac.inv_shift_val <= 2
                    return getattr(self, '_m_can_read_key_b', None)

                @property
                def can_write_access_bits(self):
                    if hasattr(self, '_m_can_write_access_bits'):
                        return self._m_can_write_access_bits

                    self._m_can_write_access_bits = self.ac.bits[2].b
                    return getattr(self, '_m_can_write_access_bits', None)

                @property
                def can_write_keys(self):
                    if hasattr(self, '_m_can_write_keys'):
                        return self._m_can_write_keys

                    self._m_can_write_keys =  (((self.ac.inv_shift_val + 1) % 3 != 0) and (self.ac.inv_shift_val < 6)) 
                    return getattr(self, '_m_can_write_keys', None)

                @property
                def key_b_controls_write(self):
                    if hasattr(self, '_m_key_b_controls_write'):
                        return self._m_key_b_controls_write

                    self._m_key_b_controls_write = (not (self.can_read_key_b))
                    return getattr(self, '_m_key_b_controls_write', None)


            class ValidChunk(KaitaiStruct):
                SEQ_FIELDS = []
                def __init__(self, inv_chunk, chunk, _io, _parent=None, _root=None):
                    super(MifareClassic.Trailer.AccessConditions.ValidChunk, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self.inv_chunk = inv_chunk
                    self.chunk = chunk
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    pass


                def _fetch_instances(self):
                    pass

                @property
                def valid(self):
                    if hasattr(self, '_m_valid'):
                        return self._m_valid

                    self._m_valid = self.inv_chunk ^ self.chunk == 15
                    return getattr(self, '_m_valid', None)


            @property
            def acs_raw(self):
                if hasattr(self, '_m_acs_raw'):
                    return self._m_acs_raw

                _pos = self._io.pos()
                self._io.seek(0)
                self._debug['_m_acs_raw']['start'] = self._io.pos()
                self._debug['_m_acs_raw']['arr'] = []
                self._m_acs_raw = []
                for i in range(self._parent.acs_in_sector):
                    self._debug['_m_acs_raw']['arr'].append({'start': self._io.pos()})
                    _t__m_acs_raw = MifareClassic.Trailer.AccessConditions.Ac(i, self._io, self, self._root)
                    try:
                        _t__m_acs_raw._read()
                    finally:
                        self._m_acs_raw.append(_t__m_acs_raw)
                    self._debug['_m_acs_raw']['arr'][i]['end'] = self._io.pos()

                self._debug['_m_acs_raw']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_acs_raw', None)

            @property
            def chunks(self):
                if hasattr(self, '_m_chunks'):
                    return self._m_chunks

                _pos = self._io.pos()
                self._io.seek(0)
                self._debug['_m_chunks']['start'] = self._io.pos()
                self._debug['_m_chunks']['arr'] = []
                self._m_chunks = []
                for i in range(self._parent.ac_bits):
                    self._debug['_m_chunks']['arr'].append({'start': self._io.pos()})
                    _t__m_chunks = MifareClassic.Trailer.AccessConditions.ValidChunk(self.raw_chunks[self.remaps[i].inv_chunk_no], self.raw_chunks[self.remaps[i].chunk_no], self._io, self, self._root)
                    try:
                        _t__m_chunks._read()
                    finally:
                        self._m_chunks.append(_t__m_chunks)
                    self._debug['_m_chunks']['arr'][i]['end'] = self._io.pos()

                self._debug['_m_chunks']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_chunks', None)

            @property
            def data_acs(self):
                if hasattr(self, '_m_data_acs'):
                    return self._m_data_acs

                _pos = self._io.pos()
                self._io.seek(0)
                self._debug['_m_data_acs']['start'] = self._io.pos()
                self._debug['_m_data_acs']['arr'] = []
                self._m_data_acs = []
                for i in range(self._parent.acs_in_sector - 1):
                    self._debug['_m_data_acs']['arr'].append({'start': self._io.pos()})
                    _t__m_data_acs = MifareClassic.Trailer.AccessConditions.DataAc(self.acs_raw[i], self._io, self, self._root)
                    try:
                        _t__m_data_acs._read()
                    finally:
                        self._m_data_acs.append(_t__m_data_acs)
                    self._debug['_m_data_acs']['arr'][i]['end'] = self._io.pos()

                self._debug['_m_data_acs']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_data_acs', None)

            @property
            def remaps(self):
                if hasattr(self, '_m_remaps'):
                    return self._m_remaps

                _pos = self._io.pos()
                self._io.seek(0)
                self._debug['_m_remaps']['start'] = self._io.pos()
                self._debug['_m_remaps']['arr'] = []
                self._m_remaps = []
                for i in range(self._parent.ac_bits):
                    self._debug['_m_remaps']['arr'].append({'start': self._io.pos()})
                    _t__m_remaps = MifareClassic.Trailer.AccessConditions.ChunkBitRemap(i, self._io, self, self._root)
                    try:
                        _t__m_remaps._read()
                    finally:
                        self._m_remaps.append(_t__m_remaps)
                    self._debug['_m_remaps']['arr'][i]['end'] = self._io.pos()

                self._debug['_m_remaps']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_remaps', None)

            @property
            def trailer_ac(self):
                if hasattr(self, '_m_trailer_ac'):
                    return self._m_trailer_ac

                _pos = self._io.pos()
                self._io.seek(0)
                self._debug['_m_trailer_ac']['start'] = self._io.pos()
                self._m_trailer_ac = MifareClassic.Trailer.AccessConditions.TrailerAc(self.acs_raw[self._parent.acs_in_sector - 1], self._io, self, self._root)
                self._m_trailer_ac._read()
                self._debug['_m_trailer_ac']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_trailer_ac', None)


        @property
        def ac_bits(self):
            if hasattr(self, '_m_ac_bits'):
                return self._m_ac_bits

            self._m_ac_bits = 3
            return getattr(self, '_m_ac_bits', None)

        @property
        def ac_count_of_chunks(self):
            if hasattr(self, '_m_ac_count_of_chunks'):
                return self._m_ac_count_of_chunks

            self._m_ac_count_of_chunks = self.ac_bits * 2
            return getattr(self, '_m_ac_count_of_chunks', None)

        @property
        def acs_in_sector(self):
            if hasattr(self, '_m_acs_in_sector'):
                return self._m_acs_in_sector

            self._m_acs_in_sector = 4
            return getattr(self, '_m_acs_in_sector', None)



