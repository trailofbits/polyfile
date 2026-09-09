# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class WindowsMinidump(KaitaiStruct):
    """Windows MiniDump (MDMP) file provides a concise way to store process
    core dumps, which is useful for debugging. Given its small size,
    modularity, some cross-platform features and native support in some
    debuggers, it is particularly useful for crash reporting, and is
    used for that purpose in Windows and Google Chrome projects.
    
    The file itself is a container, which contains a number of typed
    "streams", which contain some data according to its type attribute.
    
    .. seealso::
       Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_header
    """

    class StreamTypes(IntEnum):
        unused = 0
        reserved_0 = 1
        reserved_1 = 2
        thread_list = 3
        module_list = 4
        memory_list = 5
        exception = 6
        system_info = 7
        thread_ex_list = 8
        memory_64_list = 9
        comment_a = 10
        comment_w = 11
        handle_data = 12
        function_table = 13
        unloaded_module_list = 14
        misc_info = 15
        memory_info_list = 16
        thread_info_list = 17
        handle_operation_list = 18
        token = 19
        java_script_data = 20
        system_memory_info = 21
        process_vm_counters = 22
        ipt_trace = 23
        thread_names = 24
        ce_null = 32768
        ce_system_info = 32769
        ce_exception = 32770
        ce_module_list = 32771
        ce_process_list = 32772
        ce_thread_list = 32773
        ce_thread_context_list = 32774
        ce_thread_call_stack_list = 32775
        ce_memory_virtual_list = 32776
        ce_memory_physical_list = 32777
        ce_bucket_parameters = 32778
        ce_process_module_map = 32779
        ce_diagnosis_list = 32780
        md_crashpad_info_stream = 1129316353
        md_raw_breakpad_info = 1197932545
        md_raw_assertion_info = 1197932546
        md_linux_cpu_info = 1197932547
        md_linux_proc_status = 1197932548
        md_linux_lsb_release = 1197932549
        md_linux_cmd_line = 1197932550
        md_linux_environ = 1197932551
        md_linux_auxv = 1197932552
        md_linux_maps = 1197932553
        md_linux_dso_debug = 1197932554
    SEQ_FIELDS = ["magic1", "magic2", "version", "num_streams", "ofs_streams", "checksum", "timestamp", "flags"]
    def __init__(self, _io, _parent=None, _root=None):
        super(WindowsMinidump, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic1']['start'] = self._io.pos()
        self.magic1 = self._io.read_bytes(4)
        self._debug['magic1']['end'] = self._io.pos()
        if not self.magic1 == b"\x4D\x44\x4D\x50":
            raise kaitaistruct.ValidationNotEqualError(b"\x4D\x44\x4D\x50", self.magic1, self._io, u"/seq/0")
        self._debug['magic2']['start'] = self._io.pos()
        self.magic2 = self._io.read_bytes(2)
        self._debug['magic2']['end'] = self._io.pos()
        if not self.magic2 == b"\x93\xA7":
            raise kaitaistruct.ValidationNotEqualError(b"\x93\xA7", self.magic2, self._io, u"/seq/1")
        self._debug['version']['start'] = self._io.pos()
        self.version = self._io.read_u2le()
        self._debug['version']['end'] = self._io.pos()
        self._debug['num_streams']['start'] = self._io.pos()
        self.num_streams = self._io.read_u4le()
        self._debug['num_streams']['end'] = self._io.pos()
        self._debug['ofs_streams']['start'] = self._io.pos()
        self.ofs_streams = self._io.read_u4le()
        self._debug['ofs_streams']['end'] = self._io.pos()
        self._debug['checksum']['start'] = self._io.pos()
        self.checksum = self._io.read_u4le()
        self._debug['checksum']['end'] = self._io.pos()
        self._debug['timestamp']['start'] = self._io.pos()
        self.timestamp = self._io.read_u4le()
        self._debug['timestamp']['end'] = self._io.pos()
        self._debug['flags']['start'] = self._io.pos()
        self.flags = self._io.read_u8le()
        self._debug['flags']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        _ = self.streams
        if hasattr(self, '_m_streams'):
            pass
            for i in range(len(self._m_streams)):
                pass
                self._m_streams[i]._fetch_instances()



    class Dir(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_directory
        """
        SEQ_FIELDS = ["stream_type", "len_data", "ofs_data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.Dir, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['stream_type']['start'] = self._io.pos()
            self.stream_type = KaitaiStream.resolve_enum(WindowsMinidump.StreamTypes, self._io.read_u4le())
            self._debug['stream_type']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['ofs_data']['start'] = self._io.pos()
            self.ofs_data = self._io.read_u4le()
            self._debug['ofs_data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.data
            if hasattr(self, '_m_data'):
                pass
                _on = self.stream_type
                if _on == WindowsMinidump.StreamTypes.exception:
                    pass
                    self._m_data._fetch_instances()
                elif _on == WindowsMinidump.StreamTypes.memory_64_list:
                    pass
                    self._m_data._fetch_instances()
                elif _on == WindowsMinidump.StreamTypes.memory_list:
                    pass
                    self._m_data._fetch_instances()
                elif _on == WindowsMinidump.StreamTypes.misc_info:
                    pass
                    self._m_data._fetch_instances()
                elif _on == WindowsMinidump.StreamTypes.system_info:
                    pass
                    self._m_data._fetch_instances()
                elif _on == WindowsMinidump.StreamTypes.thread_list:
                    pass
                    self._m_data._fetch_instances()
                else:
                    pass


        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data

            _pos = self._io.pos()
            self._io.seek(self.ofs_data)
            self._debug['_m_data']['start'] = self._io.pos()
            _on = self.stream_type
            if _on == WindowsMinidump.StreamTypes.exception:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.ExceptionStream(_io__raw__m_data, self, self._root)
                self._m_data._read()
            elif _on == WindowsMinidump.StreamTypes.memory_64_list:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.Memory64List(_io__raw__m_data, self, self._root)
                self._m_data._read()
            elif _on == WindowsMinidump.StreamTypes.memory_list:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.MemoryList(_io__raw__m_data, self, self._root)
                self._m_data._read()
            elif _on == WindowsMinidump.StreamTypes.misc_info:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.MiscInfo(_io__raw__m_data, self, self._root)
                self._m_data._read()
            elif _on == WindowsMinidump.StreamTypes.system_info:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.SystemInfo(_io__raw__m_data, self, self._root)
                self._m_data._read()
            elif _on == WindowsMinidump.StreamTypes.thread_list:
                pass
                self._raw__m_data = self._io.read_bytes(self.len_data)
                _io__raw__m_data = KaitaiStream(BytesIO(self._raw__m_data))
                self._m_data = WindowsMinidump.ThreadList(_io__raw__m_data, self, self._root)
                self._m_data._read()
            else:
                pass
                self._m_data = self._io.read_bytes(self.len_data)
            self._debug['_m_data']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_data', None)


    class ExceptionRecord(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_exception
        """
        SEQ_FIELDS = ["code", "flags", "inner_exception", "addr", "num_params", "reserved", "params"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.ExceptionRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = self._io.read_u4le()
            self._debug['code']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u4le()
            self._debug['flags']['end'] = self._io.pos()
            self._debug['inner_exception']['start'] = self._io.pos()
            self.inner_exception = self._io.read_u8le()
            self._debug['inner_exception']['end'] = self._io.pos()
            self._debug['addr']['start'] = self._io.pos()
            self.addr = self._io.read_u8le()
            self._debug['addr']['end'] = self._io.pos()
            self._debug['num_params']['start'] = self._io.pos()
            self.num_params = self._io.read_u4le()
            self._debug['num_params']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_u4le()
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['params']['start'] = self._io.pos()
            self._debug['params']['arr'] = []
            self.params = []
            for i in range(15):
                self._debug['params']['arr'].append({'start': self._io.pos()})
                self.params.append(self._io.read_u8le())
                self._debug['params']['arr'][i]['end'] = self._io.pos()

            self._debug['params']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.params)):
                pass



    class ExceptionStream(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_exception_stream
        """
        SEQ_FIELDS = ["thread_id", "reserved", "exception_rec", "thread_context"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.ExceptionStream, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['thread_id']['start'] = self._io.pos()
            self.thread_id = self._io.read_u4le()
            self._debug['thread_id']['end'] = self._io.pos()
            self._debug['reserved']['start'] = self._io.pos()
            self.reserved = self._io.read_u4le()
            self._debug['reserved']['end'] = self._io.pos()
            self._debug['exception_rec']['start'] = self._io.pos()
            self.exception_rec = WindowsMinidump.ExceptionRecord(self._io, self, self._root)
            self.exception_rec._read()
            self._debug['exception_rec']['end'] = self._io.pos()
            self._debug['thread_context']['start'] = self._io.pos()
            self.thread_context = WindowsMinidump.LocationDescriptor(self._io, self, self._root)
            self.thread_context._read()
            self._debug['thread_context']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.exception_rec._fetch_instances()
            self.thread_context._fetch_instances()


    class LocationDescriptor(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_location_descriptor
        """
        SEQ_FIELDS = ["len_data", "ofs_data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.LocationDescriptor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4le()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['ofs_data']['start'] = self._io.pos()
            self.ofs_data = self._io.read_u4le()
            self._debug['ofs_data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.data
            if hasattr(self, '_m_data'):
                pass


        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data

            io = self._root._io
            _pos = io.pos()
            io.seek(self.ofs_data)
            self._debug['_m_data']['start'] = io.pos()
            self._m_data = io.read_bytes(self.len_data)
            self._debug['_m_data']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_data', None)


    class Memory64List(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_memory64_list
        """
        SEQ_FIELDS = ["num_mem_ranges", "ofs_base", "mem_ranges"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.Memory64List, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_mem_ranges']['start'] = self._io.pos()
            self.num_mem_ranges = self._io.read_u8le()
            self._debug['num_mem_ranges']['end'] = self._io.pos()
            self._debug['ofs_base']['start'] = self._io.pos()
            self.ofs_base = self._io.read_u8le()
            self._debug['ofs_base']['end'] = self._io.pos()
            self._debug['mem_ranges']['start'] = self._io.pos()
            self._debug['mem_ranges']['arr'] = []
            self.mem_ranges = []
            for i in range(self.num_mem_ranges):
                self._debug['mem_ranges']['arr'].append({'start': self._io.pos()})
                _t_mem_ranges = WindowsMinidump.MemoryDescriptor64(self._io, self, self._root)
                try:
                    _t_mem_ranges._read()
                finally:
                    self.mem_ranges.append(_t_mem_ranges)
                self._debug['mem_ranges']['arr'][i]['end'] = self._io.pos()

            self._debug['mem_ranges']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.mem_ranges)):
                pass
                self.mem_ranges[i]._fetch_instances()



    class MemoryDescriptor(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_memory_descriptor
        """
        SEQ_FIELDS = ["addr_memory_range", "memory"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.MemoryDescriptor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['addr_memory_range']['start'] = self._io.pos()
            self.addr_memory_range = self._io.read_u8le()
            self._debug['addr_memory_range']['end'] = self._io.pos()
            self._debug['memory']['start'] = self._io.pos()
            self.memory = WindowsMinidump.LocationDescriptor(self._io, self, self._root)
            self.memory._read()
            self._debug['memory']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.memory._fetch_instances()


    class MemoryDescriptor64(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_memory_descriptor64
        """
        SEQ_FIELDS = ["addr_memory_range", "len_data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.MemoryDescriptor64, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['addr_memory_range']['start'] = self._io.pos()
            self.addr_memory_range = self._io.read_u8le()
            self._debug['addr_memory_range']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u8le()
            self._debug['len_data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class MemoryList(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_memory_list
        """
        SEQ_FIELDS = ["num_mem_ranges", "mem_ranges"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.MemoryList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_mem_ranges']['start'] = self._io.pos()
            self.num_mem_ranges = self._io.read_u4le()
            self._debug['num_mem_ranges']['end'] = self._io.pos()
            self._debug['mem_ranges']['start'] = self._io.pos()
            self._debug['mem_ranges']['arr'] = []
            self.mem_ranges = []
            for i in range(self.num_mem_ranges):
                self._debug['mem_ranges']['arr'].append({'start': self._io.pos()})
                _t_mem_ranges = WindowsMinidump.MemoryDescriptor(self._io, self, self._root)
                try:
                    _t_mem_ranges._read()
                finally:
                    self.mem_ranges.append(_t_mem_ranges)
                self._debug['mem_ranges']['arr'][i]['end'] = self._io.pos()

            self._debug['mem_ranges']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.mem_ranges)):
                pass
                self.mem_ranges[i]._fetch_instances()



    class MinidumpString(KaitaiStruct):
        """Specific string serialization scheme used in MiniDump format is
        actually a simple 32-bit length-prefixed UTF-16 string.
        
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_string
        """
        SEQ_FIELDS = ["len_str", "str"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.MinidumpString, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_str']['start'] = self._io.pos()
            self.len_str = self._io.read_u4le()
            self._debug['len_str']['end'] = self._io.pos()
            self._debug['str']['start'] = self._io.pos()
            self.str = (self._io.read_bytes(self.len_str)).decode(u"UTF-16LE")
            self._debug['str']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class MiscInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_misc_info
        """
        SEQ_FIELDS = ["len_info", "flags1", "process_id", "process_create_time", "process_user_time", "process_kernel_time", "cpu_max_mhz", "cpu_cur_mhz", "cpu_limit_mhz", "cpu_max_idle_state", "cpu_cur_idle_state"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.MiscInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_info']['start'] = self._io.pos()
            self.len_info = self._io.read_u4le()
            self._debug['len_info']['end'] = self._io.pos()
            self._debug['flags1']['start'] = self._io.pos()
            self.flags1 = self._io.read_u4le()
            self._debug['flags1']['end'] = self._io.pos()
            self._debug['process_id']['start'] = self._io.pos()
            self.process_id = self._io.read_u4le()
            self._debug['process_id']['end'] = self._io.pos()
            self._debug['process_create_time']['start'] = self._io.pos()
            self.process_create_time = self._io.read_u4le()
            self._debug['process_create_time']['end'] = self._io.pos()
            self._debug['process_user_time']['start'] = self._io.pos()
            self.process_user_time = self._io.read_u4le()
            self._debug['process_user_time']['end'] = self._io.pos()
            self._debug['process_kernel_time']['start'] = self._io.pos()
            self.process_kernel_time = self._io.read_u4le()
            self._debug['process_kernel_time']['end'] = self._io.pos()
            self._debug['cpu_max_mhz']['start'] = self._io.pos()
            self.cpu_max_mhz = self._io.read_u4le()
            self._debug['cpu_max_mhz']['end'] = self._io.pos()
            self._debug['cpu_cur_mhz']['start'] = self._io.pos()
            self.cpu_cur_mhz = self._io.read_u4le()
            self._debug['cpu_cur_mhz']['end'] = self._io.pos()
            self._debug['cpu_limit_mhz']['start'] = self._io.pos()
            self.cpu_limit_mhz = self._io.read_u4le()
            self._debug['cpu_limit_mhz']['end'] = self._io.pos()
            self._debug['cpu_max_idle_state']['start'] = self._io.pos()
            self.cpu_max_idle_state = self._io.read_u4le()
            self._debug['cpu_max_idle_state']['end'] = self._io.pos()
            self._debug['cpu_cur_idle_state']['start'] = self._io.pos()
            self.cpu_cur_idle_state = self._io.read_u4le()
            self._debug['cpu_cur_idle_state']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class SystemInfo(KaitaiStruct):
        """"System info" stream provides basic information about the
        hardware and operating system which produces this dump.
        
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_system_info
        """

        class CpuArchs(IntEnum):
            intel = 0
            arm = 5
            ia64 = 6
            amd64 = 9
            unknown = 65535
        SEQ_FIELDS = ["cpu_arch", "cpu_level", "cpu_revision", "num_cpus", "os_type", "os_ver_major", "os_ver_minor", "os_build", "os_platform", "ofs_service_pack", "os_suite_mask", "reserved2"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.SystemInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['cpu_arch']['start'] = self._io.pos()
            self.cpu_arch = KaitaiStream.resolve_enum(WindowsMinidump.SystemInfo.CpuArchs, self._io.read_u2le())
            self._debug['cpu_arch']['end'] = self._io.pos()
            self._debug['cpu_level']['start'] = self._io.pos()
            self.cpu_level = self._io.read_u2le()
            self._debug['cpu_level']['end'] = self._io.pos()
            self._debug['cpu_revision']['start'] = self._io.pos()
            self.cpu_revision = self._io.read_u2le()
            self._debug['cpu_revision']['end'] = self._io.pos()
            self._debug['num_cpus']['start'] = self._io.pos()
            self.num_cpus = self._io.read_u1()
            self._debug['num_cpus']['end'] = self._io.pos()
            self._debug['os_type']['start'] = self._io.pos()
            self.os_type = self._io.read_u1()
            self._debug['os_type']['end'] = self._io.pos()
            self._debug['os_ver_major']['start'] = self._io.pos()
            self.os_ver_major = self._io.read_u4le()
            self._debug['os_ver_major']['end'] = self._io.pos()
            self._debug['os_ver_minor']['start'] = self._io.pos()
            self.os_ver_minor = self._io.read_u4le()
            self._debug['os_ver_minor']['end'] = self._io.pos()
            self._debug['os_build']['start'] = self._io.pos()
            self.os_build = self._io.read_u4le()
            self._debug['os_build']['end'] = self._io.pos()
            self._debug['os_platform']['start'] = self._io.pos()
            self.os_platform = self._io.read_u4le()
            self._debug['os_platform']['end'] = self._io.pos()
            self._debug['ofs_service_pack']['start'] = self._io.pos()
            self.ofs_service_pack = self._io.read_u4le()
            self._debug['ofs_service_pack']['end'] = self._io.pos()
            self._debug['os_suite_mask']['start'] = self._io.pos()
            self.os_suite_mask = self._io.read_u2le()
            self._debug['os_suite_mask']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_u2le()
            self._debug['reserved2']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.service_pack
            if hasattr(self, '_m_service_pack'):
                pass
                self._m_service_pack._fetch_instances()


        @property
        def service_pack(self):
            if hasattr(self, '_m_service_pack'):
                return self._m_service_pack

            if self.ofs_service_pack > 0:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs_service_pack)
                self._debug['_m_service_pack']['start'] = io.pos()
                self._m_service_pack = WindowsMinidump.MinidumpString(io, self, self._root)
                self._m_service_pack._read()
                self._debug['_m_service_pack']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_service_pack', None)


    class Thread(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_thread
        """
        SEQ_FIELDS = ["thread_id", "suspend_count", "priority_class", "priority", "teb", "stack", "thread_context"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.Thread, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['thread_id']['start'] = self._io.pos()
            self.thread_id = self._io.read_u4le()
            self._debug['thread_id']['end'] = self._io.pos()
            self._debug['suspend_count']['start'] = self._io.pos()
            self.suspend_count = self._io.read_u4le()
            self._debug['suspend_count']['end'] = self._io.pos()
            self._debug['priority_class']['start'] = self._io.pos()
            self.priority_class = self._io.read_u4le()
            self._debug['priority_class']['end'] = self._io.pos()
            self._debug['priority']['start'] = self._io.pos()
            self.priority = self._io.read_u4le()
            self._debug['priority']['end'] = self._io.pos()
            self._debug['teb']['start'] = self._io.pos()
            self.teb = self._io.read_u8le()
            self._debug['teb']['end'] = self._io.pos()
            self._debug['stack']['start'] = self._io.pos()
            self.stack = WindowsMinidump.MemoryDescriptor(self._io, self, self._root)
            self.stack._read()
            self._debug['stack']['end'] = self._io.pos()
            self._debug['thread_context']['start'] = self._io.pos()
            self.thread_context = WindowsMinidump.LocationDescriptor(self._io, self, self._root)
            self.thread_context._read()
            self._debug['thread_context']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.stack._fetch_instances()
            self.thread_context._fetch_instances()


    class ThreadList(KaitaiStruct):
        """
        .. seealso::
           Source - https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_thread_list
        """
        SEQ_FIELDS = ["num_threads", "threads"]
        def __init__(self, _io, _parent=None, _root=None):
            super(WindowsMinidump.ThreadList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_threads']['start'] = self._io.pos()
            self.num_threads = self._io.read_u4le()
            self._debug['num_threads']['end'] = self._io.pos()
            self._debug['threads']['start'] = self._io.pos()
            self._debug['threads']['arr'] = []
            self.threads = []
            for i in range(self.num_threads):
                self._debug['threads']['arr'].append({'start': self._io.pos()})
                _t_threads = WindowsMinidump.Thread(self._io, self, self._root)
                try:
                    _t_threads._read()
                finally:
                    self.threads.append(_t_threads)
                self._debug['threads']['arr'][i]['end'] = self._io.pos()

            self._debug['threads']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.threads)):
                pass
                self.threads[i]._fetch_instances()



    @property
    def streams(self):
        if hasattr(self, '_m_streams'):
            return self._m_streams

        _pos = self._io.pos()
        self._io.seek(self.ofs_streams)
        self._debug['_m_streams']['start'] = self._io.pos()
        self._debug['_m_streams']['arr'] = []
        self._m_streams = []
        for i in range(self.num_streams):
            self._debug['_m_streams']['arr'].append({'start': self._io.pos()})
            _t__m_streams = WindowsMinidump.Dir(self._io, self, self._root)
            try:
                _t__m_streams._read()
            finally:
                self._m_streams.append(_t__m_streams)
            self._debug['_m_streams']['arr'][i]['end'] = self._io.pos()

        self._debug['_m_streams']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_streams', None)


