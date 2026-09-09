# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class MonomakhSaprChg(KaitaiStruct):
    """CHG is a container format file used by
    [MONOMAKH-SAPR](https://www.liraland.com/mono/), a software
    package for analysis & design of reinforced concrete multi-storey
    buildings with arbitrary configuration in plan.
    
    CHG is a simple container, which bundles several project files
    together.
    
    Written and tested by Vladimir Shulzhitskiy, 2017
    """
    SEQ_FIELDS = ["title", "ent"]
    def __init__(self, _io, _parent=None, _root=None):
        super(MonomakhSaprChg, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['title']['start'] = self._io.pos()
        self.title = (self._io.read_bytes(10)).decode(u"ASCII")
        self._debug['title']['end'] = self._io.pos()
        self._debug['ent']['start'] = self._io.pos()
        self._debug['ent']['arr'] = []
        self.ent = []
        i = 0
        while not self._io.is_eof():
            self._debug['ent']['arr'].append({'start': self._io.pos()})
            _t_ent = MonomakhSaprChg.Block(self._io, self, self._root)
            try:
                _t_ent._read()
            finally:
                self.ent.append(_t_ent)
            self._debug['ent']['arr'][len(self.ent) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['ent']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.ent)):
            pass
            self.ent[i]._fetch_instances()


    class Block(KaitaiStruct):
        SEQ_FIELDS = ["header", "file_size", "file"]
        def __init__(self, _io, _parent=None, _root=None):
            super(MonomakhSaprChg.Block, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['header']['start'] = self._io.pos()
            self.header = (self._io.read_bytes(13)).decode(u"ASCII")
            self._debug['header']['end'] = self._io.pos()
            self._debug['file_size']['start'] = self._io.pos()
            self.file_size = self._io.read_u8le()
            self._debug['file_size']['end'] = self._io.pos()
            self._debug['file']['start'] = self._io.pos()
            self.file = self._io.read_bytes(self.file_size)
            self._debug['file']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



