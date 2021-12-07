from pathlib import Path
import struct
from typing import Iterator, Optional
import zipfile

from kaitaistruct import KaitaiStructError

from .fileutils import FileStream, Tempfile
from .kaitai.parser import KaitaiParser
from .kaitai.parsers.zip import Zip
from .kaitaimatcher import ast_to_matches
from .logger import StatusLogger
from .magic import MagicMatcher
from .polyfile import InvalidMatch, Match, Submatch, submatcher

log = StatusLogger("polyfile")

with Tempfile(b"""# The default libmagic tests for detecting ZIPs assumes they start at byte offset zero
0 search \\x50\\x4b\\x05\\x06 ZIP end of central directory record
!:mime application/zip
!:ext zip
""", prefix="RelaxedZipMatcher") as t:
    MagicMatcher.DEFAULT_INSTANCE.add(Path(t))


class CentralDirectory:
    def __init__(self, data: bytes, offset: int):
        if data[offset:offset + 4] != b"\x50\x4b\x01\x02":
            raise ValueError(f"Invalid ZIP central directory header at byte offset {offset}")
        self.offset: int = offset
        self.version_made_by: int
        self.version_needed_to_extract: int
        self.general_bit_flag: int
        self.compression_method: int
        self.file_last_modification_time: int
        self.file_last_modification_date: int
        self.crc32: int
        self.compressed_size: int
        self.uncompressed_size: int
        self.file_name_length: int
        self.extra_field_length: int
        self.file_comment_length: int
        self.disk_number: int
        self.internal_file_attrs: int
        self.external_file_attrs: int
        self.file_header_offset: int
        try:
            self.version_made_by, self.version_needed_to_extract, self.general_bit_flag, self.compression_method, \
                self.file_last_modification_time, self.file_last_modification_date, self.crc32, self.compressed_size, \
                self.uncompressed_size, self.file_name_length, self.extra_field_length, self.file_comment_length, \
                self.disk_number, self.internal_file_attrs, self.external_file_attrs, self.file_header_offset = \
                struct.unpack("<HHHHHHIIIHHHHHII", data[offset+4:offset+4+42])
        except struct.error:
            raise ValueError("Error parsing central directory")
        self.file_name: bytes = data[offset+46:offset+46+self.file_name_length]
        self.extra_field: bytes = data[
            offset+46+self.file_name_length:offset+46+self.file_name_length+self.extra_field_length
        ]
        self.file_comment: bytes = data[
            offset+46+self.file_name_length+self.extra_field_length:
            offset+46+self.file_name_length+self.extra_field_length+self.file_comment_length
        ]

    @property
    def num_bytes(self) -> int:
        return 46 + self.file_name_length + self.extra_field_length + self.file_comment_length

    @staticmethod
    def load(data: bytes, offset: int) -> Optional["CentralDirectory"]:
        try:
            return CentralDirectory(data=data, offset=offset)
        except ValueError as e:
            log.error(str(e))
            return None


class EndOfCentralDirectory:
    def __init__(self, data: bytes, offset: int):
        self.offset: int = offset
        self.data: bytes = data
        if not data[offset:].startswith(b"\x50\x4b\x05\x06"):
            raise ValueError("Invalid start to the central directory: expected \"\\x50\\x4b\\x05\\x06\" but got "
                             f"{data!r}")
        self.disk_number: int
        self.start_disk: int
        self.num_records: int
        self.total_records: int
        self.central_directory_bytes: int
        self.central_directory_offset: int
        self.comment_length: int
        try:
            self.disk_number, self.start_disk, self.num_records, self.total_records, self.central_directory_bytes, \
                self.central_directory_offset, self.comment_length = \
                struct.unpack("<HHHHIIH", data[offset+4:offset+4+18])
        except struct.error:
            raise ValueError(f"Error reading the end of central directory header at offset {offset}")
        self.comment: bytes = data[offset+22:offset+22+self.comment_length]
        self.num_bytes: int = 22 + self.comment_length

    def central_directories(self) -> Iterator[CentralDirectory]:
        cdo = self.central_directory_offset
        while cdo < self.offset:
            cd = CentralDirectory.load(self.data, cdo)
            if cd is None:
                break
            yield cd
            cdo += cd.num_bytes

    @staticmethod
    def load(file_stream: FileStream) -> Optional["EndOfCentralDirectory"]:
        offset_before = file_stream.tell()
        try:
            data = file_stream.read()
        finally:
            file_stream.seek(offset_before)
        # first, find the end of central directory record
        eocd = data.rfind(b"\x50\x4b\x05\x06")
        if eocd < 0:
            log.warning(f"Could not find central directory record for {file_stream.name}")
            return None
        try:
            return EndOfCentralDirectory(data, eocd)
        except ValueError as e:
            log.error(str(e))
            return None


