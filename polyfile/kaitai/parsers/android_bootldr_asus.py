# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidBootldrAsus(KaitaiStruct):
    """A bootloader image which only seems to have been used on a few ASUS
    devices. The encoding is ASCII, because the `releasetools.py` script
    is written using Python 2, where the default encoding is ASCII.
    
    A test file can be found in the firmware files for the "fugu" device,
    which can be downloaded from <https://developers.google.com/android/images>
    
    .. seealso::
       Source - https://android.googlesource.com/device/asus/fugu/+/android-8.1.0_r5/releasetools.py
    """
    SEQ_FIELDS = ["magic", "revision", "reserved1", "reserved2", "images"]
    def __init__(self, _io, _parent=None, _root=None):
        super(AndroidBootldrAsus, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(8)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x42\x4F\x4F\x54\x4C\x44\x52\x21":
            raise kaitaistruct.ValidationNotEqualError(b"\x42\x4F\x4F\x54\x4C\x44\x52\x21", self.magic, self._io, u"/seq/0")
        self._debug['revision']['start'] = self._io.pos()
        self.revision = self._io.read_u2le()
        self._debug['revision']['end'] = self._io.pos()
        if not self.revision >= 2:
            raise kaitaistruct.ValidationLessThanError(2, self.revision, self._io, u"/seq/1")
        self._debug['reserved1']['start'] = self._io.pos()
        self.reserved1 = self._io.read_u2le()
        self._debug['reserved1']['end'] = self._io.pos()
        self._debug['reserved2']['start'] = self._io.pos()
        self.reserved2 = self._io.read_u4le()
        self._debug['reserved2']['end'] = self._io.pos()
        self._debug['images']['start'] = self._io.pos()
        self._debug['images']['arr'] = []
        self.images = []
        for i in range(3):
            self._debug['images']['arr'].append({'start': self._io.pos()})
            _t_images = AndroidBootldrAsus.Image(self._io, self, self._root)
            try:
                _t_images._read()
            finally:
                self.images.append(_t_images)
            self._debug['images']['arr'][i]['end'] = self._io.pos()

        self._debug['images']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.images)):
            pass
            self.images[i]._fetch_instances()


    class Image(KaitaiStruct):
        SEQ_FIELDS = ["chunk_id", "len_body", "flags", "reserved1", "reserved2", "reserved3", "body"]
        def __init__(self, _io, _parent=None, _root=None):
            super(AndroidBootldrAsus.Image, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['chunk_id']['start'] = self._io.pos()
            self.chunk_id = (self._io.read_bytes(8)).decode(u"ASCII")
            self._debug['chunk_id']['end'] = self._io.pos()
            if not  ((self.chunk_id == u"IFWI!!!!") or (self.chunk_id == u"DROIDBT!") or (self.chunk_id == u"SPLASHS!")) :
                raise kaitaistruct.ValidationNotAnyOfError(self.chunk_id, self._io, u"/types/image/seq/0")
            self._debug['len_body']['start'] = self._io.pos()
            self.len_body = self._io.read_u4le()
            self._debug['len_body']['end'] = self._io.pos()
            self._debug['flags']['start'] = self._io.pos()
            self.flags = self._io.read_u1()
            self._debug['flags']['end'] = self._io.pos()
            _ = self.flags
            if not _ & 1 != 0:
                raise kaitaistruct.ValidationExprError(self.flags, self._io, u"/types/image/seq/2")
            self._debug['reserved1']['start'] = self._io.pos()
            self.reserved1 = self._io.read_u1()
            self._debug['reserved1']['end'] = self._io.pos()
            self._debug['reserved2']['start'] = self._io.pos()
            self.reserved2 = self._io.read_u1()
            self._debug['reserved2']['end'] = self._io.pos()
            self._debug['reserved3']['start'] = self._io.pos()
            self.reserved3 = self._io.read_u1()
            self._debug['reserved3']['end'] = self._io.pos()
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes(self.len_body)
            self._debug['body']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def file_name(self):
            if hasattr(self, '_m_file_name'):
                return self._m_file_name

            self._m_file_name = (u"ifwi.bin" if self.chunk_id == u"IFWI!!!!" else (u"droidboot.img" if self.chunk_id == u"DROIDBT!" else (u"splashscreen.img" if self.chunk_id == u"SPLASHS!" else u"")))
            return getattr(self, '_m_file_name', None)



