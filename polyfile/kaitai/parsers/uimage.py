# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Uimage(KaitaiStruct):
    """The new uImage format allows more flexibility in handling images of various
    types (kernel, ramdisk, etc.), it also enhances integrity protection of images
    with sha1 and md5 checksums.
    
    .. seealso::
       Source - https://source.denx.de/u-boot/u-boot/-/raw/e4dba4ba6f/include/image.h
    """

    class UimageArch(IntEnum):
        invalid = 0
        alpha = 1
        arm = 2
        i386 = 3
        ia64 = 4
        mips = 5
        mips64 = 6
        ppc = 7
        s390 = 8
        sh = 9
        sparc = 10
        sparc64 = 11
        m68k = 12
        nios = 13
        microblaze = 14
        nios2 = 15
        blackfin = 16
        avr32 = 17
        st200 = 18
        sandbox = 19
        nds32 = 20
        openrisc = 21
        arm64 = 22
        arc = 23
        x86_64 = 24
        xtensa = 25
        riscv = 26

    class UimageComp(IntEnum):
        none = 0
        gzip = 1
        bzip2 = 2
        lzma = 3
        lzo = 4
        lz4 = 5
        zstd = 6

    class UimageOs(IntEnum):
        invalid = 0
        openbsd = 1
        netbsd = 2
        freebsd = 3
        bsd4_4 = 4
        linux = 5
        svr4 = 6
        esix = 7
        solaris = 8
        irix = 9
        sco = 10
        dell = 11
        ncr = 12
        lynxos = 13
        vxworks = 14
        psos = 15
        qnx = 16
        u_boot = 17
        rtems = 18
        artos = 19
        unity = 20
        integrity = 21
        ose = 22
        plan9 = 23
        openrtos = 24
        arm_trusted_firmware = 25
        tee = 26
        opensbi = 27
        efi = 28

    class UimageType(IntEnum):
        invalid = 0
        standalone = 1
        kernel = 2
        ramdisk = 3
        multi = 4
        firmware = 5
        script = 6
        filesystem = 7
        flatdt = 8
        kwbimage = 9
        imximage = 10
        ublimage = 11
        omapimage = 12
        aisimage = 13
        kernel_noload = 14
        pblimage = 15
        mxsimage = 16
        gpimage = 17
        atmelimage = 18
        socfpgaimage = 19
        x86_setup = 20
        lpc32xximage = 21
        loadable = 22
        rkimage = 23
        rksd = 24
        rkspi = 25
        zynqimage = 26
        zynqmpimage = 27
        zynqmpbif = 28
        fpga = 29
        vybridimage = 30
        tee = 31
        firmware_ivt = 32
        pmmc = 33
        stm32image = 34
        socfpgaimage_v1 = 35
        mtkimage = 36
        imx8mimage = 37
        imx8image = 38
        copro = 39
        sunxi_egon = 40
    SEQ_FIELDS = ["header", "data"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Uimage, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = Uimage.Uheader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['data']['start'] = self._io.pos()
        self.data = self._io.read_bytes(self.header.len_image)
        self._debug['data']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()

    class Uheader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "header_crc", "timestamp", "len_image", "load_address", "entry_address", "data_crc", "os_type", "architecture", "image_type", "compression_type", "name"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Uimage.Uheader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x27\x05\x19\x56":
                raise kaitaistruct.ValidationNotEqualError(b"\x27\x05\x19\x56", self.magic, self._io, u"/types/uheader/seq/0")
            self._debug['header_crc']['start'] = self._io.pos()
            self.header_crc = self._io.read_u4be()
            self._debug['header_crc']['end'] = self._io.pos()
            self._debug['timestamp']['start'] = self._io.pos()
            self.timestamp = self._io.read_u4be()
            self._debug['timestamp']['end'] = self._io.pos()
            self._debug['len_image']['start'] = self._io.pos()
            self.len_image = self._io.read_u4be()
            self._debug['len_image']['end'] = self._io.pos()
            self._debug['load_address']['start'] = self._io.pos()
            self.load_address = self._io.read_u4be()
            self._debug['load_address']['end'] = self._io.pos()
            self._debug['entry_address']['start'] = self._io.pos()
            self.entry_address = self._io.read_u4be()
            self._debug['entry_address']['end'] = self._io.pos()
            self._debug['data_crc']['start'] = self._io.pos()
            self.data_crc = self._io.read_u4be()
            self._debug['data_crc']['end'] = self._io.pos()
            self._debug['os_type']['start'] = self._io.pos()
            self.os_type = KaitaiStream.resolve_enum(Uimage.UimageOs, self._io.read_u1())
            self._debug['os_type']['end'] = self._io.pos()
            self._debug['architecture']['start'] = self._io.pos()
            self.architecture = KaitaiStream.resolve_enum(Uimage.UimageArch, self._io.read_u1())
            self._debug['architecture']['end'] = self._io.pos()
            self._debug['image_type']['start'] = self._io.pos()
            self.image_type = KaitaiStream.resolve_enum(Uimage.UimageType, self._io.read_u1())
            self._debug['image_type']['end'] = self._io.pos()
            self._debug['compression_type']['start'] = self._io.pos()
            self.compression_type = KaitaiStream.resolve_enum(Uimage.UimageComp, self._io.read_u1())
            self._debug['compression_type']['end'] = self._io.pos()
            self._debug['name']['start'] = self._io.pos()
            self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(32), 0, False)).decode(u"UTF-8")
            self._debug['name']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



