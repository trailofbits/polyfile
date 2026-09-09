# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from polyfile.kaitai.parsers import some_ip
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SomeIpContainer(KaitaiStruct):
    SEQ_FIELDS = ["some_ip_packages"]
    def __init__(self, _io, _parent=None, _root=None):
        super(SomeIpContainer, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['some_ip_packages']['start'] = self._io.pos()
        self._debug['some_ip_packages']['arr'] = []
        self.some_ip_packages = []
        i = 0
        while not self._io.is_eof():
            self._debug['some_ip_packages']['arr'].append({'start': self._io.pos()})
            _t_some_ip_packages = some_ip.SomeIp(self._io)
            try:
                _t_some_ip_packages._read()
            finally:
                self.some_ip_packages.append(_t_some_ip_packages)
            self._debug['some_ip_packages']['arr'][len(self.some_ip_packages) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['some_ip_packages']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.some_ip_packages)):
            pass
            self.some_ip_packages[i]._fetch_instances()



