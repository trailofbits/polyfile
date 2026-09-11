# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from polyfile.kaitai.parsers import icc_4
from polyfile.kaitai.parsers import exif
from enum import IntEnum
import collections
import zlib


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Png(KaitaiStruct):
    """NOTICE: Many of the documentation comments (or docstrings) in this file were
    copied from or derived from the [Portable Network Graphics (PNG) Specification
    (Third Edition)](https://www.w3.org/TR/2025/REC-png-3-20250624/).
    Copyright © 1996-2025 [World Wide Web Consortium](https://www.w3.org/).
    <https://www.w3.org/copyright/software-license-2023/>
    
    The full text of the license for the original W3C PNG specification is
    provided below:
    
    > ## Software and Document license - 2023 version
    >
    > This work is being provided by the copyright holders under the following
    > license.
    >
    > ### License
    >
    > By obtaining and/or copying this work, you (the licensee) agree that you
    > have read, understood, and will comply with the following terms and
    > conditions.
    >
    > Permission to copy, modify, and distribute this work, with or without
    > modification, for any purpose and without fee or royalty is hereby granted,
    > provided that you include the following on ALL copies of the work or
    > portions thereof, including modifications:
    >
    > * The full text of this NOTICE in a location viewable to users of the
    >   redistributed or derivative work.
    > * Any pre-existing intellectual property disclaimers, notices, or terms and
    >   conditions. If none exist, the [W3C software and document short
    >   notice](https://www.w3.org/Consortium/Legal/2023/copyright-software-short-notice.html)
    >   should be included.
    > * Notice of any changes or modifications, through a copyright statement on
    >   the new code or document such as "This software or document includes
    >   material copied from or derived from [title and URI of the W3C document].
    >   Copyright © [$year-of-document] [World Wide Web
    >   Consortium](https://www.w3.org/).
    >   <https://www.w3.org/copyright/software-license-2023/>"
    >
    > ### Disclaimers
    >
    > THIS WORK IS PROVIDED "AS IS," AND COPYRIGHT HOLDERS MAKE NO REPRESENTATIONS
    > OR WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO, WARRANTIES
    > OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF
    > THE SOFTWARE OR DOCUMENT WILL NOT INFRINGE ANY THIRD PARTY PATENTS,
    > COPYRIGHTS, TRADEMARKS OR OTHER RIGHTS.
    >
    > COPYRIGHT HOLDERS WILL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, SPECIAL OR
    > CONSEQUENTIAL DAMAGES ARISING OUT OF ANY USE OF THE SOFTWARE OR DOCUMENT.
    >
    > The name and trademarks of copyright holders may NOT be used in advertising
    > or publicity pertaining to the work without specific, written prior
    > permission. Title to copyright in this work will at all times remain with
    > copyright holders.
    
    ---
    
    Test files for APNG can be found at the following locations:
    
      * <https://philip.html5.org/tests/apng/tests.html>
      * <http://littlesvr.ca/apng/>
    
    .. seealso::
       Source - https://www.w3.org/TR/png/
    """

    class BlendOpValues(IntEnum):
        source = 0
        over = 1

    class ColorType(IntEnum):
        greyscale = 0
        truecolor = 2
        indexed = 3
        greyscale_alpha = 4
        truecolor_alpha = 6

    class CompressionMethods(IntEnum):
        zlib = 0

    class DisposeOpValues(IntEnum):
        none = 0
        background = 1
        previous = 2

    class FilterMethod(IntEnum):
        base = 0

    class InterlaceMethod(IntEnum):
        none = 0
        adam7 = 1

    class PhysUnit(IntEnum):
        unknown = 0
        meter = 1
    SEQ_FIELDS = ["magic", "ihdr_len", "ihdr_type", "ihdr", "ihdr_crc", "chunks"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Png, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(8)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
            raise kaitaistruct.ValidationNotEqualError(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A", self.magic, self._io, u"/seq/0")
        self._debug['ihdr_len']['start'] = self._io.pos()
        self.ihdr_len = self._io.read_u4be()
        self._debug['ihdr_len']['end'] = self._io.pos()
        if not self.ihdr_len == 13:
            raise kaitaistruct.ValidationNotEqualError(13, self.ihdr_len, self._io, u"/seq/1")
        self._debug['ihdr_type']['start'] = self._io.pos()
        self.ihdr_type = self._io.read_bytes(4)
        self._debug['ihdr_type']['end'] = self._io.pos()
        if not self.ihdr_type == b"\x49\x48\x44\x52":
            raise kaitaistruct.ValidationNotEqualError(b"\x49\x48\x44\x52", self.ihdr_type, self._io, u"/seq/2")
        self._debug['ihdr']['start'] = self._io.pos()
        self.ihdr = Png.IhdrChunk(self._io, self, self._root)
        self.ihdr._read()
        self._debug['ihdr']['end'] = self._io.pos()
        self._debug['ihdr_crc']['start'] = self._io.pos()
        self.ihdr_crc = self._io.read_u4be()
        self._debug['ihdr_crc']['end'] = self._io.pos()
        self._debug['chunks']['start'] = self._io.pos()
        self._debug['chunks']['arr'] = []
        self.chunks = []
        i = 0
        while True:
            self._debug['chunks']['arr'].append({'start': self._io.pos()})
            _t_chunks = Png.Chunk(self._io, self, self._root)
            try:
                _t_chunks._read()
            finally:
                _ = _t_chunks
                self.chunks.append(_)
            self._debug['chunks']['arr'][len(self.chunks) - 1]['end'] = self._io.pos()
            if  ((_.type == u"IEND") or (self._io.is_eof())) :
                break
            i += 1
        self._debug['chunks']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.ihdr._fetch_instances()
        for i in range(len(self.chunks)):
            pass
            self.chunks[i]._fetch_instances()


    class AdobeFireworksChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://stackoverflow.com/questions/4242402/the-fireworks-png-format-any-insight-any-libs/51683285#51683285
        """
        SEQ_FIELDS = ["preview_data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.AdobeFireworksChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['preview_data']['start'] = self._io.pos()
            self._raw_preview_data = self._io.read_bytes_full()
            self.preview_data = zlib.decompress(self._raw_preview_data)
            self._debug['preview_data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class AnimationControlChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#acTL-chunk
        """
        SEQ_FIELDS = ["num_frames", "num_plays"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.AnimationControlChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_frames']['start'] = self._io.pos()
            self.num_frames = self._io.read_u4be()
            self._debug['num_frames']['end'] = self._io.pos()
            self._debug['num_plays']['start'] = self._io.pos()
            self.num_plays = self._io.read_u4be()
            self._debug['num_plays']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class AtchChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://github.com/skeeto/scratch/tree/58470254f4a95cdf7a53888e405c851c21eb2cae/pngattach
        
        
        .. seealso::
           A new protocol and tool for PNG file attachments - https://nullprogram.com/blog/2021/12/31/
        """

        class CompressionAttachMethods(IntEnum):
            none = 0
            zlib = 1
        SEQ_FIELDS = ["file_name", "compression", "data_plain", "data_zlib"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.AtchChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['file_name']['start'] = self._io.pos()
            self.file_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self._debug['file_name']['end'] = self._io.pos()
            _ = self.file_name
            if not  ((len(_) != 0) and (_[0:1] != u".")) :
                raise kaitaistruct.ValidationExprError(self.file_name, self._io, u"/types/atch_chunk/seq/0")
            self._debug['compression']['start'] = self._io.pos()
            self.compression = KaitaiStream.resolve_enum(Png.AtchChunk.CompressionAttachMethods, self._io.read_u1())
            self._debug['compression']['end'] = self._io.pos()
            if not isinstance(self.compression, Png.AtchChunk.CompressionAttachMethods):
                raise kaitaistruct.ValidationNotInEnumError(self.compression, self._io, u"/types/atch_chunk/seq/1")
            if self.compression == Png.AtchChunk.CompressionAttachMethods.none:
                pass
                self._debug['data_plain']['start'] = self._io.pos()
                self.data_plain = self._io.read_bytes_full()
                self._debug['data_plain']['end'] = self._io.pos()

            if self.compression == Png.AtchChunk.CompressionAttachMethods.zlib:
                pass
                self._debug['data_zlib']['start'] = self._io.pos()
                self._raw_data_zlib = self._io.read_bytes_full()
                self.data_zlib = zlib.decompress(self._raw_data_zlib)
                self._debug['data_zlib']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.compression == Png.AtchChunk.CompressionAttachMethods.none:
                pass

            if self.compression == Png.AtchChunk.CompressionAttachMethods.zlib:
                pass


        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data

            self._m_data = (self.data_plain if self.compression == Png.AtchChunk.CompressionAttachMethods.none else self.data_zlib)
            return getattr(self, '_m_data', None)


    class BkgdChunk(KaitaiStruct):
        """Background chunk stores default background color to display this
        image against. Contents depend on `color_type` of the image.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11bKGD
        """
        SEQ_FIELDS = ["bkgd"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.BkgdChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['bkgd']['start'] = self._io.pos()
            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.bkgd = Png.BkgdGreyscale(self._io, self, self._root)
                self.bkgd._read()
            elif _on == Png.ColorType.greyscale_alpha:
                pass
                self.bkgd = Png.BkgdGreyscale(self._io, self, self._root)
                self.bkgd._read()
            elif _on == Png.ColorType.indexed:
                pass
                self.bkgd = Png.BkgdIndexed(self._io, self, self._root)
                self.bkgd._read()
            elif _on == Png.ColorType.truecolor:
                pass
                self.bkgd = Png.BkgdTruecolor(self._io, self, self._root)
                self.bkgd._read()
            elif _on == Png.ColorType.truecolor_alpha:
                pass
                self.bkgd = Png.BkgdTruecolor(self._io, self, self._root)
                self.bkgd._read()
            self._debug['bkgd']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.bkgd._fetch_instances()
            elif _on == Png.ColorType.greyscale_alpha:
                pass
                self.bkgd._fetch_instances()
            elif _on == Png.ColorType.indexed:
                pass
                self.bkgd._fetch_instances()
            elif _on == Png.ColorType.truecolor:
                pass
                self.bkgd._fetch_instances()
            elif _on == Png.ColorType.truecolor_alpha:
                pass
                self.bkgd._fetch_instances()


    class BkgdGreyscale(KaitaiStruct):
        """Background chunk for greyscale images."""
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.BkgdGreyscale, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_u2be()
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class BkgdIndexed(KaitaiStruct):
        """Background chunk for images with indexed palette."""
        SEQ_FIELDS = ["palette_index"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.BkgdIndexed, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['palette_index']['start'] = self._io.pos()
            self.palette_index = self._io.read_u1()
            self._debug['palette_index']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class BkgdTruecolor(KaitaiStruct):
        """Background chunk for truecolor images."""
        SEQ_FIELDS = ["red", "green", "blue"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.BkgdTruecolor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['red']['start'] = self._io.pos()
            self.red = self._io.read_u2be()
            self._debug['red']['end'] = self._io.pos()
            self._debug['green']['start'] = self._io.pos()
            self.green = self._io.read_u2be()
            self._debug['green']['end'] = self._io.pos()
            self._debug['blue']['start'] = self._io.pos()
            self.blue = self._io.read_u2be()
            self._debug['blue']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class ChrmChromaticity(KaitaiStruct):
        SEQ_FIELDS = ["x_int", "y_int"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.ChrmChromaticity, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x_int']['start'] = self._io.pos()
            self.x_int = self._io.read_u4be()
            self._debug['x_int']['end'] = self._io.pos()
            self._debug['y_int']['start'] = self._io.pos()
            self.y_int = self._io.read_u4be()
            self._debug['y_int']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def x(self):
            if hasattr(self, '_m_x'):
                return self._m_x

            self._m_x = self.x_int / 100000.0
            return getattr(self, '_m_x', None)

        @property
        def y(self):
            if hasattr(self, '_m_y'):
                return self._m_y

            self._m_y = self.y_int / 100000.0
            return getattr(self, '_m_y', None)


    class ChrmChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#11cHRM
        """
        SEQ_FIELDS = ["white_point", "red", "green", "blue"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.ChrmChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['white_point']['start'] = self._io.pos()
            self.white_point = Png.ChrmChromaticity(self._io, self, self._root)
            self.white_point._read()
            self._debug['white_point']['end'] = self._io.pos()
            self._debug['red']['start'] = self._io.pos()
            self.red = Png.ChrmChromaticity(self._io, self, self._root)
            self.red._read()
            self._debug['red']['end'] = self._io.pos()
            self._debug['green']['start'] = self._io.pos()
            self.green = Png.ChrmChromaticity(self._io, self, self._root)
            self.green._read()
            self._debug['green']['end'] = self._io.pos()
            self._debug['blue']['start'] = self._io.pos()
            self.blue = Png.ChrmChromaticity(self._io, self, self._root)
            self.blue._read()
            self._debug['blue']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.white_point._fetch_instances()
            self.red._fetch_instances()
            self.green._fetch_instances()
            self.blue._fetch_instances()


    class Chunk(KaitaiStruct):
        SEQ_FIELDS = ["len", "type_raw", "body", "crc"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.Chunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u4be()
            self._debug['len']['end'] = self._io.pos()
            self._debug['type_raw']['start'] = self._io.pos()
            self.type_raw = self._io.read_bytes(4)
            self._debug['type_raw']['end'] = self._io.pos()
            _ = self.type_raw
            if not  (( (( ((KaitaiStream.byte_array_index(_, 0) >= 65) and (KaitaiStream.byte_array_index(_, 0) <= 90)) ) or ( ((KaitaiStream.byte_array_index(_, 0) >= 97) and (KaitaiStream.byte_array_index(_, 0) <= 122)) )) ) and ( (( ((KaitaiStream.byte_array_index(_, 1) >= 65) and (KaitaiStream.byte_array_index(_, 1) <= 90)) ) or ( ((KaitaiStream.byte_array_index(_, 1) >= 97) and (KaitaiStream.byte_array_index(_, 1) <= 122)) )) ) and ( (( ((KaitaiStream.byte_array_index(_, 2) >= 65) and (KaitaiStream.byte_array_index(_, 2) <= 90)) ) or ( ((KaitaiStream.byte_array_index(_, 2) >= 97) and (KaitaiStream.byte_array_index(_, 2) <= 122)) )) ) and ( (( ((KaitaiStream.byte_array_index(_, 3) >= 65) and (KaitaiStream.byte_array_index(_, 3) <= 90)) ) or ( ((KaitaiStream.byte_array_index(_, 3) >= 97) and (KaitaiStream.byte_array_index(_, 3) <= 122)) )) )) :
                raise kaitaistruct.ValidationExprError(self.type_raw, self._io, u"/types/chunk/seq/1")
            self._debug['body']['start'] = self._io.pos()
            _on = self.type
            if _on == u"PLTE":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.PlteChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"acTL":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.AnimationControlChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"atCh":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.AtchChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"bKGD":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.BkgdChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"cHRM":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.ChrmChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"cICP":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.CicpChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"cLLI":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.ClliChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"eXIf":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.ExifChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"fcTL":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.FrameControlChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"fdAT":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.FrameDataChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"gAMA":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.GamaChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"hIST":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.HistChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"iCCP":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.IccpChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"iTXt":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.InternationalTextChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"mDCV":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.MdcvChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"mkBS":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.AdobeFireworksChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"mkTS":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.AdobeFireworksChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"pHYs":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.PhysChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"prVW":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.AdobeFireworksChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"sBIT":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.SbitChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"sPLT":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.SpltChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"sRGB":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.SrgbChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"skMf":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.EvernoteSkmfChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"skRf":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.EvernoteSkrfChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"tEXt":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.TextChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"tIME":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.TimeChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"tRNS":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.TrnsChunk(_io__raw_body, self, self._root)
                self.body._read()
            elif _on == u"zTXt":
                pass
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = Png.CompressedTextChunk(_io__raw_body, self, self._root)
                self.body._read()
            else:
                pass
                self.body = self._io.read_bytes(self.len)
            self._debug['body']['end'] = self._io.pos()
            self._debug['crc']['start'] = self._io.pos()
            self.crc = self._io.read_u4be()
            self._debug['crc']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.type
            if _on == u"PLTE":
                pass
                self.body._fetch_instances()
            elif _on == u"acTL":
                pass
                self.body._fetch_instances()
            elif _on == u"atCh":
                pass
                self.body._fetch_instances()
            elif _on == u"bKGD":
                pass
                self.body._fetch_instances()
            elif _on == u"cHRM":
                pass
                self.body._fetch_instances()
            elif _on == u"cICP":
                pass
                self.body._fetch_instances()
            elif _on == u"cLLI":
                pass
                self.body._fetch_instances()
            elif _on == u"eXIf":
                pass
                self.body._fetch_instances()
            elif _on == u"fcTL":
                pass
                self.body._fetch_instances()
            elif _on == u"fdAT":
                pass
                self.body._fetch_instances()
            elif _on == u"gAMA":
                pass
                self.body._fetch_instances()
            elif _on == u"hIST":
                pass
                self.body._fetch_instances()
            elif _on == u"iCCP":
                pass
                self.body._fetch_instances()
            elif _on == u"iTXt":
                pass
                self.body._fetch_instances()
            elif _on == u"mDCV":
                pass
                self.body._fetch_instances()
            elif _on == u"mkBS":
                pass
                self.body._fetch_instances()
            elif _on == u"mkTS":
                pass
                self.body._fetch_instances()
            elif _on == u"pHYs":
                pass
                self.body._fetch_instances()
            elif _on == u"prVW":
                pass
                self.body._fetch_instances()
            elif _on == u"sBIT":
                pass
                self.body._fetch_instances()
            elif _on == u"sPLT":
                pass
                self.body._fetch_instances()
            elif _on == u"sRGB":
                pass
                self.body._fetch_instances()
            elif _on == u"skMf":
                pass
                self.body._fetch_instances()
            elif _on == u"skRf":
                pass
                self.body._fetch_instances()
            elif _on == u"tEXt":
                pass
                self.body._fetch_instances()
            elif _on == u"tIME":
                pass
                self.body._fetch_instances()
            elif _on == u"tRNS":
                pass
                self.body._fetch_instances()
            elif _on == u"zTXt":
                pass
                self.body._fetch_instances()
            else:
                pass

        @property
        def is_ancillary(self):
            """false = critical chunk, true = ancillary chunk
            """
            if hasattr(self, '_m_is_ancillary'):
                return self._m_is_ancillary

            self._m_is_ancillary = KaitaiStream.byte_array_index(self.type_raw, 0) & 32 != 0
            return getattr(self, '_m_is_ancillary', None)

        @property
        def is_private(self):
            """false = public chunk (defined by the W3C), true = private chunk (can
            be defined by anyone)
            """
            if hasattr(self, '_m_is_private'):
                return self._m_is_private

            self._m_is_private = KaitaiStream.byte_array_index(self.type_raw, 1) & 32 != 0
            return getattr(self, '_m_is_private', None)

        @property
        def is_safe_to_copy(self):
            """Defines whether the chunk may be copied if the image data (i.e.
            pixels) is modified. This tells PNG editors how to handle unknown
            chunks - see section [14.2 Behavior of PNG
            editors](https://www.w3.org/TR/2025/REC-png-3-20250624/#14Ordering) in
            the official specification.
            """
            if hasattr(self, '_m_is_safe_to_copy'):
                return self._m_is_safe_to_copy

            self._m_is_safe_to_copy = KaitaiStream.byte_array_index(self.type_raw, 3) & 32 != 0
            return getattr(self, '_m_is_safe_to_copy', None)

        @property
        def reserved_bit(self):
            """Should be `false`, i.e. all chunk types should have uppercase third
            letters (the lowercase third letter is reserved for possible future
            extensions to the PNG standard)
            """
            if hasattr(self, '_m_reserved_bit'):
                return self._m_reserved_bit

            self._m_reserved_bit = KaitaiStream.byte_array_index(self.type_raw, 2) & 32 != 0
            return getattr(self, '_m_reserved_bit', None)

        @property
        def type(self):
            if hasattr(self, '_m_type'):
                return self._m_type

            self._m_type = (self.type_raw).decode(u"ASCII")
            return getattr(self, '_m_type', None)


    class CicpChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#cICP-chunk
        
        
        .. seealso::
           Source - https://w3c.github.io/png/Implementation_Report_3e/#cicp
        """
        SEQ_FIELDS = ["color_primaries", "transfer_function", "matrix_coefficients", "video_full_range_flag"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.CicpChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['color_primaries']['start'] = self._io.pos()
            self.color_primaries = self._io.read_u1()
            self._debug['color_primaries']['end'] = self._io.pos()
            self._debug['transfer_function']['start'] = self._io.pos()
            self.transfer_function = self._io.read_u1()
            self._debug['transfer_function']['end'] = self._io.pos()
            self._debug['matrix_coefficients']['start'] = self._io.pos()
            self.matrix_coefficients = self._io.read_u1()
            self._debug['matrix_coefficients']['end'] = self._io.pos()
            if not self.matrix_coefficients == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.matrix_coefficients, self._io, u"/types/cicp_chunk/seq/2")
            self._debug['video_full_range_flag']['start'] = self._io.pos()
            self.video_full_range_flag = self._io.read_u1()
            self._debug['video_full_range_flag']['end'] = self._io.pos()
            if not  ((self.video_full_range_flag == 0) or (self.video_full_range_flag == 1)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.video_full_range_flag, self._io, u"/types/cicp_chunk/seq/3")


        def _fetch_instances(self):
            pass


    class ClliChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#cLLI-chunk
        
        
        .. seealso::
           Source - https://w3c.github.io/png/Implementation_Report_3e/#light
        """
        SEQ_FIELDS = ["max_content_light_level_int", "max_frame_average_light_level_int"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.ClliChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['max_content_light_level_int']['start'] = self._io.pos()
            self.max_content_light_level_int = self._io.read_u4be()
            self._debug['max_content_light_level_int']['end'] = self._io.pos()
            self._debug['max_frame_average_light_level_int']['start'] = self._io.pos()
            self.max_frame_average_light_level_int = self._io.read_u4be()
            self._debug['max_frame_average_light_level_int']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def max_content_light_level(self):
            """Maximum Content Light Level (MaxCLL), in cd/m^2."""
            if hasattr(self, '_m_max_content_light_level'):
                return self._m_max_content_light_level

            self._m_max_content_light_level = self.max_content_light_level_int * 0.0001
            return getattr(self, '_m_max_content_light_level', None)

        @property
        def max_frame_average_light_level(self):
            """Maximum Frame Average Light Level (MaxFALL), in cd/m^2."""
            if hasattr(self, '_m_max_frame_average_light_level'):
                return self._m_max_frame_average_light_level

            self._m_max_frame_average_light_level = self.max_frame_average_light_level_int * 0.0001
            return getattr(self, '_m_max_frame_average_light_level', None)


    class CompressedText(KaitaiStruct):
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.CompressedText, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = (self._io.read_bytes_full()).decode(u"ISO-8859-1")
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class CompressedTextChunk(KaitaiStruct):
        """Compressed textual data (`zTXt`) chunk effectively allows you to store
        key-value string pairs in the PNG container, compressing the "value" part
        (which can be quite lengthy) with zlib compression.
        
        The `zTXt` and `tEXt` chunks are semantically equivalent, but the `zTXt`
        chunk is recommended for storing large blocks of text.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11zTXt
        """
        SEQ_FIELDS = ["keyword", "compression_method", "text"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.CompressedTextChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['keyword']['start'] = self._io.pos()
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"ISO-8859-1")
            self._debug['keyword']['end'] = self._io.pos()
            self._debug['compression_method']['start'] = self._io.pos()
            self.compression_method = KaitaiStream.resolve_enum(Png.CompressionMethods, self._io.read_u1())
            self._debug['compression_method']['end'] = self._io.pos()
            if not self.compression_method == Png.CompressionMethods.zlib:
                raise kaitaistruct.ValidationNotEqualError(Png.CompressionMethods.zlib, self.compression_method, self._io, u"/types/compressed_text_chunk/seq/1")
            self._debug['text']['start'] = self._io.pos()
            self._raw__raw_text = self._io.read_bytes_full()
            self._raw_text = zlib.decompress(self._raw__raw_text)
            _io__raw_text = KaitaiStream(BytesIO(self._raw_text))
            self.text = Png.CompressedText(_io__raw_text, self, self._root)
            self.text._read()
            self._debug['text']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.text._fetch_instances()


    class EvernoteSkmfChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://web.archive.org/web/20210302212148/https://discussion.evernote.com/forums/topic/88532-how-to-extract-annotation-information-from-annotated-evernoteskitch-images/#comment-451501
        """
        SEQ_FIELDS = ["json"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.EvernoteSkmfChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['json']['start'] = self._io.pos()
            self.json = (self._io.read_bytes_full()).decode(u"UTF-8")
            self._debug['json']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class EvernoteSkrfChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://web.archive.org/web/20210302212148/https://discussion.evernote.com/forums/topic/88532-how-to-extract-annotation-information-from-annotated-evernoteskitch-images/#comment-451501
        """
        SEQ_FIELDS = ["uuid", "orig_img"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.EvernoteSkrfChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['uuid']['start'] = self._io.pos()
            self.uuid = self._io.read_bytes(16)
            self._debug['uuid']['end'] = self._io.pos()
            self._debug['orig_img']['start'] = self._io.pos()
            self.orig_img = self._io.read_bytes_full()
            self._debug['orig_img']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class ExifChunk(KaitaiStruct):
        """Exchangeable Image File (Exif) Profile (`eXIf`) chunk.
        
        Only one `eXIf` chunk is allowed in a PNG datastream.
        
        The `eXIf` chunk contains metadata concerning the original image data. If
        the image has been edited subsequent to creation of the Exif profile, this
        data might no longer apply to the PNG image data.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#eXIf
        """
        SEQ_FIELDS = ["exif"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.ExifChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['exif']['start'] = self._io.pos()
            self.exif = exif.Exif(self._io)
            self.exif._read()
            self._debug['exif']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.exif._fetch_instances()


    class FrameControlChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#fcTL-chunk
        """
        SEQ_FIELDS = ["sequence_number", "width", "height", "x_offset", "y_offset", "delay_num", "delay_den", "dispose_op", "blend_op"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.FrameControlChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['sequence_number']['start'] = self._io.pos()
            self.sequence_number = self._io.read_u4be()
            self._debug['sequence_number']['end'] = self._io.pos()
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_u4be()
            self._debug['width']['end'] = self._io.pos()
            if not self.width >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.width, self._io, u"/types/frame_control_chunk/seq/1")
            if not self.width <= self._root.ihdr.width:
                raise kaitaistruct.ValidationGreaterThanError(self._root.ihdr.width, self.width, self._io, u"/types/frame_control_chunk/seq/1")
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_u4be()
            self._debug['height']['end'] = self._io.pos()
            if not self.height >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.height, self._io, u"/types/frame_control_chunk/seq/2")
            if not self.height <= self._root.ihdr.height:
                raise kaitaistruct.ValidationGreaterThanError(self._root.ihdr.height, self.height, self._io, u"/types/frame_control_chunk/seq/2")
            self._debug['x_offset']['start'] = self._io.pos()
            self.x_offset = self._io.read_u4be()
            self._debug['x_offset']['end'] = self._io.pos()
            if not self.x_offset <= self._root.ihdr.width - self.width:
                raise kaitaistruct.ValidationGreaterThanError(self._root.ihdr.width - self.width, self.x_offset, self._io, u"/types/frame_control_chunk/seq/3")
            self._debug['y_offset']['start'] = self._io.pos()
            self.y_offset = self._io.read_u4be()
            self._debug['y_offset']['end'] = self._io.pos()
            if not self.y_offset <= self._root.ihdr.height - self.height:
                raise kaitaistruct.ValidationGreaterThanError(self._root.ihdr.height - self.height, self.y_offset, self._io, u"/types/frame_control_chunk/seq/4")
            self._debug['delay_num']['start'] = self._io.pos()
            self.delay_num = self._io.read_u2be()
            self._debug['delay_num']['end'] = self._io.pos()
            self._debug['delay_den']['start'] = self._io.pos()
            self.delay_den = self._io.read_u2be()
            self._debug['delay_den']['end'] = self._io.pos()
            self._debug['dispose_op']['start'] = self._io.pos()
            self.dispose_op = KaitaiStream.resolve_enum(Png.DisposeOpValues, self._io.read_u1())
            self._debug['dispose_op']['end'] = self._io.pos()
            if not isinstance(self.dispose_op, Png.DisposeOpValues):
                raise kaitaistruct.ValidationNotInEnumError(self.dispose_op, self._io, u"/types/frame_control_chunk/seq/7")
            self._debug['blend_op']['start'] = self._io.pos()
            self.blend_op = KaitaiStream.resolve_enum(Png.BlendOpValues, self._io.read_u1())
            self._debug['blend_op']['end'] = self._io.pos()
            if not isinstance(self.blend_op, Png.BlendOpValues):
                raise kaitaistruct.ValidationNotInEnumError(self.blend_op, self._io, u"/types/frame_control_chunk/seq/8")


        def _fetch_instances(self):
            pass

        @property
        def delay(self):
            """Time to display this frame, in seconds."""
            if hasattr(self, '_m_delay'):
                return self._m_delay

            self._m_delay = self.delay_num / (100.0 if self.delay_den == 0 else self.delay_den)
            return getattr(self, '_m_delay', None)


    class FrameDataChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#fdAT-chunk
        """
        SEQ_FIELDS = ["sequence_number", "frame_data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.FrameDataChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['sequence_number']['start'] = self._io.pos()
            self.sequence_number = self._io.read_u4be()
            self._debug['sequence_number']['end'] = self._io.pos()
            self._debug['frame_data']['start'] = self._io.pos()
            self.frame_data = self._io.read_bytes_full()
            self._debug['frame_data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class GamaChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#11gAMA
        """
        SEQ_FIELDS = ["gamma_int"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.GamaChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['gamma_int']['start'] = self._io.pos()
            self.gamma_int = self._io.read_u4be()
            self._debug['gamma_int']['end'] = self._io.pos()
            _ = self.gamma_int
            if not _ != 0:
                raise kaitaistruct.ValidationExprError(self.gamma_int, self._io, u"/types/gama_chunk/seq/0")


        def _fetch_instances(self):
            pass

        @property
        def gamma(self):
            """Image gamma, typically 0.45455 = 1/2.2."""
            if hasattr(self, '_m_gamma'):
                return self._m_gamma

            self._m_gamma = self.gamma_int / 100000.0
            return getattr(self, '_m_gamma', None)

        @property
        def inv_gamma(self):
            """Inverse of the image gamma (1 / gamma), typically 2.2 (not considering
            rounding)
            """
            if hasattr(self, '_m_inv_gamma'):
                return self._m_inv_gamma

            self._m_inv_gamma = 100000.0 / self.gamma_int
            return getattr(self, '_m_inv_gamma', None)


    class HistChunk(KaitaiStruct):
        """Image histogram (`hIST`) chunk gives the approximate usage frequency of
        each color in the palette. A histogram chunk can appear only when a `PLTE`
        chunk appears.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11hIST
        """
        SEQ_FIELDS = ["usage_freqs"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.HistChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['usage_freqs']['start'] = self._io.pos()
            self._debug['usage_freqs']['arr'] = []
            self.usage_freqs = []
            i = 0
            while not self._io.is_eof():
                self._debug['usage_freqs']['arr'].append({'start': self._io.pos()})
                self.usage_freqs.append(self._io.read_u2be())
                self._debug['usage_freqs']['arr'][len(self.usage_freqs) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['usage_freqs']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.usage_freqs)):
                pass



    class IccpChunk(KaitaiStruct):
        """Embedded ICC profile (`iCCP`) chunk.
        
        If the `iCCP` chunk is present, the image samples conform to the color
        space represented by the embedded ICC profile as defined by the
        International Color Consortium.
        
        This chunk is ignored unless it is the [highest-precedence color
        chunk](https://www.w3.org/TR/png/#color-chunk-precendence) understood by
        the decoder. Unless a `cICP` chunk exists, a PNG datastream should contain
        at most one embedded profile, whether specified explicitly with an `iCCP`
        or implicitly with an `sRGB` chunk.
        
        It is recommended that the `sRGB` and `iCCP` chunks do not appear
        simultaneously in a PNG datastream.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11iCCP
        """
        SEQ_FIELDS = ["profile_name", "compression_method", "profile"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.IccpChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['profile_name']['start'] = self._io.pos()
            self.profile_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ISO-8859-1")
            self._debug['profile_name']['end'] = self._io.pos()
            self._debug['compression_method']['start'] = self._io.pos()
            self.compression_method = KaitaiStream.resolve_enum(Png.CompressionMethods, self._io.read_u1())
            self._debug['compression_method']['end'] = self._io.pos()
            if not self.compression_method == Png.CompressionMethods.zlib:
                raise kaitaistruct.ValidationNotEqualError(Png.CompressionMethods.zlib, self.compression_method, self._io, u"/types/iccp_chunk/seq/1")
            self._debug['profile']['start'] = self._io.pos()
            self._raw__raw_profile = self._io.read_bytes_full()
            self._raw_profile = zlib.decompress(self._raw__raw_profile)
            _io__raw_profile = KaitaiStream(BytesIO(self._raw_profile))
            self.profile = icc_4.Icc4(_io__raw_profile)
            self.profile._read()
            self._debug['profile']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.profile._fetch_instances()


    class IhdrChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#11IHDR
        """
        SEQ_FIELDS = ["width", "height", "bit_depth", "color_type", "compression_method", "filter_method", "interlace_method"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.IhdrChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['width']['start'] = self._io.pos()
            self.width = self._io.read_u4be()
            self._debug['width']['end'] = self._io.pos()
            if not self.width >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.width, self._io, u"/types/ihdr_chunk/seq/0")
            self._debug['height']['start'] = self._io.pos()
            self.height = self._io.read_u4be()
            self._debug['height']['end'] = self._io.pos()
            if not self.height >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.height, self._io, u"/types/ihdr_chunk/seq/1")
            self._debug['bit_depth']['start'] = self._io.pos()
            self.bit_depth = self._io.read_u1()
            self._debug['bit_depth']['end'] = self._io.pos()
            if not  ((self.bit_depth == 1) or (self.bit_depth == 2) or (self.bit_depth == 4) or (self.bit_depth == 8) or (self.bit_depth == 16)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.bit_depth, self._io, u"/types/ihdr_chunk/seq/2")
            self._debug['color_type']['start'] = self._io.pos()
            self.color_type = KaitaiStream.resolve_enum(Png.ColorType, self._io.read_u1())
            self._debug['color_type']['end'] = self._io.pos()
            if not isinstance(self.color_type, Png.ColorType):
                raise kaitaistruct.ValidationNotInEnumError(self.color_type, self._io, u"/types/ihdr_chunk/seq/3")
            self._debug['compression_method']['start'] = self._io.pos()
            self.compression_method = KaitaiStream.resolve_enum(Png.CompressionMethods, self._io.read_u1())
            self._debug['compression_method']['end'] = self._io.pos()
            if not isinstance(self.compression_method, Png.CompressionMethods):
                raise kaitaistruct.ValidationNotInEnumError(self.compression_method, self._io, u"/types/ihdr_chunk/seq/4")
            self._debug['filter_method']['start'] = self._io.pos()
            self.filter_method = KaitaiStream.resolve_enum(Png.FilterMethod, self._io.read_u1())
            self._debug['filter_method']['end'] = self._io.pos()
            if not isinstance(self.filter_method, Png.FilterMethod):
                raise kaitaistruct.ValidationNotInEnumError(self.filter_method, self._io, u"/types/ihdr_chunk/seq/5")
            self._debug['interlace_method']['start'] = self._io.pos()
            self.interlace_method = KaitaiStream.resolve_enum(Png.InterlaceMethod, self._io.read_u1())
            self._debug['interlace_method']['end'] = self._io.pos()
            if not isinstance(self.interlace_method, Png.InterlaceMethod):
                raise kaitaistruct.ValidationNotInEnumError(self.interlace_method, self._io, u"/types/ihdr_chunk/seq/6")


        def _fetch_instances(self):
            pass


    class InternationalText(KaitaiStruct):
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.InternationalText, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = (self._io.read_bytes_full()).decode(u"UTF-8")
            self._debug['value']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class InternationalTextChunk(KaitaiStruct):
        """International textual data (`iTXt`) chunk effectively allows you to store
        key-value string pairs in the PNG container.
        
        The "key" part (`keyword`) is restricted to printable ISO-8859-1 (Latin-1)
        characters and spaces. The translated keyword and the "value" part
        (`text`) are stored in UTF-8 and thus can store text in any language -
        this language can be indicated via the language tag (`language_tag`).
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11iTXt
        """
        SEQ_FIELDS = ["keyword", "compression_flag", "compression_method", "language_tag", "translated_keyword", "text_plain", "text_zlib"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.InternationalTextChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['keyword']['start'] = self._io.pos()
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"ISO-8859-1")
            self._debug['keyword']['end'] = self._io.pos()
            self._debug['compression_flag']['start'] = self._io.pos()
            self.compression_flag = self._io.read_u1()
            self._debug['compression_flag']['end'] = self._io.pos()
            if not  ((self.compression_flag == 0) or (self.compression_flag == 1)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.compression_flag, self._io, u"/types/international_text_chunk/seq/1")
            self._debug['compression_method']['start'] = self._io.pos()
            self.compression_method = KaitaiStream.resolve_enum(Png.CompressionMethods, self._io.read_u1())
            self._debug['compression_method']['end'] = self._io.pos()
            if not self.compression_method == (Png.CompressionMethods.zlib if self.compression_flag == 1 else self.compression_method):
                raise kaitaistruct.ValidationNotEqualError((Png.CompressionMethods.zlib if self.compression_flag == 1 else self.compression_method), self.compression_method, self._io, u"/types/international_text_chunk/seq/2")
            self._debug['language_tag']['start'] = self._io.pos()
            self.language_tag = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['language_tag']['end'] = self._io.pos()
            self._debug['translated_keyword']['start'] = self._io.pos()
            self.translated_keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self._debug['translated_keyword']['end'] = self._io.pos()
            if self.compression_flag == 0:
                pass
                self._debug['text_plain']['start'] = self._io.pos()
                self._raw_text_plain = self._io.read_bytes_full()
                _io__raw_text_plain = KaitaiStream(BytesIO(self._raw_text_plain))
                self.text_plain = Png.InternationalText(_io__raw_text_plain, self, self._root)
                self.text_plain._read()
                self._debug['text_plain']['end'] = self._io.pos()

            if self.compression_flag == 1:
                pass
                self._debug['text_zlib']['start'] = self._io.pos()
                self._raw__raw_text_zlib = self._io.read_bytes_full()
                self._raw_text_zlib = zlib.decompress(self._raw__raw_text_zlib)
                _io__raw_text_zlib = KaitaiStream(BytesIO(self._raw_text_zlib))
                self.text_zlib = Png.InternationalText(_io__raw_text_zlib, self, self._root)
                self.text_zlib._read()
                self._debug['text_zlib']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if self.compression_flag == 0:
                pass
                self.text_plain._fetch_instances()

            if self.compression_flag == 1:
                pass
                self.text_zlib._fetch_instances()


        @property
        def text(self):
            """Text string (the "value" of this key-value pair), written in language
            specified in `language_tag`.
            
            Although it is not null-terminated (unlike other textual data in the
            `iTXt` chunk), it must not contain a zero byte
            (U+0000 NULL character). A newline should be represented by a single
            U+000A LINE FEED (LF) character (aka `\n`). The remaining control
            characters (U+0001..U+0009, U+000B..0+001F, U+007F..U+009F) are
            discouraged.
            """
            if hasattr(self, '_m_text'):
                return self._m_text

            self._m_text = (self.text_plain if self.compression_flag == 0 else self.text_zlib).value
            return getattr(self, '_m_text', None)


    class MdcvChromaticity(KaitaiStruct):
        SEQ_FIELDS = ["x_int", "y_int"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.MdcvChromaticity, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x_int']['start'] = self._io.pos()
            self.x_int = self._io.read_u2be()
            self._debug['x_int']['end'] = self._io.pos()
            self._debug['y_int']['start'] = self._io.pos()
            self.y_int = self._io.read_u2be()
            self._debug['y_int']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def x(self):
            if hasattr(self, '_m_x'):
                return self._m_x

            self._m_x = self.x_int * 0.00002
            return getattr(self, '_m_x', None)

        @property
        def y(self):
            if hasattr(self, '_m_y'):
                return self._m_y

            self._m_y = self.y_int * 0.00002
            return getattr(self, '_m_y', None)


    class MdcvChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#mDCV-chunk
        
        
        .. seealso::
           Source - https://w3c.github.io/png/Implementation_Report_3e/#mastering
        """
        SEQ_FIELDS = ["red", "green", "blue", "white_point", "max_luminance_int", "min_luminance_int"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.MdcvChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['red']['start'] = self._io.pos()
            self.red = Png.MdcvChromaticity(self._io, self, self._root)
            self.red._read()
            self._debug['red']['end'] = self._io.pos()
            self._debug['green']['start'] = self._io.pos()
            self.green = Png.MdcvChromaticity(self._io, self, self._root)
            self.green._read()
            self._debug['green']['end'] = self._io.pos()
            self._debug['blue']['start'] = self._io.pos()
            self.blue = Png.MdcvChromaticity(self._io, self, self._root)
            self.blue._read()
            self._debug['blue']['end'] = self._io.pos()
            self._debug['white_point']['start'] = self._io.pos()
            self.white_point = Png.MdcvChromaticity(self._io, self, self._root)
            self.white_point._read()
            self._debug['white_point']['end'] = self._io.pos()
            self._debug['max_luminance_int']['start'] = self._io.pos()
            self.max_luminance_int = self._io.read_u4be()
            self._debug['max_luminance_int']['end'] = self._io.pos()
            self._debug['min_luminance_int']['start'] = self._io.pos()
            self.min_luminance_int = self._io.read_u4be()
            self._debug['min_luminance_int']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.red._fetch_instances()
            self.green._fetch_instances()
            self.blue._fetch_instances()
            self.white_point._fetch_instances()

        @property
        def max_luminance(self):
            """Maximum luminance in cd/m^2."""
            if hasattr(self, '_m_max_luminance'):
                return self._m_max_luminance

            self._m_max_luminance = self.max_luminance_int * 0.0001
            return getattr(self, '_m_max_luminance', None)

        @property
        def min_luminance(self):
            """Minimum luminance in cd/m^2."""
            if hasattr(self, '_m_min_luminance'):
                return self._m_min_luminance

            self._m_min_luminance = self.min_luminance_int * 0.0001
            return getattr(self, '_m_min_luminance', None)


    class PhysChunk(KaitaiStruct):
        """Physical pixel dimensions (`pHYs`) chunk specifies the intended physical
        size of the pixels (in meters) or pixel aspect ratio for display of the
        image.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11pHYs
        """
        SEQ_FIELDS = ["pixels_per_unit_x", "pixels_per_unit_y", "unit"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.PhysChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['pixels_per_unit_x']['start'] = self._io.pos()
            self.pixels_per_unit_x = self._io.read_u4be()
            self._debug['pixels_per_unit_x']['end'] = self._io.pos()
            self._debug['pixels_per_unit_y']['start'] = self._io.pos()
            self.pixels_per_unit_y = self._io.read_u4be()
            self._debug['pixels_per_unit_y']['end'] = self._io.pos()
            self._debug['unit']['start'] = self._io.pos()
            self.unit = KaitaiStream.resolve_enum(Png.PhysUnit, self._io.read_u1())
            self._debug['unit']['end'] = self._io.pos()
            if not isinstance(self.unit, Png.PhysUnit):
                raise kaitaistruct.ValidationNotInEnumError(self.unit, self._io, u"/types/phys_chunk/seq/2")


        def _fetch_instances(self):
            pass

        @property
        def dots_per_inch_x(self):
            """Horizontal resolution (DPI)."""
            if hasattr(self, '_m_dots_per_inch_x'):
                return self._m_dots_per_inch_x

            if self.unit == Png.PhysUnit.meter:
                pass
                self._m_dots_per_inch_x = self.pixels_per_unit_x * 0.0254

            return getattr(self, '_m_dots_per_inch_x', None)

        @property
        def dots_per_inch_y(self):
            """Vertical resolution (DPI)."""
            if hasattr(self, '_m_dots_per_inch_y'):
                return self._m_dots_per_inch_y

            if self.unit == Png.PhysUnit.meter:
                pass
                self._m_dots_per_inch_y = self.pixels_per_unit_y * 0.0254

            return getattr(self, '_m_dots_per_inch_y', None)


    class PlteChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#11PLTE
        """
        SEQ_FIELDS = ["entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.PlteChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['entries']['start'] = self._io.pos()
            self._debug['entries']['arr'] = []
            self.entries = []
            i = 0
            while not self._io.is_eof():
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = Png.Rgb(self._io, self, self._root)
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



    class Rgb(KaitaiStruct):
        SEQ_FIELDS = ["r", "g", "b"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.Rgb, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['r']['start'] = self._io.pos()
            self.r = self._io.read_u1()
            self._debug['r']['end'] = self._io.pos()
            self._debug['g']['start'] = self._io.pos()
            self.g = self._io.read_u1()
            self._debug['g']['end'] = self._io.pos()
            self._debug['b']['start'] = self._io.pos()
            self.b = self._io.read_u1()
            self._debug['b']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class SbitChunk(KaitaiStruct):
        """Significant bits (`sBIT`) chunk stores the original number of significant
        bits of the sample values (which can be less than or equal to the sample
        depth). This allows PNG decoders to recover the original data losslessly
        even if the data had a sample depth not directly supported by PNG.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11sBIT
        """
        SEQ_FIELDS = ["significant_bits"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.SbitChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['significant_bits']['start'] = self._io.pos()
            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.significant_bits = Png.SbitGreyscale(False, self._io, self, self._root)
                self.significant_bits._read()
            elif _on == Png.ColorType.greyscale_alpha:
                pass
                self.significant_bits = Png.SbitGreyscale(True, self._io, self, self._root)
                self.significant_bits._read()
            elif _on == Png.ColorType.indexed:
                pass
                self.significant_bits = Png.SbitTruecolor(False, self._io, self, self._root)
                self.significant_bits._read()
            elif _on == Png.ColorType.truecolor:
                pass
                self.significant_bits = Png.SbitTruecolor(False, self._io, self, self._root)
                self.significant_bits._read()
            elif _on == Png.ColorType.truecolor_alpha:
                pass
                self.significant_bits = Png.SbitTruecolor(True, self._io, self, self._root)
                self.significant_bits._read()
            self._debug['significant_bits']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.significant_bits._fetch_instances()
            elif _on == Png.ColorType.greyscale_alpha:
                pass
                self.significant_bits._fetch_instances()
            elif _on == Png.ColorType.indexed:
                pass
                self.significant_bits._fetch_instances()
            elif _on == Png.ColorType.truecolor:
                pass
                self.significant_bits._fetch_instances()
            elif _on == Png.ColorType.truecolor_alpha:
                pass
                self.significant_bits._fetch_instances()

        @property
        def sample_depth(self):
            if hasattr(self, '_m_sample_depth'):
                return self._m_sample_depth

            self._m_sample_depth = (8 if self._root.ihdr.color_type == Png.ColorType.indexed else self._root.ihdr.bit_depth)
            return getattr(self, '_m_sample_depth', None)


    class SbitGreyscale(KaitaiStruct):
        SEQ_FIELDS = ["grey", "alpha"]
        def __init__(self, has_alpha, _io, _parent=None, _root=None):
            super(Png.SbitGreyscale, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.has_alpha = has_alpha
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['grey']['start'] = self._io.pos()
            self.grey = self._io.read_u1()
            self._debug['grey']['end'] = self._io.pos()
            if not self.grey >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.grey, self._io, u"/types/sbit_greyscale/seq/0")
            if not self.grey <= self._parent.sample_depth:
                raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.grey, self._io, u"/types/sbit_greyscale/seq/0")
            if self.has_alpha:
                pass
                self._debug['alpha']['start'] = self._io.pos()
                self.alpha = self._io.read_u1()
                self._debug['alpha']['end'] = self._io.pos()
                if not self.alpha >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.alpha, self._io, u"/types/sbit_greyscale/seq/1")
                if not self.alpha <= self._parent.sample_depth:
                    raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.alpha, self._io, u"/types/sbit_greyscale/seq/1")



        def _fetch_instances(self):
            pass
            if self.has_alpha:
                pass



    class SbitTruecolor(KaitaiStruct):
        SEQ_FIELDS = ["red", "green", "blue", "alpha"]
        def __init__(self, has_alpha, _io, _parent=None, _root=None):
            super(Png.SbitTruecolor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.has_alpha = has_alpha
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['red']['start'] = self._io.pos()
            self.red = self._io.read_u1()
            self._debug['red']['end'] = self._io.pos()
            if not self.red >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.red, self._io, u"/types/sbit_truecolor/seq/0")
            if not self.red <= self._parent.sample_depth:
                raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.red, self._io, u"/types/sbit_truecolor/seq/0")
            self._debug['green']['start'] = self._io.pos()
            self.green = self._io.read_u1()
            self._debug['green']['end'] = self._io.pos()
            if not self.green >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.green, self._io, u"/types/sbit_truecolor/seq/1")
            if not self.green <= self._parent.sample_depth:
                raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.green, self._io, u"/types/sbit_truecolor/seq/1")
            self._debug['blue']['start'] = self._io.pos()
            self.blue = self._io.read_u1()
            self._debug['blue']['end'] = self._io.pos()
            if not self.blue >= 1:
                raise kaitaistruct.ValidationLessThanError(1, self.blue, self._io, u"/types/sbit_truecolor/seq/2")
            if not self.blue <= self._parent.sample_depth:
                raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.blue, self._io, u"/types/sbit_truecolor/seq/2")
            if self.has_alpha:
                pass
                self._debug['alpha']['start'] = self._io.pos()
                self.alpha = self._io.read_u1()
                self._debug['alpha']['end'] = self._io.pos()
                if not self.alpha >= 1:
                    raise kaitaistruct.ValidationLessThanError(1, self.alpha, self._io, u"/types/sbit_truecolor/seq/3")
                if not self.alpha <= self._parent.sample_depth:
                    raise kaitaistruct.ValidationGreaterThanError(self._parent.sample_depth, self.alpha, self._io, u"/types/sbit_truecolor/seq/3")



        def _fetch_instances(self):
            pass
            if self.has_alpha:
                pass



    class SpltChunk(KaitaiStruct):
        """Suggested palette (`sPLT`) chunk.
        
        Multiple `sPLT` chunks are permitted, but each must have a different
        palette name.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11sPLT
        
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#12Suggested-palettes
        """
        SEQ_FIELDS = ["palette_name", "sample_depth", "entries"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.SpltChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['palette_name']['start'] = self._io.pos()
            self.palette_name = (self._io.read_bytes_term(0, False, True, True)).decode(u"ISO-8859-1")
            self._debug['palette_name']['end'] = self._io.pos()
            self._debug['sample_depth']['start'] = self._io.pos()
            self.sample_depth = self._io.read_u1()
            self._debug['sample_depth']['end'] = self._io.pos()
            if not  ((self.sample_depth == 8) or (self.sample_depth == 16)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.sample_depth, self._io, u"/types/splt_chunk/seq/1")
            self._debug['entries']['start'] = self._io.pos()
            self._debug['entries']['arr'] = []
            self.entries = []
            i = 0
            while not self._io.is_eof():
                self._debug['entries']['arr'].append({'start': self._io.pos()})
                _t_entries = Png.SpltEntry(self._io, self, self._root)
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



    class SpltEntry(KaitaiStruct):
        SEQ_FIELDS = ["red", "green", "blue", "alpha", "freq"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.SpltEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['red']['start'] = self._io.pos()
            _on = self._parent.sample_depth
            if _on == 8:
                pass
                self.red = self._io.read_u1()
            else:
                pass
                self.red = self._io.read_u2be()
            self._debug['red']['end'] = self._io.pos()
            self._debug['green']['start'] = self._io.pos()
            _on = self._parent.sample_depth
            if _on == 8:
                pass
                self.green = self._io.read_u1()
            else:
                pass
                self.green = self._io.read_u2be()
            self._debug['green']['end'] = self._io.pos()
            self._debug['blue']['start'] = self._io.pos()
            _on = self._parent.sample_depth
            if _on == 8:
                pass
                self.blue = self._io.read_u1()
            else:
                pass
                self.blue = self._io.read_u2be()
            self._debug['blue']['end'] = self._io.pos()
            self._debug['alpha']['start'] = self._io.pos()
            _on = self._parent.sample_depth
            if _on == 8:
                pass
                self.alpha = self._io.read_u1()
            else:
                pass
                self.alpha = self._io.read_u2be()
            self._debug['alpha']['end'] = self._io.pos()
            self._debug['freq']['start'] = self._io.pos()
            self.freq = self._io.read_u2be()
            self._debug['freq']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self._parent.sample_depth
            if _on == 8:
                pass
            else:
                pass
            _on = self._parent.sample_depth
            if _on == 8:
                pass
            else:
                pass
            _on = self._parent.sample_depth
            if _on == 8:
                pass
            else:
                pass
            _on = self._parent.sample_depth
            if _on == 8:
                pass
            else:
                pass


    class SrgbChunk(KaitaiStruct):
        """
        .. seealso::
           Source - https://www.w3.org/TR/png/#11sRGB
        """

        class Intent(IntEnum):
            perceptual = 0
            relative_colorimetric = 1
            saturation = 2
            absolute_colorimetric = 3
        SEQ_FIELDS = ["render_intent"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.SrgbChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['render_intent']['start'] = self._io.pos()
            self.render_intent = KaitaiStream.resolve_enum(Png.SrgbChunk.Intent, self._io.read_u1())
            self._debug['render_intent']['end'] = self._io.pos()
            if not isinstance(self.render_intent, Png.SrgbChunk.Intent):
                raise kaitaistruct.ValidationNotInEnumError(self.render_intent, self._io, u"/types/srgb_chunk/seq/0")


        def _fetch_instances(self):
            pass


    class TextChunk(KaitaiStruct):
        """Textual data (`tEXt`) chunk effectively allows you to store key-value
        string pairs in the PNG container.
        
        Both the "key" (`keyword`) and "value" (`text`) parts are restricted to
        printable ISO-8859-1 (Latin-1) characters and ASCII spaces, with the
        exception that `text` can also contain newlines (U+000A LINE FEED (LF)
        characters) and U+00A0 NON-BREAKING SPACE characters.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11tEXt
        """
        SEQ_FIELDS = ["keyword", "text"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.TextChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['keyword']['start'] = self._io.pos()
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"ISO-8859-1")
            self._debug['keyword']['end'] = self._io.pos()
            self._debug['text']['start'] = self._io.pos()
            self.text = (self._io.read_bytes_full()).decode(u"ISO-8859-1")
            self._debug['text']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class TimeChunk(KaitaiStruct):
        """Time chunk stores time stamp of last modification of this image,
        up to 1 second precision in UTC timezone.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11tIME
        """
        SEQ_FIELDS = ["year", "month", "day", "hour", "minute", "second"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.TimeChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['year']['start'] = self._io.pos()
            self.year = self._io.read_u2be()
            self._debug['year']['end'] = self._io.pos()
            self._debug['month']['start'] = self._io.pos()
            self.month = self._io.read_u1()
            self._debug['month']['end'] = self._io.pos()
            self._debug['day']['start'] = self._io.pos()
            self.day = self._io.read_u1()
            self._debug['day']['end'] = self._io.pos()
            self._debug['hour']['start'] = self._io.pos()
            self.hour = self._io.read_u1()
            self._debug['hour']['end'] = self._io.pos()
            self._debug['minute']['start'] = self._io.pos()
            self.minute = self._io.read_u1()
            self._debug['minute']['end'] = self._io.pos()
            self._debug['second']['start'] = self._io.pos()
            self.second = self._io.read_u1()
            self._debug['second']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class TrnsChunk(KaitaiStruct):
        """Transparency (`tRNS`) chunk specifies either alpha values that are
        associated with palette entries (for indexed-color images) or a single
        transparent color (for greyscale and truecolor images).
        
        A `tRNS` chunk must not appear for color types
        `color_type::greyscale_alpha` = 4 and `color_type::truecolor_alpha` = 6,
        since a full alpha channel is already present in those cases.
        
        .. seealso::
           Source - https://www.w3.org/TR/png/#11tRNS
        """
        SEQ_FIELDS = ["palette_alphas", "transparent_color"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.TrnsChunk, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if self._root.ihdr.color_type == Png.ColorType.indexed:
                pass
                self._debug['palette_alphas']['start'] = self._io.pos()
                self._debug['palette_alphas']['arr'] = []
                self.palette_alphas = []
                i = 0
                while not self._io.is_eof():
                    self._debug['palette_alphas']['arr'].append({'start': self._io.pos()})
                    self.palette_alphas.append(self._io.read_u1())
                    self._debug['palette_alphas']['arr'][len(self.palette_alphas) - 1]['end'] = self._io.pos()
                    i += 1

                self._debug['palette_alphas']['end'] = self._io.pos()

            self._debug['transparent_color']['start'] = self._io.pos()
            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.transparent_color = Png.TrnsGreyscaleColor(self._io, self, self._root)
                self.transparent_color._read()
            elif _on == Png.ColorType.truecolor:
                pass
                self.transparent_color = Png.TrnsTruecolorColor(self._io, self, self._root)
                self.transparent_color._read()
            self._debug['transparent_color']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            if self._root.ihdr.color_type == Png.ColorType.indexed:
                pass
                for i in range(len(self.palette_alphas)):
                    pass


            _on = self._root.ihdr.color_type
            if _on == Png.ColorType.greyscale:
                pass
                self.transparent_color._fetch_instances()
            elif _on == Png.ColorType.truecolor:
                pass
                self.transparent_color._fetch_instances()

        @property
        def sample_mask(self):
            if hasattr(self, '_m_sample_mask'):
                return self._m_sample_mask

            self._m_sample_mask = (1 << self._root.ihdr.bit_depth) - 1
            return getattr(self, '_m_sample_mask', None)


    class TrnsGreyscaleColor(KaitaiStruct):
        SEQ_FIELDS = ["grey_raw"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.TrnsGreyscaleColor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['grey_raw']['start'] = self._io.pos()
            self.grey_raw = self._io.read_u2be()
            self._debug['grey_raw']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def grey(self):
            if hasattr(self, '_m_grey'):
                return self._m_grey

            self._m_grey = self.grey_raw & self._parent.sample_mask
            return getattr(self, '_m_grey', None)


    class TrnsTruecolorColor(KaitaiStruct):
        SEQ_FIELDS = ["red_raw", "green_raw", "blue_raw"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Png.TrnsTruecolorColor, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['red_raw']['start'] = self._io.pos()
            self.red_raw = self._io.read_u2be()
            self._debug['red_raw']['end'] = self._io.pos()
            self._debug['green_raw']['start'] = self._io.pos()
            self.green_raw = self._io.read_u2be()
            self._debug['green_raw']['end'] = self._io.pos()
            self._debug['blue_raw']['start'] = self._io.pos()
            self.blue_raw = self._io.read_u2be()
            self._debug['blue_raw']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass

        @property
        def blue(self):
            if hasattr(self, '_m_blue'):
                return self._m_blue

            self._m_blue = self.blue_raw & self._parent.sample_mask
            return getattr(self, '_m_blue', None)

        @property
        def green(self):
            if hasattr(self, '_m_green'):
                return self._m_green

            self._m_green = self.green_raw & self._parent.sample_mask
            return getattr(self, '_m_green', None)

        @property
        def red(self):
            if hasattr(self, '_m_red'):
                return self._m_red

            self._m_red = self.red_raw & self._parent.sample_mask
            return getattr(self, '_m_red', None)



