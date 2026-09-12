from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Iterator, List, Optional, Set, Tuple
from unittest import TestCase
import struct
import zipfile

from polyfile.fileutils import FileStream
from polyfile.magic import MagicMatcher, MatchContext
from polyfile.polyfile import Match, Matcher
from polyfile.structs import Constant
from polyfile.zipmatcher import EOCD_SIGNATURE, EndOfCentralDirectory, parse_zip

MEMBERS: Dict[str, bytes] = {
    "first.txt": b"the first member of the archive\n",
    "nested/second.txt": b"the second member of the archive\n",
}

MANIFEST: Dict[str, bytes] = {"META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n\n"}

# The size of an end of central directory record that carries no comment:
EOCD_SIZE = 22

# A minimal but valid PNG, so the prepended data is a real file type rather than filler:
PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def build_zip(
        prefix: bytes = b"",
        members: Optional[Dict[str, bytes]] = None,
        comment: bytes = b"",
        compression: int = zipfile.ZIP_DEFLATED,
) -> bytes:
    """Builds a ZIP archive, optionally appended to unrelated leading data.

    Args:
        prefix: Bytes to place before the archive, as in a polyglot file.
        members: The archive members to write, defaulting to :data:`MEMBERS`.
        comment: The archive comment, which the end of central directory record carries.
        compression: The compression method to store the members with.

    Returns:
        The contents of the resulting file.
    """
    if members is None:
        members = MEMBERS
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
        archive.comment = comment
    return prefix + buffer.getvalue()


@contextmanager
def temporary_file(data: bytes) -> Iterator[Path]:
    """Writes bytes to a temporary file that is removed when the context exits."""
    with NamedTemporaryFile("wb", suffix=".bin", delete=False) as f:
        f.write(data)
        path = Path(f.name)
    try:
        yield path
    finally:
        path.unlink()


