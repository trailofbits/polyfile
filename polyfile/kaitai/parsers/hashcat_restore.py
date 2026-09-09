# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class HashcatRestore(KaitaiStruct):
    """
    .. seealso::
       Source - https://hashcat.net/wiki/doku.php?id=restore
    """
    SEQ_FIELDS = ["version", "cwd", "dicts_pos", "masks_pos", "padding", "current_restore_point", "argc", "padding2", "argv"]
    def __init__(self, _io, _parent=None, _root=None):
        super(HashcatRestore, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u4le()
        self._debug['version']['end'] = self._io.pos()
        self._debug['cwd']['start'] = self._io.pos()
        self.cwd = (KaitaiStream.bytes_terminate(self._io.read_bytes(256), 0, False)).decode(u"UTF-8")
        self._debug['cwd']['end'] = self._io.pos()
        self._debug['dicts_pos']['start'] = self._io.pos()
        self.dicts_pos = self._io.read_u4le()
        self._debug['dicts_pos']['end'] = self._io.pos()
        self._debug['masks_pos']['start'] = self._io.pos()
        self.masks_pos = self._io.read_u4le()
        self._debug['masks_pos']['end'] = self._io.pos()
        self._debug['padding']['start'] = self._io.pos()
        self.padding = self._io.read_bytes(4)
        self._debug['padding']['end'] = self._io.pos()
        self._debug['current_restore_point']['start'] = self._io.pos()
        self.current_restore_point = self._io.read_u8le()
        self._debug['current_restore_point']['end'] = self._io.pos()
        self._debug['argc']['start'] = self._io.pos()
        self.argc = self._io.read_u4le()
        self._debug['argc']['end'] = self._io.pos()
        self._debug['padding2']['start'] = self._io.pos()
        self.padding2 = self._io.read_bytes(12)
        self._debug['padding2']['end'] = self._io.pos()
        self._debug['argv']['start'] = self._io.pos()
        self._debug['argv']['arr'] = []
        self.argv = []
        for i in range(self.argc):
            self._debug['argv']['arr'].append({'start': self._io.pos()})
            self.argv.append((self._io.read_bytes_term(10, False, True, True)).decode(u"UTF-8"))
            self._debug['argv']['arr'][i]['end'] = self._io.pos()

        self._debug['argv']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.argv)):
            pass



