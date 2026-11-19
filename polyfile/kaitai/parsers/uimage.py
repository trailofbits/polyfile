# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Uimage(KaitaiStruct):
    """The legacy U-Boot image format (uImage), as created by `mkimage`: a 64-byte
    header followed by the image data (e.g. a Linux kernel, a ramdisk or a
    script). The header describes the data (OS, CPU architecture, image type,
    compression, load and entry point addresses, name) and protects both the
    header and the data with CRC-32 checksums.
    
    U-Boot's newer FIT (Flattened Image Tree) format is not covered by this spec.
    
    .. seealso::
       Git tag "v2026.07" - https://github.com/u-boot/u-boot/blob/ece349ade2973e220f524ce59e59711cc919263f/include/image.h
    """

    class MagicTypes(IntEnum):
        allnet_all_sg8316m = 5
        allnet_all_sg8208m = 6
        allnet_all_sg8324m = 22
        datto_l8 = 7353344
        allnet_all_wapc0450c = 9453568
        engenius_ews2910p_v3 = 50398464
        engenius_ews1200_28tfp = 50402048
        engenius_ews7926efp = 50402050
        engenius_ews7952p = 50406401
        engenius_ews2908p = 50409728
        engenius_ews7928p_v2 = 51450112
        engenius_ews1200_28tfp_v2 = 51450624
        engenius_ews2910p = 58730768
        engenius_ews5912fp = 58743058
        engenius_ews7928p = 58751272
        engenius_ews1200d_10t = 59187216
        engenius_ews1200_28t = 59187240
        engenius_ews7928fp = 59216527
        engenius_ews1200_52t = 60235858
        engenius_ews7952fp = 60265775
        youku_yk_l1 = 304680960
        realtek_sdk = 305418240
        netgear_gs750e = 391006017
        netgear_gs728tp_v2 = 391006018
        bolt_bl100 = 638656533
        uimage = 654645590
        netgear_wnce4004 = 654645607
        netgear_wnr612_v2_early = 808857906
        netgear_wnr1000_v2_vc = 825241648
        netgear_wnr1000_v2 = 825241649
        netgear_wnr1000_v2_vm = 825241650
        netgear_wnr1000_v4 = 825241652
        netgear_wpn824n = 825307184
        zyxel_uag50 = 827343191
        netgear_wnr2000 = 842018865
        netgear_wnr2000_v3 = 842018867
        netgear_wnr2000_v4 = 842018868
        netgear_wnr612_v2 = 842020401
        netgear_wnr2200 = 842149936
        netgear_wndr3700 = 859254832
        netgear_wndr3700_v2 = 859254833
        netgear_wndr3700_v4 = 859254835
        netgear_r6100 = 909127728
        netgear_wnr612 = 909193778
        mitrastar_comb = 1129270594
        mitrastar_comc = 1129270595
        netgear_gs308t = 1313293109
        netgear_nge = 1313293600
        netgear_ngf = 1313293856
        netgear_ngg = 1313294112
        netgear_ngh = 1313294368
        netgear_ngi = 1313294624
        netgear_ngp = 1313296416
        openwrt_okli = 1330334793
        openwrt_dlink_covr = 1752396147
        openwrt_senao_okli = 1936805707
        engenius_ecs1112fp = 2155872258
        engenius_fitswitch = 2155872259
        engenius_ews1200_28tfp_old_fw = 2197885696
        engenius_ews7926efp_old_fw = 2197885698
        engenius_ews7952p_old_fw = 2197890049
        realtek_rtl838x = 2206203904
        iodata_bsh_g08m = 2206203905
        iodata_bsh_gp08 = 2206203906
        iodata_bsh_g16m = 2206203907
        iodata_bsh_g24m = 2206203908
        iodata_bsh_g08mb = 2206203920
        iodata_bsh_gp08mb = 2206203921
        iodata_bsh_g16mb = 2206203922
        iodata_bsh_g24mb = 2206203923
        trendnet_tpe_3012ls = 2206210573
        trendnet_tpe_3018ls = 2206210574
        engenius_egs2108p_old_fw = 2206212360
        engenius_egs2110p_old_fw = 2206212368
        engenius_ews2910p_old_fw = 2206214416
        engenius_egs5110p_old_fw = 2206224656
        engenius_egs5212fp_old_fw = 2206224914
        engenius_ews5912fp_old_fw = 2206226706
        engenius_ews7928p_old_fw = 2206234920
        engenius_ews1200d_10t_old_fw = 2206670864
        engenius_ews1200_28t_old_fw = 2206670888
        engenius_egs7228fp_old_fw = 2206671503
        engenius_ews7928fp_old_fw = 2206700175
        realtek_rtl839x = 2207252480
        realtek_rtl8396 = 2207645696
        engenius_ews1200_52t_old_fw = 2207719506
        engenius_egs7252fp_old_fw = 2207720751
        engenius_ews7952fp_old_fw = 2207749423
        realtek_rtl930x = 2466250752
        zyxel_xgs1010_12 = 2466254864
        zyxel_xgs1210_12 = 2466255376
        zyxel_xgs1250_12 = 2466255440
        nicgiga_s100_0800s_m = 2466447360
        plasmacloud_psx28 = 2467299328

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
        mz = 9
        xip = 10

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
        elf = 29

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
        sunxi_toc0 = 41
        fdt_legacy = 42
        renesas_spkg = 43
        starfive_spl = 44
        tfa_bl31 = 45
        stm32image_v2 = 46
        amlimage = 47
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

    class AsusFirmwareInformation(KaitaiStruct):
        """ASUS firmware images [overlay the 32-byte image
        name](https://github.com/drag0njoe/RT-AC55U/blob/cf5874684ab6995ee07e91a52dfdd0562fcc2655/release/src/asustools/mkimage.src/include/image.h#L185-L188)
        with a [`TAIL`
        structure](https://github.com/drag0njoe/RT-AC55U/blob/cf5874684ab6995ee07e91a52dfdd0562fcc2655/release/src/asustools/mkimage.src/include/image.h#L151-L171)
        that contains version information and the product ID (model name).
        
        The first 16 bytes have the same structure in all three known variants of
        the `TAIL` structure. The meaning of the last 16 bytes differs across the
        variants - therefore, for simplicity, this Kaitai Struct implementation
        treats them as an opaque byte array named `extra_info`. For an overview of
        the variants, see the documentation for `extra_info`.
        """
        SEQ_FIELDS = ["kernel_version", "fs_version", "product_id", "extra_info"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Uimage.AsusFirmwareInformation, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['kernel_version']['start'] = self._io.pos()
            self.kernel_version = Uimage.Version(self._io, self, self._root)
            self.kernel_version._read()
            self._debug['kernel_version']['end'] = self._io.pos()
            self._debug['fs_version']['start'] = self._io.pos()
            self.fs_version = Uimage.Version(self._io, self, self._root)
            self.fs_version._read()
            self._debug['fs_version']['end'] = self._io.pos()
            self._debug['product_id']['start'] = self._io.pos()
            self.product_id = (KaitaiStream.bytes_terminate(self._io.read_bytes(12), 0, False)).decode(u"UTF-8")
            self._debug['product_id']['end'] = self._io.pos()
            self._debug['extra_info']['start'] = self._io.pos()
            self.extra_info = self._io.read_bytes(16)
            self._debug['extra_info']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.kernel_version._fetch_instances()
            self.fs_version._fetch_instances()


    class NameOrAsusInfo(KaitaiStruct):
        SEQ_FIELDS = ["name", "asus_info"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Uimage.NameOrAsusInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if (not (self.has_asus_info)):
                pass
                self._debug['name']['start'] = self._io.pos()
                self.name = (self._io.read_bytes_term(0, False, True, False)).decode(u"UTF-8")
                self._debug['name']['end'] = self._io.pos()

            if self.has_asus_info:
                pass
                self._debug['asus_info']['start'] = self._io.pos()
                self.asus_info = Uimage.AsusFirmwareInformation(self._io, self, self._root)
                self.asus_info._read()
                self._debug['asus_info']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if (not (self.has_asus_info)):
                pass

            if self.has_asus_info:
                pass
                self.asus_info._fetch_instances()

            _ = self.byte0
            if hasattr(self, '_m_byte0'):
                pass

            _ = self.byte4
            if hasattr(self, '_m_byte4'):
                pass


        @property
        def byte0(self):
            if hasattr(self, '_m_byte0'):
                return self._m_byte0

            _pos = self._io.pos()
            self._io.seek(0)
            self._debug['_m_byte0']['start'] = self._io.pos()
            self._m_byte0 = self._io.read_u1()
            self._debug['_m_byte0']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_byte0', None)

        @property
        def byte4(self):
            if hasattr(self, '_m_byte4'):
                return self._m_byte4

            _pos = self._io.pos()
            self._io.seek(4)
            self._debug['_m_byte4']['start'] = self._io.pos()
            self._m_byte4 = self._io.read_u1()
            self._debug['_m_byte4']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_byte4', None)

        @property
        def has_asus_info(self):
            """Whether this type stores ASUS firmware information (`asus_info`)
            rather than an image name (`name`).
            
            The header doesn't say which one it is, so we infer it using a
            heuristic based on the layout of the `asus_firmware_information` type.
            If ASUS firmware info is present, the first byte (the major kernel
            version number) is a small integer (i.e. not a printable character),
            and byte 4 (first byte of the product ID/model name) is a printable
            character. An empty name is not mistaken for ASUS information, because
            its byte 4 is a null byte.
            
            The highest known major kernel version number is 9 (e.g. in
            `DSL-N55U_9.0.0.4_380_3925-gad8f412_Annex_A.trx` from
            <https://dlcdnets.asus.com/pub/ASUS/wireless/DSL-N55U/FW_DSL_N55U_90043803925.zip>,
            released on 2016-08-04 and listed on
            <https://www.asus.com/supportonly/dsl-n55u/helpdesk_bios/>). ASUS
            seems to use such high major versions (9, sometimes 7) for beta
            releases, whereas regular releases use 3 (or 1 in older firmware).
            
            It can also be 0, in particular due to a bug in the MediaTek MT798X
            build of ASUS's `mkimage` (it reads the `-V` values from fixed `argv`
            positions, even though it parses the options using `getopt()` - see
            <https://github.com/blocktrron/tuf-ax4200-gpl/blob/a4fe37f4d78473f97c6d47cf93d97c3811af90cc/release/src-mtk-MT798X/Uboot-upstream/tools/mkimage.c#L317-L333>).
            For example, this is the case in
            `RT-AX52_3.0.0.4_388_34015-g9488655.trx` from
            <https://dlcdnets.asus.com/pub/ASUS/wireless/RT-AX52/FW_RT-AX52_300438834015.zip>,
            released on 2026-03-20 and listed on
            <https://www.asus.com/supportonly/rt-ax52/helpdesk_bios?model2Name=RT-AX52>.
            """
            if hasattr(self, '_m_has_asus_info'):
                return self._m_has_asus_info

            self._m_has_asus_info =  ((self.byte0 < 32) and (self.byte4 >= 32) and (self.byte4 < 127)) 
            return getattr(self, '_m_has_asus_info', None)


    class Uheader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "header_crc", "timestamp", "len_image", "load_address", "entry_address", "data_crc", "os_type", "architecture", "image_type", "compression_type", "name_or_asus_info"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Uimage.Uheader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = KaitaiStream.resolve_enum(Uimage.MagicTypes, self._io.read_u4be())
            self._debug['magic']['end'] = self._io.pos()
            if not isinstance(self.magic, Uimage.MagicTypes):
                raise kaitaistruct.ValidationNotInEnumError(self.magic, self._io, u"/types/uheader/seq/0")
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
            if not isinstance(self.os_type, Uimage.UimageOs):
                raise kaitaistruct.ValidationNotInEnumError(self.os_type, self._io, u"/types/uheader/seq/7")
            self._debug['architecture']['start'] = self._io.pos()
            self.architecture = KaitaiStream.resolve_enum(Uimage.UimageArch, self._io.read_u1())
            self._debug['architecture']['end'] = self._io.pos()
            if not isinstance(self.architecture, Uimage.UimageArch):
                raise kaitaistruct.ValidationNotInEnumError(self.architecture, self._io, u"/types/uheader/seq/8")
            self._debug['image_type']['start'] = self._io.pos()
            self.image_type = KaitaiStream.resolve_enum(Uimage.UimageType, self._io.read_u1())
            self._debug['image_type']['end'] = self._io.pos()
            if not isinstance(self.image_type, Uimage.UimageType):
                raise kaitaistruct.ValidationNotInEnumError(self.image_type, self._io, u"/types/uheader/seq/9")
            self._debug['compression_type']['start'] = self._io.pos()
            self.compression_type = KaitaiStream.resolve_enum(Uimage.UimageComp, self._io.read_u1())
            self._debug['compression_type']['end'] = self._io.pos()
            if not isinstance(self.compression_type, Uimage.UimageComp):
                raise kaitaistruct.ValidationNotInEnumError(self.compression_type, self._io, u"/types/uheader/seq/10")
            self._debug['name_or_asus_info']['start'] = self._io.pos()
            self._raw_name_or_asus_info = self._io.read_bytes(32)
            _io__raw_name_or_asus_info = KaitaiStream(BytesIO(self._raw_name_or_asus_info))
            self.name_or_asus_info = Uimage.NameOrAsusInfo(_io__raw_name_or_asus_info, self, self._root)
            self.name_or_asus_info._read()
            self._debug['name_or_asus_info']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name_or_asus_info._fetch_instances()


    class Version(KaitaiStruct):
        SEQ_FIELDS = ["major", "minor"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Uimage.Version, self).__init__(_io)
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