class TestZipMatcher(TestCase):
    def member_names(self, data: bytes) -> List[bytes]:
        with temporary_file(data) as path, FileStream(str(path)) as stream:
            eocd = EndOfCentralDirectory.load(stream)
            self.assertIsNotNone(eocd)
            return [
                cd.local_file_header(stream).file_name for cd in eocd.central_directories(stream)
            ]

    def parsed_matches(self, data: bytes, parse: bool = False) -> List[Match]:
        parent = Match("application/zip", None, 0, length=len(data), matcher=Matcher(parse=parse))
        with temporary_file(data) as path, FileStream(str(path)) as stream:
            return list(parse_zip(stream, parent))

    def parsed_names(self, data: bytes) -> List[str]:
        return [match.name for match in self.parsed_matches(data)]

    def archive_offsets(self, data: bytes) -> List[int]:
        """Returns the byte offset at which each archive in the file starts, first one first."""
        with temporary_file(data) as path, FileStream(str(path)) as stream:
            return [eocd.archive_offset for eocd in EndOfCentralDirectory.load_all(stream)][::-1]

    def records(self, data: bytes) -> List[Tuple[str, int]]:
        """Returns the name and byte offset of every ZIP record that `parse_zip` maps."""
        parent = Match("application/zip", None, 0, length=len(data), matcher=Matcher(parse=False))
        with temporary_file(data) as path, FileStream(str(path)) as stream:
            return [
                (match.name, match.offset)
                for match in parse_zip(stream, parent)
                if match.parent is parent
            ]

    def record_offsets(self, data: bytes, name: str) -> List[int]:
        """Returns the byte offset of every mapped ZIP record of one kind."""
        return [offset for record_name, offset in self.records(data) if record_name == name]

    def matched_mime_types(self, data: bytes) -> Set[str]:
        with temporary_file(data) as path, FileStream(str(path)) as stream:
            context = MatchContext.load(stream, only_match_mime=True)
            return {
                result.test.mime.resolve(context)
                for match in MagicMatcher.DEFAULT_INSTANCE.match(context)
                for result in match
                if result.test.mime is not None
            }

    def assert_structure_parsed(self, data: bytes):
        names = self.parsed_names(data)
        self.assertEqual(len(MEMBERS), names.count("LocalFileHeader"))
        self.assertEqual(len(MEMBERS), names.count("CentralDirectory"))
        self.assertEqual(1, names.count("EndOfCentralDirectory"))

    def test_archive_offset(self):
        with temporary_file(build_zip()) as path, FileStream(str(path)) as stream:
            self.assertEqual(0, EndOfCentralDirectory.load(stream).archive_offset)
        with temporary_file(build_zip(PNG)) as path, FileStream(str(path)) as stream:
            self.assertEqual(len(PNG), EndOfCentralDirectory.load(stream).archive_offset)

    def test_members_at_offset_zero(self):
        expected = [name.encode("utf-8") for name in MEMBERS]
        self.assertEqual(expected, self.member_names(build_zip()))

    def test_members_with_prepended_data(self):
        """Regression test for #3364.

        Before the fix, offsets recorded in the central directory were used as absolute file
        offsets, so every read landed inside the prepended PNG and raised a StructError.
        """
        expected = [name.encode("utf-8") for name in MEMBERS]
        self.assertEqual(expected, self.member_names(build_zip(PNG)))

    def test_parse_zip_at_offset_zero(self):
        self.assert_structure_parsed(build_zip())

    def test_parse_zip_with_prepended_data(self):
        self.assert_structure_parsed(build_zip(PNG))

    def test_no_matches_inside_constant_fields(self):
        """Regression test for #3470.

        Every bytes field used to be written to a temporary file and re-matched to find
        embedded files, including the fixed signatures declared as Constant fields. The four
        bytes of `EndOfCentralDirectory.magic` matched as an empty archive, so each ZIP
        reported a nested `application/zip` on its own magic, and the magic of the other two
        records reported a nested `application/octet-stream`.
        """
        constants = [match for match in self.parsed_matches(build_zip()) if isinstance(match.match, Constant)]
        self.assertEqual(2 * len(MEMBERS) + 1, len(constants))
        for match in constants:
            self.assertEqual((), match.children, f"{match.name} at offset {match.offset} was re-matched")

    def test_no_parser_warning_for_constant_fields(self):
        """The nested match on the magic ran parse_zip on four bytes, which logged a warning."""
        with self.assertNoLogs("polyfile", "WARNING"):
            self.parsed_matches(build_zip(), parse=True)

    def test_concatenated_archives(self):
        """Regression test for #3466.

        `EndOfCentralDirectory.load` searched with `rfind`, so only the last archive of a
        file holding concatenated archives was walked. Every byte of the archives before it
        went unmapped, even though the match claimed to span the whole file.
        """
        first, second = build_zip(), build_zip(members=MANIFEST)
        self.assertEqual([0, len(first)], self.archive_offsets(first + second))
        self.assertEqual(
            [len(first) - EOCD_SIZE, len(first) + len(second) - EOCD_SIZE],
            self.record_offsets(first + second, "EndOfCentralDirectory"),
        )
        headers = self.record_offsets(first + second, "LocalFileHeader")
        self.assertEqual(len(MEMBERS) + len(MANIFEST), len(headers))
        self.assertEqual(0, headers[0])

    def test_three_concatenated_archives(self):
        parts = [build_zip(), build_zip(members=MANIFEST), build_zip(members=MEMBERS)]
        data = b"".join(parts)
        self.assertEqual(
            [0, len(parts[0]), len(parts[0]) + len(parts[1])], self.archive_offsets(data)
        )
        self.assertEqual(3, len(self.record_offsets(data, "EndOfCentralDirectory")))

    def test_single_archive_is_one_archive(self):
        self.assertEqual([0], self.archive_offsets(build_zip()))
        self.assertEqual([len(PNG)], self.archive_offsets(build_zip(PNG)))

    def test_nested_archive_is_not_a_sibling(self):
        """An archive stored inside another is a member of it, not a second archive.

        The signature of the stored archive's end of central directory record is in the
        bytes of the containing archive, so a search that took every occurrence at face
        value would report the two as siblings that overlap.
        """
        inner = build_zip(members=MANIFEST)
        outer = build_zip(members={"inner.zip": inner}, compression=zipfile.ZIP_STORED)
        self.assertEqual([0], self.archive_offsets(outer))
        self.assertEqual(1, len(self.record_offsets(outer, "EndOfCentralDirectory")))
        self.assertEqual([0], self.record_offsets(outer, "LocalFileHeader"))

    def test_signature_in_archive_comment(self):
        """A comment holding the signature bytes does not end an archive.

        Before the fix the search stopped at the occurrence in the comment and read a record
        out of the comment text, which failed and left the archive unmapped.
        """
        data = build_zip(comment=b"a comment holding \x50\x4b\x05\x06 in the middle of it")
        self.assertEqual([0], self.archive_offsets(data))
        self.assertEqual(len(MEMBERS), len(self.record_offsets(data, "LocalFileHeader")))

    def test_comment_that_reads_as_a_record(self):
        """A comment can hold bytes that read as a whole record, and still not be one.

        22 zero bytes are a valid record for an empty archive, so a comment holding them is
        only told apart from a second archive by where the record they read as would have to
        end.
        """
        data = build_zip(comment=EOCD_SIGNATURE + bytes(18) + b" and the rest of the comment")
        self.assertEqual([0], self.archive_offsets(data))
        self.assertEqual(len(MEMBERS), len(self.record_offsets(data, "LocalFileHeader")))

    def test_comment_that_ends_in_a_record(self):
        """A comment whose last bytes read as a record is told apart by its central directory.

        The forged record ends where a real one would, so the only thing left that separates
        it from a second archive is that nothing points back at a central directory.
        """
        forged = EOCD_SIGNATURE + struct.pack("<HHHHIIH", 0, 0, 1, 1, 46, 0, 0)
        data = build_zip(comment=b"a comment that ends in " + forged)
        self.assertEqual([0], self.archive_offsets(data))
        self.assertEqual(len(MEMBERS), len(self.record_offsets(data, "LocalFileHeader")))

    def test_trailing_signature_is_not_an_archive(self):
        """Bytes after an archive that start with the signature do not hide the archive.

        Before the fix the search took the trailing occurrence, read a record that was not
        there, and mapped nothing at all.
        """
        data = build_zip() + EOCD_SIGNATURE + b"\xde\xad\xbe\xef" * 4
        self.assertEqual([0], self.archive_offsets(data))
        self.assertEqual(len(MEMBERS), len(self.record_offsets(data, "LocalFileHeader")))

    def test_archive_that_zipfile_refuses_is_still_mapped(self):
        """The structure of an archive is reported even when its members cannot be read.

        Python's zipfile locates the end of central directory record with the same backwards
        search, so a comment holding the signature makes it refuse the file. Its refusal used
        to abort the parse and leave every record of the archive unmapped.
        """
        data = build_zip(comment=b"a comment holding \x50\x4b\x05\x06 in the middle of it")
        self.assertEqual(
            len(MEMBERS) * 2 + 1,
            len([name for name, _ in self.records(data)]),
        )

    def test_jar_with_prepended_data(self):
        """RelaxedJarMatcher reads local file headers, so it needs the archive offset too."""
        members = dict(MEMBERS)
        members.update(MANIFEST)
        mime_types = self.matched_mime_types(build_zip(PNG, members))
        self.assertIn("application/java-archive", mime_types)
        self.assertIn("image/png", mime_types)
