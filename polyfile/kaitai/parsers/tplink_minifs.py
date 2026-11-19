# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class TplinkMinifs(KaitaiStruct):
    """MiniFS is a file system found in certain firmware files from TP-Link
    (including its Mercusys brand) and Mercury. Such firmware contains an RTOS
    kernel, e.g. VxWorks in
    [`RE450(V4)_210531.zip`](https://static.tp-link.com/firmware/2021/202107/20210709/RE450(V4)_210531.zip)
    ([archived](https://web.archive.org/web/20261105175157/https://static.tp-link.com/firmware/2021/202107/20210709/RE450(V4)_210531.zip))
    or TPOS, TP-Link's RTOS, in
    [`TL-WA850RE(EU)_V7.0_250808.zip`](https://static.tp-link.com/upload/firmware/2025/202509/20250919/TL-WA850RE(EU)_V7.0_250808.zip)
    ([archived](https://web.archive.org/web/20260903180047/https://static.tp-link.com/upload/firmware/2025/202509/20250919/TL-WA850RE(EU)_V7.0_250808.zip)).
    
    According to a TP-Link manager quoted in a
    [2021 article](https://shiftdelete.net/tp-link-mercusys-ile-ilgili-hedeflerini-paylasti)
    ([archived](https://web.archive.org/web/20230513175833/https://shiftdelete.net/tp-link-mercusys-ile-ilgili-hedeflerini-paylasti)),
    Mercusys has been sold in China as Mercury since 2001. All Mercury images
    examined contain a certificate with `O=tplink` in its issuer and subject.
    
    All versions share the same header, and its `version` field determines the
    layout of the rest of the image.
    
    In version 3, the header is followed by a table of directory paths and file
    names, followed by meta information for each file, meta information about
    the LZMA compressed blobs including length, offset and uncompressed length,
    and then a number of LZMA compressed blobs.
    
    The LZMA blobs can contain the concatenated contents of multiple files.
    The meta information of a file contains the offsets of its directory path
    and file name, the LZMA blob (numbering starts at 0), the offset of the file
    in the uncompressed data and the size of the uncompressed file.
    
    Some version 3 images have no uncompressed length in the meta information
    about the blobs (see `has_8_byte_lzma_metas` in `body_v3`).
    
    In version 2, the header is followed by the length of the files area and a
    meta information record for each file, each followed directly by the file's
    data. Unlike versions 1 and 3, version 2 stores no paths or file names at
    all, only the MD5 hash of each file's path.
    
    In version 1, the header is followed by a record with the path, the compressed
    length and the offset of each file, and then one LZMA blob per file.
    
    This Kaitai Struct implementation was written independently of the paper
    [Reverse Engineered MiniFS File System](https://arxiv.org/abs/2407.05064v1).
    It was started in the firmware analysis project
    [BANG](https://github.com/armijnhemel/binaryanalysis-ng) (Binary Analysis
    Next Generation) in
    [2021](https://github.com/armijnhemel/binaryanalysis-ng/commit/531203a076e3761116320b77b2b9c64a9dca6186)
    and submitted to the Kaitai Struct format gallery in
    [September 2023](https://github.com/kaitai-io/kaitai_struct_formats/pull/682),
    whereas the paper was published in July 2024.
    
    .. seealso::
       The paper, section 4 (version 3) - https://arxiv.org/html/2407.05064v1#S4
    
    
    .. seealso::
       tp_research's `Minifs.py` (version 2) - https://github.com/zh-explorer/tp_research/blob/a42f9d0427ad0c453a7060f3236c4174bb883441/Minifs.py
    
    
    .. seealso::
       unblob's MiniFS handler (version 3) - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py
    """

    class CompressionType(IntEnum):
        lzma = 0
        raw = 2
        lzma_2014 = 4
    SEQ_FIELDS = ["header", "body"]
    def __init__(self, _io, _parent=None, _root=None):
        super(TplinkMinifs, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = TplinkMinifs.MinifsHeader(self._io, self, self._root)
        self.header._read()
        self._debug['header']['end'] = self._io.pos()
        self._debug['body']['start'] = self._io.pos()
        _on = self.header.version
        if _on == 1:
            pass
            self.body = TplinkMinifs.BodyV1(self._io, self, self._root)
            self.body._read()
        elif _on == 2:
            pass
            self.body = TplinkMinifs.BodyV2(self._io, self, self._root)
            self.body._read()
        elif _on == 3:
            pass
            self.body = TplinkMinifs.BodyV3(self._io, self, self._root)
            self.body._read()
        self._debug['body']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.header._fetch_instances()
        _on = self.header.version
        if _on == 1:
            pass
            self.body._fetch_instances()
        elif _on == 2:
            pass
            self.body._fetch_instances()
        elif _on == 3:
            pass
            self.body._fetch_instances()

    class BodyV1(KaitaiStruct):
        """
        .. seealso::
           Source - https://arxiv.org/html/2407.05064v1#S2.SS2
        """
        SEQ_FIELDS = ["inodes", "blobs_area"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.BodyV1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['inodes']['start'] = self._io.pos()
            self._debug['inodes']['arr'] = []
            self.inodes = []
            for i in range(self._root.header.num_files):
                self._debug['inodes']['arr'].append({'start': self._io.pos()})
                _t_inodes = TplinkMinifs.InodeV1((self.inodes[i - 1].ofs_end if i != 0 else 0), self._io, self, self._root)
                try:
                    _t_inodes._read()
                finally:
                    self.inodes.append(_t_inodes)
                self._debug['inodes']['arr'][i]['end'] = self._io.pos()

            self._debug['inodes']['end'] = self._io.pos()
            self._debug['blobs_area']['start'] = self._io.pos()
            self._raw_blobs_area = self._io.read_bytes(self.inodes[-1].ofs_end)
            _io__raw_blobs_area = KaitaiStream(BytesIO(self._raw_blobs_area))
            self.blobs_area = TplinkMinifs.Dummy(_io__raw_blobs_area, self, self._root)
            self.blobs_area._read()
            self._debug['blobs_area']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.inodes)):
                pass
                self.inodes[i]._fetch_instances()

            self.blobs_area._fetch_instances()


    class BodyV2(KaitaiStruct):
        SEQ_FIELDS = ["len_files_area", "files_area"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.BodyV2, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_files_area']['start'] = self._io.pos()
            self.len_files_area = self._io.read_u4be()
            self._debug['len_files_area']['end'] = self._io.pos()
            self._debug['files_area']['start'] = self._io.pos()
            self._raw_files_area = self._io.read_bytes(self.len_files_area)
            _io__raw_files_area = KaitaiStream(BytesIO(self._raw_files_area))
            self.files_area = TplinkMinifs.FilesAreaV2(_io__raw_files_area, self, self._root)
            self.files_area._read()
            self._debug['files_area']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.files_area._fetch_instances()


    class BodyV3(KaitaiStruct):
        SEQ_FIELDS = ["len_name_table", "name_table", "inodes", "_unnamed3", "lzma_metas", "lzma_blobs_area"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.BodyV3, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len_name_table']['start'] = self._io.pos()
            self.len_name_table = self._io.read_u4be()
            self._debug['len_name_table']['end'] = self._io.pos()
            self._debug['name_table']['start'] = self._io.pos()
            self._raw_name_table = self._io.read_bytes(self.len_name_table)
            _io__raw_name_table = KaitaiStream(BytesIO(self._raw_name_table))
            self.name_table = TplinkMinifs.NameTable(_io__raw_name_table, self, self._root)
            self.name_table._read()
            self._debug['name_table']['end'] = self._io.pos()
            self._debug['inodes']['start'] = self._io.pos()
            self._debug['inodes']['arr'] = []
            self.inodes = []
            for i in range(self._root.header.num_files):
                self._debug['inodes']['arr'].append({'start': self._io.pos()})
                _t_inodes = TplinkMinifs.Inode((self.inodes[i - 1].cur_max_lzma_blob if i != 0 else 0), self._io, self, self._root)
                try:
                    _t_inodes._read()
                finally:
                    self.inodes.append(_t_inodes)
                self._debug['inodes']['arr'][i]['end'] = self._io.pos()

            self._debug['inodes']['end'] = self._io.pos()
            if self.ofs_lzma_metas < 0:
                pass
                self._debug['_unnamed3']['start'] = self._io.pos()
                self._unnamed3 = self._io.read_bytes(0)
                self._debug['_unnamed3']['end'] = self._io.pos()

            self._debug['lzma_metas']['start'] = self._io.pos()
            self._debug['lzma_metas']['arr'] = []
            self.lzma_metas = []
            for i in range(self.num_lzma_blobs):
                self._debug['lzma_metas']['arr'].append({'start': self._io.pos()})
                _t_lzma_metas = TplinkMinifs.LzmaMeta((self.lzma_metas[i - 1].ofs_end if i != 0 else 0), self._io, self, self._root)
                try:
                    _t_lzma_metas._read()
                finally:
                    self.lzma_metas.append(_t_lzma_metas)
                self._debug['lzma_metas']['arr'][i]['end'] = self._io.pos()

            self._debug['lzma_metas']['end'] = self._io.pos()
            self._debug['lzma_blobs_area']['start'] = self._io.pos()
            self._raw_lzma_blobs_area = self._io.read_bytes(self.lzma_metas[-1].ofs_end)
            _io__raw_lzma_blobs_area = KaitaiStream(BytesIO(self._raw_lzma_blobs_area))
            self.lzma_blobs_area = TplinkMinifs.Dummy(_io__raw_lzma_blobs_area, self, self._root)
            self.lzma_blobs_area._read()
            self._debug['lzma_blobs_area']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.name_table._fetch_instances()
            for i in range(len(self.inodes)):
                pass
                self.inodes[i]._fetch_instances()

            if self.ofs_lzma_metas < 0:
                pass

            for i in range(len(self.lzma_metas)):
                pass
                self.lzma_metas[i]._fetch_instances()

            self.lzma_blobs_area._fetch_instances()
            _ = self.len_first_blob_uncompressed_if_8_byte_metas
            if hasattr(self, '_m_len_first_blob_uncompressed_if_8_byte_metas'):
                pass


        @property
        def has_8_byte_lzma_metas(self):
            """Whether each record in `lzma_metas` lacks `len_blob_uncompressed` and
            is therefore 8 bytes in size instead of 12.
            
            The MiniFS header doesn't say which size is used (both use version 3),
            so this Kaitai Struct implementation infers it using a heuristic based
            on the `.lzma` header of the first blob. Bytes 5 to 12 of that header
            are the uncompressed size, which was unknown (all bits set) for all
            blobs in all version 3 images examined. So with 8-byte records,
            `len_first_blob_uncompressed_if_8_byte_metas` has all bits set. With
            12-byte records, the same 8 bytes aren't the uncompressed size. With 3
            or more blobs, they include a whole offset or length in `lzma_metas`,
            which would have to be 4 GiB. With 1 or 2 blobs, they include the
            first blob's dictionary size, which is 8 MiB in all images examined.
            
            An image with 8-byte records and a known uncompressed size would be
            rejected, or misparsed if it has a single blob and other data follows it.
            
            In the images examined, 8-byte records occur in firmware files with
            modification times from 2018 to 2022 (as stored in their ZIPs), e.g. in
            [`MW301R(EU)_V2_180821.zip`](https://static.mercusys.com/software/MW301R(EU)_V2_180821.zip)
            ([archived](https://web.archive.org/web/20261105093950/https://static.mercusys.com/software/MW301R(EU)_V2_180821.zip)),
            listed on <https://www.mercusys.com/en/download/mw301r/v2/>
            ([archived](https://web.archive.org/web/20261105142659/https://www.mercusys.com/en/download/mw301r/v2/)).
            
            As far as we know, this implementation is the first description of
            8-byte records. The other descriptions and tools found either assume
            12 bytes or don't read `lzma_metas` at all. So there is no reference
            to compare it with, and the evidence comes from the images. In all 49
            distinct images examined with 8-byte records, the bytes at each
            record's offset and length are exactly one complete LZMA stream. Each
            such stream decompresses to exactly the length that the files packed
            into it need. The file that ends last in it ends exactly where the
            decompressed data ends. In addition:
            
            * 2614 of the 7230 files in these 49 images have the same path and
              contents as a file in an image with 12-byte records. For example,
              49 files are the same in the image with 8-byte records in
              [`TL-WA850RE(EU)_V7_201029.zip`](https://static.tp-link.com/2021/202102/20210209/TL-WA850RE(EU)_V7_201029.zip)
              ([archived](https://web.archive.org/web/20220326032207/https://static.tp-link.com/2021/202102/20210209/TL-WA850RE(EU)_V7_201029.zip))
              and the image with 12-byte records in
              [`TL-WA850RE(EU)_V7.0_250808.zip`](https://static.tp-link.com/upload/firmware/2025/202509/20250919/TL-WA850RE(EU)_V7.0_250808.zip)
              ([archived](https://web.archive.org/web/20260903180047/https://static.tp-link.com/upload/firmware/2025/202509/20250919/TL-WA850RE(EU)_V7.0_250808.zip)).
            * The repository
              [NurMohammadDuari/mw325r-hack-lab](https://github.com/NurMohammadDuari/mw325r-hack-lab/tree/024da680dbf4f9ca287d562622f02d7d8875bd45)
              has the [files](https://github.com/NurMohammadDuari/mw325r-hack-lab/tree/024da680dbf4f9ca287d562622f02d7d8875bd45/extracted-minifs)
              of the image with 8-byte records in
              [`MW325R(EU)_V2_20111620201211065426.zip`](https://static.mercusys.com/software/MW325R(EU)_V2_20111620201211065426.zip)
              ([archived](https://web.archive.org/web/20261105093427/https://static.mercusys.com/software/MW325R(EU)_V2_20111620201211065426.zip)).
              They match the files parsed by this implementation in all 92 files
              that can be compared. Its
              [extractor](https://github.com/NurMohammadDuari/mw325r-hack-lab/blob/024da680dbf4f9ca287d562622f02d7d8875bd45/analysis/minifs_extract.py)
              finds the blobs by searching for LZMA headers instead of reading
              `lzma_metas`.
            """
            if hasattr(self, '_m_has_8_byte_lzma_metas'):
                return self._m_has_8_byte_lzma_metas

            self._m_has_8_byte_lzma_metas = self.len_first_blob_uncompressed_if_8_byte_metas == 18446744073709551615
            return getattr(self, '_m_has_8_byte_lzma_metas', None)

        @property
        def len_first_blob_uncompressed_if_8_byte_metas(self):
            """The uncompressed size in the `.lzma` header of the first blob, if
            `lzma_metas` have 8-byte records. It follows the properties byte and the
            4-byte dictionary size.
            """
            if hasattr(self, '_m_len_first_blob_uncompressed_if_8_byte_metas'):
                return self._m_len_first_blob_uncompressed_if_8_byte_metas

            _pos = self._io.pos()
            self._io.seek((self.ofs_lzma_metas + 8 * self.num_lzma_blobs) + 5)
            self._debug['_m_len_first_blob_uncompressed_if_8_byte_metas']['start'] = self._io.pos()
            self._m_len_first_blob_uncompressed_if_8_byte_metas = self._io.read_u8le()
            self._debug['_m_len_first_blob_uncompressed_if_8_byte_metas']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_len_first_blob_uncompressed_if_8_byte_metas', None)

        @property
        def len_lzma_meta(self):
            """The size of each record in `lzma_metas` (8 or 12 bytes)."""
            if hasattr(self, '_m_len_lzma_meta'):
                return self._m_len_lzma_meta

            self._m_len_lzma_meta = (8 if self.has_8_byte_lzma_metas else 12)
            return getattr(self, '_m_len_lzma_meta', None)

        @property
        def num_lzma_blobs(self):
            """Count starts at 0, so there is one more blob than the highest blob number.
            
            .. seealso::
               Source - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py#L129-L130
            """
            if hasattr(self, '_m_num_lzma_blobs'):
                return self._m_num_lzma_blobs

            self._m_num_lzma_blobs = self.inodes[-1].cur_max_lzma_blob + 1
            return getattr(self, '_m_num_lzma_blobs', None)

        @property
        def ofs_lzma_metas(self):
            if hasattr(self, '_m_ofs_lzma_metas'):
                return self._m_ofs_lzma_metas

            self._m_ofs_lzma_metas = self._io.pos()
            return getattr(self, '_m_ofs_lzma_metas', None)


    class Dummy(KaitaiStruct):
        SEQ_FIELDS = []
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.Dummy, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass


    class FileV2(KaitaiStruct):
        """
        .. seealso::
           Source - https://github.com/zh-explorer/tp_research/blob/a42f9d0427ad0c453a7060f3236c4174bb883441/Minifs.py#L41-L52
        """
        SEQ_FIELDS = ["path_md5", "len_data", "ofs_data", "len_data_uncompressed", "compression", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.FileV2, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['path_md5']['start'] = self._io.pos()
            self.path_md5 = self._io.read_bytes(16)
            self._debug['path_md5']['end'] = self._io.pos()
            self._debug['len_data']['start'] = self._io.pos()
            self.len_data = self._io.read_u4be()
            self._debug['len_data']['end'] = self._io.pos()
            self._debug['ofs_data']['start'] = self._io.pos()
            self.ofs_data = self._io.read_u4be()
            self._debug['ofs_data']['end'] = self._io.pos()
            if not self.ofs_data == self._io.pos() + 8:
                raise kaitaistruct.ValidationNotEqualError(self._io.pos() + 8, self.ofs_data, self._io, u"/types/file_v2/seq/2")
            self._debug['len_data_uncompressed']['start'] = self._io.pos()
            self.len_data_uncompressed = self._io.read_u4be()
            self._debug['len_data_uncompressed']['end'] = self._io.pos()
            self._debug['compression']['start'] = self._io.pos()
            self.compression = KaitaiStream.resolve_enum(TplinkMinifs.CompressionType, self._io.read_u4be())
            self._debug['compression']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self.data = self._io.read_bytes(self.len_data)
            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class FilesAreaV2(KaitaiStruct):
        SEQ_FIELDS = ["files"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.FilesAreaV2, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['files']['start'] = self._io.pos()
            self._debug['files']['arr'] = []
            self.files = []
            for i in range(self._root.header.num_files):
                self._debug['files']['arr'].append({'start': self._io.pos()})
                _t_files = TplinkMinifs.FileV2(self._io, self, self._root)
                try:
                    _t_files._read()
                finally:
                    self.files.append(_t_files)
                self._debug['files']['arr'][i]['end'] = self._io.pos()

            self._debug['files']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.files)):
                pass
                self.files[i]._fetch_instances()



    class Inode(KaitaiStruct):
        """
        .. seealso::
           Source - https://arxiv.org/html/2407.05064v1#S4.SS3
        
        
        .. seealso::
           Source - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py#L36-L42
        """
        SEQ_FIELDS = ["ofs_directory_path", "ofs_file_name", "lzma_blob", "ofs_file", "len_file"]
        def __init__(self, prev_max_lzma_blob, _io, _parent=None, _root=None):
            super(TplinkMinifs.Inode, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.prev_max_lzma_blob = prev_max_lzma_blob
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_directory_path']['start'] = self._io.pos()
            self.ofs_directory_path = self._io.read_u4be()
            self._debug['ofs_directory_path']['end'] = self._io.pos()
            self._debug['ofs_file_name']['start'] = self._io.pos()
            self.ofs_file_name = self._io.read_u4be()
            self._debug['ofs_file_name']['end'] = self._io.pos()
            self._debug['lzma_blob']['start'] = self._io.pos()
            self.lzma_blob = self._io.read_u4be()
            self._debug['lzma_blob']['end'] = self._io.pos()
            self._debug['ofs_file']['start'] = self._io.pos()
            self.ofs_file = self._io.read_u4be()
            self._debug['ofs_file']['end'] = self._io.pos()
            self._debug['len_file']['start'] = self._io.pos()
            self.len_file = self._io.read_u4be()
            self._debug['len_file']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _ = self.directory_path
            if hasattr(self, '_m_directory_path'):
                pass

            _ = self.file_name
            if hasattr(self, '_m_file_name'):
                pass


        @property
        def cur_max_lzma_blob(self):
            if hasattr(self, '_m_cur_max_lzma_blob'):
                return self._m_cur_max_lzma_blob

            self._m_cur_max_lzma_blob = (self.lzma_blob if self.lzma_blob > self.prev_max_lzma_blob else self.prev_max_lzma_blob)
            return getattr(self, '_m_cur_max_lzma_blob', None)

        @property
        def directory_path(self):
            if hasattr(self, '_m_directory_path'):
                return self._m_directory_path

            io = self._parent.name_table._io
            _pos = io.pos()
            io.seek(self.ofs_directory_path)
            self._debug['_m_directory_path']['start'] = io.pos()
            self._m_directory_path = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['_m_directory_path']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_directory_path', None)

        @property
        def file_name(self):
            if hasattr(self, '_m_file_name'):
                return self._m_file_name

            io = self._parent.name_table._io
            _pos = io.pos()
            io.seek(self.ofs_file_name)
            self._debug['_m_file_name']['start'] = io.pos()
            self._m_file_name = (io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self._debug['_m_file_name']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_file_name', None)


    class InodeV1(KaitaiStruct):
        SEQ_FIELDS = ["path", "len_blob", "ofs_blob"]
        def __init__(self, prev_ofs_end, _io, _parent=None, _root=None):
            super(TplinkMinifs.InodeV1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.prev_ofs_end = prev_ofs_end
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['path']['start'] = self._io.pos()
            self.path = (KaitaiStream.bytes_terminate(self._io.read_bytes(80), 0, False)).decode(u"ASCII")
            self._debug['path']['end'] = self._io.pos()
            self._debug['len_blob']['start'] = self._io.pos()
            self.len_blob = self._io.read_u4be()
            self._debug['len_blob']['end'] = self._io.pos()
            self._debug['ofs_blob']['start'] = self._io.pos()
            self.ofs_blob = self._io.read_u4be()
            self._debug['ofs_blob']['end'] = self._io.pos()
            if not self.ofs_blob == self.prev_ofs_end:
                raise kaitaistruct.ValidationNotEqualError(self.prev_ofs_end, self.ofs_blob, self._io, u"/types/inode_v1/seq/2")


        def _fetch_instances(self):
            pass
            _ = self.blob
            if hasattr(self, '_m_blob'):
                pass


        @property
        def blob(self):
            """An LZMA stream in the `.lzma` format (also known as LZMA_Alone) with
            the contents of the file. Decompress it in the same way as
            `<lzma_meta>.blob`.
            
            In all images examined, the `.lzma` header specifies the properties
            lc = 0, lp = 0, pb = 2 and an 8 MiB dictionary, so it starts with the
            bytes `5A 00 00 80 00`. It also specifies the uncompressed size of the
            stream, and there is no end-of-payload marker.
            """
            if hasattr(self, '_m_blob'):
                return self._m_blob

            io = self._parent.blobs_area._io
            _pos = io.pos()
            io.seek(self.ofs_blob)
            self._debug['_m_blob']['start'] = io.pos()
            self._m_blob = io.read_bytes(self.len_blob)
            self._debug['_m_blob']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_blob', None)

        @property
        def ofs_end(self):
            if hasattr(self, '_m_ofs_end'):
                return self._m_ofs_end

            self._m_ofs_end = self.ofs_blob + self.len_blob
            return getattr(self, '_m_ofs_end', None)


    class LzmaMeta(KaitaiStruct):
        """
        .. seealso::
           Source - https://arxiv.org/html/2407.05064v1#S4.SS4
        
        
        .. seealso::
           Source - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py#L44-L48
        """
        SEQ_FIELDS = ["ofs_blob", "len_blob", "len_blob_uncompressed"]
        def __init__(self, prev_ofs_end, _io, _parent=None, _root=None):
            super(TplinkMinifs.LzmaMeta, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.prev_ofs_end = prev_ofs_end
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['ofs_blob']['start'] = self._io.pos()
            self.ofs_blob = self._io.read_u4be()
            self._debug['ofs_blob']['end'] = self._io.pos()
            if not self.ofs_blob == self.prev_ofs_end:
                raise kaitaistruct.ValidationNotEqualError(self.prev_ofs_end, self.ofs_blob, self._io, u"/types/lzma_meta/seq/0")
            self._debug['len_blob']['start'] = self._io.pos()
            self.len_blob = self._io.read_u4be()
            self._debug['len_blob']['end'] = self._io.pos()
            if (not (self._parent.has_8_byte_lzma_metas)):
                pass
                self._debug['len_blob_uncompressed']['start'] = self._io.pos()
                self.len_blob_uncompressed = self._io.read_u4be()
                self._debug['len_blob_uncompressed']['end'] = self._io.pos()



        def _fetch_instances(self):
            pass
            if (not (self._parent.has_8_byte_lzma_metas)):
                pass

            _ = self.blob
            if hasattr(self, '_m_blob'):
                pass


        @property
        def blob(self):
            """An LZMA stream in the `.lzma` format (also known as LZMA_Alone):
            a 13-byte header followed by the compressed data. Decompress it
            with a ready-made LZMA decoder that reads this header, e.g. in
            Python with `lzma.decompress(blob, format=lzma.FORMAT_ALONE)`. The
            size of the decompressed data is `len_blob_uncompressed`, if present.
            
            In all images examined with `header.version` = 3, the `.lzma` header
            specifies the properties lc = 3, lp = 0, pb = 2 and an 8 MiB
            dictionary, so it starts with the bytes `5D 00 00 80 00`. The
            uncompressed size in the header is unknown (`0xFFFF_FFFF_FFFF_FFFF`),
            so the stream ends with an end-of-payload marker.
            
            .. seealso::
               Source - https://arxiv.org/html/2407.05064v1#S4.SS5
            
            
            .. seealso::
               Source - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py#L175-L187
            """
            if hasattr(self, '_m_blob'):
                return self._m_blob

            io = self._parent.lzma_blobs_area._io
            _pos = io.pos()
            io.seek(self.ofs_blob)
            self._debug['_m_blob']['start'] = io.pos()
            self._m_blob = io.read_bytes(self.len_blob)
            self._debug['_m_blob']['end'] = io.pos()
            io.seek(_pos)
            return getattr(self, '_m_blob', None)

        @property
        def ofs_end(self):
            if hasattr(self, '_m_ofs_end'):
                return self._m_ofs_end

            self._m_ofs_end = self.ofs_blob + self.len_blob
            return getattr(self, '_m_ofs_end', None)


    class MinifsHeader(KaitaiStruct):
        """
        .. seealso::
           Source - https://arxiv.org/html/2407.05064v1#S4.SS1
        
        
        .. seealso::
           Source - https://github.com/onekey-sec/unblob/blob/678dbce13dcabe3b4ff16b2b958d6f2cfce9ae3f/python/unblob/handlers/filesystem/minifs.py#L27-L34
        """
        SEQ_FIELDS = ["magic", "version", "num_files", "len_largest_file"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.MinifsHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(16)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x4D\x49\x4E\x49\x46\x53\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x4D\x49\x4E\x49\x46\x53\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", self.magic, self._io, u"/types/minifs_header/seq/0")
            self._debug['version']['start'] = self._io.pos()
            self.version = self._io.read_u4be()
            self._debug['version']['end'] = self._io.pos()
            if not  ((self.version == 1) or (self.version == 2) or (self.version == 3)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.version, self._io, u"/types/minifs_header/seq/1")
            self._debug['num_files']['start'] = self._io.pos()
            self.num_files = self._io.read_u4be()
            self._debug['num_files']['end'] = self._io.pos()
            self._debug['len_largest_file']['start'] = self._io.pos()
            self.len_largest_file = self._io.read_u4be()
            self._debug['len_largest_file']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class NameTable(KaitaiStruct):
        """Table of null-terminated directory paths and file names, referenced by
        `<inode>.ofs_directory_path` and `<inode>.ofs_file_name`. In all images
        examined, each non-empty string occurs only once, which saves space in
        flash memory, as many files share a directory or a name.
        
        In all images examined, the table is padded with null bytes to a multiple
        of 4 bytes, so `names` can end with up to 3 empty strings (one for each
        padding byte).
        
        .. seealso::
           Source - https://arxiv.org/html/2407.05064v1#S4.SS2
        """
        SEQ_FIELDS = ["names"]
        def __init__(self, _io, _parent=None, _root=None):
            super(TplinkMinifs.NameTable, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['names']['start'] = self._io.pos()
            self._debug['names']['arr'] = []
            self.names = []
            i = 0
            while not self._io.is_eof():
                self._debug['names']['arr'].append({'start': self._io.pos()})
                self.names.append((self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII"))
                self._debug['names']['arr'][len(self.names) - 1]['end'] = self._io.pos()
                i += 1

            self._debug['names']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.names)):
                pass




