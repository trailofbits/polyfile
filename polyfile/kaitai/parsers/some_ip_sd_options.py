# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import IntEnum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SomeIpSdOptions(KaitaiStruct):
    """FormatOptions are used to transport additional information to the entries.
    This includes forinstance the information how a service instance is
    reachable (IP-Address, TransportProtocol, Port Number).
    
    .. seealso::
       section 4.1.2.4 Options Format - https://www.autosar.org/fileadmin/standards/foundation/19-11/AUTOSAR_PRS_SOMEIPServiceDiscoveryProtocol.pdf
       -
    """
    SEQ_FIELDS = ["entries"]
    def __init__(self, _io, _parent=None, _root=None):
        super(SomeIpSdOptions, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['entries']['start'] = self._io.pos()
        self._debug['entries']['arr'] = []
        self.entries = []
        i = 0
        while not self._io.is_eof():
            self._debug['entries']['arr'].append({'start': self._io.pos()})
            _t_entries = SomeIpSdOptions.SdOption(self._io, self, self._root)
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


    class SdOption(KaitaiStruct):

        class OptionTypes(IntEnum):
            configuration_option = 1
            load_balancing_option = 2
            ipv4_endpoint_option = 4
            ipv6_endpoint_option = 6
            ipv4_multicast_option = 20
            ipv6_multicast_option = 22
            ipv4_sd_endpoint_option = 36
            ipv6_sd_endpoint_option = 38
        SEQ_FIELDS = ["header", "content"]
        def __init__(self, _io, _parent=None, _root=None):
            super(SomeIpSdOptions.SdOption, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['header']['start'] = self._io.pos()
            self.header = SomeIpSdOptions.SdOption.SdOptionHeader(self._io, self, self._root)
            self.header._read()
            self._debug['header']['end'] = self._io.pos()
            self._debug['content']['start'] = self._io.pos()
            _on = self.header.type
            if _on == SomeIpSdOptions.SdOption.OptionTypes.configuration_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdConfigurationOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_endpoint_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv4EndpointOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_multicast_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv4MulticastOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_sd_endpoint_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv4SdEndpointOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_endpoint_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv6EndpointOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_multicast_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv6MulticastOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_sd_endpoint_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdIpv6SdEndpointOption(self._io, self, self._root)
                self.content._read()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.load_balancing_option:
                pass
                self.content = SomeIpSdOptions.SdOption.SdLoadBalancingOption(self._io, self, self._root)
                self.content._read()
            self._debug['content']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.header._fetch_instances()
            _on = self.header.type
            if _on == SomeIpSdOptions.SdOption.OptionTypes.configuration_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_endpoint_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_multicast_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv4_sd_endpoint_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_endpoint_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_multicast_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.ipv6_sd_endpoint_option:
                pass
                self.content._fetch_instances()
            elif _on == SomeIpSdOptions.SdOption.OptionTypes.load_balancing_option:
                pass
                self.content._fetch_instances()

        class SdConfigKvPair(KaitaiStruct):
            SEQ_FIELDS = ["key", "value"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdConfigKvPair, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['key']['start'] = self._io.pos()
                self.key = (self._io.read_bytes_term(61, False, True, True)).decode(u"ASCII")
                self._debug['key']['end'] = self._io.pos()
                self._debug['value']['start'] = self._io.pos()
                self.value = (self._io.read_bytes_full()).decode(u"ASCII")
                self._debug['value']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdConfigString(KaitaiStruct):
            SEQ_FIELDS = ["length", "config"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdConfigString, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['length']['start'] = self._io.pos()
                self.length = self._io.read_u1()
                self._debug['length']['end'] = self._io.pos()
                if self.length != 0:
                    pass
                    self._debug['config']['start'] = self._io.pos()
                    self._raw_config = self._io.read_bytes(self.length)
                    _io__raw_config = KaitaiStream(BytesIO(self._raw_config))
                    self.config = SomeIpSdOptions.SdOption.SdConfigKvPair(_io__raw_config, self, self._root)
                    self.config._read()
                    self._debug['config']['end'] = self._io.pos()



            def _fetch_instances(self):
                pass
                if self.length != 0:
                    pass
                    self.config._fetch_instances()



        class SdConfigStringsContainer(KaitaiStruct):
            SEQ_FIELDS = ["config_strings"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdConfigStringsContainer, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['config_strings']['start'] = self._io.pos()
                self._debug['config_strings']['arr'] = []
                self.config_strings = []
                i = 0
                while not self._io.is_eof():
                    self._debug['config_strings']['arr'].append({'start': self._io.pos()})
                    _t_config_strings = SomeIpSdOptions.SdOption.SdConfigString(self._io, self, self._root)
                    try:
                        _t_config_strings._read()
                    finally:
                        self.config_strings.append(_t_config_strings)
                    self._debug['config_strings']['arr'][len(self.config_strings) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['config_strings']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.config_strings)):
                    pass
                    self.config_strings[i]._fetch_instances()



        class SdConfigurationOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "configurations"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdConfigurationOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['configurations']['start'] = self._io.pos()
                self._raw_configurations = self._io.read_bytes(self._parent.header.length - 1)
                _io__raw_configurations = KaitaiStream(BytesIO(self._raw_configurations))
                self.configurations = SomeIpSdOptions.SdOption.SdConfigStringsContainer(_io__raw_configurations, self, self._root)
                self.configurations._read()
                self._debug['configurations']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                self.configurations._fetch_instances()


        class SdIpv4EndpointOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv4EndpointOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(4)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdIpv4MulticastOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv4MulticastOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(4)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdIpv4SdEndpointOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv4SdEndpointOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(4)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdIpv6EndpointOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv6EndpointOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(16)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdIpv6MulticastOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv6MulticastOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(16)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdIpv6SdEndpointOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "address", "reserved2", "l4_protocol", "port"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdIpv6SdEndpointOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['address']['start'] = self._io.pos()
                self.address = self._io.read_bytes(16)
                self._debug['address']['end'] = self._io.pos()
                self._debug['reserved2']['start'] = self._io.pos()
                self.reserved2 = self._io.read_u1()
                self._debug['reserved2']['end'] = self._io.pos()
                self._debug['l4_protocol']['start'] = self._io.pos()
                self.l4_protocol = self._io.read_u1()
                self._debug['l4_protocol']['end'] = self._io.pos()
                self._debug['port']['start'] = self._io.pos()
                self.port = self._io.read_u2be()
                self._debug['port']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdLoadBalancingOption(KaitaiStruct):
            SEQ_FIELDS = ["reserved", "priority", "weight"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdLoadBalancingOption, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['reserved']['start'] = self._io.pos()
                self.reserved = self._io.read_u1()
                self._debug['reserved']['end'] = self._io.pos()
                self._debug['priority']['start'] = self._io.pos()
                self.priority = self._io.read_u2be()
                self._debug['priority']['end'] = self._io.pos()
                self._debug['weight']['start'] = self._io.pos()
                self.weight = self._io.read_u2be()
                self._debug['weight']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class SdOptionHeader(KaitaiStruct):
            SEQ_FIELDS = ["length", "type"]
            def __init__(self, _io, _parent=None, _root=None):
                super(SomeIpSdOptions.SdOption.SdOptionHeader, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['length']['start'] = self._io.pos()
                self.length = self._io.read_u2be()
                self._debug['length']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(SomeIpSdOptions.SdOption.OptionTypes, self._io.read_u1())
                self._debug['type']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass




