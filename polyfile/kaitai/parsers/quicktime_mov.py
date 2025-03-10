# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class QuicktimeMov(KaitaiStruct):
    """
    .. seealso::
       Source - https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFChap1/qtff1.html#//apple_ref/doc/uid/TP40000939-CH203-BBCGDDDF
    """

    class AtomType(Enum):
        xtra = 1484026465
        dinf = 1684631142
        dref = 1685218662
        edts = 1701082227
        elst = 1701606260
        free = 1718773093
        ftyp = 1718909296
        hdlr = 1751411826
        iods = 1768907891
        mdat = 1835295092
        mdhd = 1835296868
        mdia = 1835297121
        meta = 1835365473
        minf = 1835626086
        moof = 1836019558
        moov = 1836019574
        mvhd = 1836476516
        smhd = 1936549988
        stbl = 1937007212
        stco = 1937007471
        stsc = 1937011555
        stsd = 1937011556
        stsz = 1937011578
        stts = 1937011827
        tkhd = 1953196132
        traf = 1953653094
        trak = 1953653099
        tref = 1953654118
        udta = 1969517665
        vmhd = 1986881636

    class Brand(Enum):
        x_3g2a = 862401121
        x_3ge6 = 862414134
        x_3ge7 = 862414135
        x_3ge9 = 862414137
        x_3gf9 = 862414393
        x_3gg6 = 862414646
        x_3gg9 = 862414649
        x_3gh9 = 862414905
        x_3gm9 = 862416185
        x_3gma = 862416193
        x_3gp4 = 862416948
        x_3gp5 = 862416949
        x_3gp6 = 862416950
        x_3gp7 = 862416951
        x_3gp8 = 862416952
        x_3gp9 = 862416953
        x_3gr6 = 862417462
        x_3gr9 = 862417465
        x_3gs6 = 862417718
        x_3gs9 = 862417721
        x_3gt8 = 862417976
        x_3gt9 = 862417977
        x_3gtv = 862418038
        x_3gvr = 862418546
        x_3vra = 863400545
        x_3vrb = 863400546
        x_3vrm = 863400557
        arri = 1095914057
        caep = 1128351056
        cdes = 1128555891
        j2p0 = 1244811312
        j2p1 = 1244811313
        lcag = 1279476039
        m4a = 1295270176
        m4b = 1295270432
        m4p = 1295274016
        m4v = 1295275552
        ma1a = 1296118081
        ma1b = 1296118082
        mfsm = 1296454477
        mgsv = 1296520022
        mppi = 1297109065
        msnv = 1297305174
        miab = 1298743618
        miac = 1298743619
        mian = 1298743662
        mibu = 1298743925
        micm = 1298744173
        miha = 1298745409
        mihb = 1298745410
        mihe = 1298745413
        mipr = 1298747506
        ross = 1380930387
        seau = 1397047637
        sebk = 1397047883
        xavc = 1480676931
        adti = 1633973353
        aid3 = 1634296883
        av01 = 1635135537
        avc1 = 1635148593
        avci = 1635148649
        avcs = 1635148659
        avde = 1635148901
        avif = 1635150182
        avio = 1635150191
        avis = 1635150195
        bbxm = 1650620525
        ca4m = 1667314797
        ca4s = 1667314803
        caaa = 1667326305
        caac = 1667326307
        cabl = 1667326572
        cama = 1667329377
        camc = 1667329379
        caqv = 1667330422
        casu = 1667330933
        ccea = 1667458401
        ccff = 1667458662
        cdm1 = 1667525937
        cdm4 = 1667525940
        ceac = 1667588451
        cfhd = 1667655780
        cfsd = 1667658596
        chd1 = 1667785777
        chd2 = 1667785778
        chdf = 1667785830
        chev = 1667786102
        chh1 = 1667786801
        chhd = 1667786852
        cint = 1667853940
        clg1 = 1668048689
        clg2 = 1668048690
        cmf2 = 1668113970
        cmfc = 1668114019
        cmff = 1668114022
        cmfl = 1668114028
        cmfs = 1668114035
        cmhm = 1668114541
        cmhs = 1668114547
        comp = 1668246896
        csh1 = 1668507697
        cud1 = 1668637745
        cud2 = 1668637746
        cud8 = 1668637752
        cud9 = 1668637753
        cuvd = 1668642404
        cvid = 1668704612
        cvvc = 1668707939
        cwvt = 1668773492
        da0a = 1684090977
        da0b = 1684090978
        da1a = 1684091233
        da1b = 1684091234
        da2a = 1684091489
        da2b = 1684091490
        da3a = 1684091745
        da3b = 1684091746
        dash = 1684108136
        dby1 = 1684175153
        dmb1 = 1684890161
        dsms = 1685286259
        dts1 = 1685353265
        dts2 = 1685353266
        dts3 = 1685353267
        dv1a = 1685467489
        dv1b = 1685467490
        dv2a = 1685467745
        dv2b = 1685467746
        dv3a = 1685468001
        dv3b = 1685468002
        dvr1 = 1685484081
        dvt1 = 1685484593
        dxo = 1685614368
        emsg = 1701671783
        heic = 1751476579
        heim = 1751476589
        heis = 1751476595
        heix = 1751476600
        heoi = 1751478121
        hevc = 1751479907
        hevd = 1751479908
        hevi = 1751479913
        hevm = 1751479917
        hevs = 1751479923
        hevx = 1751479928
        hvce = 1752589157
        hvci = 1752589161
        hvcx = 1752589176
        hvti = 1752593513
        ifaa = 1768317281
        ifah = 1768317288
        ifai = 1768317289
        ifas = 1768317299
        ifau = 1768317301
        ifav = 1768317302
        ifhd = 1768319076
        ifhh = 1768319080
        ifhr = 1768319090
        ifhs = 1768319091
        ifhu = 1768319093
        ifhx = 1768319096
        ifrm = 1768321645
        ifsd = 1768321892
        im1i = 1768763753
        im1t = 1768763764
        im2i = 1768764009
        im2t = 1768764020
        isc2 = 1769169714
        iso2 = 1769172786
        iso3 = 1769172787
        iso4 = 1769172788
        iso5 = 1769172789
        iso6 = 1769172790
        iso7 = 1769172791
        iso8 = 1769172792
        iso9 = 1769172793
        isoa = 1769172833
        isob = 1769172834
        isoc = 1769172835
        isom = 1769172845
        j2is = 1781688691
        j2ki = 1781689193
        j2ks = 1781689203
        jp2 = 1785737760
        jpeg = 1785750887
        jpgs = 1785751411
        jpm = 1785752864
        jpoi = 1785753449
        jpsi = 1785754473
        jpx = 1785755680
        jpxb = 1785755746
        jxl = 1786276896
        jxs = 1786278688
        jxsc = 1786278755
        jxsi = 1786278761
        jxss = 1786278771
        lhte = 1818784869
        lhti = 1818784873
        lmsg = 1819112295
        miaf = 1835622758
        mif1 = 1835623985
        mif2 = 1835623986
        mj2s = 1835676275
        mjp2 = 1835692082
        mp21 = 1836069425
        mp41 = 1836069937
        mp42 = 1836069938
        mp71 = 1836070705
        mpuf = 1836086630
        msdh = 1836278888
        msf1 = 1836279345
        msix = 1836280184
        niko = 1852402543
        nlsl = 1852601196
        nras = 1852989811
        oa2d = 1868640868
        oabl = 1868653164
        odcf = 1868850022
        ompp = 1869443184
        opf2 = 1869637170
        opx2 = 1869641778
        ovdp = 1870029936
        ovly = 1870031993
        paff = 1885431398
        pana = 1885433441
        piff = 1885955686
        pmff = 1886217830
        pnvi = 1886287465
        pred = 1886545252
        qt = 1903435808
        relo = 1919249519
        risx = 1919513464
        sdv = 1935963680
        senv = 1936027254
        sims = 1936289139
        sisx = 1936290680
        siti = 1936290921
        sitv = 1936290934
        slh1 = 1936484401
        slh2 = 1936484402
        slh3 = 1936484403
        ssss = 1936946035
        ttml = 1953787244
        ttwv = 1953789814
        uhvi = 1969780329
        unif = 1970170214
        uvvu = 1970697845
        v3mp = 1983081840
        v3mt = 1983081844
        v3nt = 1983082100
        v3st = 1983083380
        vvci = 1987470185
        vvoi = 1987473257
        vwpt = 1987539060
        yt4 = 2037658656
    SEQ_FIELDS = ["atoms"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['atoms']['start'] = self._io.pos()
        self.atoms = QuicktimeMov.AtomList(self._io, self, self._root)
        self.atoms._read()
        self._debug['atoms']['end'] = self._io.pos()

    class MvhdBody(KaitaiStruct):
        """
        .. seealso::
           Source - https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html#//apple_ref/doc/uid/TP40000939-CH204-BBCGFGJG
        """
        SEQ_FIELDS = ["version", "flags", "creation_time", "modification_time", "time_scale", "duration", "preferred_rate", "preferred_volume", "reserved1", "matrix", "preview_time", "preview_duration", "poster_time", "selection_time", "selection_duration", "current_time", "next_track_id"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u1()
            self._debug['version']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_bytes(3)
            self._debug['flags']['end'] = self._io.pos()
            self._debug['creation_time']['start'] = self._io.pos()
            self.creation_time = self._io.read_u4be()
            self._debug['creation_time']['end'] = self._io.pos()
            self._debug['modification_time']['start'] = self._io.pos()
            self.modification_time = self._io.read_u4be()
            self._debug['modification_time']['end'] = self._io.pos()
            self._debug['time_scale']['start'] = self._io.pos()
            self.time_scale = self._io.read_u4be()
            self._debug['time_scale']['end'] = self._io.pos()
            self._debug['duration']['start'] = self._io.pos()
            self.duration = self._io.read_u4be()
            self._debug['duration']['end'] = self._io.pos()
            self._debug['preferred_rate']['start'] = self._io.pos()
            self.preferred_rate = QuicktimeMov.Fixed32(self._io, self, self._root)
            self.preferred_rate._read()
            self._debug['preferred_rate']['end'] = self._io.pos()
            self._debug['preferred_volume']['start'] = self._io.pos()
            self.preferred_volume = QuicktimeMov.Fixed16(self._io, self, self._root)
            self.preferred_volume._read()
            self._debug['preferred_volume']['end'] = self._io.pos()
            self._debug['reserved1']['start'] = self._io.pos()
            self.reserved1 = self._io.read_bytes(10)
            self._debug['reserved1']['end'] = self._io.pos()
            self._debug['matrix']['start'] = self._io.pos()
            self.matrix = self._io.read_bytes(36)
            self._debug['matrix']['end'] = self._io.pos()
            self._debug['preview_time']['start'] = self._io.pos()
            self.preview_time = self._io.read_u4be()
            self._debug['preview_time']['end'] = self._io.pos()
            self._debug['preview_duration']['start'] = self._io.pos()
            self.preview_duration = self._io.read_u4be()
            self._debug['preview_duration']['end'] = self._io.pos()
            self._debug['poster_time']['start'] = self._io.pos()
            self.poster_time = self._io.read_u4be()
            self._debug['poster_time']['end'] = self._io.pos()
            self._debug['selection_time']['start'] = self._io.pos()
            self.selection_time = self._io.read_u4be()
            self._debug['selection_time']['end'] = self._io.pos()
            self._debug['selection_duration']['start'] = self._io.pos()
            self.selection_duration = self._io.read_u4be()
            self._debug['selection_duration']['end'] = self._io.pos()
            self._debug['current_time']['start'] = self._io.pos()
            self.current_time = self._io.read_u4be()
            self._debug['current_time']['end'] = self._io.pos()
            self._debug['next_track_id']['start'] = self._io.pos()
            self.next_track_id = self._io.read_u4be()
            self._debug['next_track_id']['end'] = self._io.pos()


    class FtypBody(KaitaiStruct):
        """
        .. seealso::
           Source - https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFChap1/qtff1.html#//apple_ref/doc/uid/TP40000939-CH203-CJBCBIFF
        """
        SEQ_FIELDS = ["major_brand", "minor_version", "compatible_brands"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['major_brand']['start'] = self._io.pos()
            self.major_brand = KaitaiStream.resolve_enum(QuicktimeMov.Brand, self._io.read_u4be())
            self._debug['major_brand']['end'] = self._io.pos()
            self._debug['minor_version']['start'] = self._io.pos()
            self.minor_version = self._io.read_bytes(4)
            self._debug['minor_version']['end'] = self._io.pos()
            self._debug['compatible_brands']['start'] = self._io.pos()
            self.compatible_brands = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['compatible_brands']:
                    self._debug['compatible_brands']['arr'] = []
                self._debug['compatible_brands']['arr'].append({'start': self._io.pos()})
                self.compatible_brands.append(KaitaiStream.resolve_enum(QuicktimeMov.Brand, self._io.read_u4be()))
                self._debug['compatible_brands']['arr'][len(self.compatible_brands) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['compatible_brands']['end'] = self._io.pos()


    class Fixed32(KaitaiStruct):
        """Fixed-point 32-bit number."""
        SEQ_FIELDS = ["int_part", "frac_part"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['int_part']['start'] = self._io.pos()
            self.int_part = self._io.read_s2be()
            self._debug['int_part']['end'] = self._io.pos()
            self._debug['frac_part']['start'] = self._io.pos()
            self.frac_part = self._io.read_u2be()
            self._debug['frac_part']['end'] = self._io.pos()


    class Fixed16(KaitaiStruct):
        """Fixed-point 16-bit number."""
        SEQ_FIELDS = ["int_part", "frac_part"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['int_part']['start'] = self._io.pos()
            self.int_part = self._io.read_s1()
            self._debug['int_part']['end'] = self._io.pos()
            self._debug['frac_part']['start'] = self._io.pos()
            self.frac_part = self._io.read_u1()
            self._debug['frac_part']['end'] = self._io.pos()


    class Atom(KaitaiStruct):
        SEQ_FIELDS = ["len32", "atom_type", "len64", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len32']['start'] = self._io.pos()
            self.len32 = self._io.read_u4be()
            self._debug['len32']['end'] = self._io.pos()
            self._debug['atom_type']['start'] = self._io.pos()
            self.atom_type = KaitaiStream.resolve_enum(QuicktimeMov.AtomType, self._io.read_u4be())
            self._debug['atom_type']['end'] = self._io.pos()
            if self.len32 == 1:
                self._debug['len64']['start'] = self._io.pos()
                self.len64 = self._io.read_u8be()
                self._debug['len64']['end'] = self._io.pos()

            self._debug['body']['start'] = self._io.pos()
            _on = self.atom_type
            if _on == QuicktimeMov.AtomType.moof:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.tkhd:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.TkhdBody(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.stbl:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.traf:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.minf:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.trak:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.moov:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.mdia:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.dinf:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.AtomList(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.mvhd:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.MvhdBody(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == QuicktimeMov.AtomType.ftyp:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = QuicktimeMov.FtypBody(_io__raw_body, self, self._root)
                self.body._read()
            else:
                self.body = self._io.read_bytes(self.len)
            self._debug['body']['end'] = self._io.pos()

        @property
        def len(self):
            if hasattr(self, '_m_len'):
                return self._m_len if hasattr(self, '_m_len') else None

            self._m_len = ((self._io.size() - 8) if self.len32 == 0 else ((self.len64 - 16) if self.len32 == 1 else (self.len32 - 8)))
            return self._m_len if hasattr(self, '_m_len') else None


    class TkhdBody(KaitaiStruct):
        """
        .. seealso::
           Source - https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html#//apple_ref/doc/uid/TP40000939-CH204-25550
        """
        SEQ_FIELDS = ["version", "flags", "creation_time", "modification_time", "track_id", "reserved1", "duration", "reserved2", "layer", "alternative_group", "volume", "reserved3", "matrix", "width", "height"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u1()
            self._debug['version']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_bytes(3)
            self._debug['flags']['end'] = self._io.pos()
            self._debug['creation_time']['start'] = self._io.pos()
            self.creation_time = self._io.read_u4be()
            self._debug['creation_time']['end'] = self._io.pos()
            self._debug['modification_time']['start'] = self._io.pos()
            self.modification_time = self._io.read_u4be()
            self._debug['modification_time']['end'] = self._io.pos()
            self._debug['track_id']['start'] = self._io.pos()
            self.track_id = self._io.read_u4be()
            self._debug['track_id']['end'] = self._io.pos()
            self._debug['reserved1']['start'] = self._io.pos()
            self.reserved1 = self._io.read_bytes(4)
            self._debug['reserved1']['end'] = self._io.pos()
            self._debug['duration']['start'] = self._io.pos()
            self.duration = self._io.read_u4be()
            self._debug['duration']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_bytes(8)
            self._debug['reserved2']['end'] = self._io.pos()
            self._debug['layer']['start'] = self._io.pos()
            self.layer = self._io.read_u2be()
            self._debug['layer']['end'] = self._io.pos()
            self._debug['alternative_group']['start'] = self._io.pos()
            self.alternative_group = self._io.read_u2be()
            self._debug['alternative_group']['end'] = self._io.pos()
            self._debug['volume']['start'] = self._io.pos()
            self.volume = self._io.read_u2be()
            self._debug['volume']['end'] = self._io.pos()
            self._debug['reserved3']['start'] = self._io.pos()
            self.reserved3 = self._io.read_u2be()
            self._debug['reserved3']['end'] = self._io.pos()
            self._debug['matrix']['start'] = self._io.pos()
            self.matrix = self._io.read_bytes(36)
            self._debug['matrix']['end'] = self._io.pos()
            self._debug['width']['start'] = self._io.pos()
            self.width = QuicktimeMov.Fixed32(self._io, self, self._root)
            self.width._read()
            self._debug['width']['end'] = self._io.pos()
            self._debug['height']['start'] = self._io.pos()
            self.height = QuicktimeMov.Fixed32(self._io, self, self._root)
            self.height._read()
            self._debug['height']['end'] = self._io.pos()


    class AtomList(KaitaiStruct):
        SEQ_FIELDS = ["items"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['items']['start'] = self._io.pos()
            self.items = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['items']:
                    self._debug['items']['arr'] = []
                self._debug['items']['arr'].append({'start': self._io.pos()})
                _t_items = QuicktimeMov.Atom(self._io, self, self._root)
                _t_items._read()
                self.items.append(_t_items)
                self._debug['items']['arr'][len(self.items) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['items']['end'] = self._io.pos()



