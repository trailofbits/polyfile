# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class AndroidBootldrQcom(KaitaiStruct):
    """A bootloader for Android used on various devices powered by Qualcomm
    Snapdragon chips:
    
    <https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors>
    
    Although not all of the Snapdragon based Android devices use this particular
    bootloader format, it is known that devices with the following chips have used
    it (example devices are given for each chip):
    
    * APQ8064 ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_S4_Pro))
      - Nexus 4 "mako": [sample][sample-mako] ([other samples][others-mako]),
        [releasetools.py](https://android.googlesource.com/device/lge/mako/+/33f0114/releasetools.py#98)
    
    * MSM8974AA ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_800,_801_and_805_(2013/14)))
      - Nexus 5 "hammerhead": [sample][sample-hammerhead] ([other samples][others-hammerhead]),
        [releasetools.py](https://android.googlesource.com/device/lge/hammerhead/+/7618a7d/releasetools.py#116)
    
    * MSM8992 ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_808_and_810_(2015)))
      - Nexus 5X "bullhead": [sample][sample-bullhead] ([other samples][others-bullhead]),
        [releasetools.py](https://android.googlesource.com/device/lge/bullhead/+/2994b6b/releasetools.py#126)
    
    * APQ8064-1AA ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_600_(2013)))
      - Nexus 7 \[2013] (Mobile) "deb" <a href="#doc-note-data-after-img-bodies">(\**)</a>: [sample][sample-deb] ([other samples][others-deb]),
        [releasetools.py](https://android.googlesource.com/device/asus/deb/+/14c1638/releasetools.py#105)
      - Nexus 7 \[2013] (Wi-Fi) "flo" <a href="#doc-note-data-after-img-bodies">(\**)</a>: [sample][sample-flo] ([other samples][others-flo]),
        [releasetools.py](https://android.googlesource.com/device/asus/flo/+/9d9fee9/releasetools.py#130)
    
    * MSM8996 Pro-AB ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_820_and_821_(2016)))
      - Pixel "sailfish" <a href="#doc-note-bootloader-size">(\*)</a>:
        [sample][sample-sailfish] ([other samples][others-sailfish])
      - Pixel XL "marlin" <a href="#doc-note-bootloader-size">(\*)</a>:
        [sample][sample-marlin] ([other samples][others-marlin])
    
    * MSM8998 ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_835_(2017)))
      - Pixel 2 "walleye" <a href="#doc-note-bootloader-size">(\*)</a>: [sample][sample-walleye] ([other samples][others-walleye])
      - Pixel 2 XL "taimen": [sample][sample-taimen] ([other samples][others-taimen])
    
    <small id="doc-note-bootloader-size">(\*)
    `bootloader_size` is equal to the size of the whole file (not just `img_bodies` as usual).
    </small>
    
    <small id="doc-note-data-after-img-bodies">(\**)
    There are some data after the end of `img_bodies`.
    </small>
    
    ---
    
    On the other hand, devices with these chips **do not** use this format:
    
    * <del>APQ8084</del> ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_800,_801_and_805_(2013/14)))
      - Nexus 6 "shamu": [sample][foreign-sample-shamu] ([other samples][foreign-others-shamu]),
        [releasetools.py](https://android.googlesource.com/device/moto/shamu/+/df9354d/releasetools.py#12) -
        uses "Motoboot packed image format" instead
    
    * <del>MSM8994</del> ([devices](https://en.wikipedia.org/wiki/Devices_using_Qualcomm_Snapdragon_processors#Snapdragon_808_and_810_(2015)))
      - Nexus 6P "angler": [sample][foreign-sample-angler] ([other samples][foreign-others-angler]),
        [releasetools.py](https://android.googlesource.com/device/huawei/angler/+/cf92cd8/releasetools.py#29) -
        uses "Huawei Bootloader packed image format" instead
    
    [sample-mako]: https://androidfilehost.com/?fid=96039337900113996 "bootloader-mako-makoz30f.img"
    [others-mako]: https://androidfilehost.com/?w=search&s=bootloader-mako&type=files
    
    [sample-hammerhead]: https://androidfilehost.com/?fid=385035244224410247 "bootloader-hammerhead-hhz20h.img"
    [others-hammerhead]: https://androidfilehost.com/?w=search&s=bootloader-hammerhead&type=files
    
    [sample-bullhead]: https://androidfilehost.com/?fid=11410963190603870177 "bootloader-bullhead-bhz32c.img"
    [others-bullhead]: https://androidfilehost.com/?w=search&s=bootloader-bullhead&type=files
    
    [sample-deb]: https://androidfilehost.com/?fid=23501681358552487 "bootloader-deb-flo-04.02.img"
    [others-deb]: https://androidfilehost.com/?w=search&s=bootloader-deb-flo&type=files
    
    [sample-flo]: https://androidfilehost.com/?fid=23991606952593542 "bootloader-flo-flo-04.05.img"
    [others-flo]: https://androidfilehost.com/?w=search&s=bootloader-flo-flo&type=files
    
    [sample-sailfish]: https://androidfilehost.com/?fid=6006931924117907154 "bootloader-sailfish-8996-012001-1904111134.img"
    [others-sailfish]: https://androidfilehost.com/?w=search&s=bootloader-sailfish&type=files
    
    [sample-marlin]: https://androidfilehost.com/?fid=6006931924117907131 "bootloader-marlin-8996-012001-1904111134.img"
    [others-marlin]: https://androidfilehost.com/?w=search&s=bootloader-marlin&type=files
    
    [sample-walleye]: https://androidfilehost.com/?fid=14943124697586348540 "bootloader-walleye-mw8998-003.0085.00.img"
    [others-walleye]: https://androidfilehost.com/?w=search&s=bootloader-walleye&type=files
    
    [sample-taimen]: https://androidfilehost.com/?fid=14943124697586348536 "bootloader-taimen-tmz30m.img"
    [others-taimen]: https://androidfilehost.com/?w=search&s=bootloader-taimen&type=files
    
    [foreign-sample-shamu]: https://androidfilehost.com/?fid=745849072291678307 "bootloader-shamu-moto-apq8084-72.04.img"
    [foreign-others-shamu]: https://androidfilehost.com/?w=search&s=bootloader-shamu&type=files
    
    [foreign-sample-angler]: https://androidfilehost.com/?fid=11410963190603870158 "bootloader-angler-angler-03.84.img"
    [foreign-others-angler]: https://androidfilehost.com/?w=search&s=bootloader-angler&type=files
    
    ---
    
    The `bootloader-*.img` samples referenced above originally come from factory
    images packed in ZIP archives that can be found on the page [Factory Images
    for Nexus and Pixel Devices](https://developers.google.com/android/images) on
    the Google Developers site. Note that the codenames on that page may be
    different than the ones that are written in the list above. That's because the
    Google page indicates **ROM codenames** in headings (e.g. "occam" for Nexus 4)
    but the above list uses **model codenames** (e.g. "mako" for Nexus 4) because
    that is how the original `bootloader-*.img` files are identified. For most
    devices, however, these code names are the same.
    
    .. seealso::
       Source - https://android.googlesource.com/device/lge/hammerhead/+/7618a7d/releasetools.py
    """
    SEQ_FIELDS = ["magic", "num_images", "ofs_img_bodies", "bootloader_size", "img_headers"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(8)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x42\x4F\x4F\x54\x4C\x44\x52\x21":
            raise kaitaistruct.ValidationNotEqualError(b"\x42\x4F\x4F\x54\x4C\x44\x52\x21", self.magic, self._io, u"/seq/0")
        self._debug['num_images']['start'] = self._io.pos()
        self.num_images = self._io.read_u4le()
        self._debug['num_images']['end'] = self._io.pos()
        self._debug['ofs_img_bodies']['start'] = self._io.pos()
        self.ofs_img_bodies = self._io.read_u4le()
        self._debug['ofs_img_bodies']['end'] = self._io.pos()
        self._debug['bootloader_size']['start'] = self._io.pos()
        self.bootloader_size = self._io.read_u4le()
        self._debug['bootloader_size']['end'] = self._io.pos()
        self._debug['img_headers']['start'] = self._io.pos()
        self.img_headers = [None] * (self.num_images)
        for i in range(self.num_images):
            if not 'arr' in self._debug['img_headers']:
                self._debug['img_headers']['arr'] = []
            self._debug['img_headers']['arr'].append({'start': self._io.pos()})
            _t_img_headers = AndroidBootldrQcom.ImgHeader(self._io, self, self._root)
            _t_img_headers._read()
            self.img_headers[i] = _t_img_headers
            self._debug['img_headers']['arr'][i]['end'] = self._io.pos()

        self._debug['img_headers']['end'] = self._io.pos()

    class ImgHeader(KaitaiStruct):
        SEQ_FIELDS = ["name", "len_body"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name']['start'] = self._io.pos()
            self.name = (KaitaiStream.bytes_terminate(self._io.read_bytes(64), 0, False)).decode(u"ASCII")
            self._debug['name']['end'] = self._io.pos()
            self._debug['len_body']['start'] = self._io.pos()
            self.len_body = self._io.read_u4le()
            self._debug['len_body']['end'] = self._io.pos()


    class ImgBody(KaitaiStruct):
        SEQ_FIELDS = ["body"]
        def __init__(self, idx, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.idx = idx
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['body']['start'] = self._io.pos()
            self.body = self._io.read_bytes(self.img_header.len_body)
            self._debug['body']['end'] = self._io.pos()

        @property
        def img_header(self):
            if hasattr(self, '_m_img_header'):
                return self._m_img_header if hasattr(self, '_m_img_header') else None

            self._m_img_header = self._root.img_headers[self.idx]
            return self._m_img_header if hasattr(self, '_m_img_header') else None


    @property
    def img_bodies(self):
        if hasattr(self, '_m_img_bodies'):
            return self._m_img_bodies if hasattr(self, '_m_img_bodies') else None

        _pos = self._io.pos()
        self._io.seek(self.ofs_img_bodies)
        self._debug['_m_img_bodies']['start'] = self._io.pos()
        self._m_img_bodies = [None] * (self.num_images)
        for i in range(self.num_images):
            if not 'arr' in self._debug['_m_img_bodies']:
                self._debug['_m_img_bodies']['arr'] = []
            self._debug['_m_img_bodies']['arr'].append({'start': self._io.pos()})
            _t__m_img_bodies = AndroidBootldrQcom.ImgBody(i, self._io, self, self._root)
            _t__m_img_bodies._read()
            self._m_img_bodies[i] = _t__m_img_bodies
            self._debug['_m_img_bodies']['arr'][i]['end'] = self._io.pos()

        self._debug['_m_img_bodies']['end'] = self._io.pos()
        self._io.seek(_pos)
        return self._m_img_bodies if hasattr(self, '_m_img_bodies') else None


