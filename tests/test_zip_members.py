"""Check physical and decoded ZIP members through the registered parser."""

from collections.abc import Sequence
from io import BytesIO, UnsupportedOperation
import struct
from unittest import TestCase, main
from zipfile import ZIP_DEFLATED, ZipFile
import zlib

from polyfile.polyfile import Matcher
from polyfile.fileutils import FileStream
from polyfile.structs import StructReadError
from polyfile.zipmatcher import EndOfCentralDirectory


class StreamingOutput(BytesIO):
    def seek(self, *args: object) -> int:
        raise UnsupportedOperation("stream has no seek operation")


class TestZipMembers(TestCase):
    def assert_members(self, data: bytes, expected: Sequence[tuple[int, bytes, bytes]]) -> None:
        actual = []
        for member in Matcher().match(data):
            if member.name == "decoded_content" and member.parent is not None:
                physical = member.parent
                if physical.name == "compressed_data" and physical.source == "file":
                    payload = data[physical.offset:physical.offset + physical.length]
                    actual.append((physical.offset, payload, member.decoded))
        self.assertEqual(expected, actual)

    def check_archive(self, data: bytes) -> None:
        expected = []
        with ZipFile(BytesIO(data)) as archive:
            for info in archive.infolist():
                name_length, extra_length = struct.unpack_from("<HH", data, info.header_offset + 26)
                offset = info.header_offset + 30 + name_length + extra_length
                compressed = data[offset:offset + info.compress_size]
                decoded = archive.read(info)
                self.assertEqual(decoded, zlib.decompress(compressed, -15))
                expected.append((offset, compressed, decoded))
        self.assert_members(data, expected)

    def test_duplicate_filenames(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("same", b"first")
            with self.assertWarnsRegex(UserWarning, "Duplicate name"):
                archive.writestr("same", b"second")
        self.check_archive(buffer.getvalue())

    def test_data_descriptors(self) -> None:
        buffer = StreamingOutput()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("a", b"first")
            archive.writestr("b", b"second")
        self.check_archive(buffer.getvalue())

    def test_zip64_local_sizes(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            with archive.open("member", "w", force_zip64=True) as member:
                member.write(b"forced ZIP64")
        self.check_archive(buffer.getvalue())

    def test_truncated_zip64_size(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            with archive.open("a", "w", force_zip64=True) as member:
                member.write(b"data")
        data = bytearray(buffer.getvalue())
        struct.pack_into("<H", data, 33, 8)
        with FileStream(bytes(data)) as stream:
            end = EndOfCentralDirectory.load(stream)
            assert end is not None
            record = next(end.central_directories(stream))
            with self.assertRaisesRegex(StructReadError, "ZIP64.*compressed size"):
                record.local_file_header(stream)

    def test_concatenated_members(self) -> None:
        data = b"prefix"
        expected = []
        for name, payload in (("one", b"first"), ("two", b"second")):
            buffer = BytesIO()
            with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
                archive.writestr(name, payload)
            part = buffer.getvalue()
            offset = 30 + len(name)
            expected.append((len(data) + offset, part[offset:part.index(b"PK\x01\x02")], payload))
            data += part
        self.assert_members(data, expected)

    def test_reordered_directory(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("a", b"first")
            archive.writestr("b", b"second")
        data = buffer.getvalue()
        start = data.index(b"PK\x01\x02")
        second = data.index(b"PK\x01\x02", start + 4)
        end = data.index(b"PK\x05\x06", second + 4)
        reordered = data[:start] + data[second:end] + data[start:second] + data[end:]
        for prefix in (b"", b"prefix"):
            with self.subTest(prefix=prefix):
                self.check_archive(prefix + reordered)


if __name__ == "__main__":
    main()
