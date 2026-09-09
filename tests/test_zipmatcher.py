from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List
from unittest import TestCase
import zipfile

from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher
from polyfile.zipmatcher import EndOfCentralDirectory, parse_zip

MEMBERS: Dict[str, bytes] = {
    "first.txt": b"the first member of the archive\n",
    "nested/second.txt": b"the second member of the archive\n",
}

# A minimal but valid PNG, so the prepended data is a real file type rather than filler:
PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def build_zip(prefix: bytes = b"") -> bytes:
    """Builds a ZIP archive, optionally appended to unrelated leading data.

    Args:
        prefix: Bytes to place before the archive, as in a polyglot file.

    Returns:
        The contents of the resulting file.
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in MEMBERS.items():
            archive.writestr(name, content)
    return prefix + buffer.getvalue()


class TestZipMatcher(TestCase):
    def member_names(self, data: bytes) -> List[bytes]:
        with FileStream(data) as stream:
            eocd = EndOfCentralDirectory.load(stream)
            self.assertIsNotNone(eocd)
            return [
                cd.local_file_header(stream).file_name for cd in eocd.central_directories(stream)
            ]

    def test_archive_offset(self):
        with FileStream(build_zip()) as stream:
            self.assertEqual(0, EndOfCentralDirectory.load(stream).archive_offset)
        with FileStream(build_zip(PNG)) as stream:
            self.assertEqual(len(PNG), EndOfCentralDirectory.load(stream).archive_offset)

    def test_members_at_offset_zero(self):
        expected = [name.encode("utf-8") for name in MEMBERS]
        self.assertEqual(expected, self.member_names(build_zip()))

    def test_members_with_prepended_data(self):
        """Regression test for #3364.

        Before the fix, the offsets recorded in the central directory were used as absolute
        file offsets, so every read landed inside the prepended PNG and raised a StructError.
        """
        expected = [name.encode("utf-8") for name in MEMBERS]
        self.assertEqual(expected, self.member_names(build_zip(PNG)))

    def parsed_names(self, data: bytes) -> List[str]:
        parent = Match("application/zip", None, 0, length=len(data), matcher=Matcher(parse=False))
        with NamedTemporaryFile("wb", suffix=".bin", delete=False) as f:
            f.write(data)
            path = Path(f.name)
        try:
            with FileStream(str(path)) as stream:
                return [match.name for match in parse_zip(stream, parent)]
        finally:
            path.unlink()

    def test_parse_zip_with_prepended_data(self):
        names = self.parsed_names(build_zip(PNG))
        self.assertEqual(len(MEMBERS), names.count("LocalFileHeader"))
        self.assertEqual(len(MEMBERS), names.count("CentralDirectory"))
        self.assertEqual(1, names.count("EndOfCentralDirectory"))

    def test_parse_zip_at_offset_zero(self):
        names = self.parsed_names(build_zip())
        self.assertEqual(len(MEMBERS), names.count("LocalFileHeader"))
        self.assertEqual(len(MEMBERS), names.count("CentralDirectory"))
        self.assertEqual(1, names.count("EndOfCentralDirectory"))
