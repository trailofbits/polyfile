# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Mp4(KaitaiStruct):

    class Fourcc(Enum):
        avc1 = 1635148593
        avc_c = 1635148611
        dfl8 = 1684433976
        dinf = 1684631142
        dref = 1685218662
        edts = 1701082227
        elst = 1701606260
        ftyp = 1718909296
        hdlr = 1751411826
        mdat = 1835295092
        mdhd = 1835296868
        mdia = 1835297121
        minf = 1835626086
        moof = 1836019558
        moov = 1836019574
        mvex = 1836475768
        mvhd = 1836476516
        prhd = 1886546020
        proj = 1886547818
        sidx = 1936286840
        st3d = 1936995172
        stbl = 1937007212
        stco = 1937007471
        stsc = 1937011555
        stsd = 1937011556
        stss = 1937011571
        stsz = 1937011578
        stts = 1937011827
        sv3d = 1937126244
        svhd = 1937139812
        tkhd = 1953196132
        trak = 1953653099
        url = 1970433056
        uuid = 1970628964
        vmhd = 1986881636
        ytmp = 2037673328
    SEQ_FIELDS = ["boxes"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['boxes']['start'] = self._io.pos()
        self.boxes = []
        i = 0
        while not self._io.is_eof():
            if not 'arr' in self._debug['boxes']:
                self._debug['boxes']['arr'] = []
            self._debug['boxes']['arr'].append({'start': self._io.pos()})
            _t_boxes = Mp4.Box(self._io, self, self._root)
            _t_boxes._read()
            self.boxes.append(_t_boxes)
            self._debug['boxes']['arr'][len(self.boxes) - 1]['end'] = self._io.pos()
            i += 1

        self._debug['boxes']['end'] = self._io.pos()

    class Dref(KaitaiStruct):
        SEQ_FIELDS = ["unknown_x0", "boxes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['unknown_x0']['start'] = self._io.pos()
            self.unknown_x0 = self._io.read_bytes(8)
            self._debug['unknown_x0']['end'] = self._io.pos()
            self._debug['boxes']['start'] = self._io.pos()
            self.boxes = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['boxes']:
                    self._debug['boxes']['arr'] = []
                self._debug['boxes']['arr'].append({'start': self._io.pos()})
                _t_boxes = Mp4.Box(self._io, self, self._root)
                _t_boxes._read()
                self.boxes.append(_t_boxes)
                self._debug['boxes']['arr'][len(self.boxes) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['boxes']['end'] = self._io.pos()


    class Stsd(KaitaiStruct):
        SEQ_FIELDS = ["unknown_x0", "boxes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['unknown_x0']['start'] = self._io.pos()
            self.unknown_x0 = self._io.read_u8be()
            self._debug['unknown_x0']['end'] = self._io.pos()
            self._debug['boxes']['start'] = self._io.pos()
            self.boxes = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['boxes']:
                    self._debug['boxes']['arr'] = []
                self._debug['boxes']['arr'].append({'start': self._io.pos()})
                _t_boxes = Mp4.Box(self._io, self, self._root)
                _t_boxes._read()
                self.boxes.append(_t_boxes)
                self._debug['boxes']['arr'][len(self.boxes) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['boxes']['end'] = self._io.pos()


    class BoxContainer(KaitaiStruct):
        SEQ_FIELDS = ["boxes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['boxes']['start'] = self._io.pos()
            self.boxes = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['boxes']:
                    self._debug['boxes']['arr'] = []
                self._debug['boxes']['arr'].append({'start': self._io.pos()})
                _t_boxes = Mp4.Box(self._io, self, self._root)
                _t_boxes._read()
                self.boxes.append(_t_boxes)
                self._debug['boxes']['arr'][len(self.boxes) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['boxes']['end'] = self._io.pos()


    class Uuid(KaitaiStruct):
        SEQ_FIELDS = ["uuid", "xml_metadata"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['uuid']['start'] = self._io.pos()
            self.uuid = self._io.read_bytes(16)
            self._debug['uuid']['end'] = self._io.pos()
            self._debug['xml_metadata']['start'] = self._io.pos()
            self.xml_metadata = self._io.read_bytes_full()
            self._debug['xml_metadata']['end'] = self._io.pos()


    class Ytmp(KaitaiStruct):
        SEQ_FIELDS = ["unknown_x0", "crc", "encoding", "payload"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['unknown_x0']['start'] = self._io.pos()
            self.unknown_x0 = self._io.read_u4be()
            self._debug['unknown_x0']['end'] = self._io.pos()
            self._debug['crc']['start'] = self._io.pos()
            self.crc = self._io.read_u4be()
            self._debug['crc']['end'] = self._io.pos()
            self._debug['encoding']['start'] = self._io.pos()
            self.encoding = KaitaiStream.resolve_enum(Mp4.Fourcc, self._io.read_u4be())
            self._debug['encoding']['end'] = self._io.pos()
            self._debug['payload']['start'] = self._io.pos()
            _on = self.encoding
            if _on == Mp4.Fourcc.dfl8:
                self.payload = Mp4.YtmpPayloadZlib(self._io, self, self._root)
                self.payload._read()
            self._debug['payload']['end'] = self._io.pos()


    class Avc1(KaitaiStruct):
        SEQ_FIELDS = ["unknown_x0", "boxes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['unknown_x0']['start'] = self._io.pos()
            self.unknown_x0 = self._io.read_bytes(78)
            self._debug['unknown_x0']['end'] = self._io.pos()
            self._debug['boxes']['start'] = self._io.pos()
            self.boxes = []
            i = 0
            while not self._io.is_eof():
                if not 'arr' in self._debug['boxes']:
                    self._debug['boxes']['arr'] = []
                self._debug['boxes']['arr'].append({'start': self._io.pos()})
                _t_boxes = Mp4.Box(self._io, self, self._root)
                _t_boxes._read()
                self.boxes.append(_t_boxes)
                self._debug['boxes']['arr'][len(self.boxes) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['boxes']['end'] = self._io.pos()


    class Box(KaitaiStruct):
        SEQ_FIELDS = ["length", "type", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['length']['start'] = self._io.pos()
            self.length = self._io.read_u4be()
            self._debug['length']['end'] = self._io.pos()
            self._debug['type']['start'] = self._io.pos()
            self.type = KaitaiStream.resolve_enum(Mp4.Fourcc, self._io.read_u4be())
            self._debug['type']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            _on = self.type
            if _on == Mp4.Fourcc.sv3d:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.ytmp:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.Ytmp(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.stbl:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.trak:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.minf:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.dref:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.Dref(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.stsd:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.Stsd(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.dinf:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.moov:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.mdia:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.edts:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.uuid:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.Uuid(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.avc1:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.Avc1(_io__raw_data, self, self._root)
                self.data._read()
            elif _on == Mp4.Fourcc.proj:
                self._raw_data = self._io.read_bytes((self.length - 8))
                _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                self.data = Mp4.BoxContainer(_io__raw_data, self, self._root)
                self.data._read()
            else:
                self.data = self._io.read_bytes((self.length - 8))
            self._debug['data']['end'] = self._io.pos()


    class YtmpPayloadZlib(KaitaiStruct):
        SEQ_FIELDS = ["data"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes_full()
            self._debug['data']['end'] = self._io.pos()



