# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidImg(KaitaiStruct):
    """
    .. seealso::
       Source - https://source.android.com/docs/core/architecture/bootloader/boot-image-header
    """
    SEQ_FIELDS = ["magic", "kernel", "ramdisk", "second", "tags_load", "page_size", "header_version", "os_version", "name", "cmdline", "sha", "extra_cmdline", "recovery_dtbo", "boot_header_size", "dtb"]
    def __init__(self, _io, _parent=None, _root=None):
        super(AndroidImg, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(8)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x41\x4E\x44\x52\x4F\x49\x44\x21":
            raise kaitaistruct.ValidationNotEqualError(b"\x41\x4E\x44\x52\x4F\x49\x44\x21", self.magic, self._io, u"/seq/0")
        self._debug['kernel']['start'] = self._io.pos()
        self.kernel = AndroidImg.Load(self._io, self, self._root)
        self.kernel._read()
        self._debug['kernel']['end'] = self._io.pos()
        self._debug['ramdisk']['start'] = self._io.pos()
        self.ramdisk = AndroidImg.Load(self._io, self, self._root)
        self.ramdisk._read()
        self._debug['ramdisk']['end'] = self._io.pos()
        self._debug['second']['start'] = self._io.pos()
        self.second = AndroidImg.Load(self._io, self, self._root)
        self.second._read()
        self._debug['second']['end'] = self._io.pos()
        self._debug['tags_load']['start'] = self._io.pos()
        self.tags_load = self._io.read_u4le()
        self._debug['tags_load']['end'] = self._io.pos()
        self._debug['page_size']['start'] = self._io.pos()
        self.page_size = self._io.read_u4le()
        self._debug['page_size']['end'] = self._io.pos()
        self._debug['header_version']['start'] = self._io.pos()
        self.header_version = self._io.read_u4le()
        self._debug['header_version']['end'] = self._io.pos()
        self._debug['os_version']['start'] = self._io.pos()
        self.os_version = AndroidImg.OsVersion(self._io, self, self._root)
        self.os_version._read()
        self._debug['os_version']['end'] = self._io.pos()
        self._debug['name']['start'] = self._io.pos()
        self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(16), 0, False)).decode(u"ASCII")
        self._debug['name']['end'] = self._io.pos()
        self._debug['cmdline']['start'] = self._io.pos()
        self.cmdline = (KaitaiStream.bytes_terminate(self._io.read_bytes(512), 0, False)).decode(u"ASCII")
        self._debug['cmdline']['end'] = self._io.pos()
        self._debug['sha']['start'] = self._io.pos()
        self.sha = self._io.read_bytes(32)
        self._debug['sha']['end'] = self._io.pos()
        self._debug['extra_cmdline']['start'] = self._io.pos()
        self.extra_cmdline = (KaitaiStream.bytes_terminate(self._io.read_bytes(1024), 0, False)).decode(u"ASCII")
        self._debug['extra_cmdline']['end'] = self._io.pos()
        if self.header_version > 0:
            pass
            self._debug['recovery_dtbo']['start'] = self._io.pos()
            self.recovery_dtbo = AndroidImg.SizeOffset(self._io, self, self._root)
            self.recovery_dtbo._read()
            self._debug['recovery_dtbo']['end'] = self._io.pos()

        if self.header_version > 0:
            pass
            self._debug['boot_header_size']['start'] = self._io.pos()
            self.boot_header_size = self._io.read_u4le()
            self._debug['boot_header_size']['end'] = self._io.pos()

        if self.header_version > 1:
            pass
            self._debug['dtb']['start'] = self._io.pos()
            self.dtb = AndroidImg.LoadLong(self._io, self, self._root)
            self.dtb._read()
            self._debug['dtb']['end'] = self._io.pos()



    def _fetch_instances(self):
        pass
        self.kernel._fetch_instances()
        self.ramdisk._fetch_instances()
        self.second._fetch_instances()
        self.os_version._fetch_instances()
        if self.header_version > 0:
            pass
            self.recovery_dtbo._fetch_instances()

        if self.header_version > 0:
            pass

        if self.header_version > 1:
            pass
            self.dtb._fetch_instances()

        _ = self.dtb_img
        if hasattr(self, '_m_dtb_img'):
            pass

        _ = self.kernel_img
        if hasattr(self, '_m_kernel_img'):
            pass

        _ = self.ramdisk_img
        if hasattr(self, '_m_ramdisk_img'):
            pass

        _ = self.recovery_dtbo_img
        if hasattr(self, '_m_recovery_dtbo_img'):
            pass

        _ = self.second_img
        if hasattr(self, '_m_second_img'):
            pass


    class Load(KaitaiStruct):
        SEQ_FIELDS = ["size", "addr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidImg.Load, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['addr']['start'] = self._io.pos()
            self.addr = self._io.read_u4le()
            self._debug['addr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class LoadLong(KaitaiStruct):
        SEQ_FIELDS = ["size", "addr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidImg.LoadLong, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['addr']['start'] = self._io.pos()
            self.addr = self._io.read_u8le()
            self._debug['addr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class OsVersion(KaitaiStruct):
        SEQ_FIELDS = ["version"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidImg.OsVersion, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4le()
            self._debug['version']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def major(self):
            if hasattr(self, '_m_major'):
                return self._m_major

            self._m_major = self.version >> 25 & 127
            return getattr(self, '_m_major', None)

        @property
        def minor(self):
            if hasattr(self, '_m_minor'):
                return self._m_minor

            self._m_minor = self.version >> 18 & 127
            return getattr(self, '_m_minor', None)

        @property
        def month(self):
            if hasattr(self, '_m_month'):
                return self._m_month

            self._m_month = self.version & 15
            return getattr(self, '_m_month', None)

        @property
        def patch(self):
            if hasattr(self, '_m_patch'):
                return self._m_patch

            self._m_patch = self.version >> 11 & 127
            return getattr(self, '_m_patch', None)

        @property
        def year(self):
            if hasattr(self, '_m_year'):
                return self._m_year

            self._m_year = (self.version >> 4 & 127) + 2000
            return getattr(self, '_m_year', None)


    class SizeOffset(KaitaiStruct):
        SEQ_FIELDS = ["size", "offset"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidImg.SizeOffset, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['size']['start'] = self._io.pos()
            self.size = self._io.read_u4le()
            self._debug['size']['end'] = self._io.pos()
            self._debug['offset']['start'] = self._io.pos()
            self.offset = self._io.read_u8le()
            self._debug['offset']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    @property
    def base(self):
        """base loading address."""
        if hasattr(self, '_m_base'):
            return self._m_base

        self._m_base = self.kernel.addr - 32768
        return getattr(self, '_m_base', None)

    @property
    def dtb_img(self):
        if hasattr(self, '_m_dtb_img'):
            return self._m_dtb_img

        if  ((self.header_version > 1) and (self.dtb.size > 0)) :
            pass
            _pos = self._io.pos()
            self._io.seek((((((((self.page_size + self.kernel.size) + self.ramdisk.size) + self.second.size) + self.recovery_dtbo.size) + self.page_size) - 1) // self.page_size) * self.page_size)
            self._debug['_m_dtb_img']['start'] = self._io.pos()
            self._m_dtb_img = self._io.read_bytes(self.dtb.size)
            self._debug['_m_dtb_img']['end'] = self._io.pos()
            self._io.seek(_pos)

        return getattr(self, '_m_dtb_img', None)

    @property
    def dtb_offset(self):
        """dtb offset from base."""
        if hasattr(self, '_m_dtb_offset'):
            return self._m_dtb_offset

        if self.header_version > 1:
            pass
            self._m_dtb_offset = (self.dtb.addr - self.base if self.dtb.addr > 0 else 0)

        return getattr(self, '_m_dtb_offset', None)

    @property
    def kernel_img(self):
        if hasattr(self, '_m_kernel_img'):
            return self._m_kernel_img

        _pos = self._io.pos()
        self._io.seek(self.page_size)
        self._debug['_m_kernel_img']['start'] = self._io.pos()
        self._m_kernel_img = self._io.read_bytes(self.kernel.size)
        self._debug['_m_kernel_img']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_kernel_img', None)

    @property
    def kernel_offset(self):
        """kernel offset from base."""
        if hasattr(self, '_m_kernel_offset'):
            return self._m_kernel_offset

        self._m_kernel_offset = self.kernel.addr - self.base
        return getattr(self, '_m_kernel_offset', None)

    @property
    def ramdisk_img(self):
        if hasattr(self, '_m_ramdisk_img'):
            return self._m_ramdisk_img

        if self.ramdisk.size > 0:
            pass
            _pos = self._io.pos()
            self._io.seek(((((self.page_size + self.kernel.size) + self.page_size) - 1) // self.page_size) * self.page_size)
            self._debug['_m_ramdisk_img']['start'] = self._io.pos()
            self._m_ramdisk_img = self._io.read_bytes(self.ramdisk.size)
            self._debug['_m_ramdisk_img']['end'] = self._io.pos()
            self._io.seek(_pos)

        return getattr(self, '_m_ramdisk_img', None)

    @property
    def ramdisk_offset(self):
        """ramdisk offset from base."""
        if hasattr(self, '_m_ramdisk_offset'):
            return self._m_ramdisk_offset

        self._m_ramdisk_offset = (self.ramdisk.addr - self.base if self.ramdisk.addr > 0 else 0)
        return getattr(self, '_m_ramdisk_offset', None)

    @property
    def recovery_dtbo_img(self):
        if hasattr(self, '_m_recovery_dtbo_img'):
            return self._m_recovery_dtbo_img

        if  ((self.header_version > 0) and (self.recovery_dtbo.size > 0)) :
            pass
            _pos = self._io.pos()
            self._io.seek(self.recovery_dtbo.offset)
            self._debug['_m_recovery_dtbo_img']['start'] = self._io.pos()
            self._m_recovery_dtbo_img = self._io.read_bytes(self.recovery_dtbo.size)
            self._debug['_m_recovery_dtbo_img']['end'] = self._io.pos()
            self._io.seek(_pos)

        return getattr(self, '_m_recovery_dtbo_img', None)

    @property
    def second_img(self):
        if hasattr(self, '_m_second_img'):
            return self._m_second_img

        if self.second.size > 0:
            pass
            _pos = self._io.pos()
            self._io.seek((((((self.page_size + self.kernel.size) + self.ramdisk.size) + self.page_size) - 1) // self.page_size) * self.page_size)
            self._debug['_m_second_img']['start'] = self._io.pos()
            self._m_second_img = self._io.read_bytes(self.second.size)
            self._debug['_m_second_img']['end'] = self._io.pos()
            self._io.seek(_pos)

        return getattr(self, '_m_second_img', None)

    @property
    def second_offset(self):
        """2nd bootloader offset from base."""
        if hasattr(self, '_m_second_offset'):
            return self._m_second_offset

        self._m_second_offset = (self.second.addr - self.base if self.second.addr > 0 else 0)
        return getattr(self, '_m_second_offset', None)

    @property
    def tags_offset(self):
        """tags offset from base."""
        if hasattr(self, '_m_tags_offset'):
            return self._m_tags_offset

        self._m_tags_offset = self.tags_load - self.base
        return getattr(self, '_m_tags_offset', None)


