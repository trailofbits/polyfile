# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class TlsClientHello(KaitaiStruct):
    SEQ_FIELDS = ["version", "random", "session_id", "cipher_suites", "compression_methods", "extensions"]
    def __init__(self, _io, _parent=None, _root=None):
        super(TlsClientHello, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['version']['start'] = self._io.pos()
        self.version = TlsClientHello.Version(self._io, self, self._root)
        self.version._read()
        self._debug['version']['end'] = self._io.pos()
        self._debug['random']['start'] = self._io.pos()
        self.random = TlsClientHello.Random(self._io, self, self._root)
        self.random._read()
        self._debug['random']['end'] = self._io.pos()
        self._debug['session_id']['start'] = self._io.pos()
        self.session_id = TlsClientHello.SessionId(self._io, self, self._root)
        self.session_id._read()
        self._debug['session_id']['end'] = self._io.pos()
        self._debug['cipher_suites']['start'] = self._io.pos()
        self.cipher_suites = TlsClientHello.CipherSuites(self._io, self, self._root)
        self.cipher_suites._read()
        self._debug['cipher_suites']['end'] = self._io.pos()
        self._debug['compression_methods']['start'] = self._io.pos()
        self.compression_methods = TlsClientHello.CompressionMethods(self._io, self, self._root)
        self.compression_methods._read()
        self._debug['compression_methods']['end'] = self._io.pos()
        if self._io.is_eof() == False:
            pass
            self._debug['extensions']['start'] = self._io.pos()
            self.extensions = TlsClientHello.Extensions(self._io, self, self._root)
            self.extensions._read()
            self._debug['extensions']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        self.version._fetch_instances()
        self.random._fetch_instances()
        self.session_id._fetch_instances()
        self.cipher_suites._fetch_instances()
        self.compression_methods._fetch_instances()
        if self._io.is_eof() == False:
            pass
            self.extensions._fetch_instances()


    class Alpn(KaitaiStruct):
        SEQ_FIELDS = ["ext_len", "alpn_protocols"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Alpn, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ext_len']['start'] = self._io.pos()
            self.ext_len = self._io.read_u2be()
            self._debug['ext_len']['end'] = self._io.pos()
            self._debug['alpn_protocols']['start'] = self._io.pos()
            self._debug['alpn_protocols']['arr'] = []
            self.alpn_protocols = []
            i = 0
            while not self._io.is_eof():
                self._debug['alpn_protocols']['arr'].append({'start': self._io.pos()})
                _t_alpn_protocols = TlsClientHello.Protocol(self._io, self, self._root)
                try:
                    _t_alpn_protocols._read()
                finally:
                    self.alpn_protocols.append(_t_alpn_protocols)
                self._debug['alpn_protocols']['arr'][len(self.alpn_protocols) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['alpn_protocols']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.alpn_protocols)):
                pass
                self.alpn_protocols[i]._fetch_instances()



    class CipherSuites(KaitaiStruct):
        SEQ_FIELDS = ["len", "cipher_suites"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.CipherSuites, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u2be()
            self._debug['len']['end'] = self._io.pos()
            self._debug['cipher_suites']['start'] = self._io.pos()
            self._debug['cipher_suites']['arr'] = []
            self.cipher_suites = []
            for i in range(self.len // 2):
                self._debug['cipher_suites']['arr'].append({'start': self._io.pos()})
                self.cipher_suites.append(self._io.read_u2be())
                self._debug['cipher_suites']['arr'][i]['end'] = self._io.pos()

            self._debug['cipher_suites']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.cipher_suites)):
                pass



    class CompressionMethods(KaitaiStruct):
        SEQ_FIELDS = ["len", "compression_methods"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.CompressionMethods, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['compression_methods']['start'] = self._io.pos()
            self.compression_methods = self._io.read_bytes(self.len)
            self._debug['compression_methods']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Extension(KaitaiStruct):
        SEQ_FIELDS = ["type", "len", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Extension, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['type']['start'] = self._io.pos()
            self.type = self._io.read_u2be()
            self._debug['type']['end'] = self._io.pos()
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u2be()
            self._debug['len']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == 0:
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = TlsClientHello.Sni(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == 16:
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = TlsClientHello.Alpn(_io__raw_body, self, self._root)
                self.body._read()
            else:
                pass
                self.body = self._io.read_bytes(self.len)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.type
            if _on == 0:
                pass
                self.body._fetch_instances()
            elif _on == 16:
                pass
                self.body._fetch_instances()
            else:
                pass


    class Extensions(KaitaiStruct):
        SEQ_FIELDS = ["len", "extensions"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Extensions, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u2be()
            self._debug['len']['end'] = self._io.pos()
            self._debug['extensions']['start'] = self._io.pos()
            self._debug['extensions']['arr'] = []
            self.extensions = []
            i = 0
            while not self._io.is_eof():
                self._debug['extensions']['arr'].append({'start': self._io.pos()})
                _t_extensions = TlsClientHello.Extension(self._io, self, self._root)
                try:
                    _t_extensions._read()
                finally:
                    self.extensions.append(_t_extensions)
                self._debug['extensions']['arr'][len(self.extensions) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['extensions']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.extensions)):
                pass
                self.extensions[i]._fetch_instances()



    class Protocol(KaitaiStruct):
        SEQ_FIELDS = ["strlen", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Protocol, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['strlen']['start'] = self._io.pos()
            self.strlen = self._io.read_u1()
            self._debug['strlen']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = self._io.read_bytes(self.strlen)
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Random(KaitaiStruct):
        SEQ_FIELDS = ["gmt_unix_time", "random"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Random, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['gmt_unix_time']['start'] = self._io.pos()
            self.gmt_unix_time = self._io.read_u4be()
            self._debug['gmt_unix_time']['end'] = self._io.pos()
            self._debug['random']['start'] = self._io.pos()
            self.random = self._io.read_bytes(28)
            self._debug['random']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class ServerName(KaitaiStruct):
        SEQ_FIELDS = ["name_type", "length", "host_name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.ServerName, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name_type']['start'] = self._io.pos()
            self.name_type = self._io.read_u1()
            self._debug['name_type']['end'] = self._io.pos()
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u2be()
            self._debug['length']['end'] = self._io.pos()
            self._debug['host_name']['start'] = self._io.pos()
            self.host_name = self._io.read_bytes(self.length)
            self._debug['host_name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class SessionId(KaitaiStruct):
        SEQ_FIELDS = ["len", "sid"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.SessionId, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['sid']['start'] = self._io.pos()
            self.sid = self._io.read_bytes(self.len)
            self._debug['sid']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Sni(KaitaiStruct):
        SEQ_FIELDS = ["list_length", "server_names"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Sni, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['list_length']['start'] = self._io.pos()
            self.list_length = self._io.read_u2be()
            self._debug['list_length']['end'] = self._io.pos()
            self._debug['server_names']['start'] = self._io.pos()
            self._debug['server_names']['arr'] = []
            self.server_names = []
            i = 0
            while not self._io.is_eof():
                self._debug['server_names']['arr'].append({'start': self._io.pos()})
                _t_server_names = TlsClientHello.ServerName(self._io, self, self._root)
                try:
                    _t_server_names._read()
                finally:
                    self.server_names.append(_t_server_names)
                self._debug['server_names']['arr'][len(self.server_names) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['server_names']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.server_names)):
                pass
                self.server_names[i]._fetch_instances()



    class Version(KaitaiStruct):
        SEQ_FIELDS = ["major", "minor"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TlsClientHello.Version, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['major']['start'] = self._io.pos()
            self.major = self._io.read_u1()
            self._debug['major']['end'] = self._io.pos()
            self._debug['minor']['start'] = self._io.pos()
            self.minor = self._io.read_u1()
            self._debug['minor']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



