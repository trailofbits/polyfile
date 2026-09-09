# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class HeroesOfMightAndMagicAgg(KaitaiStruct):
    """
    .. seealso::
       Source - https://web.archive.org/web/20170215190034/http://rewiki.regengedanken.de/wiki/.AGG_(Heroes_of_Might_and_Magic)
    """
    SEQ_FIELDS = ["num_files", "entries"]
    def __init__(self, _io, _parent=None, _root=None):
        super(HeroesOfMightAndMagicAgg, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['num_files']['start'] = self._io.pos()
        self.num_files = self._io.read_u2le()
        self._debug['num_files']['end'] = self._io.pos()
        self._debug['entries']['start'] = self._io.pos()
        self._debug['entries']['arr'] = []
        self.entries = []
        for i in range(self.num_files):
            self._debug['entries']['arr'].append({'start': self._io.pos()})
            _t_entries = HeroesOfMightAndMagicAgg.Entry(self._io, self, self._root)
            try:
                _t_entries._read()
            finally:
                self.entries.append(_t_entries)
            self._debug['entries']['arr'][i]['end'] = self._io.pos()

        self._debug['entries']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.entries)):
            pass
            self.entries[i]._fetch_instances()

        _ = self.filenames
        if hasattr(self, '_m_filenames'):
            pass
            for i in range(len(self._m_filenames)):
                pass
                self._m_filenames[i]._fetch_instances()



    class Entry(KaitaiStruct):
        SEQ_FIELDS = ["hash", "offset", "size", "size2"]
        def __init__(self, _io, _parent=None, _root=None):
            super(HeroesOfMightAndMagicAgg.Entry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['hash']['start'] = self._io.pos()
            self.hash = self._io.read_u2le()
            self._debug['hash']['end'] = self._io.pos()
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u4le()
            self._debug['offset']['end'] = self._io.pos()
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['size2']['start'] = self._io.pos()
            self.size2 = self._io.read_u4le()
            self._debug['size2']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.body
            if hasattr(self, '_m_body'):
                pass


        @property
        def body(self):
            if hasattr(self, '_m_body'):
                return self._m_body

            _pos = self._io.pos()
            self._io.seek(self.offset)
            self._debug['_m_body']['start'] = self._io.pos()
            self._m_body = self._io.read_bytes(self.size)
            self._debug['_m_body']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_body', None)


    class Filename(KaitaiStruct):
        SEQ_FIELDS = ["str"]
        def __init__(self, _io, _parent=None, _root=None):
            super(HeroesOfMightAndMagicAgg.Filename, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    @property
    def filenames(self):
        if hasattr(self, '_m_filenames'):
            return self._m_filenames

        _pos = self._io.pos()
        self._io.seek(self.entries[-1].offset + self.entries[-1].size)
        self._debug['_m_filenames']['start'] = self._io.pos()
        self._debug['_m_filenames']['arr'] = []
        self._raw__m_filenames = []
        self._m_filenames = []
        for i in range(self.num_files):
            self._debug['_m_filenames']['arr'].append({'start': self._io.pos()})
            self._raw__m_filenames.append(self._io.read_bytes(15))
            _io__raw__m_filenames = KaitaiStream(BytesIO(self._raw__m_filenames[i]))
            _t__m_filenames = HeroesOfMightAndMagicAgg.Filename(_io__raw__m_filenames, self, self._root)
            try:
                _t__m_filenames._read()
            finally:
                self._m_filenames.append(_t__m_filenames)
            self._debug['_m_filenames']['arr'][i]['end'] = self._io.pos()

        self._debug['_m_filenames']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_filenames', None)


