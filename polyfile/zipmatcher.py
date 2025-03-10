from io import BytesIO
from pathlib import Path
from typing import Iterator, Optional
from zipfile import ZipFile as PythonZip

from .fileutils import ExactNamedTempfile, FileStream, Tempfile
from .logger import StatusLogger
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType
from .polyfile import InvalidMatch, register_parser
from .structmatcher import PolyFileStruct
from .structs import ByteField, Constant, Endianness, StructError, UInt16, UInt32

log = StatusLogger("polyfile")

with ExactNamedTempfile(b"""# The default libmagic tests for detecting ZIPs assumes they start at byte offset zero
0 search \\x50\\x4b\\x05\\x06 ZIP end of central directory record
!:mime application/zip
!:ext zip
""", name="RelaxedZipMatcher") as t:
    relaxed_zip_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t))[0]


# The default libmagic test for detecting JARs is too restrictive:
class RelaxedJarMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/java-archive",
            extensions=("jar",),
            message="Java JAR archive",
            parent=relaxed_zip_matcher
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if parent_match is None:
            return FailedTest(self, offset=absolute_offset, message="file is not a ZIP")
        bstream = BytesIO(data)
        setattr(bstream, "name", "RelaxedJarMatcherBytes")
        stream = FileStream(bstream)
        stream.seek(parent_match.offset)
        try:
            eocd = EndOfCentralDirectory.read(stream)
            for cd in eocd.central_directories(stream):
                header = cd.local_file_header(stream)
                if header.extra_field == b"\xFE\xCA\x00\x00" or header.file_name == b"META-INF/MANIFEST.MF":
                    return MatchedTest(self, value=data, offset=0, length=len(data))
        except StructError as e:
            return FailedTest(self, offset=absolute_offset, message=str(e))
        return FailedTest(self, offset=0, message="ZIP file does not appear to be a JAR")


MagicMatcher.DEFAULT_INSTANCE.add(RelaxedJarMatcher())


class LocalFileHeader(PolyFileStruct):
    endianness = Endianness.LITTLE

    magic: Constant[b"\x50\x4b\x03\x04"]
    version_needed_to_extract: UInt16
    general_purpose_bit_flag: UInt16
    compression_method: UInt16
    file_last_modification_time: UInt16
    file_last_modification_date: UInt16
    crc32: UInt32
    compressed_size: UInt32
    uncompressed_size: UInt32
    file_name_length: UInt16
    extra_field_length: UInt16
    file_name: ByteField["file_name_length"]
    extra_field: ByteField["extra_field_length"]
    compressed_data: ByteField["compressed_size"]


class CentralDirectory(PolyFileStruct):
    endianness = Endianness.LITTLE

    magic: Constant[b"\x50\x4b\x01\x02"]
    version_made_by: UInt16
    version_needed_to_extract: UInt16
    general_bit_flag: UInt16
    compression_method: UInt16
    file_last_modification_time: UInt16
    file_last_modification_date: UInt16
    crc32: UInt32
    compressed_size: UInt32
    uncompressed_size: UInt32
    file_name_length: UInt16
    extra_field_length: UInt16
    file_comment_length: UInt16
    disk_number: UInt16
    internal_file_attrs: UInt16
    external_file_attrs: UInt32
    file_header_offset: UInt32
    file_name: ByteField["file_name_length"]
    extra_field: ByteField["extra_field_length"]
    file_comment: ByteField["file_comment_length"]

    def local_file_header(self, stream: FileStream) -> LocalFileHeader:
        with stream.save_pos():
            stream.seek(self.file_header_offset)
            return LocalFileHeader.read(stream)


class EndOfCentralDirectory(PolyFileStruct):
    endianness = Endianness.LITTLE

    magic: Constant[b"\x50\x4b\x05\x06"]
    disk_number: UInt16
    start_disk: UInt16
    num_records: UInt16
    total_records: UInt16
    central_directory_bytes: UInt32
    central_directory_offset: UInt32
    comment_length: UInt16
    comment: ByteField["comment_length"]

    def central_directories(self, file_stream: FileStream) -> Iterator[CentralDirectory]:
        with file_stream.save_pos() as f:
            cdo = self.central_directory_offset
            while cdo < self.start_offset:
                f.seek(cdo)
                cd = CentralDirectory.read(f)
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
        del data
        try:
            with file_stream.save_pos() as f:
                f.seek(eocd)
                return EndOfCentralDirectory.read(f)
        except ValueError as e:
            log.error(str(e))
            return None


@register_parser("application/zip")
@register_parser("application/java-archive")
def parse_zip(file_stream, parent):
    eocd = EndOfCentralDirectory.load(file_stream)
    if eocd is None:
        raise InvalidMatch()
    cds = list(eocd.central_directories(file_stream))
    fhs = list(cd.local_file_header(file_stream) for cd in cds)
    zf: Optional[PythonZip] = None
    for fh in fhs:
        if zf is None:
            with file_stream.save_pos():
                file_stream.seek(fh.start_offset)
                zip_data = file_stream.read(eocd.start_offset + eocd.num_bytes - fh.start_offset)
                with Tempfile(zip_data) as tmp:
                    zf = PythonZip(tmp)
        for match in fh.match(matcher=parent.matcher, parent=parent):
            is_data = False
            if match.name == "compressed_data" and match.parent.parent == parent:
                try:
                    match.decoded = zf.read(fh.file_name.decode("utf-8"))
                    is_data = True
                except Exception as e:
                    log.warning(f"Error decompressing file {fh.file_name!r} at byte offset {match.offset}")
            yield match
            if is_data:
                with Tempfile(match.decoded) as tmp:
                    yield from parent.matcher.match(tmp, parent=match)
    for cd in cds:
        yield from cd.match(matcher=parent.matcher, parent=parent)
    yield from eocd.match(matcher=parent.matcher, parent=parent)