def find_zip_start(file_stream: FileStream) -> Optional[int]:
    offset_before = file_stream.tell()
    try:
        data = file_stream.read()
    finally:
        file_stream.seek(offset_before)
    # first, find the end of central directory record
    eocd = data.rfind(b"\x50\x4b\x05\x06")
    if eocd < 0:
        log.warning(f"Could not find central directory record for {file_stream.name}")
        return None
    try:
        central_dir_offset = struct.unpack("<I", data[eocd+16:eocd+16+4])[0]
    except struct.error:
        log.error("Error reading the central directory offset from the end of central directory header")
        return None
    # find the smallest local file offset
    fho: Optional[int] = None
    while central_dir_offset < eocd:
        cd = CentralDirectory.read(data, central_dir_offset)
        if cd is None:
            return None
        central_dir_offset += cd.num_bytes
        if data[cd.file_header_offset:cd.file_header_offset+4] != b"\x50\x4b\x03\x04":
            log.error(f"Invalid file header at offset {cd.file_header_offset}")
        elif fho is None or cd.file_header_offset < fho:
            fho = cd.file_header_offset
    return fho


@submatcher("application/zip")
class ZipFile(Match):
    def submatch(self, file_stream):
        eocd = EndOfCentralDirectory.load(file_stream)
        if eocd is None:
            raise InvalidMatch()
        for cd in eocd.central_directories():
            cd_obj = Submatch(
                "CentralDirectory",
                match_obj=eocd.data[cd.offset:cd.offset+cd.num_bytes],
                relative_offset=cd.offset,
                length=cd.num_bytes,
                parent=self,
                matcher=self.matcher,
            )
            yield cd_obj

        eocd_obj = Submatch(
            "EndOfCentralDirectory",
            match_obj=eocd.data[eocd.offset:eocd.offset+eocd.num_bytes],
            relative_offset=eocd.offset,
            length=eocd.num_bytes,
            parent=self,
            matcher=self.matcher
        )
        yield eocd_obj
        for name, value, relative_offset, length in (
                ("Signature", 0x06054b50, 0, 4),
                ("DiskNumber", eocd.disk_number, 4, 2),
                ("StartDisk", eocd.start_disk, 6, 2),
                ("NumRecords", eocd.num_records, 8, 2),
                ("TotalRecords", eocd.total_records, 10, 2),
                ("CentralDirectoryBytes", eocd.central_directory_bytes, 12, 4),
                ("CentralDirectoryOffset", eocd.central_directory_offset, 16, 4),
                ("CommentLength", eocd.comment_length, 20, 2),
                ("Comment", eocd.comment, 22, eocd.comment_length)
        ):
            last_obj = Submatch(
                name,
                match_obj=value,
                relative_offset=relative_offset,
                length=length,
                parent=eocd_obj,
                matcher=self.matcher
            )
            yield last_obj
        with Tempfile(eocd.comment) as comment_file:
            # last_obj should be the comment match
            yield from self.matcher.match(comment_file, parent=last_obj)
        #
        # offset = find_zip_start(file_stream)
        # if offset is None:
        #     offset = 0
        # file_stream = FileStream(file_stream, start=offset)
        # yielded = False
        # try:
        #     file_stream.seek(offset)
        #     ast = KaitaiParser(Zip).parse(file_stream).ast
        #     yield from ast_to_matches(ast, parent=self)
        #     yielded = True
        # except (KaitaiStructError, EOFError) as e:
        #     log.debug(str(e))
        # try:
        #     file_stream.seek(offset)
        #     with zipfile.ZipFile(file_stream) as zf:
        #         for name in zf.namelist():
        #             with Tempfile(zf.read(name)) as f:
        #                 yield from self.matcher.match(f, parent=self)
        #     yielded = True
        # except (zipfile.BadZipFile, EOFError):
        #     pass
        # if not yielded:
        #     raise InvalidMatch()
