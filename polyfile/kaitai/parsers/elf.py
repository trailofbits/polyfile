# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Elf(KaitaiStruct):
    """
    .. seealso::
       Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h
    
    
    .. seealso::
       Source - https://refspecs.linuxfoundation.org/elf/gabi4+/contents.html
    
    
    .. seealso::
       Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/elf-application-binary-interface.html
    """

    class Bits(IntEnum):
        b32 = 1
        b64 = 2

    class DynamicArrayTags(IntEnum):
        null = 0
        needed = 1
        pltrelsz = 2
        pltgot = 3
        hash = 4
        strtab = 5
        symtab = 6
        rela = 7
        relasz = 8
        relaent = 9
        strsz = 10
        syment = 11
        init = 12
        fini = 13
        soname = 14
        rpath = 15
        symbolic = 16
        rel = 17
        relsz = 18
        relent = 19
        pltrel = 20
        debug = 21
        textrel = 22
        jmprel = 23
        bind_now = 24
        init_array = 25
        fini_array = 26
        init_arraysz = 27
        fini_arraysz = 28
        runpath = 29
        flags = 30
        preinit_array = 32
        preinit_arraysz = 33
        symtab_shndx = 34
        relrsz = 35
        relr = 36
        relrent = 37
        deprecated_sparc_register = 117440513
        sunw_auxiliary = 1610612749
        sunw_rtldinf = 1610612750
        sunw_filter = 1610612751
        sunw_cap = 1610612752
        sunw_symtab = 1610612753
        sunw_symsz = 1610612754
        sunw_sortent = 1610612755
        sunw_symsort = 1610612756
        sunw_symsortsz = 1610612757
        sunw_tlssort = 1610612758
        sunw_tlssortsz = 1610612759
        sunw_capinfo = 1610612760
        sunw_strpad = 1610612761
        sunw_capchain = 1610612762
        sunw_ldmach = 1610612763
        sunw_symtab_shndx = 1610612764
        sunw_capchainent = 1610612765
        sunw_deferred = 1610612766
        sunw_capchainsz = 1610612767
        sunw_phname = 1610612768
        sunw_parent = 1610612769
        sunw_sx_aslr = 1610612771
        sunw_relax = 1610612773
        sunw_kmod = 1610612775
        sunw_sx_nxheap = 1610612777
        sunw_sx_nxstack = 1610612779
        sunw_sx_adiheap = 1610612781
        sunw_sx_adistack = 1610612783
        sunw_sx_ssbd = 1610612785
        sunw_symnsort = 1610612786
        sunw_symnsortsz = 1610612787
        gnu_flags_1 = 1879047668
        gnu_prelinked = 1879047669
        gnu_conflictsz = 1879047670
        gnu_liblistsz = 1879047671
        checksum = 1879047672
        pltpadsz = 1879047673
        moveent = 1879047674
        movesz = 1879047675
        feature_1 = 1879047676
        posflag_1 = 1879047677
        syminsz = 1879047678
        syminent = 1879047679
        gnu_hash = 1879047925
        tlsdesc_plt = 1879047926
        tlsdesc_got = 1879047927
        gnu_conflict = 1879047928
        gnu_liblist = 1879047929
        config = 1879047930
        depaudit = 1879047931
        audit = 1879047932
        pltpad = 1879047933
        movetab = 1879047934
        syminfo = 1879047935
        versym = 1879048176
        relacount = 1879048185
        relcount = 1879048186
        flags_1 = 1879048187
        verdef = 1879048188
        verdefnum = 1879048189
        verneed = 1879048190
        verneednum = 1879048191
        sparc_register = 1879048193
        auxiliary = 2147483645
        used = 2147483646
        filter = 2147483647

    class Endian(IntEnum):
        le = 1
        be = 2

    class Machine(IntEnum):
        no_machine = 0
        m32 = 1
        sparc = 2
        i386 = 3
        m68k = 4
        m88k = 5
        iamcu = 6
        i860 = 7
        mips = 8
        s370 = 9
        mips_rs3_le = 10
        old_sparc_v9 = 11
        parisc = 15
        vpp500 = 17
        sparc32plus = 18
        i960 = 19
        powerpc = 20
        powerpc64 = 21
        s390 = 22
        spu = 23
        v800 = 36
        fr20 = 37
        rh32 = 38
        mcore = 39
        arm = 40
        old_alpha = 41
        superh = 42
        sparc_v9 = 43
        tricore = 44
        arc = 45
        h8_300 = 46
        h8_300h = 47
        h8s = 48
        h8_500 = 49
        ia_64 = 50
        mips_x = 51
        coldfire = 52
        m68hc12 = 53
        mma = 54
        pcp = 55
        ncpu = 56
        ndr1 = 57
        starcore = 58
        me16 = 59
        st100 = 60
        tinyj = 61
        x86_64 = 62
        pdsp = 63
        pdp10 = 64
        pdp11 = 65
        fx66 = 66
        st9plus = 67
        st7 = 68
        m68hc16 = 69
        m68hc11 = 70
        m68hc08 = 71
        m68hc05 = 72
        svx = 73
        st19 = 74
        vax = 75
        cris = 76
        javelin = 77
        firepath = 78
        zsp = 79
        mmix = 80
        huany = 81
        prism = 82
        avr = 83
        fr30 = 84
        d10v = 85
        d30v = 86
        v850 = 87
        m32r = 88
        mn10300 = 89
        mn10200 = 90
        picojava = 91
        or1k = 92
        arc_compact = 93
        xtensa = 94
        videocore = 95
        tmm_gpp = 96
        ns32k = 97
        tpc = 98
        snp1k = 99
        st200 = 100
        ip2k = 101
        max = 102
        cr = 103
        f2mc16 = 104
        msp430 = 105
        blackfin = 106
        se_c33 = 107
        sep = 108
        arca = 109
        unicore = 110
        excess = 111
        dxp = 112
        altera_nios2 = 113
        crx = 114
        xgate = 115
        c166 = 116
        m16c = 117
        dspic30f = 118
        freescale_ce = 119
        m32c = 120
        tsk3000 = 131
        rs08 = 132
        sharc = 133
        ecog2 = 134
        score7 = 135
        dsp24 = 136
        videocore3 = 137
        latticemico32 = 138
        se_c17 = 139
        ti_c6000 = 140
        ti_c2000 = 141
        ti_c5500 = 142
        ti_arp32 = 143
        ti_pru = 144
        mmdsp_plus = 160
        cypress_m8c = 161
        r32c = 162
        trimedia = 163
        qdsp6 = 164
        i8051 = 165
        stxp7x = 166
        nds32 = 167
        ecog1x = 168
        maxq30 = 169
        ximo16 = 170
        manik = 171
        cray_nv2 = 172
        rx = 173
        metag = 174
        mcst_elbrus = 175
        ecog16 = 176
        cr16 = 177
        etpu = 178
        sle9x = 179
        l1om = 180
        k1om = 181
        intel182 = 182
        aarch64 = 183
        arm184 = 184
        avr32 = 185
        stm8 = 186
        tile64 = 187
        tilepro = 188
        microblaze = 189
        cuda = 190
        tilegx = 191
        cloudshield = 192
        corea_1st = 193
        corea_2nd = 194
        arc_compact2 = 195
        open8 = 196
        rl78 = 197
        videocore5 = 198
        renesas_78k0r = 199
        freescale_56800ex = 200
        ba1 = 201
        ba2 = 202
        xcore = 203
        mchp_pic = 204
        intelgt = 205
        intel206 = 206
        intel207 = 207
        intel208 = 208
        intel209 = 209
        km32 = 210
        kmx32 = 211
        kmx16 = 212
        kmx8 = 213
        kvarc = 214
        cdp = 215
        coge = 216
        cool = 217
        norc = 218
        csr_kalimba = 219
        z80 = 220
        visium = 221
        ft32 = 222
        moxie = 223
        amdgpu = 224
        riscv = 243
        lanai = 244
        ceva = 245
        ceva_x2 = 246
        bpf = 247
        graphcore_ipu = 248
        img1 = 249
        nfp = 250
        ve = 251
        csky = 252
        arc_compact3_64 = 253
        mcs6502 = 254
        arc_compact3 = 255
        kvx = 256
        wdc_65816 = 257
        loongarch = 258
        kf32 = 259
        u16_u8core = 260
        tachyum = 261
        nxp_56800ef = 262
        sbf = 263
        ai_engine = 264
        sima_mla = 265
        bang = 266
        loonggpu = 267
        sw64 = 268
        ai_engine_ctrlcode = 269
        ppu = 270
        avr_old = 4183
        msp430_old = 4185
        adapteva_epiphany = 4643
        mt = 9520
        cygnus_fr30 = 13104
        webassembly = 16727
        xc16x = 18056
        s12z = 19951
        cygnus_frv = 21569
        dlx = 23205
        cygnus_d10v = 30288
        cygnus_d30v = 30326
        ip2k_old = 33303
        cygnus_powerpc = 36901
        alpha = 36902
        cygnus_m32r = 36929
        cygnus_v850 = 36992
        s390_old = 41872
        xtensa_old = 43975
        xstormy16 = 44357
        microblaze_old = 47787
        cygnus_mn10300 = 48879
        cygnus_mn10200 = 57005
        cygnus_mep = 61453
        m32c_old = 65200
        iq2000 = 65210
        nios32 = 65211
        moxie_old = 65261

    class ObjType(IntEnum):
        no_file_type = 0
        relocatable = 1
        executable = 2
        shared = 3
        core = 4

    class OsAbi(IntEnum):
        system_v = 0
        hp_ux = 1
        netbsd = 2
        gnu = 3
        solaris = 6
        aix = 7
        irix = 8
        freebsd = 9
        tru64 = 10
        modesto = 11
        openbsd = 12
        openvms = 13
        nsk = 14
        aros = 15
        fenixos = 16
        cloudabi = 17
        openvos = 18
        cuda = 51
        arm_aeabi = 64
        arm_fdpic = 65
        amdgpu_mesa3d = 66
        arm = 97
        standalone = 255

    class PhType(IntEnum):
        null_type = 0
        load = 1
        dynamic = 2
        interp = 3
        note = 4
        shlib = 5
        phdr = 6
        tls = 7
        sunw_unwind = 1684333904
        gnu_eh_frame = 1685382480
        gnu_stack = 1685382481
        gnu_relro = 1685382482
        gnu_property = 1685382483
        gnu_sframe = 1685382484
        pax_flags = 1694766464
        openbsd_mutable = 1705237477
        openbsd_randomize = 1705237478
        openbsd_wxneeded = 1705237479
        openbsd_nobtcfi = 1705237480
        openbsd_syscalls = 1705237481
        openbsd_bootdata = 1705253862
        sunw_sysstat_zone = 1879048183
        sunw_sysstat = 1879048184
        sunw_reserve = 1879048185
        sunw_bss = 1879048186
        sunw_stack = 1879048187
        sunw_dtrace = 1879048188
        sunw_cap = 1879048189
        arm_archext = 1879048192
        arm_exidx = 1879048193
        aarch64_memtag_mte = 1879048194
        riscv_attributes = 1879048195

    class SectionHeaderIdxSpecial(IntEnum):
        undefined = 0
        before = 65280
        after = 65281
        amd64_lcommon = 65282
        sunw_ignore = 65343
        abs = 65521
        common = 65522
        xindex = 65535

    class ShType(IntEnum):
        null_type = 0
        progbits = 1
        symtab = 2
        strtab = 3
        rela = 4
        hash = 5
        dynamic = 6
        note = 7
        nobits = 8
        rel = 9
        shlib = 10
        dynsym = 11
        init_array = 14
        fini_array = 15
        preinit_array = 16
        group = 17
        symtab_shndx = 18
        relr = 19
        android_rel = 1610612737
        android_rela = 1610612738
        gnu_incremental_inputs = 1879000832
        llvm_odrtab = 1879002112
        llvm_linker_options = 1879002113
        llvm_addrsig = 1879002115
        llvm_dependent_libraries = 1879002116
        llvm_sympart = 1879002117
        llvm_part_ehdr = 1879002118
        llvm_part_phdr = 1879002119
        llvm_bb_addr_map_v0 = 1879002120
        llvm_call_graph_profile = 1879002121
        llvm_bb_addr_map = 1879002122
        llvm_offloading = 1879002123
        llvm_lto = 1879002124
        llvm_jt_sizes = 1879002125
        llvm_cfi_jump_table = 1879002126
        llvm_call_graph = 1879002127
        llvm_dyndbg_elf = 1879002128
        android_relr = 1879047936
        sunw_ctf = 1879048171
        sunw_symnsort = 1879048172
        sunw_phname = 1879048173
        sunw_ancillary = 1879048174
        sunw_capchain = 1879048175
        sunw_capinfo = 1879048176
        sunw_symsort = 1879048177
        sunw_tlssort = 1879048178
        sunw_ldynsym = 1879048179
        gnu_sframe = 1879048180
        gnu_attributes = 1879048181
        gnu_hash = 1879048182
        gnu_liblist = 1879048183
        checksum = 1879048184
        gnu_object_only = 1879048185
        sunw_move = 1879048186
        sunw_comdat = 1879048187
        sunw_syminfo = 1879048188
        gnu_verdef = 1879048189
        gnu_verneed = 1879048190
        gnu_versym = 1879048191
        sparc_gotdata = 1879048192
        x86_64_unwind = 1879048193
        arm_preemptmap = 1879048194
        arm_attributes = 1879048195
        arm_debugoverlay = 1879048196
        arm_overlaysection = 1879048197
        aarch64_memtag_globals_static = 1879048199
        aarch64_memtag_globals_dynamic = 1879048200

    class SymbolBinding(IntEnum):
        local = 0
        global_symbol = 1
        weak = 2
        os10 = 10
        os11 = 11
        os12 = 12
        proc13 = 13
        proc14 = 14
        proc15 = 15

    class SymbolType(IntEnum):
        no_type = 0
        object = 1
        func = 2
        section = 3
        file = 4
        common = 5
        tls = 6
        relc = 8
        srelc = 9
        gnu_ifunc = 10
        os11 = 11
        os12 = 12
        proc13 = 13
        proc14 = 14
        proc15 = 15

    class SymbolVisibility(IntEnum):
        default = 0
        internal = 1
        hidden = 2
        protected = 3
        exported = 4
        singleton = 5
        eliminate = 6

    class VersionIndexSpecial(IntEnum):
        local = 0
        global_symbol = 1
        eliminate = 65281
    SEQ_FIELDS = ["magic", "bits", "endian", "ei_version", "abi", "abi_version", "pad", "header"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Elf, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x7F\x45\x4C\x46":
            raise kaitaistruct.ValidationNotEqualError(b"\x7F\x45\x4C\x46", self.magic, self._io, u"/seq/0")
        self._debug['bits']['start'] = self._io.pos()
        self.bits = KaitaiStream.resolve_enum(Elf.Bits, self._io.read_u1())
        self._debug['bits']['end'] = self._io.pos()
        self._debug['endian']['start'] = self._io.pos()
        self.endian = KaitaiStream.resolve_enum(Elf.Endian, self._io.read_u1())
        self._debug['endian']['end'] = self._io.pos()
        self._debug['ei_version']['start'] = self._io.pos()
        self.ei_version = self._io.read_u1()
        self._debug['ei_version']['end'] = self._io.pos()
        if not self.ei_version == 1:
            raise kaitaistruct.ValidationNotEqualError(1, self.ei_version, self._io, u"/seq/3")
        self._debug['abi']['start'] = self._io.pos()
        self.abi = KaitaiStream.resolve_enum(Elf.OsAbi, self._io.read_u1())
        self._debug['abi']['end'] = self._io.pos()
        self._debug['abi_version']['start'] = self._io.pos()
        self.abi_version = self._io.read_u1()
        self._debug['abi_version']['end'] = self._io.pos()
        self._debug['pad']['start'] = self._io.pos()
        self.pad = self._io.read_bytes(7)
        self._debug['pad']['end'] = self._io.pos()
        if not self.pad == b"\x00\x00\x00\x00\x00\x00\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00\x00\x00\x00\x00", self.pad, self._io, u"/seq/6")
        self._debug['header']['start'] = self._io.pos()
        self.header = Elf.EndianElf(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()

    class DtFlag1Values(KaitaiStruct):
        """
        .. seealso::
           Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L1008
        
        
        .. seealso::
           Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html#GUID-4336A69A-D905-4FCE-A398-80375A9E6464__CHAPTER6-TBL-53
        """
        SEQ_FIELDS = []
        def __init__(self, value, _io, _parent=None, _root=None):
            super(Elf.DtFlag1Values, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.value = value
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass

        @property
        def conf_alt(self):
            """Configuration alternative created.
            
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L1023
            """
            if hasattr(self, '_m_conf_alt'):
                return self._m_conf_alt

            self._m_conf_alt = self.value & 8192 != 0
            return getattr(self, '_m_conf_alt', None)

        @property
        def direct(self):
            """Direct binding enabled."""
            if hasattr(self, '_m_direct'):
                return self._m_direct

            self._m_direct = self.value & 256 != 0
            return getattr(self, '_m_direct', None)

        @property
        def disp_rel_dne(self):
            """Displacement relocation done (applied at build time)."""
            if hasattr(self, '_m_disp_rel_dne'):
                return self._m_disp_rel_dne

            self._m_disp_rel_dne = self.value & 32768 != 0
            return getattr(self, '_m_disp_rel_dne', None)

        @property
        def disp_rel_pnd(self):
            """Displacement relocation pending (applied at runtime)."""
            if hasattr(self, '_m_disp_rel_pnd'):
                return self._m_disp_rel_pnd

            self._m_disp_rel_pnd = self.value & 65536 != 0
            return getattr(self, '_m_disp_rel_pnd', None)

        @property
        def edited(self):
            """Object is modified after built."""
            if hasattr(self, '_m_edited'):
                return self._m_edited

            self._m_edited = self.value & 2097152 != 0
            return getattr(self, '_m_edited', None)

        @property
        def end_filtee(self):
            """Filtee terminates filters search."""
            if hasattr(self, '_m_end_filtee'):
                return self._m_end_filtee

            self._m_end_filtee = self.value & 16384 != 0
            return getattr(self, '_m_end_filtee', None)

        @property
        def glob_audit(self):
            """Global auditing required."""
            if hasattr(self, '_m_glob_audit'):
                return self._m_glob_audit

            self._m_glob_audit = self.value & 16777216 != 0
            return getattr(self, '_m_glob_audit', None)

        @property
        def group(self):
            """Set `RTLD_GROUP` for this object."""
            if hasattr(self, '_m_group'):
                return self._m_group

            self._m_group = self.value & 4 != 0
            return getattr(self, '_m_group', None)

        @property
        def ign_mul_def(self):
            if hasattr(self, '_m_ign_mul_def'):
                return self._m_ign_mul_def

            self._m_ign_mul_def = self.value & 262144 != 0
            return getattr(self, '_m_ign_mul_def', None)

        @property
        def init_first(self):
            """Set `RTLD_INITFIRST` for this object."""
            if hasattr(self, '_m_init_first'):
                return self._m_init_first

            self._m_init_first = self.value & 32 != 0
            return getattr(self, '_m_init_first', None)

        @property
        def interpose(self):
            """Object is used to interpose."""
            if hasattr(self, '_m_interpose'):
                return self._m_interpose

            self._m_interpose = self.value & 1024 != 0
            return getattr(self, '_m_interpose', None)

        @property
        def kmod(self):
            """Object is a kernel module."""
            if hasattr(self, '_m_kmod'):
                return self._m_kmod

            self._m_kmod = self.value & 268435456 != 0
            return getattr(self, '_m_kmod', None)

        @property
        def load_fltr(self):
            """Trigger filtee loading at runtime."""
            if hasattr(self, '_m_load_fltr'):
                return self._m_load_fltr

            self._m_load_fltr = self.value & 16 != 0
            return getattr(self, '_m_load_fltr', None)

        @property
        def no_common(self):
            """No COMMON symbols exist.
            
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L1040
            """
            if hasattr(self, '_m_no_common'):
                return self._m_no_common

            self._m_no_common = self.value & 1073741824 != 0
            return getattr(self, '_m_no_common', None)

        @property
        def no_def_lib(self):
            """Ignore the default library search path."""
            if hasattr(self, '_m_no_def_lib'):
                return self._m_no_def_lib

            self._m_no_def_lib = self.value & 2048 != 0
            return getattr(self, '_m_no_def_lib', None)

        @property
        def no_delete(self):
            """Set `RTLD_NODELETE` for this object."""
            if hasattr(self, '_m_no_delete'):
                return self._m_no_delete

            self._m_no_delete = self.value & 8 != 0
            return getattr(self, '_m_no_delete', None)

        @property
        def no_direct(self):
            """Object contains non-direct bindings."""
            if hasattr(self, '_m_no_direct'):
                return self._m_no_direct

            self._m_no_direct = self.value & 131072 != 0
            return getattr(self, '_m_no_direct', None)

        @property
        def no_dump(self):
            """Object can't be dldump'ed."""
            if hasattr(self, '_m_no_dump'):
                return self._m_no_dump

            self._m_no_dump = self.value & 4096 != 0
            return getattr(self, '_m_no_dump', None)

        @property
        def no_hdr(self):
            if hasattr(self, '_m_no_hdr'):
                return self._m_no_hdr

            self._m_no_hdr = self.value & 1048576 != 0
            return getattr(self, '_m_no_hdr', None)

        @property
        def no_ksyms(self):
            if hasattr(self, '_m_no_ksyms'):
                return self._m_no_ksyms

            self._m_no_ksyms = self.value & 524288 != 0
            return getattr(self, '_m_no_ksyms', None)

        @property
        def no_open(self):
            """Set `RTLD_NOOPEN` for this object."""
            if hasattr(self, '_m_no_open'):
                return self._m_no_open

            self._m_no_open = self.value & 64 != 0
            return getattr(self, '_m_no_open', None)

        @property
        def no_reloc(self):
            if hasattr(self, '_m_no_reloc'):
                return self._m_no_reloc

            self._m_no_reloc = self.value & 4194304 != 0
            return getattr(self, '_m_no_reloc', None)

        @property
        def now(self):
            """Set `RTLD_NOW` for this object."""
            if hasattr(self, '_m_now'):
                return self._m_now

            self._m_now = self.value & 1 != 0
            return getattr(self, '_m_now', None)

        @property
        def origin(self):
            """`$ORIGIN` must be handled.
            """
            if hasattr(self, '_m_origin'):
                return self._m_origin

            self._m_origin = self.value & 128 != 0
            return getattr(self, '_m_origin', None)

        @property
        def pie(self):
            """Object is a Position Independent Executable (PIE)."""
            if hasattr(self, '_m_pie'):
                return self._m_pie

            self._m_pie = self.value & 134217728 != 0
            return getattr(self, '_m_pie', None)

        @property
        def rtld_global(self):
            """Set `RTLD_GLOBAL` for this object."""
            if hasattr(self, '_m_rtld_global'):
                return self._m_rtld_global

            self._m_rtld_global = self.value & 2 != 0
            return getattr(self, '_m_rtld_global', None)

        @property
        def singleton(self):
            """Singleton symbols are used."""
            if hasattr(self, '_m_singleton'):
                return self._m_singleton

            self._m_singleton = self.value & 33554432 != 0
            return getattr(self, '_m_singleton', None)

        @property
        def stub(self):
            """Object is a stub.
            See [Stub Objects](https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/stub-objects.html).
            """
            if hasattr(self, '_m_stub'):
                return self._m_stub

            self._m_stub = self.value & 67108864 != 0
            return getattr(self, '_m_stub', None)

        @property
        def sym_intpose(self):
            """Object has individual symbol interposers."""
            if hasattr(self, '_m_sym_intpose'):
                return self._m_sym_intpose

            self._m_sym_intpose = self.value & 8388608 != 0
            return getattr(self, '_m_sym_intpose', None)

        @property
        def trans(self):
            """
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L1019
            """
            if hasattr(self, '_m_trans'):
                return self._m_trans

            self._m_trans = self.value & 512 != 0
            return getattr(self, '_m_trans', None)

        @property
        def weak_filter(self):
            """Object is a weak standard filter."""
            if hasattr(self, '_m_weak_filter'):
                return self._m_weak_filter

            self._m_weak_filter = self.value & 536870912 != 0
            return getattr(self, '_m_weak_filter', None)


    class DtFlagValues(KaitaiStruct):
        """
        .. seealso::
           Figure 5-11: DT_FLAGS values - https://refspecs.linuxbase.org/elf/gabi4+/ch5.dynamic.html
        
        
        .. seealso::
           Source - https://github.com/golang/go/blob/48dfddbab3/src/debug/elf/elf.go#L1079-L1095
        
        
        .. seealso::
           Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html#GUID-4336A69A-D905-4FCE-A398-80375A9E6464__CHAPTER7-TBL-5
        """
        SEQ_FIELDS = []
        def __init__(self, value, _io, _parent=None, _root=None):
            super(Elf.DtFlagValues, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.value = value
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass

        @property
        def bind_now(self):
            """all relocations for this object must be processed before returning
            control to the program
            """
            if hasattr(self, '_m_bind_now'):
                return self._m_bind_now

            self._m_bind_now = self.value & 8 != 0
            return getattr(self, '_m_bind_now', None)

        @property
        def origin(self):
            """object may reference the $ORIGIN substitution string."""
            if hasattr(self, '_m_origin'):
                return self._m_origin

            self._m_origin = self.value & 1 != 0
            return getattr(self, '_m_origin', None)

        @property
        def static_tls(self):
            """object uses static thread-local storage scheme."""
            if hasattr(self, '_m_static_tls'):
                return self._m_static_tls

            self._m_static_tls = self.value & 16 != 0
            return getattr(self, '_m_static_tls', None)

        @property
        def symbolic(self):
            """symbolic linking."""
            if hasattr(self, '_m_symbolic'):
                return self._m_symbolic

            self._m_symbolic = self.value & 2 != 0
            return getattr(self, '_m_symbolic', None)

        @property
        def textrel(self):
            """relocation entries might request modifications to a non-writable segment."""
            if hasattr(self, '_m_textrel'):
                return self._m_textrel

            self._m_textrel = self.value & 4 != 0
            return getattr(self, '_m_textrel', None)


    class EndianElf(KaitaiStruct):
        """
        .. seealso::
           Source - https://gabi.xinuos.com/v42/elf/02-eheader.html
        
        
        .. seealso::
           Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/elf-header.html
        """
        SEQ_FIELDS = ["e_type", "machine", "e_version", "entry_point", "ofs_program_headers", "ofs_section_headers", "flags", "e_ehsize", "program_header_size", "num_program_headers", "section_header_size", "num_section_headers", "section_names_idx"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Elf.EndianElf, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            _on = self._root.endian
            if _on == Elf.Endian.le:
                pass
                self._is_le = True
            elif _on == Elf.Endian.be:
                pass
                self._is_le = False
            if not hasattr(self, '_is_le'):
                raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf")
            elif self._is_le == True:
                self._read_le()
            elif self._is_le == False:
                self._read_be()

        def _read_le(self):
            self._debug['e_type']['start'] = self._io.pos()
            self.e_type = KaitaiStream.resolve_enum(Elf.ObjType, self._io.read_u2le())
            self._debug['e_type']['end'] = self._io.pos()
            self._debug['machine']['start'] = self._io.pos()
            self.machine = KaitaiStream.resolve_enum(Elf.Machine, self._io.read_u2le())
            self._debug['machine']['end'] = self._io.pos()
            if not isinstance(self.machine, Elf.Machine):
                raise kaitaistruct.ValidationNotInEnumError(self.machine, self._io, u"/types/endian_elf/seq/1")
            self._debug['e_version']['start'] = self._io.pos()
            self.e_version = self._io.read_u4le()
            self._debug['e_version']['end'] = self._io.pos()
            self._debug['entry_point']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.entry_point = self._io.read_u4le()
            elif _on == Elf.Bits.b64:
                pass
                self.entry_point = self._io.read_u8le()
            self._debug['entry_point']['end'] = self._io.pos()
            self._debug['ofs_program_headers']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.ofs_program_headers = self._io.read_u4le()
            elif _on == Elf.Bits.b64:
                pass
                self.ofs_program_headers = self._io.read_u8le()
            self._debug['ofs_program_headers']['end'] = self._io.pos()
            self._debug['ofs_section_headers']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.ofs_section_headers = self._io.read_u4le()
            elif _on == Elf.Bits.b64:
                pass
                self.ofs_section_headers = self._io.read_u8le()
            self._debug['ofs_section_headers']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_bytes(4)
            self._debug['flags']['end'] = self._io.pos()
            self._debug['e_ehsize']['start'] = self._io.pos()
            self.e_ehsize = self._io.read_u2le()
            self._debug['e_ehsize']['end'] = self._io.pos()
            self._debug['program_header_size']['start'] = self._io.pos()
            self.program_header_size = self._io.read_u2le()
            self._debug['program_header_size']['end'] = self._io.pos()
            self._debug['num_program_headers']['start'] = self._io.pos()
            self.num_program_headers = self._io.read_u2le()
            self._debug['num_program_headers']['end'] = self._io.pos()
            self._debug['section_header_size']['start'] = self._io.pos()
            self.section_header_size = self._io.read_u2le()
            self._debug['section_header_size']['end'] = self._io.pos()
            self._debug['num_section_headers']['start'] = self._io.pos()
            self.num_section_headers = self._io.read_u2le()
            self._debug['num_section_headers']['end'] = self._io.pos()
            self._debug['section_names_idx']['start'] = self._io.pos()
            self.section_names_idx = self._io.read_u2le()
            self._debug['section_names_idx']['end'] = self._io.pos()

        def _read_be(self):
            self._debug['e_type']['start'] = self._io.pos()
            self.e_type = KaitaiStream.resolve_enum(Elf.ObjType, self._io.read_u2be())
            self._debug['e_type']['end'] = self._io.pos()
            self._debug['machine']['start'] = self._io.pos()
            self.machine = KaitaiStream.resolve_enum(Elf.Machine, self._io.read_u2be())
            self._debug['machine']['end'] = self._io.pos()
            if not isinstance(self.machine, Elf.Machine):
                raise kaitaistruct.ValidationNotInEnumError(self.machine, self._io, u"/types/endian_elf/seq/1")
            self._debug['e_version']['start'] = self._io.pos()
            self.e_version = self._io.read_u4be()
            self._debug['e_version']['end'] = self._io.pos()
            self._debug['entry_point']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.entry_point = self._io.read_u4be()
            elif _on == Elf.Bits.b64:
                pass
                self.entry_point = self._io.read_u8be()
            self._debug['entry_point']['end'] = self._io.pos()
            self._debug['ofs_program_headers']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.ofs_program_headers = self._io.read_u4be()
            elif _on == Elf.Bits.b64:
                pass
                self.ofs_program_headers = self._io.read_u8be()
            self._debug['ofs_program_headers']['end'] = self._io.pos()
            self._debug['ofs_section_headers']['start'] = self._io.pos()
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
                self.ofs_section_headers = self._io.read_u4be()
            elif _on == Elf.Bits.b64:
                pass
                self.ofs_section_headers = self._io.read_u8be()
            self._debug['ofs_section_headers']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_bytes(4)
            self._debug['flags']['end'] = self._io.pos()
            self._debug['e_ehsize']['start'] = self._io.pos()
            self.e_ehsize = self._io.read_u2be()
            self._debug['e_ehsize']['end'] = self._io.pos()
            self._debug['program_header_size']['start'] = self._io.pos()
            self.program_header_size = self._io.read_u2be()
            self._debug['program_header_size']['end'] = self._io.pos()
            self._debug['num_program_headers']['start'] = self._io.pos()
            self.num_program_headers = self._io.read_u2be()
            self._debug['num_program_headers']['end'] = self._io.pos()
            self._debug['section_header_size']['start'] = self._io.pos()
            self.section_header_size = self._io.read_u2be()
            self._debug['section_header_size']['end'] = self._io.pos()
            self._debug['num_section_headers']['start'] = self._io.pos()
            self.num_section_headers = self._io.read_u2be()
            self._debug['num_section_headers']['end'] = self._io.pos()
            self._debug['section_names_idx']['start'] = self._io.pos()
            self.section_names_idx = self._io.read_u2be()
            self._debug['section_names_idx']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
            elif _on == Elf.Bits.b64:
                pass
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
            elif _on == Elf.Bits.b64:
                pass
            _on = self._root.bits
            if _on == Elf.Bits.b32:
                pass
            elif _on == Elf.Bits.b64:
                pass
            _ = self.program_headers
            if hasattr(self, '_m_program_headers'):
                pass
                for i in range(len(self._m_program_headers)):
                    pass
                    self._m_program_headers[i]._fetch_instances()


            _ = self.section_headers
            if hasattr(self, '_m_section_headers'):
                pass
                for i in range(len(self._m_section_headers)):
                    pass
                    self._m_section_headers[i]._fetch_instances()


            _ = self.section_names
            if hasattr(self, '_m_section_names'):
                pass
                self._m_section_names._fetch_instances()


        class DynsymSection(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.DynsymSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/dynsym_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.DynsymSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        self.entries.append(_t_entries)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.DynsymSectionEntry(self._io, self, self._root, self._is_le)
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


            @property
            def is_string_table_linked(self):
                if hasattr(self, '_m_is_string_table_linked'):
                    return self._m_is_string_table_linked

                self._m_is_string_table_linked = self._parent.linked_section.type == Elf.ShType.strtab
                return getattr(self, '_m_is_string_table_linked', None)


        class DynsymSectionEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://gabi.xinuos.com/elf/05-symtab.html
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/symbol-table-section.html
            """
            SEQ_FIELDS = ["ofs_name", "value_b32", "size_b32", "bind", "type", "other", "sh_idx", "value_b64", "size_b64"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.DynsymSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/dynsym_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4le()
                self._debug['ofs_name']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['value_b32']['start'] = self._io.pos()
                    self.value_b32 = self._io.read_u4le()
                    self._debug['value_b32']['end'] = self._io.pos()

                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['size_b32']['start'] = self._io.pos()
                    self.size_b32 = self._io.read_u4le()
                    self._debug['size_b32']['end'] = self._io.pos()

                self._debug['bind']['start'] = self._io.pos()
                self.bind = KaitaiStream.resolve_enum(Elf.SymbolBinding, self._io.read_bits_int_be(4))
                self._debug['bind']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.SymbolType, self._io.read_bits_int_be(4))
                self._debug['type']['end'] = self._io.pos()
                self._debug['other']['start'] = self._io.pos()
                self.other = self._io.read_u1()
                self._debug['other']['end'] = self._io.pos()
                self._debug['sh_idx']['start'] = self._io.pos()
                self.sh_idx = self._io.read_u2le()
                self._debug['sh_idx']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['value_b64']['start'] = self._io.pos()
                    self.value_b64 = self._io.read_u8le()
                    self._debug['value_b64']['end'] = self._io.pos()

                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['size_b64']['start'] = self._io.pos()
                    self.size_b64 = self._io.read_u8le()
                    self._debug['size_b64']['end'] = self._io.pos()


            def _read_be(self):
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4be()
                self._debug['ofs_name']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['value_b32']['start'] = self._io.pos()
                    self.value_b32 = self._io.read_u4be()
                    self._debug['value_b32']['end'] = self._io.pos()

                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['size_b32']['start'] = self._io.pos()
                    self.size_b32 = self._io.read_u4be()
                    self._debug['size_b32']['end'] = self._io.pos()

                self._debug['bind']['start'] = self._io.pos()
                self.bind = KaitaiStream.resolve_enum(Elf.SymbolBinding, self._io.read_bits_int_be(4))
                self._debug['bind']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.SymbolType, self._io.read_bits_int_be(4))
                self._debug['type']['end'] = self._io.pos()
                self._debug['other']['start'] = self._io.pos()
                self.other = self._io.read_u1()
                self._debug['other']['end'] = self._io.pos()
                self._debug['sh_idx']['start'] = self._io.pos()
                self.sh_idx = self._io.read_u2be()
                self._debug['sh_idx']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['value_b64']['start'] = self._io.pos()
                    self.value_b64 = self._io.read_u8be()
                    self._debug['value_b64']['end'] = self._io.pos()

                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['size_b64']['start'] = self._io.pos()
                    self.size_b64 = self._io.read_u8be()
                    self._debug['size_b64']['end'] = self._io.pos()



            def _fetch_instances(self):
                pass
                if self._root.bits == Elf.Bits.b32:
                    pass

                if self._root.bits == Elf.Bits.b32:
                    pass

                if self._root.bits == Elf.Bits.b64:
                    pass

                if self._root.bits == Elf.Bits.b64:
                    pass

                _ = self.name
                if hasattr(self, '_m_name'):
                    pass


            @property
            def is_sh_idx_os(self):
                if hasattr(self, '_m_is_sh_idx_os'):
                    return self._m_is_sh_idx_os

                self._m_is_sh_idx_os =  ((self.sh_idx >= self._root.sh_idx_lo_os) and (self.sh_idx <= self._root.sh_idx_hi_os)) 
                return getattr(self, '_m_is_sh_idx_os', None)

            @property
            def is_sh_idx_proc(self):
                if hasattr(self, '_m_is_sh_idx_proc'):
                    return self._m_is_sh_idx_proc

                self._m_is_sh_idx_proc =  ((self.sh_idx >= self._root.sh_idx_lo_proc) and (self.sh_idx <= self._root.sh_idx_hi_proc)) 
                return getattr(self, '_m_is_sh_idx_proc', None)

            @property
            def is_sh_idx_reserved(self):
                if hasattr(self, '_m_is_sh_idx_reserved'):
                    return self._m_is_sh_idx_reserved

                self._m_is_sh_idx_reserved =  ((self.sh_idx >= self._root.sh_idx_lo_reserved) and (self.sh_idx <= self._root.sh_idx_hi_reserved)) 
                return getattr(self, '_m_is_sh_idx_reserved', None)

            @property
            def name(self):
                if hasattr(self, '_m_name'):
                    return self._m_name

                if  ((self.ofs_name != 0) and (self._parent.is_string_table_linked)) :
                    pass
                    io = self._parent._parent.linked_section.body._io
                    _pos = io.pos()
                    io.seek(self.ofs_name)
                    if self._is_le:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    else:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_name', None)

            @property
            def sh_idx_special(self):
                if hasattr(self, '_m_sh_idx_special'):
                    return self._m_sh_idx_special

                self._m_sh_idx_special = KaitaiStream.resolve_enum(Elf.SectionHeaderIdxSpecial, self.sh_idx)
                return getattr(self, '_m_sh_idx_special', None)

            @property
            def size(self):
                if hasattr(self, '_m_size'):
                    return self._m_size

                self._m_size = (self.size_b32 if self._root.bits == Elf.Bits.b32 else (self.size_b64 if self._root.bits == Elf.Bits.b64 else 0))
                return getattr(self, '_m_size', None)

            @property
            def value(self):
                if hasattr(self, '_m_value'):
                    return self._m_value

                self._m_value = (self.value_b32 if self._root.bits == Elf.Bits.b32 else (self.value_b64 if self._root.bits == Elf.Bits.b64 else 0))
                return getattr(self, '_m_value', None)

            @property
            def visibility(self):
                """
                .. seealso::
                   Source - https://github.com/xinuos/gabi/commit/acd5ebb2962cf243dca4983bc934442b42ef96f5
                """
                if hasattr(self, '_m_visibility'):
                    return self._m_visibility

                self._m_visibility = KaitaiStream.resolve_enum(Elf.SymbolVisibility, self.other & 7)
                return getattr(self, '_m_visibility', None)


        class NoteSection(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.NoteSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/note_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.NoteSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        self.entries.append(_t_entries)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.NoteSectionEntry(self._io, self, self._root, self._is_le)
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



        class NoteSectionEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/note-section.html
            
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/elf/gabi4+/ch5.pheader.html#note_section
            """
            SEQ_FIELDS = ["len_name", "len_descriptor", "type", "name", "name_padding", "descriptor", "descriptor_padding"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.NoteSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/note_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['len_name']['start'] = self._io.pos()
                self.len_name = self._io.read_u4le()
                self._debug['len_name']['end'] = self._io.pos()
                self._debug['len_descriptor']['start'] = self._io.pos()
                self.len_descriptor = self._io.read_u4le()
                self._debug['len_descriptor']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = self._io.read_u4le()
                self._debug['type']['end'] = self._io.pos()
                self._debug['name']['start'] = self._io.pos()
                self.name = KaitaiStream.bytes_terminate(self._io.read_bytes(self.len_name), 0, False)
                self._debug['name']['end'] = self._io.pos()
                self._debug['name_padding']['start'] = self._io.pos()
                self.name_padding = self._io.read_bytes(-(self.len_name) % 4)
                self._debug['name_padding']['end'] = self._io.pos()
                self._debug['descriptor']['start'] = self._io.pos()
                self.descriptor = self._io.read_bytes(self.len_descriptor)
                self._debug['descriptor']['end'] = self._io.pos()
                self._debug['descriptor_padding']['start'] = self._io.pos()
                self.descriptor_padding = self._io.read_bytes(-(self.len_descriptor) % 4)
                self._debug['descriptor_padding']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['len_name']['start'] = self._io.pos()
                self.len_name = self._io.read_u4be()
                self._debug['len_name']['end'] = self._io.pos()
                self._debug['len_descriptor']['start'] = self._io.pos()
                self.len_descriptor = self._io.read_u4be()
                self._debug['len_descriptor']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = self._io.read_u4be()
                self._debug['type']['end'] = self._io.pos()
                self._debug['name']['start'] = self._io.pos()
                self.name = KaitaiStream.bytes_terminate(self._io.read_bytes(self.len_name), 0, False)
                self._debug['name']['end'] = self._io.pos()
                self._debug['name_padding']['start'] = self._io.pos()
                self.name_padding = self._io.read_bytes(-(self.len_name) % 4)
                self._debug['name_padding']['end'] = self._io.pos()
                self._debug['descriptor']['start'] = self._io.pos()
                self.descriptor = self._io.read_bytes(self.len_descriptor)
                self._debug['descriptor']['end'] = self._io.pos()
                self._debug['descriptor_padding']['start'] = self._io.pos()
                self.descriptor_padding = self._io.read_bytes(-(self.len_descriptor) % 4)
                self._debug['descriptor_padding']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class PhDynamicSection(KaitaiStruct):
            """Same type as `sh_dynamic_section`, but it does not use
            `_parent.linked_section`, which is available only in section headers
            (i.e. when `_parent` is of type `section_header`). This allows it to
            be used in program headers (i.e. from the `program_header` type).
            
            The inability to access `linked_section` means that offsets in the
            string table (which should be stored in the `.dynstr` section) will
            not be resolved to strings and will be provided only in raw form in
            the `value_or_ptr` field. In other words, the
            `ph_dynamic_section_entry` type has no `value_str` instance, unlike
            the `sh_dynamic_section_entry` type.
            
            There is another way to find the string table referenced by the
            dynamic section entries that does not rely on `linked_section`, but is
            a bit more complex (and is therefore considered out of scope of this
            .ksy spec): the mandatory dynamic tag `dynamic_array_tags::strtab`
            (`DT_STRTAB`) specifies the virtual address of the string table, and
            `dynamic_array_tags::strsz` (`DT_STRSZ`) specifies its size in bytes.
            The virtual address can be converted to a file offset by reading the
            program headers - see the source code for the `readelf` command:
            
            1. [`offset_from_vma` call site with an address from `DT_STRTAB` as an
              argument](https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/binutils/readelf.c#L13018)
            2. [`offset_from_vma` function
              definition](https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/binutils/readelf.c#L7788)
            
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/08-dynamic.html#dynamic-section
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html
            """
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.PhDynamicSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/ph_dynamic_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while True:
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.PhDynamicSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        _ = _t_entries
                        self.entries.append(_)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    if _.tag_enum == Elf.DynamicArrayTags.null:
                        break
                    i += 1
                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while True:
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.PhDynamicSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        _ = _t_entries
                        self.entries.append(_)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    if _.tag_enum == Elf.DynamicArrayTags.null:
                        break
                    i += 1
                self._debug['entries']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.entries)):
                    pass
                    self.entries[i]._fetch_instances()



        class PhDynamicSectionEntry(KaitaiStruct):
            """Same type as `sh_dynamic_section_entry`, but without the `value_str`
            instance - see the documentation for `ph_dynamic_section` for more
            details.
            
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/08-dynamic.html#dynamic-section
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html
            """
            SEQ_FIELDS = ["tag", "value_or_ptr"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.PhDynamicSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/ph_dynamic_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['tag']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.tag = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.tag = self._io.read_u8le()
                self._debug['tag']['end'] = self._io.pos()
                self._debug['value_or_ptr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.value_or_ptr = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.value_or_ptr = self._io.read_u8le()
                self._debug['value_or_ptr']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['tag']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.tag = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.tag = self._io.read_u8be()
                self._debug['tag']['end'] = self._io.pos()
                self._debug['value_or_ptr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.value_or_ptr = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.value_or_ptr = self._io.read_u8be()
                self._debug['value_or_ptr']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _ = self.flag_1_values
                if hasattr(self, '_m_flag_1_values'):
                    pass
                    self._m_flag_1_values._fetch_instances()

                _ = self.flag_values
                if hasattr(self, '_m_flag_values'):
                    pass
                    self._m_flag_values._fetch_instances()


            @property
            def flag_1_values(self):
                if hasattr(self, '_m_flag_1_values'):
                    return self._m_flag_1_values

                if self.tag_enum == Elf.DynamicArrayTags.flags_1:
                    pass
                    if self._is_le:
                        self._debug['_m_flag_1_values']['start'] = self._io.pos()
                        self._m_flag_1_values = Elf.DtFlag1Values(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_1_values._read()
                        self._debug['_m_flag_1_values']['end'] = self._io.pos()
                    else:
                        self._debug['_m_flag_1_values']['start'] = self._io.pos()
                        self._m_flag_1_values = Elf.DtFlag1Values(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_1_values._read()
                        self._debug['_m_flag_1_values']['end'] = self._io.pos()

                return getattr(self, '_m_flag_1_values', None)

            @property
            def flag_values(self):
                if hasattr(self, '_m_flag_values'):
                    return self._m_flag_values

                if self.tag_enum == Elf.DynamicArrayTags.flags:
                    pass
                    if self._is_le:
                        self._debug['_m_flag_values']['start'] = self._io.pos()
                        self._m_flag_values = Elf.DtFlagValues(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_values._read()
                        self._debug['_m_flag_values']['end'] = self._io.pos()
                    else:
                        self._debug['_m_flag_values']['start'] = self._io.pos()
                        self._m_flag_values = Elf.DtFlagValues(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_values._read()
                        self._debug['_m_flag_values']['end'] = self._io.pos()

                return getattr(self, '_m_flag_values', None)

            @property
            def is_value_str(self):
                if hasattr(self, '_m_is_value_str'):
                    return self._m_is_value_str

                self._m_is_value_str =  ((self.value_or_ptr != 0) and ( ((self.tag_enum == Elf.DynamicArrayTags.needed) or (self.tag_enum == Elf.DynamicArrayTags.soname) or (self.tag_enum == Elf.DynamicArrayTags.rpath) or (self.tag_enum == Elf.DynamicArrayTags.runpath) or (self.tag_enum == Elf.DynamicArrayTags.sunw_auxiliary) or (self.tag_enum == Elf.DynamicArrayTags.sunw_filter) or (self.tag_enum == Elf.DynamicArrayTags.auxiliary) or (self.tag_enum == Elf.DynamicArrayTags.filter) or (self.tag_enum == Elf.DynamicArrayTags.config) or (self.tag_enum == Elf.DynamicArrayTags.depaudit) or (self.tag_enum == Elf.DynamicArrayTags.audit)) )) 
                return getattr(self, '_m_is_value_str', None)

            @property
            def tag_enum(self):
                if hasattr(self, '_m_tag_enum'):
                    return self._m_tag_enum

                self._m_tag_enum = KaitaiStream.resolve_enum(Elf.DynamicArrayTags, self.tag)
                return getattr(self, '_m_tag_enum', None)


        class ProgramHeader(KaitaiStruct):
            """
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/07-pheader.html#program-header-entry
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/program-header.html
            """
            SEQ_FIELDS = ["type", "flags64", "ofs_body", "virt_addr", "phys_addr", "len_body", "memory_size", "flags32", "align"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.ProgramHeader, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/program_header")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.PhType, self._io.read_u4le())
                self._debug['type']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['flags64']['start'] = self._io.pos()
                    self.flags64 = self._io.read_u4le()
                    self._debug['flags64']['end'] = self._io.pos()

                self._debug['ofs_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.ofs_body = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.ofs_body = self._io.read_u8le()
                self._debug['ofs_body']['end'] = self._io.pos()
                self._debug['virt_addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.virt_addr = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.virt_addr = self._io.read_u8le()
                self._debug['virt_addr']['end'] = self._io.pos()
                self._debug['phys_addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.phys_addr = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.phys_addr = self._io.read_u8le()
                self._debug['phys_addr']['end'] = self._io.pos()
                self._debug['len_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.len_body = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.len_body = self._io.read_u8le()
                self._debug['len_body']['end'] = self._io.pos()
                self._debug['memory_size']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.memory_size = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.memory_size = self._io.read_u8le()
                self._debug['memory_size']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['flags32']['start'] = self._io.pos()
                    self.flags32 = self._io.read_u4le()
                    self._debug['flags32']['end'] = self._io.pos()

                self._debug['align']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.align = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.align = self._io.read_u8le()
                self._debug['align']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.PhType, self._io.read_u4be())
                self._debug['type']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b64:
                    pass
                    self._debug['flags64']['start'] = self._io.pos()
                    self.flags64 = self._io.read_u4be()
                    self._debug['flags64']['end'] = self._io.pos()

                self._debug['ofs_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.ofs_body = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.ofs_body = self._io.read_u8be()
                self._debug['ofs_body']['end'] = self._io.pos()
                self._debug['virt_addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.virt_addr = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.virt_addr = self._io.read_u8be()
                self._debug['virt_addr']['end'] = self._io.pos()
                self._debug['phys_addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.phys_addr = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.phys_addr = self._io.read_u8be()
                self._debug['phys_addr']['end'] = self._io.pos()
                self._debug['len_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.len_body = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.len_body = self._io.read_u8be()
                self._debug['len_body']['end'] = self._io.pos()
                self._debug['memory_size']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.memory_size = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.memory_size = self._io.read_u8be()
                self._debug['memory_size']['end'] = self._io.pos()
                if self._root.bits == Elf.Bits.b32:
                    pass
                    self._debug['flags32']['start'] = self._io.pos()
                    self.flags32 = self._io.read_u4be()
                    self._debug['flags32']['end'] = self._io.pos()

                self._debug['align']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.align = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.align = self._io.read_u8be()
                self._debug['align']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                if self._root.bits == Elf.Bits.b64:
                    pass

                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                if self._root.bits == Elf.Bits.b32:
                    pass

                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _ = self.body
                if hasattr(self, '_m_body'):
                    pass
                    _on = self.type
                    if _on == Elf.PhType.dynamic:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.PhType.interp:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.PhType.note:
                        pass
                        self._m_body._fetch_instances()
                    else:
                        pass

                _ = self.flags_obj
                if hasattr(self, '_m_flags_obj'):
                    pass
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                        self._m_flags_obj._fetch_instances()
                    elif _on == Elf.Bits.b64:
                        pass
                        self._m_flags_obj._fetch_instances()


            class PhInterpreter(KaitaiStruct):
                """
                .. seealso::
                   Source - https://gabi.xinuos.com/v42/elf/08-dynamic.html#program-interpreter
                
                
                .. seealso::
                   Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/program-interpreter.html
                """
                SEQ_FIELDS = ["path_name"]
                def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                    super(Elf.EndianElf.ProgramHeader.PhInterpreter, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self._is_le = _is_le
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    if not hasattr(self, '_is_le'):
                        raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/program_header/types/ph_interpreter")
                    elif self._is_le == True:
                        self._read_le()
                    elif self._is_le == False:
                        self._read_be()

                def _read_le(self):
                    self._debug['path_name']['start'] = self._io.pos()
                    self.path_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                    self._debug['path_name']['end'] = self._io.pos()

                def _read_be(self):
                    self._debug['path_name']['start'] = self._io.pos()
                    self.path_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                    self._debug['path_name']['end'] = self._io.pos()


                def _fetch_instances(self):
                    pass


            @property
            def body(self):
                """Note: a program header may not have a valid body in the same ELF
                file, so accessing `body` may result in reading garbage or
                triggering EOF errors.
                
                In particular, `*.debug` files produced by elfutils'
                `eu-strip --strip-debug` (as used by Fedora/RHEL and other
                RPM-based distros for their `*-debuginfo` packages, e.g.
                `glibc-debuginfo`) copy the original binary's program header table
                verbatim, including `ofs_body`/`len_body` (i.e.
                `p_offset`/`p_filesz`), while dropping the actual contents of most
                segments. Such segments can be recognized by the fact that the
                corresponding section headers have type `sh_type::nobits`
                (`SHT_NOBITS`). However, this Kaitai Struct implementation doesn't
                know the mapping between program headers and section headers, so
                this must be handled externally.
                
                `*.debug` files from Debian/Ubuntu `*-dbg` packages (e.g.
                `libc6-dbg`) are usually not affected by this issue, because they
                are produced using GNU Binutils (`objcopy --only-keep-debug`),
                which zeroes `len_body` for segments whose contents were omitted
                (which reliably tells us that there is no `body`).
                """
                if hasattr(self, '_m_body'):
                    return self._m_body

                if self.len_body != 0:
                    pass
                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self.ofs_body)
                    if self._is_le:
                        self._debug['_m_body']['start'] = io.pos()
                        _on = self.type
                        if _on == Elf.PhType.dynamic:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.PhDynamicSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.PhType.interp:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.ProgramHeader.PhInterpreter(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.PhType.note:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.NoteSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        else:
                            pass
                            self._m_body = io.read_bytes(self.len_body)
                        self._debug['_m_body']['end'] = io.pos()
                    else:
                        self._debug['_m_body']['start'] = io.pos()
                        _on = self.type
                        if _on == Elf.PhType.dynamic:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.PhDynamicSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.PhType.interp:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.ProgramHeader.PhInterpreter(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.PhType.note:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.NoteSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        else:
                            pass
                            self._m_body = io.read_bytes(self.len_body)
                        self._debug['_m_body']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_body', None)

            @property
            def flags_obj(self):
                if hasattr(self, '_m_flags_obj'):
                    return self._m_flags_obj

                if self._is_le:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                        self._m_flags_obj = Elf.PhdrTypeFlags(self.flags32, self._io, self, self._root)
                        self._m_flags_obj._read()
                    elif _on == Elf.Bits.b64:
                        pass
                        self._m_flags_obj = Elf.PhdrTypeFlags(self.flags64, self._io, self, self._root)
                        self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                else:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                        self._m_flags_obj = Elf.PhdrTypeFlags(self.flags32, self._io, self, self._root)
                        self._m_flags_obj._read()
                    elif _on == Elf.Bits.b64:
                        pass
                        self._m_flags_obj = Elf.PhdrTypeFlags(self.flags64, self._io, self, self._root)
                        self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                return getattr(self, '_m_flags_obj', None)


        class RelocationSection(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/relocation-sections.html
            
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.reloc.html
            """
            SEQ_FIELDS = ["entries"]
            def __init__(self, has_addend, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.RelocationSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self.has_addend = has_addend
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/relocation_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.RelocationSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        self.entries.append(_t_entries)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.RelocationSectionEntry(self._io, self, self._root, self._is_le)
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



        class RelocationSectionEntry(KaitaiStruct):
            SEQ_FIELDS = ["offset", "info", "addend"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.RelocationSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/relocation_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['offset']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.offset = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.offset = self._io.read_u8le()
                self._debug['offset']['end'] = self._io.pos()
                self._debug['info']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.info = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.info = self._io.read_u8le()
                self._debug['info']['end'] = self._io.pos()
                if self._parent.has_addend:
                    pass
                    self._debug['addend']['start'] = self._io.pos()
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                        self.addend = self._io.read_s4le()
                    elif _on == Elf.Bits.b64:
                        pass
                        self.addend = self._io.read_s8le()
                    self._debug['addend']['end'] = self._io.pos()


            def _read_be(self):
                self._debug['offset']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.offset = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.offset = self._io.read_u8be()
                self._debug['offset']['end'] = self._io.pos()
                self._debug['info']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.info = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.info = self._io.read_u8be()
                self._debug['info']['end'] = self._io.pos()
                if self._parent.has_addend:
                    pass
                    self._debug['addend']['start'] = self._io.pos()
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                        self.addend = self._io.read_s4be()
                    elif _on == Elf.Bits.b64:
                        pass
                        self.addend = self._io.read_s8be()
                    self._debug['addend']['end'] = self._io.pos()



            def _fetch_instances(self):
                pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                if self._parent.has_addend:
                    pass
                    _on = self._root.bits
                    if _on == Elf.Bits.b32:
                        pass
                    elif _on == Elf.Bits.b64:
                        pass



        class SectionHeader(KaitaiStruct):
            """
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/03-sheader.html#section-header-table-entry
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html
            """
            SEQ_FIELDS = ["ofs_name", "type", "flags", "addr", "ofs_body", "len_body", "linked_section_idx", "info", "align", "entry_size"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.SectionHeader, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/section_header")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4le()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.ShType, self._io.read_u4le())
                self._debug['type']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.flags = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.flags = self._io.read_u8le()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.addr = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.addr = self._io.read_u8le()
                self._debug['addr']['end'] = self._io.pos()
                self._debug['ofs_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.ofs_body = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.ofs_body = self._io.read_u8le()
                self._debug['ofs_body']['end'] = self._io.pos()
                self._debug['len_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.len_body = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.len_body = self._io.read_u8le()
                self._debug['len_body']['end'] = self._io.pos()
                self._debug['linked_section_idx']['start'] = self._io.pos()
                self.linked_section_idx = self._io.read_u4le()
                self._debug['linked_section_idx']['end'] = self._io.pos()
                self._debug['info']['start'] = self._io.pos()
                self.info = self._io.read_u4le()
                self._debug['info']['end'] = self._io.pos()
                self._debug['align']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.align = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.align = self._io.read_u8le()
                self._debug['align']['end'] = self._io.pos()
                self._debug['entry_size']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.entry_size = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.entry_size = self._io.read_u8le()
                self._debug['entry_size']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4be()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['type']['start'] = self._io.pos()
                self.type = KaitaiStream.resolve_enum(Elf.ShType, self._io.read_u4be())
                self._debug['type']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.flags = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.flags = self._io.read_u8be()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['addr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.addr = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.addr = self._io.read_u8be()
                self._debug['addr']['end'] = self._io.pos()
                self._debug['ofs_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.ofs_body = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.ofs_body = self._io.read_u8be()
                self._debug['ofs_body']['end'] = self._io.pos()
                self._debug['len_body']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.len_body = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.len_body = self._io.read_u8be()
                self._debug['len_body']['end'] = self._io.pos()
                self._debug['linked_section_idx']['start'] = self._io.pos()
                self.linked_section_idx = self._io.read_u4be()
                self._debug['linked_section_idx']['end'] = self._io.pos()
                self._debug['info']['start'] = self._io.pos()
                self.info = self._io.read_u4be()
                self._debug['info']['end'] = self._io.pos()
                self._debug['align']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.align = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.align = self._io.read_u8be()
                self._debug['align']['end'] = self._io.pos()
                self._debug['entry_size']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.entry_size = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.entry_size = self._io.read_u8be()
                self._debug['entry_size']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _ = self.body
                if hasattr(self, '_m_body'):
                    pass
                    _on = self.type
                    if _on == Elf.ShType.dynamic:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.dynsym:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.gnu_verdef:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.gnu_verneed:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.gnu_versym:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.note:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.rel:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.rela:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.strtab:
                        pass
                        self._m_body._fetch_instances()
                    elif _on == Elf.ShType.symtab:
                        pass
                        self._m_body._fetch_instances()
                    else:
                        pass

                _ = self.flags_obj
                if hasattr(self, '_m_flags_obj'):
                    pass
                    self._m_flags_obj._fetch_instances()

                _ = self.name
                if hasattr(self, '_m_name'):
                    pass


            @property
            def body(self):
                if hasattr(self, '_m_body'):
                    return self._m_body

                if self.type != Elf.ShType.nobits:
                    pass
                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self.ofs_body)
                    if self._is_le:
                        self._debug['_m_body']['start'] = io.pos()
                        _on = self.type
                        if _on == Elf.ShType.dynamic:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.ShDynamicSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.dynsym:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.DynsymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_verdef:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VerdefSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_verneed:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VerneedSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_versym:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VersymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.note:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.NoteSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.rel:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.RelocationSection(False, _io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.rela:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.RelocationSection(True, _io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.strtab:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.StringsStruct(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.symtab:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.DynsymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        else:
                            pass
                            self._m_body = io.read_bytes(self.len_body)
                        self._debug['_m_body']['end'] = io.pos()
                    else:
                        self._debug['_m_body']['start'] = io.pos()
                        _on = self.type
                        if _on == Elf.ShType.dynamic:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.ShDynamicSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.dynsym:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.DynsymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_verdef:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VerdefSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_verneed:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VerneedSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.gnu_versym:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.VersymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.note:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.NoteSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.rel:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.RelocationSection(False, _io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.rela:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.RelocationSection(True, _io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.strtab:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.StringsStruct(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        elif _on == Elf.ShType.symtab:
                            pass
                            self._raw__m_body = io.read_bytes(self.len_body)
                            _io__raw__m_body = KaitaiStream(BytesIO(self._raw__m_body))
                            self._m_body = Elf.EndianElf.DynsymSection(_io__raw__m_body, self, self._root, self._is_le)
                            self._m_body._read()
                        else:
                            pass
                            self._m_body = io.read_bytes(self.len_body)
                        self._debug['_m_body']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_body', None)

            @property
            def flags_obj(self):
                if hasattr(self, '_m_flags_obj'):
                    return self._m_flags_obj

                if self._is_le:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.SectionHeaderFlags(self.flags, self._io, self, self._root)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                else:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.SectionHeaderFlags(self.flags, self._io, self, self._root)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                return getattr(self, '_m_flags_obj', None)

            @property
            def linked_section(self):
                """may reference a later section header, so don't try to access too early (use only lazy `instances`).
                
                .. seealso::
                   Source - https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.sheader.html#sh_link
                """
                if hasattr(self, '_m_linked_section'):
                    return self._m_linked_section

                if  ((self.linked_section_idx != int(Elf.SectionHeaderIdxSpecial.undefined)) and (self.linked_section_idx < self._root.header.num_section_headers)) :
                    pass
                    self._m_linked_section = self._root.header.section_headers[self.linked_section_idx]

                return getattr(self, '_m_linked_section', None)

            @property
            def name(self):
                if hasattr(self, '_m_name'):
                    return self._m_name

                io = self._root.header.section_names._io
                _pos = io.pos()
                io.seek(self.ofs_name)
                if self._is_le:
                    self._debug['_m_name']['start'] = io.pos()
                    self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                    self._debug['_m_name']['end'] = io.pos()
                else:
                    self._debug['_m_name']['start'] = io.pos()
                    self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                    self._debug['_m_name']['end'] = io.pos()
                io.seek(_pos)
                return getattr(self, '_m_name', None)


        class ShDynamicSection(KaitaiStruct):
            """Same type as `ph_dynamic_section`, but it depends on
            `_parent.linked_section`, so it can be used only in the
            `section_header` type. See the documentation for `ph_dynamic_section`
            for more details.
            
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/08-dynamic.html#dynamic-section
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html
            """
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.ShDynamicSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/sh_dynamic_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while True:
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.ShDynamicSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        _ = _t_entries
                        self.entries.append(_)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    if _.tag_enum == Elf.DynamicArrayTags.null:
                        break
                    i += 1
                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while True:
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.ShDynamicSectionEntry(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        _ = _t_entries
                        self.entries.append(_)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    if _.tag_enum == Elf.DynamicArrayTags.null:
                        break
                    i += 1
                self._debug['entries']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.entries)):
                    pass
                    self.entries[i]._fetch_instances()


            @property
            def is_string_table_linked(self):
                if hasattr(self, '_m_is_string_table_linked'):
                    return self._m_is_string_table_linked

                self._m_is_string_table_linked = self._parent.linked_section.type == Elf.ShType.strtab
                return getattr(self, '_m_is_string_table_linked', None)


        class ShDynamicSectionEntry(KaitaiStruct):
            """Same type as `ph_dynamic_section_entry`, but with the `value_str`
            instance - see the documentation for `ph_dynamic_section` for more
            details.
            
            .. seealso::
               Source - https://gabi.xinuos.com/v42/elf/08-dynamic.html#dynamic-section
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/dynamic-section.html
            """
            SEQ_FIELDS = ["tag", "value_or_ptr"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.ShDynamicSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/sh_dynamic_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['tag']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.tag = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.tag = self._io.read_u8le()
                self._debug['tag']['end'] = self._io.pos()
                self._debug['value_or_ptr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.value_or_ptr = self._io.read_u4le()
                elif _on == Elf.Bits.b64:
                    pass
                    self.value_or_ptr = self._io.read_u8le()
                self._debug['value_or_ptr']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['tag']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.tag = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.tag = self._io.read_u8be()
                self._debug['tag']['end'] = self._io.pos()
                self._debug['value_or_ptr']['start'] = self._io.pos()
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                    self.value_or_ptr = self._io.read_u4be()
                elif _on == Elf.Bits.b64:
                    pass
                    self.value_or_ptr = self._io.read_u8be()
                self._debug['value_or_ptr']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _on = self._root.bits
                if _on == Elf.Bits.b32:
                    pass
                elif _on == Elf.Bits.b64:
                    pass
                _ = self.flag_1_values
                if hasattr(self, '_m_flag_1_values'):
                    pass
                    self._m_flag_1_values._fetch_instances()

                _ = self.flag_values
                if hasattr(self, '_m_flag_values'):
                    pass
                    self._m_flag_values._fetch_instances()

                _ = self.value_str
                if hasattr(self, '_m_value_str'):
                    pass


            @property
            def flag_1_values(self):
                if hasattr(self, '_m_flag_1_values'):
                    return self._m_flag_1_values

                if self.tag_enum == Elf.DynamicArrayTags.flags_1:
                    pass
                    if self._is_le:
                        self._debug['_m_flag_1_values']['start'] = self._io.pos()
                        self._m_flag_1_values = Elf.DtFlag1Values(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_1_values._read()
                        self._debug['_m_flag_1_values']['end'] = self._io.pos()
                    else:
                        self._debug['_m_flag_1_values']['start'] = self._io.pos()
                        self._m_flag_1_values = Elf.DtFlag1Values(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_1_values._read()
                        self._debug['_m_flag_1_values']['end'] = self._io.pos()

                return getattr(self, '_m_flag_1_values', None)

            @property
            def flag_values(self):
                if hasattr(self, '_m_flag_values'):
                    return self._m_flag_values

                if self.tag_enum == Elf.DynamicArrayTags.flags:
                    pass
                    if self._is_le:
                        self._debug['_m_flag_values']['start'] = self._io.pos()
                        self._m_flag_values = Elf.DtFlagValues(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_values._read()
                        self._debug['_m_flag_values']['end'] = self._io.pos()
                    else:
                        self._debug['_m_flag_values']['start'] = self._io.pos()
                        self._m_flag_values = Elf.DtFlagValues(self.value_or_ptr, self._io, self, self._root)
                        self._m_flag_values._read()
                        self._debug['_m_flag_values']['end'] = self._io.pos()

                return getattr(self, '_m_flag_values', None)

            @property
            def is_value_str(self):
                if hasattr(self, '_m_is_value_str'):
                    return self._m_is_value_str

                self._m_is_value_str =  ((self.value_or_ptr != 0) and ( ((self.tag_enum == Elf.DynamicArrayTags.needed) or (self.tag_enum == Elf.DynamicArrayTags.soname) or (self.tag_enum == Elf.DynamicArrayTags.rpath) or (self.tag_enum == Elf.DynamicArrayTags.runpath) or (self.tag_enum == Elf.DynamicArrayTags.sunw_auxiliary) or (self.tag_enum == Elf.DynamicArrayTags.sunw_filter) or (self.tag_enum == Elf.DynamicArrayTags.auxiliary) or (self.tag_enum == Elf.DynamicArrayTags.filter) or (self.tag_enum == Elf.DynamicArrayTags.config) or (self.tag_enum == Elf.DynamicArrayTags.depaudit) or (self.tag_enum == Elf.DynamicArrayTags.audit)) )) 
                return getattr(self, '_m_is_value_str', None)

            @property
            def tag_enum(self):
                if hasattr(self, '_m_tag_enum'):
                    return self._m_tag_enum

                self._m_tag_enum = KaitaiStream.resolve_enum(Elf.DynamicArrayTags, self.tag)
                return getattr(self, '_m_tag_enum', None)

            @property
            def value_str(self):
                if hasattr(self, '_m_value_str'):
                    return self._m_value_str

                if  ((self.is_value_str) and (self._parent.is_string_table_linked)) :
                    pass
                    io = self._parent._parent.linked_section.body._io
                    _pos = io.pos()
                    io.seek(self.value_or_ptr)
                    if self._is_le:
                        self._debug['_m_value_str']['start'] = io.pos()
                        self._m_value_str = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                        self._debug['_m_value_str']['end'] = io.pos()
                    else:
                        self._debug['_m_value_str']['start'] = io.pos()
                        self._m_value_str = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
                        self._debug['_m_value_str']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_value_str', None)


        class StringsStruct(KaitaiStruct):
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.StringsStruct, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/strings_struct")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    self.entries.append((self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8"))
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    self.entries.append((self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8"))
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.entries)):
                    pass



        class VerdauxEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#VERDEFEXTS
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-definition-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["_unnamed0", "ofs_name", "ofs_next"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VerdauxEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/verdaux_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4le()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4le()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 8)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verdaux_entry/seq/2")

            def _read_be(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4be()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4be()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 8)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verdaux_entry/seq/2")


            def _fetch_instances(self):
                pass
                if self.ofs_start < 0:
                    pass

                _ = self.name
                if hasattr(self, '_m_name'):
                    pass

                _ = self.next
                if hasattr(self, '_m_next'):
                    pass
                    self._m_next._fetch_instances()


            @property
            def name(self):
                if hasattr(self, '_m_name'):
                    return self._m_name

                if self._parent.is_string_table_linked:
                    pass
                    io = self._parent._parent.linked_section.body._io
                    _pos = io.pos()
                    io.seek(self.ofs_name)
                    if self._is_le:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    else:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_name', None)

            @property
            def next(self):
                if hasattr(self, '_m_next'):
                    return self._m_next

                if self.ofs_next != 0:
                    pass
                    _pos = self._io.pos()
                    self._io.seek(self.ofs_start + self.ofs_next)
                    if self._is_le:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerdauxEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    else:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerdauxEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    self._io.seek(_pos)

                return getattr(self, '_m_next', None)

            @property
            def ofs_start(self):
                if hasattr(self, '_m_ofs_start'):
                    return self._m_ofs_start

                self._m_ofs_start = self._io.pos()
                return getattr(self, '_m_ofs_start', None)


        class VerdefSection(KaitaiStruct):
            """Version Definitions, contained in the special section named
            `.gnu.version_d` with the section type `sh_type::gnu_verdef`
            (`SHT_GNU_verdef`).
            
            The number of entries in this section must match the value of the
            dynamic tag `dynamic_array_tags::verdefnum` (`DT_VERDEFNUM`) in the
            Dynamic Section (`.dynamic`).
            
            `_parent.linked_section` must be the string table that contains the
            strings referenced by this section. Specifically, the string table in
            the `.dynstr` section should be used (side note: the `readelf` command
            doesn't even check which string table `sh_link` points to, and always
            uses `.dynstr` for the lookups - see
            <https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/binutils/readelf.c#L13787>).
            
            The `is_string_table_linked` value instance indicates whether the
            string table is linked. If it is not, version names (the `name`
            instance in the `verdaux_entry` type) will not be available.
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#SYMVERDEFS
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-definition-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["first_entry"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VerdefSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/verdef_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['first_entry']['start'] = self._io.pos()
                self.first_entry = Elf.EndianElf.VerdefSectionEntry(self._io, self, self._root, self._is_le)
                self.first_entry._read()
                self._debug['first_entry']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['first_entry']['start'] = self._io.pos()
                self.first_entry = Elf.EndianElf.VerdefSectionEntry(self._io, self, self._root, self._is_le)
                self.first_entry._read()
                self._debug['first_entry']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                self.first_entry._fetch_instances()

            @property
            def is_string_table_linked(self):
                """Indicates whether a string table is linked. This should always be
                `true` in spec-compliant ELF files. If it is `false`, the string
                offsets in this section will not be resolved to strings.
                """
                if hasattr(self, '_m_is_string_table_linked'):
                    return self._m_is_string_table_linked

                self._m_is_string_table_linked = self._parent.linked_section.type == Elf.ShType.strtab
                return getattr(self, '_m_is_string_table_linked', None)

            @property
            def num_entries(self):
                """Number of entries (version definitions).
                
                .. seealso::
                   Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html#GUID-2CBE4879-2E76-426E-BB7F-CF0CB1D87C52__CHAPTER6-47976
                """
                if hasattr(self, '_m_num_entries'):
                    return self._m_num_entries

                self._m_num_entries = self._parent.info
                return getattr(self, '_m_num_entries', None)


        class VerdefSectionEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#VERDEFENTRIES
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-definition-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["_unnamed0", "version", "flags", "version_index", "num_aux_entries", "hash", "ofs_first_aux", "ofs_next"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VerdefSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/verdef_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['version']['start'] = self._io.pos()
                self.version = self._io.read_u2le()
                self._debug['version']['end'] = self._io.pos()
                if not self.version == 1:
                    raise kaitaistruct.ValidationNotEqualError(1, self.version, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/1")
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u2le()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['version_index']['start'] = self._io.pos()
                self.version_index = self._io.read_u2le()
                self._debug['version_index']['end'] = self._io.pos()
                _ = self.version_index
                if not _ & 32768 == 0:
                    raise kaitaistruct.ValidationExprError(self.version_index, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/3")
                self._debug['num_aux_entries']['start'] = self._io.pos()
                self.num_aux_entries = self._io.read_u2le()
                self._debug['num_aux_entries']['end'] = self._io.pos()
                if not self.num_aux_entries >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.num_aux_entries, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/4")
                self._debug['hash']['start'] = self._io.pos()
                self.hash = self._io.read_u4le()
                self._debug['hash']['end'] = self._io.pos()
                self._debug['ofs_first_aux']['start'] = self._io.pos()
                self.ofs_first_aux = self._io.read_u4le()
                self._debug['ofs_first_aux']['end'] = self._io.pos()
                if not self.ofs_first_aux >= 20:
                    raise kaitaistruct.ValidationLessThanError(20, self.ofs_first_aux, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/6")
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4le()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 20)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/7")

            def _read_be(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['version']['start'] = self._io.pos()
                self.version = self._io.read_u2be()
                self._debug['version']['end'] = self._io.pos()
                if not self.version == 1:
                    raise kaitaistruct.ValidationNotEqualError(1, self.version, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/1")
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u2be()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['version_index']['start'] = self._io.pos()
                self.version_index = self._io.read_u2be()
                self._debug['version_index']['end'] = self._io.pos()
                _ = self.version_index
                if not _ & 32768 == 0:
                    raise kaitaistruct.ValidationExprError(self.version_index, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/3")
                self._debug['num_aux_entries']['start'] = self._io.pos()
                self.num_aux_entries = self._io.read_u2be()
                self._debug['num_aux_entries']['end'] = self._io.pos()
                if not self.num_aux_entries >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.num_aux_entries, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/4")
                self._debug['hash']['start'] = self._io.pos()
                self.hash = self._io.read_u4be()
                self._debug['hash']['end'] = self._io.pos()
                self._debug['ofs_first_aux']['start'] = self._io.pos()
                self.ofs_first_aux = self._io.read_u4be()
                self._debug['ofs_first_aux']['end'] = self._io.pos()
                if not self.ofs_first_aux >= 20:
                    raise kaitaistruct.ValidationLessThanError(20, self.ofs_first_aux, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/6")
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4be()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 20)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verdef_section_entry/seq/7")


            def _fetch_instances(self):
                pass
                if self.ofs_start < 0:
                    pass

                _ = self.first_aux
                if hasattr(self, '_m_first_aux'):
                    pass
                    self._m_first_aux._fetch_instances()

                _ = self.flags_obj
                if hasattr(self, '_m_flags_obj'):
                    pass
                    self._m_flags_obj._fetch_instances()

                _ = self.next
                if hasattr(self, '_m_next'):
                    pass
                    self._m_next._fetch_instances()


            @property
            def first_aux(self):
                """First auxiliary entry of type `verdaux_entry` (`Elfxx_Verdaux`).
                The rest follow its `next` instance.
                """
                if hasattr(self, '_m_first_aux'):
                    return self._m_first_aux

                _pos = self._io.pos()
                self._io.seek(self.ofs_start + self.ofs_first_aux)
                if self._is_le:
                    self._debug['_m_first_aux']['start'] = self._io.pos()
                    self._m_first_aux = Elf.EndianElf.VerdauxEntry(self._io, self._parent, self._root, self._is_le)
                    self._m_first_aux._read()
                    self._debug['_m_first_aux']['end'] = self._io.pos()
                else:
                    self._debug['_m_first_aux']['start'] = self._io.pos()
                    self._m_first_aux = Elf.EndianElf.VerdauxEntry(self._io, self._parent, self._root, self._is_le)
                    self._m_first_aux._read()
                    self._debug['_m_first_aux']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_first_aux', None)

            @property
            def flags_obj(self):
                if hasattr(self, '_m_flags_obj'):
                    return self._m_flags_obj

                if self._is_le:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.EndianElf.VersionFlags(self.flags, self._io, self, self._root, self._is_le)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                else:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.EndianElf.VersionFlags(self.flags, self._io, self, self._root, self._is_le)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                return getattr(self, '_m_flags_obj', None)

            @property
            def next(self):
                if hasattr(self, '_m_next'):
                    return self._m_next

                if self.ofs_next != 0:
                    pass
                    _pos = self._io.pos()
                    self._io.seek(self.ofs_start + self.ofs_next)
                    if self._is_le:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerdefSectionEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    else:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerdefSectionEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    self._io.seek(_pos)

                return getattr(self, '_m_next', None)

            @property
            def ofs_start(self):
                if hasattr(self, '_m_ofs_start'):
                    return self._m_ofs_start

                self._m_ofs_start = self._io.pos()
                return getattr(self, '_m_ofs_start', None)

            @property
            def version_index_special(self):
                if hasattr(self, '_m_version_index_special'):
                    return self._m_version_index_special

                self._m_version_index_special = KaitaiStream.resolve_enum(Elf.VersionIndexSpecial, self.version_index)
                return getattr(self, '_m_version_index_special', None)


        class VernauxEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#VERNEEDEXTFIG
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-dependency-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["_unnamed0", "hash", "flags", "version_index", "ofs_name", "ofs_next"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VernauxEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/vernaux_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['hash']['start'] = self._io.pos()
                self.hash = self._io.read_u4le()
                self._debug['hash']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u2le()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['version_index']['start'] = self._io.pos()
                self.version_index = Elf.EndianElf.VersionIndex(self._io, self, self._root, self._is_le)
                self.version_index._read()
                self._debug['version_index']['end'] = self._io.pos()
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4le()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4le()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 16)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/vernaux_entry/seq/5")

            def _read_be(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['hash']['start'] = self._io.pos()
                self.hash = self._io.read_u4be()
                self._debug['hash']['end'] = self._io.pos()
                self._debug['flags']['start'] = self._io.pos()
                self.flags = self._io.read_u2be()
                self._debug['flags']['end'] = self._io.pos()
                self._debug['version_index']['start'] = self._io.pos()
                self.version_index = Elf.EndianElf.VersionIndex(self._io, self, self._root, self._is_le)
                self.version_index._read()
                self._debug['version_index']['end'] = self._io.pos()
                self._debug['ofs_name']['start'] = self._io.pos()
                self.ofs_name = self._io.read_u4be()
                self._debug['ofs_name']['end'] = self._io.pos()
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4be()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 16)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/vernaux_entry/seq/5")


            def _fetch_instances(self):
                pass
                if self.ofs_start < 0:
                    pass

                self.version_index._fetch_instances()
                _ = self.flags_obj
                if hasattr(self, '_m_flags_obj'):
                    pass
                    self._m_flags_obj._fetch_instances()

                _ = self.name
                if hasattr(self, '_m_name'):
                    pass

                _ = self.next
                if hasattr(self, '_m_next'):
                    pass
                    self._m_next._fetch_instances()


            @property
            def flags_obj(self):
                if hasattr(self, '_m_flags_obj'):
                    return self._m_flags_obj

                if self._is_le:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.EndianElf.VersionFlags(self.flags, self._io, self, self._root, self._is_le)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                else:
                    self._debug['_m_flags_obj']['start'] = self._io.pos()
                    self._m_flags_obj = Elf.EndianElf.VersionFlags(self.flags, self._io, self, self._root, self._is_le)
                    self._m_flags_obj._read()
                    self._debug['_m_flags_obj']['end'] = self._io.pos()
                return getattr(self, '_m_flags_obj', None)

            @property
            def name(self):
                if hasattr(self, '_m_name'):
                    return self._m_name

                if self._parent.is_string_table_linked:
                    pass
                    io = self._parent._parent.linked_section.body._io
                    _pos = io.pos()
                    io.seek(self.ofs_name)
                    if self._is_le:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    else:
                        self._debug['_m_name']['start'] = io.pos()
                        self._m_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_name']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_name', None)

            @property
            def next(self):
                if hasattr(self, '_m_next'):
                    return self._m_next

                if self.ofs_next != 0:
                    pass
                    _pos = self._io.pos()
                    self._io.seek(self.ofs_start + self.ofs_next)
                    if self._is_le:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VernauxEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    else:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VernauxEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    self._io.seek(_pos)

                return getattr(self, '_m_next', None)

            @property
            def ofs_start(self):
                if hasattr(self, '_m_ofs_start'):
                    return self._m_ofs_start

                self._m_ofs_start = self._io.pos()
                return getattr(self, '_m_ofs_start', None)


        class VerneedSection(KaitaiStruct):
            """Version Requirements, contained in the special section named
            `.gnu.version_r` with the section type `sh_type::gnu_verneed`
            (`SHT_GNU_verneed`). This section defines the required versions of
            dynamic symbols from other shared objects.
            
            The number of entries in this section must match the value of the
            dynamic tag `dynamic_array_tags::verneednum` (`DT_VERNEEDNUM`) in the
            Dynamic Section (`.dynamic`).
            
            `_parent.linked_section` must be the string table that contains the
            strings referenced by this section. Specifically, the string table in
            the `.dynstr` section should be used (side note: the `readelf` command
            doesn't even check which string table `sh_link` points to, and always
            uses `.dynstr` for the lookups - see
            <https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/binutils/readelf.c#L13941>).
            
            The `is_string_table_linked` value instance indicates whether the
            string table is linked. If it is not, file names (the `file_name`
            instance in the `verneed_section_entry` type) or version names (the
            `name` instance in the `vernaux_entry` type) will not be available.
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#SYMVERRQMTS
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-dependency-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["first_entry"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VerneedSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/verneed_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['first_entry']['start'] = self._io.pos()
                self.first_entry = Elf.EndianElf.VerneedSectionEntry(self._io, self, self._root, self._is_le)
                self.first_entry._read()
                self._debug['first_entry']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['first_entry']['start'] = self._io.pos()
                self.first_entry = Elf.EndianElf.VerneedSectionEntry(self._io, self, self._root, self._is_le)
                self.first_entry._read()
                self._debug['first_entry']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                self.first_entry._fetch_instances()

            @property
            def is_string_table_linked(self):
                """Indicates whether a string table is linked. This should always be
                `true` in spec-compliant ELF files. If it is `false`, the string
                offsets in this section will not be resolved to strings.
                """
                if hasattr(self, '_m_is_string_table_linked'):
                    return self._m_is_string_table_linked

                self._m_is_string_table_linked = self._parent.linked_section.type == Elf.ShType.strtab
                return getattr(self, '_m_is_string_table_linked', None)

            @property
            def num_entries(self):
                """Number of entries (dependency versions).
                
                .. seealso::
                   Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html#GUID-2CBE4879-2E76-426E-BB7F-CF0CB1D87C52__CHAPTER6-47976
                """
                if hasattr(self, '_m_num_entries'):
                    return self._m_num_entries

                self._m_num_entries = self._parent.info
                return getattr(self, '_m_num_entries', None)


        class VerneedSectionEntry(KaitaiStruct):
            """
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#VERNEEDFIG
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-dependency-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["_unnamed0", "version", "num_aux_entries", "ofs_file_name", "ofs_first_aux", "ofs_next"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VerneedSectionEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/verneed_section_entry")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['version']['start'] = self._io.pos()
                self.version = self._io.read_u2le()
                self._debug['version']['end'] = self._io.pos()
                if not self.version == 1:
                    raise kaitaistruct.ValidationNotEqualError(1, self.version, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/1")
                self._debug['num_aux_entries']['start'] = self._io.pos()
                self.num_aux_entries = self._io.read_u2le()
                self._debug['num_aux_entries']['end'] = self._io.pos()
                if not self.num_aux_entries >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.num_aux_entries, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/2")
                self._debug['ofs_file_name']['start'] = self._io.pos()
                self.ofs_file_name = self._io.read_u4le()
                self._debug['ofs_file_name']['end'] = self._io.pos()
                self._debug['ofs_first_aux']['start'] = self._io.pos()
                self.ofs_first_aux = self._io.read_u4le()
                self._debug['ofs_first_aux']['end'] = self._io.pos()
                if not self.ofs_first_aux >= 16:
                    raise kaitaistruct.ValidationLessThanError(16, self.ofs_first_aux, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/4")
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4le()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 16)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/5")

            def _read_be(self):
                if self.ofs_start < 0:
                    pass
                    self._debug['_unnamed0']['start'] = self._io.pos()
                    self._unnamed0 = self._io.read_bytes(0)
                    self._debug['_unnamed0']['end'] = self._io.pos()

                self._debug['version']['start'] = self._io.pos()
                self.version = self._io.read_u2be()
                self._debug['version']['end'] = self._io.pos()
                if not self.version == 1:
                    raise kaitaistruct.ValidationNotEqualError(1, self.version, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/1")
                self._debug['num_aux_entries']['start'] = self._io.pos()
                self.num_aux_entries = self._io.read_u2be()
                self._debug['num_aux_entries']['end'] = self._io.pos()
                if not self.num_aux_entries >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.num_aux_entries, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/2")
                self._debug['ofs_file_name']['start'] = self._io.pos()
                self.ofs_file_name = self._io.read_u4be()
                self._debug['ofs_file_name']['end'] = self._io.pos()
                self._debug['ofs_first_aux']['start'] = self._io.pos()
                self.ofs_first_aux = self._io.read_u4be()
                self._debug['ofs_first_aux']['end'] = self._io.pos()
                if not self.ofs_first_aux >= 16:
                    raise kaitaistruct.ValidationLessThanError(16, self.ofs_first_aux, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/4")
                self._debug['ofs_next']['start'] = self._io.pos()
                self.ofs_next = self._io.read_u4be()
                self._debug['ofs_next']['end'] = self._io.pos()
                _ = self.ofs_next
                if not  ((_ == 0) or (_ >= 16)) :
                    raise kaitaistruct.ValidationExprError(self.ofs_next, self._io, u"/types/endian_elf/types/verneed_section_entry/seq/5")


            def _fetch_instances(self):
                pass
                if self.ofs_start < 0:
                    pass

                _ = self.file_name
                if hasattr(self, '_m_file_name'):
                    pass

                _ = self.first_aux
                if hasattr(self, '_m_first_aux'):
                    pass
                    self._m_first_aux._fetch_instances()

                _ = self.next
                if hasattr(self, '_m_next'):
                    pass
                    self._m_next._fetch_instances()


            @property
            def file_name(self):
                if hasattr(self, '_m_file_name'):
                    return self._m_file_name

                if self._parent.is_string_table_linked:
                    pass
                    io = self._parent._parent.linked_section.body._io
                    _pos = io.pos()
                    io.seek(self.ofs_file_name)
                    if self._is_le:
                        self._debug['_m_file_name']['start'] = io.pos()
                        self._m_file_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_file_name']['end'] = io.pos()
                    else:
                        self._debug['_m_file_name']['start'] = io.pos()
                        self._m_file_name = (io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                        self._debug['_m_file_name']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_file_name', None)

            @property
            def first_aux(self):
                """First auxiliary entry of type `vernaux_entry` (`Elfxx_Vernaux`).
                The rest follow its `next` instance.
                """
                if hasattr(self, '_m_first_aux'):
                    return self._m_first_aux

                _pos = self._io.pos()
                self._io.seek(self.ofs_start + self.ofs_first_aux)
                if self._is_le:
                    self._debug['_m_first_aux']['start'] = self._io.pos()
                    self._m_first_aux = Elf.EndianElf.VernauxEntry(self._io, self._parent, self._root, self._is_le)
                    self._m_first_aux._read()
                    self._debug['_m_first_aux']['end'] = self._io.pos()
                else:
                    self._debug['_m_first_aux']['start'] = self._io.pos()
                    self._m_first_aux = Elf.EndianElf.VernauxEntry(self._io, self._parent, self._root, self._is_le)
                    self._m_first_aux._read()
                    self._debug['_m_first_aux']['end'] = self._io.pos()
                self._io.seek(_pos)
                return getattr(self, '_m_first_aux', None)

            @property
            def next(self):
                if hasattr(self, '_m_next'):
                    return self._m_next

                if self.ofs_next != 0:
                    pass
                    _pos = self._io.pos()
                    self._io.seek(self.ofs_start + self.ofs_next)
                    if self._is_le:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerneedSectionEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    else:
                        self._debug['_m_next']['start'] = self._io.pos()
                        self._m_next = Elf.EndianElf.VerneedSectionEntry(self._io, self._parent, self._root, self._is_le)
                        self._m_next._read()
                        self._debug['_m_next']['end'] = self._io.pos()
                    self._io.seek(_pos)

                return getattr(self, '_m_next', None)

            @property
            def ofs_start(self):
                if hasattr(self, '_m_ofs_start'):
                    return self._m_ofs_start

                self._m_ofs_start = self._io.pos()
                return getattr(self, '_m_ofs_start', None)


        class VersionFlags(KaitaiStruct):
            """Version information flag bitmask, shared by the `flags` (`vd_flags`)
            field of `verdef_section_entry` (`Elfxx_Verdef`) and the `flags`
            (`vna_flags`) field of `vernaux_entry` (`Elfxx_Vernaux`).
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#SYMSTARTSEQ
            
            
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L1078
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = []
            def __init__(self, value, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VersionFlags, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self.value = value
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/version_flags")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                pass

            def _read_be(self):
                pass


            def _fetch_instances(self):
                pass

            @property
            def base(self):
                """Version definition of the file itself (the base definition)."""
                if hasattr(self, '_m_base'):
                    return self._m_base

                self._m_base = self.value & 1 != 0
                return getattr(self, '_m_base', None)

            @property
            def info(self):
                """Version reference exists for informational purposes and does not
                need to be validated at runtime.
                
                .. seealso::
                   Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-dependency-section.html
                """
                if hasattr(self, '_m_info'):
                    return self._m_info

                self._m_info = self.value & 4 != 0
                return getattr(self, '_m_info', None)

            @property
            def weak(self):
                """Weak version identifier.
                
                A weak version definition has no symbols associated with the
                version. See [Creating a Weak Version
                Definition](https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/creating-weak-version-definition.html).
                """
                if hasattr(self, '_m_weak'):
                    return self._m_weak

                self._m_weak = self.value & 2 != 0
                return getattr(self, '_m_weak', None)


        class VersionIndex(KaitaiStruct):
            SEQ_FIELDS = ["raw"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VersionIndex, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/version_index")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['raw']['start'] = self._io.pos()
                self.raw = self._io.read_u2le()
                self._debug['raw']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['raw']['start'] = self._io.pos()
                self.raw = self._io.read_u2be()
                self._debug['raw']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass

            @property
            def is_hidden(self):
                """This bit is set if the symbol is hidden, and is only visible with
                an explicit version number. This is a GNU extension.
                
                .. seealso::
                   Source - https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/include/elf/common.h#L1379
                """
                if hasattr(self, '_m_is_hidden'):
                    return self._m_is_hidden

                self._m_is_hidden = self.raw & 32768 != 0
                return getattr(self, '_m_is_hidden', None)

            @property
            def value(self):
                """The values `version_index_special::local` (0) and
                `version_index_special::global_symbol` (1) have special meanings.
                The `version_index_special` value instance converts the integer
                value to the `version_index_special` enum.
                """
                if hasattr(self, '_m_value'):
                    return self._m_value

                self._m_value = self.raw & 32767
                return getattr(self, '_m_value', None)

            @property
            def version_index_special(self):
                """Note: we match special constants against the full 16-bit integer
                value (called `raw` in this .ksy implementation), because that's
                what the `readelf` command does when deciding whether to print
                `0 (*local*)` or `1 (*global*)` in the `.gnu.version`
                (`SHT_GNU_versym`) section - see
                <https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/binutils/readelf.c#L14079>.
                
                Besides, `version_index_special::eliminate` (`VER_NDX_ELIMINATE`)
                has a value of `0xff01`, which is a 16-bit value. If we matched
                against `value` instead, `version_index_special::eliminate` would
                be unreachable, because `value` contains only the lower 15 bits,
                so its maximum possible value is `0x7fff`.
                """
                if hasattr(self, '_m_version_index_special'):
                    return self._m_version_index_special

                self._m_version_index_special = KaitaiStream.resolve_enum(Elf.VersionIndexSpecial, self.raw)
                return getattr(self, '_m_version_index_special', None)


        class VersymSection(KaitaiStruct):
            """Symbol Version Table, contained in the special section named
            `.gnu.version` with the section type `sh_type::gnu_versym`
            (`SHT_GNU_versym`).
            
            This section must have the same number of entries as the Dynamic
            Symbol Table in the `.dynsym` section (section type `sh_type::dynsym`
            / `SHT_DYNSYM`). Each entry specifies the version defined for or
            required by the corresponding symbol in the Dynamic Symbol Table.
            
            .. seealso::
               Source - https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/symversion.html#SYMVERTBL
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/version-symbol-section.html
            
            
            .. seealso::
               Source - https://www.akkadia.org/drepper/symbol-versioning
            """
            SEQ_FIELDS = ["entries"]
            def __init__(self, _io, _parent=None, _root=None, _is_le=None):
                super(Elf.EndianElf.VersymSection, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._is_le = _is_le
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if not hasattr(self, '_is_le'):
                    raise kaitaistruct.UndecidedEndiannessError("/types/endian_elf/types/versym_section")
                elif self._is_le == True:
                    self._read_le()
                elif self._is_le == False:
                    self._read_be()

            def _read_le(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.VersionIndex(self._io, self, self._root, self._is_le)
                    try:
                        _t_entries._read()
                    finally:
                        self.entries.append(_t_entries)
                    self._debug['entries']['arr'][len(self.entries) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['entries']['end'] = self._io.pos()

            def _read_be(self):
                self._debug['entries']['start'] = self._io.pos()
                self._debug['entries']['arr'] = []
                self.entries = []
                i = 0
                while not self._io.is_eof():
                    self._debug['entries']['arr'].append({'start': self._io.pos()})
                    _t_entries = Elf.EndianElf.VersionIndex(self._io, self, self._root, self._is_le)
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



        @property
        def program_headers(self):
            if hasattr(self, '_m_program_headers'):
                return self._m_program_headers

            _pos = self._io.pos()
            self._io.seek(self.ofs_program_headers)
            self._debug['_m_program_headers']['start'] = self._io.pos()
            self._debug['_m_program_headers']['arr'] = []
            if self._is_le:
                self._raw__m_program_headers = []
                self._m_program_headers = []
                for i in range(self.num_program_headers):
                    self._debug['_m_program_headers']['arr'].append({'start': self._io.pos()})
                    self._raw__m_program_headers.append(self._io.read_bytes(self.program_header_size))
                    _io__raw__m_program_headers = KaitaiStream(BytesIO(self._raw__m_program_headers[i]))
                    _t__m_program_headers = Elf.EndianElf.ProgramHeader(_io__raw__m_program_headers, self, self._root, self._is_le)
                    try:
                        _t__m_program_headers._read()
                    finally:
                        self._m_program_headers.append(_t__m_program_headers)
                    self._debug['_m_program_headers']['arr'][i]['end'] = self._io.pos()

            else:
                self._raw__m_program_headers = []
                self._m_program_headers = []
                for i in range(self.num_program_headers):
                    self._debug['_m_program_headers']['arr'].append({'start': self._io.pos()})
                    self._raw__m_program_headers.append(self._io.read_bytes(self.program_header_size))
                    _io__raw__m_program_headers = KaitaiStream(BytesIO(self._raw__m_program_headers[i]))
                    _t__m_program_headers = Elf.EndianElf.ProgramHeader(_io__raw__m_program_headers, self, self._root, self._is_le)
                    try:
                        _t__m_program_headers._read()
                    finally:
                        self._m_program_headers.append(_t__m_program_headers)
                    self._debug['_m_program_headers']['arr'][i]['end'] = self._io.pos()

            self._debug['_m_program_headers']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_program_headers', None)

        @property
        def section_headers(self):
            if hasattr(self, '_m_section_headers'):
                return self._m_section_headers

            _pos = self._io.pos()
            self._io.seek(self.ofs_section_headers)
            self._debug['_m_section_headers']['start'] = self._io.pos()
            self._debug['_m_section_headers']['arr'] = []
            if self._is_le:
                self._raw__m_section_headers = []
                self._m_section_headers = []
                for i in range(self.num_section_headers):
                    self._debug['_m_section_headers']['arr'].append({'start': self._io.pos()})
                    self._raw__m_section_headers.append(self._io.read_bytes(self.section_header_size))
                    _io__raw__m_section_headers = KaitaiStream(BytesIO(self._raw__m_section_headers[i]))
                    _t__m_section_headers = Elf.EndianElf.SectionHeader(_io__raw__m_section_headers, self, self._root, self._is_le)
                    try:
                        _t__m_section_headers._read()
                    finally:
                        self._m_section_headers.append(_t__m_section_headers)
                    self._debug['_m_section_headers']['arr'][i]['end'] = self._io.pos()

            else:
                self._raw__m_section_headers = []
                self._m_section_headers = []
                for i in range(self.num_section_headers):
                    self._debug['_m_section_headers']['arr'].append({'start': self._io.pos()})
                    self._raw__m_section_headers.append(self._io.read_bytes(self.section_header_size))
                    _io__raw__m_section_headers = KaitaiStream(BytesIO(self._raw__m_section_headers[i]))
                    _t__m_section_headers = Elf.EndianElf.SectionHeader(_io__raw__m_section_headers, self, self._root, self._is_le)
                    try:
                        _t__m_section_headers._read()
                    finally:
                        self._m_section_headers.append(_t__m_section_headers)
                    self._debug['_m_section_headers']['arr'][i]['end'] = self._io.pos()

            self._debug['_m_section_headers']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_section_headers', None)

        @property
        def section_names(self):
            if hasattr(self, '_m_section_names'):
                return self._m_section_names

            if  ((self.section_names_idx != int(Elf.SectionHeaderIdxSpecial.undefined)) and (self.section_names_idx < self._root.header.num_section_headers)) :
                pass
                _pos = self._io.pos()
                self._io.seek(self.section_headers[self.section_names_idx].ofs_body)
                if self._is_le:
                    self._debug['_m_section_names']['start'] = self._io.pos()
                    self._raw__m_section_names = self._io.read_bytes(self.section_headers[self.section_names_idx].len_body)
                    _io__raw__m_section_names = KaitaiStream(BytesIO(self._raw__m_section_names))
                    self._m_section_names = Elf.EndianElf.StringsStruct(_io__raw__m_section_names, self, self._root, self._is_le)
                    self._m_section_names._read()
                    self._debug['_m_section_names']['end'] = self._io.pos()
                else:
                    self._debug['_m_section_names']['start'] = self._io.pos()
                    self._raw__m_section_names = self._io.read_bytes(self.section_headers[self.section_names_idx].len_body)
                    _io__raw__m_section_names = KaitaiStream(BytesIO(self._raw__m_section_names))
                    self._m_section_names = Elf.EndianElf.StringsStruct(_io__raw__m_section_names, self, self._root, self._is_le)
                    self._m_section_names._read()
                    self._debug['_m_section_names']['end'] = self._io.pos()
                self._io.seek(_pos)

            return getattr(self, '_m_section_names', None)


    class PhdrTypeFlags(KaitaiStruct):
        SEQ_FIELDS = []
        def __init__(self, value, _io, _parent=None, _root=None):
            super(Elf.PhdrTypeFlags, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.value = value
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass

        @property
        def execute(self):
            if hasattr(self, '_m_execute'):
                return self._m_execute

            self._m_execute = self.value & 1 != 0
            return getattr(self, '_m_execute', None)

        @property
        def mask_proc(self):
            if hasattr(self, '_m_mask_proc'):
                return self._m_mask_proc

            self._m_mask_proc = self.value & 4026531840 != 0
            return getattr(self, '_m_mask_proc', None)

        @property
        def read(self):
            if hasattr(self, '_m_read'):
                return self._m_read

            self._m_read = self.value & 4 != 0
            return getattr(self, '_m_read', None)

        @property
        def write(self):
            if hasattr(self, '_m_write'):
                return self._m_write

            self._m_write = self.value & 2 != 0
            return getattr(self, '_m_write', None)


    class SectionHeaderFlags(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html#GUID-2CBE4879-2E76-426E-BB7F-CF0CB1D87C52__CHAPTER6-10675
        
        
        .. seealso::
           Source - https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/include/elf/common.h#L614
        
        
        .. seealso::
           Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L468
        """
        SEQ_FIELDS = []
        def __init__(self, value, _io, _parent=None, _root=None):
            super(Elf.SectionHeaderFlags, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.value = value
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass

        @property
        def alloc(self):
            """Occupies memory during execution."""
            if hasattr(self, '_m_alloc'):
                return self._m_alloc

            self._m_alloc = self.value & 2 != 0
            return getattr(self, '_m_alloc', None)

        @property
        def compressed(self):
            """Section with compressed data."""
            if hasattr(self, '_m_compressed'):
                return self._m_compressed

            self._m_compressed = self.value & 2048 != 0
            return getattr(self, '_m_compressed', None)

        @property
        def exclude(self):
            """Section is excluded unless referenced or allocated (Solaris)."""
            if hasattr(self, '_m_exclude'):
                return self._m_exclude

            self._m_exclude = self.value & 2147483648 != 0
            return getattr(self, '_m_exclude', None)

        @property
        def exec_instr(self):
            """Executable machine instructions."""
            if hasattr(self, '_m_exec_instr'):
                return self._m_exec_instr

            self._m_exec_instr = self.value & 4 != 0
            return getattr(self, '_m_exec_instr', None)

        @property
        def gnu_mbind(self):
            """Mbind section.
            
            .. seealso::
               Source - https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/include/elf/common.h#L631
            """
            if hasattr(self, '_m_gnu_mbind'):
                return self._m_gnu_mbind

            self._m_gnu_mbind = self.value & 16777216 != 0
            return getattr(self, '_m_gnu_mbind', None)

        @property
        def group(self):
            """Member of a section group."""
            if hasattr(self, '_m_group'):
                return self._m_group

            self._m_group = self.value & 512 != 0
            return getattr(self, '_m_group', None)

        @property
        def info_link(self):
            """Section header's `sh_info` field holds a section header table index
            """
            if hasattr(self, '_m_info_link'):
                return self._m_info_link

            self._m_info_link = self.value & 64 != 0
            return getattr(self, '_m_info_link', None)

        @property
        def link_order(self):
            """Preserve section ordering when linking."""
            if hasattr(self, '_m_link_order'):
                return self._m_link_order

            self._m_link_order = self.value & 128 != 0
            return getattr(self, '_m_link_order', None)

        @property
        def mask_os(self):
            """OS-specific semantics."""
            if hasattr(self, '_m_mask_os'):
                return self._m_mask_os

            self._m_mask_os = self.value & 267386880 != 0
            return getattr(self, '_m_mask_os', None)

        @property
        def mask_proc(self):
            """Processor-specific semantics."""
            if hasattr(self, '_m_mask_proc'):
                return self._m_mask_proc

            self._m_mask_proc = self.value & 4026531840 != 0
            return getattr(self, '_m_mask_proc', None)

        @property
        def merge(self):
            """Data in this section can be merged to eliminate duplication."""
            if hasattr(self, '_m_merge'):
                return self._m_merge

            self._m_merge = self.value & 16 != 0
            return getattr(self, '_m_merge', None)

        @property
        def ordered(self):
            """Special ordering requirement (Solaris)
            
            From <https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html#GUID-2CBE4879-2E76-426E-BB7F-CF0CB1D87C52__CHAPTER6-10675>:
            
            > `SHF_ORDERED` is an older version of the functionality provided by
            > `SHF_LINK_ORDER`, and has been superseded by `SHF_LINK_ORDER`.
            > `SHF_ORDERED` is no longer supported.
            
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L485
            
            
            .. seealso::
               Source - https://docs.oracle.com/en/operating-systems/solaris/oracle-solaris/11.4/linkers-libraries/section-headers.html#GUID-2CBE4879-2E76-426E-BB7F-CF0CB1D87C52__CHAPTER6-10675
            """
            if hasattr(self, '_m_ordered'):
                return self._m_ordered

            self._m_ordered = self.value & 1073741824 != 0
            return getattr(self, '_m_ordered', None)

        @property
        def os_nonconforming(self):
            """Special OS-specific handling required."""
            if hasattr(self, '_m_os_nonconforming'):
                return self._m_os_nonconforming

            self._m_os_nonconforming = self.value & 256 != 0
            return getattr(self, '_m_os_nonconforming', None)

        @property
        def retain(self):
            """Section should not be garbage collected by the linker.
            
            .. seealso::
               Source - https://forge.sourceware.org/binutils-gdb/binutils-gdb-mirror/src/tag/binutils-2_46_1/include/elf/common.h#L630
            
            
            
            .. seealso::
               Source - https://forge.sourceware.org/glibc/glibc-mirror/src/tag/glibc-2.43/elf/elf.h#L484
            """
            if hasattr(self, '_m_retain'):
                return self._m_retain

            self._m_retain = self.value & 2097152 != 0
            return getattr(self, '_m_retain', None)

        @property
        def strings(self):
            """Contains null-terminated character strings."""
            if hasattr(self, '_m_strings'):
                return self._m_strings

            self._m_strings = self.value & 32 != 0
            return getattr(self, '_m_strings', None)

        @property
        def tls(self):
            """Thread-local storage section (`.tbss` or `.tdata` according to [ELF
            Handling For Thread-Local
            Storage](https://www.akkadia.org/drepper/tls.pdf))
            """
            if hasattr(self, '_m_tls'):
                return self._m_tls

            self._m_tls = self.value & 1024 != 0
            return getattr(self, '_m_tls', None)

        @property
        def write(self):
            """Writable during execution."""
            if hasattr(self, '_m_write'):
                return self._m_write

            self._m_write = self.value & 1 != 0
            return getattr(self, '_m_write', None)


    @property
    def sh_idx_hi_os(self):
        if hasattr(self, '_m_sh_idx_hi_os'):
            return self._m_sh_idx_hi_os

        self._m_sh_idx_hi_os = 65343
        return getattr(self, '_m_sh_idx_hi_os', None)

    @property
    def sh_idx_hi_proc(self):
        if hasattr(self, '_m_sh_idx_hi_proc'):
            return self._m_sh_idx_hi_proc

        self._m_sh_idx_hi_proc = 65311
        return getattr(self, '_m_sh_idx_hi_proc', None)

    @property
    def sh_idx_hi_reserved(self):
        if hasattr(self, '_m_sh_idx_hi_reserved'):
            return self._m_sh_idx_hi_reserved

        self._m_sh_idx_hi_reserved = 65535
        return getattr(self, '_m_sh_idx_hi_reserved', None)

    @property
    def sh_idx_lo_os(self):
        if hasattr(self, '_m_sh_idx_lo_os'):
            return self._m_sh_idx_lo_os

        self._m_sh_idx_lo_os = 65312
        return getattr(self, '_m_sh_idx_lo_os', None)

    @property
    def sh_idx_lo_proc(self):
        if hasattr(self, '_m_sh_idx_lo_proc'):
            return self._m_sh_idx_lo_proc

        self._m_sh_idx_lo_proc = 65280
        return getattr(self, '_m_sh_idx_lo_proc', None)

    @property
    def sh_idx_lo_reserved(self):
        if hasattr(self, '_m_sh_idx_lo_reserved'):
            return self._m_sh_idx_lo_reserved

        self._m_sh_idx_lo_reserved = 65280
        return getattr(self, '_m_sh_idx_lo_reserved', None)


