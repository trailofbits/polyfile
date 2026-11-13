import zlib
from io import BytesIO
from itertools import chain
from lzma import LZMAError
from pathlib import Path
from typing import Optional
from collections.abc import Iterator
from zipfile import BadZipFile
from zipfile import ZipFile as PythonZip

from polyfile.compression import CHUNK_SIZE, DecodeError, OutputBuffer, match_decoded

from .fileutils import ExactNamedTempfile, FileStream, Tempfile
from .logger import StatusLogger
from .magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)
from .polyfile import InvalidMatch, Match, register_parser
from .structmatcher import PolyFileStruct
from .structs import ByteField, Constant, Endianness, StructError, UInt16, UInt32

log = StatusLogger("polyfile")

LOCAL_FILE_HEADER_SIGNATURE = b"\x50\x4b\x03\x04"
CENTRAL_DIRECTORY_SIGNATURE = b"\x50\x4b\x01\x02"
EOCD_SIGNATURE = b"\x50\x4b\x05\x06"

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

    def test(self, data: bytes, absolute_offset: int, parent_match: TestResult | None) -> TestResult:
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

    magic: Constant[LOCAL_FILE_HEADER_SIGNATURE]  # ty: ignore[invalid-type-form]  # Runtime DSL.
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
    file_name: ByteField["file_name_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    extra_field: ByteField["extra_field_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    compressed_data: ByteField["compressed_size"]  # ty: ignore[invalid-type-form]  # Runtime DSL.


class CentralDirectory(PolyFileStruct):
    endianness = Endianness.LITTLE

    magic: Constant[CENTRAL_DIRECTORY_SIGNATURE]  # ty: ignore[invalid-type-form]  # Runtime DSL.
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
    file_name: ByteField["file_name_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    extra_field: ByteField["extra_field_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    file_comment: ByteField["file_comment_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.

    archive_offset: int = 0
    """Byte offset at which the containing archive starts within the file."""

    def local_file_header(self, stream: FileStream) -> LocalFileHeader:
        """Reads the local file header that this central directory record points to.

        The record stores the header offset relative to the start of the archive, so
        :attr:`archive_offset` is added to locate the header inside ``stream``.

        Args:
            stream: The stream containing the whole file, not only the archive.

        Returns:
            The local file header for this record.
        """
        with stream.save_pos():
            stream.seek(self.archive_offset + self.file_header_offset)
            return LocalFileHeader.read(stream)


class EndOfCentralDirectory(PolyFileStruct):
    endianness = Endianness.LITTLE

    magic: Constant[EOCD_SIGNATURE]  # ty: ignore[invalid-type-form]  # Runtime DSL.
    disk_number: UInt16
    start_disk: UInt16
    num_records: UInt16
    total_records: UInt16
    central_directory_bytes: UInt32
    central_directory_offset: UInt32
    comment_length: UInt16
    comment: ByteField["comment_length"]  # ty: ignore[invalid-type-form]  # Runtime DSL.

    @property
    def archive_offset(self) -> int:
        """Byte offset at which the archive starts within the file.

        ZIP records store offsets relative to the start of the archive, but an archive can
        be appended to other data, as in a polyglot or a self-extracting executable. The
        end of central directory record sits immediately after the central directory, so
        subtracting the central directory size and its recorded offset from the position of
        the record itself yields the length of whatever precedes the archive.

        Returns:
            The number of bytes that precede the archive, or 0 if the record is malformed.
        """
        offset = self.start_offset - self.central_directory_bytes - self.central_directory_offset
        return max(offset, 0)

    def central_directories(self, file_stream: FileStream) -> Iterator[CentralDirectory]:
        """Iterates over the central directory records of this archive.

        Args:
            file_stream: The stream containing the whole file, not only the archive.

        Yields:
            Each central directory record, with :attr:`CentralDirectory.archive_offset` set
            so that its local file header can be located.
        """
        archive_offset = self.archive_offset
        with file_stream.save_pos() as f:
            cdo = archive_offset + self.central_directory_offset
            while cdo < self.start_offset:
                f.seek(cdo)
                cd = CentralDirectory.read(f)
                if cd is None:
                    break
                cd.archive_offset = archive_offset
                yield cd
                cdo += cd.num_bytes

    def terminates_archive(self, file_stream: FileStream, archive_end: int) -> bool:
        """Checks whether this record ends an archive that ends at `archive_end`.

        The four signature bytes also occur inside archive comments and inside the data of
        stored members, so a record found by searching for them is only believable if it is
        the last thing in its archive, which is where the record belongs, and if the central
        directory it points to is really where it says it is.

        Args:
            file_stream: The stream containing the whole file, not only the archive.
            archive_end: The byte offset at which the archive has to end.

        Returns:
            True if the record is consistent with the rest of the file.
        """
        archive_offset = (
            self.start_offset - self.central_directory_bytes - self.central_directory_offset
        )
        record_end = self.start_offset + self.num_bytes
        if record_end != archive_end or archive_offset < 0:
            return False
        elif self.total_records == 0:
            return self.central_directory_bytes == 0
        try:
            with file_stream.save_pos():
                file_stream.seek(archive_offset + self.central_directory_offset)
                return file_stream.read(len(CENTRAL_DIRECTORY_SIGNATURE)) == CENTRAL_DIRECTORY_SIGNATURE
        except IndexError:
            # FileStream.seek rejects a position past the end of the stream
            return False

    @staticmethod
    def read_at(file_stream: FileStream, offset: int) -> Optional["EndOfCentralDirectory"]:
        """Reads a record at a byte offset.

        Args:
            file_stream: The stream containing the whole file, not only the archive.
            offset: The byte offset of the record within the stream.

        Returns:
            The record, or None if the bytes at that offset are not a complete record.
        """
        try:
            with file_stream.save_pos() as f:
                f.seek(offset)
                return EndOfCentralDirectory.read(f)
        except (IndexError, StructError, ValueError):
            return None

    @staticmethod
    def read_before(
            file_stream: FileStream, data: bytes, base: int, search_end: int
    ) -> Optional["EndOfCentralDirectory"]:
        """Reads the last record that starts before a byte offset.

        Args:
            file_stream: The stream containing the whole file, not only the archive.
            data: The contents of the stream from byte offset `base` onward.
            base: The byte offset within the stream at which `data` starts.
            search_end: The index within `data` before which the record must start.

        Returns:
            The last record before `search_end`, or None if there is none.
        """
        while search_end > 0:
            candidate = data.rfind(EOCD_SIGNATURE, 0, search_end)
            if candidate < 0:
                return None
            eocd = EndOfCentralDirectory.read_at(file_stream, base + candidate)
            if eocd is not None:
                return eocd
            search_end = candidate + len(EOCD_SIGNATURE) - 1
        return None

    @staticmethod
    def load_all(file_stream: FileStream) -> Iterator["EndOfCentralDirectory"]:
        """Finds the end of central directory record of every archive in the file.

        ZIP archives can be concatenated, and each archive keeps its own end of central
        directory record, so the last record in a file describes only the last archive. The
        search runs backwards from the end of the file and resumes ahead of the start of
        each archive it reports, which is what keeps an archive stored inside another from
        being reported as a sibling of it.

        A record is only reported if it validates, because reporting an archive on the
        strength of four signature bytes would invent one. When nothing in the file
        validates, as in a ZIP64 archive or in one volume of a split archive, whose records
        hold offsets these fields cannot express, the last record that reads is reported on
        its own, which is the archive the search found before it looked for more than one.

        Args:
            file_stream: The stream containing the whole file.

        Yields:
            One record per archive, from the last archive in the file to the first.
        """
        offset_before = file_stream.tell()
        try:
            data = file_stream.read()
        finally:
            file_stream.seek(offset_before)
        archive_end = offset_before + len(data)
        search_end = len(data)
        found = False
        while search_end > 0:
            eocd = EndOfCentralDirectory.read_before(file_stream, data, offset_before, search_end)
            if eocd is None:
                break
            elif not eocd.terminates_archive(file_stream, archive_end):
                search_end = eocd.start_offset - offset_before + len(EOCD_SIGNATURE) - 1
                continue
            found = True
            yield eocd
            archive_end = eocd.archive_offset
            search_end = archive_end - offset_before
        if not found:
            yield from EndOfCentralDirectory.load_unvalidated(file_stream, data, offset_before)

    @staticmethod
    def load_unvalidated(
            file_stream: FileStream, data: bytes, base: int
    ) -> Iterator["EndOfCentralDirectory"]:
        """Reports the last record in a file in which no record validates.

        Args:
            file_stream: The stream containing the whole file.
            data: The contents of the stream from byte offset `base` onward.
            base: The byte offset within the stream at which `data` starts.

        Yields:
            The last record that reads, if the file holds one.
        """
        eocd = EndOfCentralDirectory.read_before(file_stream, data, base, len(data))
        if eocd is None:
            log.warning(f"Could not find central directory record for {file_stream.name}")
        else:
            yield eocd

    @staticmethod
    def load(file_stream: FileStream) -> Optional["EndOfCentralDirectory"]:
        """Reads the end of central directory record of the last archive in the file.

        Args:
            file_stream: The stream containing the whole file.

        Returns:
            The record of the last archive, or None if the file holds no archive.
        """
        for eocd in EndOfCentralDirectory.load_all(file_stream):
            return eocd
        return None


def open_archive(
        file_stream: FileStream, eocd: EndOfCentralDirectory, start: int
) -> PythonZip | None:
    """Opens an archive with Python's zipfile module, so that its members can be decompressed.

    Args:
        file_stream: The stream containing the whole file, not only the archive.
        eocd: The end of central directory record of the archive.
        start: The byte offset of the first local file header of the archive.

    Returns:
        The open archive, or None if zipfile refuses to read it.
    """
    with file_stream.save_pos():
        file_stream.seek(start)
        zip_data = file_stream.read(eocd.start_offset + eocd.num_bytes - start)
    with Tempfile(zip_data) as tmp:
        try:
            return PythonZip(tmp)
        except BadZipFile as e:
            log.warning(f"Could not read the members of the archive at byte offset {start}: {e!s}")
            return None



def _zip_decode_policy(fh: LocalFileHeader, parent: Match) -> tuple[str, str] | None:
    limits = parent.analysis_context.limits
    if limits.max_depth is not None and parent.analysis_depth >= limits.max_depth:
        return "limited", "ZIP member decoding exceeds the configured recursive depth"
    memory = limits.max_codec_memory
    if memory is not None and fh.compression_method == 8 and memory < 64 * 1024:
        return "limited", "ZIP DEFLATE requires a 64 KiB codec-memory allowance"
    output_limited = parent.analysis_context.member_limit is not None
    if fh.compression_method in (12, 14) and (output_limited or memory is not None):
        return (
            "unsupported",
            "The ZIP bzip2/LZMA backend cannot enforce configured decoder limits",
        )
    return None


def member_data(
        zf: PythonZip | None, fh: LocalFileHeader, match: Match, parent: Match
) -> bytes | None:
    """Decompresses the member of an archive whose compressed data a match covers.

    Args:
        zf: The archive as zipfile reads it, or None if zipfile refused to read it.
        fh: The local file header of the member.
        match: A match for one of the fields of `fh`.
        parent: The match that contains the archive.

    Returns:
        The decompressed contents of the member, or None if `match` covers another field or
        the member cannot be decompressed.
    """
    if zf is None or match.name != "compressed_data":
        return None
    assert match.parent is not None
    if match.parent.parent != parent:
        return None
    policy = _zip_decode_policy(fh, parent)
    if policy is not None:
        match.analysis_status, match.analysis_message = policy
        return None
    try:
        output = OutputBuffer(parent.analysis_context.member_limit)
        encoding = "utf-8" if fh.general_purpose_bit_flag & 0x800 else "cp437"
        with zf.open(fh.file_name.decode(encoding)) as member:
            while True:
                data = member.read(min(CHUNK_SIZE, output.next_size))
                if not data:
                    break
                output.append(data)
        return output.finish()
    except DecodeError as error:
        match.analysis_status = error.status
        match.analysis_message = str(error)
        return None
    except NotImplementedError as error:
        match.analysis_status = "unsupported"
        match.analysis_message = str(error)
        return None
    except (BadZipFile, EOFError, KeyError, LZMAError, OSError, RuntimeError,
            UnicodeError, zlib.error) as error:
        match.analysis_status = "invalid"
        match.analysis_message = f"Cannot decode ZIP member {fh.file_name!r}: {error}"
        return None




def _decoded_zip_parsers(header: LocalFileHeader, match: Match) -> set[str]:
    """Identify raw interpretations whose decoded contents were already analyzed."""
    if header.compression_method == 12:
        return {"application/x-bzip2"}
    if header.compression_method == 0:
        return {
            child.name
            for source in match.children if source.name == "decoded_content"
            for child in source.children
        }
    return set()


def _member_matches(
    header: LocalFileHeader, archive: PythonZip | None, parent: Match
) -> Iterator[Match]:
    """Map one member header and its admitted decoded payload."""
    assert parent.matcher is not None
    for match in header.match(matcher=parent.matcher, parent=parent):
        match.analysis_member_counted = True
        decoded = member_data(archive, header, match, parent)
        yield match
        if decoded is not None:
            yield from match_decoded(match, decoded, member_counted=True)
            match.analysis_skip_parsers.update(_decoded_zip_parsers(header, match))


def parse_archive(
        file_stream: FileStream, eocd: EndOfCentralDirectory, parent: Match
) -> Iterator[Match]:
    """Yields the matches for the one archive that ends at `eocd`.

    Args:
        file_stream: The stream containing the whole file, not only the archive.
        eocd: The end of central directory record of the archive to parse.
        parent: The match that contains the archive.

    Yields:
        A match for each record of the archive, and for the files its members contain.
    """
    assert parent.matcher is not None
    if parent.analysis_context.remaining_members == 0:
        parent.analysis_status = "limited"
        parent.analysis_message = "ZIP member count exceeds its analysis allowance"
        return
    cds = list(eocd.central_directories(file_stream))
    fhs = list(cd.local_file_header(file_stream) for cd in cds)
    zf = open_archive(file_stream, eocd, fhs[0].start_offset) if fhs else None
    try:
        for fh in fhs:
            reason = parent.analysis_context.claim_entry()
            if reason is not None:
                parent.analysis_status, parent.analysis_message = "limited", reason
                return
            yield from _member_matches(fh, zf, parent)
        for record in [*cds, eocd]:
            for match in record.match(matcher=parent.matcher, parent=parent):
                match.analysis_member_counted = True
                yield match
    finally:
        if zf is not None:
            zf.close()


@register_parser("application/zip")
@register_parser("application/java-archive")
def parse_zip(file_stream, parent):
    """Yields the matches for every archive in the file, the first archive first.

    This returns an iterator instead of being a generator itself, so that an archive nested
    inside another costs no more stack to parse than it did when a file held one archive.

    Args:
        file_stream: The stream containing the whole file.
        parent: The match for the file.

    Returns:
        An iterator over the matches for every archive in the file.

    Raises:
        InvalidMatch: If the file holds no archive.
    """
    archives = list(EndOfCentralDirectory.load_all(file_stream))
    if not archives:
        raise InvalidMatch()
    return chain.from_iterable(
        parse_archive(file_stream, eocd, parent) for eocd in reversed(archives)
    )
