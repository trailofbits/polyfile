from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Iterator, List, Optional, Set
from unittest import TestCase
import zipfile

from polyfile.fileutils import FileStream
from polyfile.magic import MagicMatcher, MatchContext
from polyfile.polyfile import Match, Matcher
from polyfile.structs import Constant
from polyfile.zipmatcher import EndOfCentralDirectory, parse_zip

MEMBERS: Dict[str, bytes] = {
    "first.txt": b"the first member of the archive\n",
    "nested/second.txt": b"the second member of the archive\n",
}

MANIFEST: Dict[str, bytes] = {"META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n\n"}

# A minimal but valid PNG, so the prepended data is a real file type rather than filler:
PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def build_zip(prefix: bytes = b"", members: Optional[Dict[str, bytes]] = None) -> bytes:
    """Builds a ZIP archive, optionally appended to unrelated leading data.

    Args:
        prefix: Bytes to place before the archive, as in a polyglot file.
        members: The archive members to write, defaulting to :data:`MEMBERS`.

    Returns:
        The contents of the resulting file.
    """
    if members is None:
        members = MEMBERS
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
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

    def test_jar_with_prepended_data(self):
        """RelaxedJarMatcher reads local file headers, so it needs the archive offset too."""
        members = dict(MEMBERS)
        members.update(MANIFEST)
        mime_types = self.matched_mime_types(build_zip(PNG, members))
        self.assertIn("application/java-archive", mime_types)
        self.assertIn("image/png", mime_types)
