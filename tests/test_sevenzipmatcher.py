"""7z structure, integrity, isolated decoding, and recursive budget regressions."""

import json
import lzma
import os
import struct
import subprocess
import sys
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from polyfile import sevenzipmatcher
from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher
from polyfile.sevenzipmatcher import parse_sevenzip

FIXTURES = Path(__file__).parent / "fixtures" / "sevenzip"
MIME = "application/x-7z-compressed"
FIRST = b'{"first":true}\n'
OTHER = b'{"other":true}\n'


def analyzed(data: bytes, limits: AnalysisLimits | None = None) -> Match:
    """Analyze the 7z interpretation directly, including malformed signatures."""
    parent = Match(MIME, None, length=len(data), matcher=Matcher(limits=limits))
    with FileStream(data) as stream:
        list(parse_sevenzip(stream, parent))
    return parent


def nodes(parent: Match) -> Iterator[Match]:
    yield parent
    for child in parent.children:
        yield from nodes(child)


def decoded(parent: Match) -> list[Match]:
    return [node for node in nodes(parent) if node.name == "decoded_content"]


def rewritten(data: bytes, header: bytes) -> bytes:
    """Replace a plain or encoded next header and repair its enclosing checksums."""
    offset = 32 + struct.unpack_from("<Q", data, 12)[0]
    signature = bytearray(data[:32])
    struct.pack_into("<QI", signature, 20, len(header), zlib.crc32(header))
    struct.pack_into("<I", signature, 8, zlib.crc32(signature[12:]))
    return bytes(signature) + data[32:offset] + header


def next_header(data: bytes) -> bytes:
    offset = 32 + struct.unpack_from("<Q", data, 12)[0]
    return data[offset:]


@pytest.mark.parametrize("name", ["copy", "nonsolid", "solid"])
def test_reference_archives_decode_with_independent_member_sources(name: str) -> None:
    result = analyzed((FIXTURES / f"{name}.7z").read_bytes())
    assert result.analysis_status is None
    contents = decoded(result)
    assert FIRST in [node.decoded for node in contents]
    assert len({node.source for node in contents}) == len(contents)
    assert all(node.source != "file" and node.offset == 0 for node in contents)
    assert any(node.name == "application/json" for node in nodes(result))
    if name != "copy":
        assert OTHER in [node.decoded for node in contents]


def test_solid_compressed_headers_preserve_physical_packed_regions() -> None:
    data = (FIXTURES / "solid.7z").read_bytes()
    result = analyzed(data)
    regions = [node for node in nodes(result) if node.name in ("packed_stream", "packed_header")]
    assert {node.name for node in regions} == {"packed_stream", "packed_header"}
    header = next(node for node in nodes(result) if node.name == "next_header")
    assert header.offset == 32 + struct.unpack_from("<Q", data, 12)[0]
    assert all(node.source == "file" and 32 <= node.offset < header.offset for node in regions)
    assert all(node.offset + node.length <= header.offset for node in regions)
    assert any(node.name == "application/zip" and node.source != "file" for node in nodes(result))
    assert b'{"nested":true}\n' in [node.decoded for node in decoded(result)]


def test_empty_files_and_directories_consume_entries_without_filesystem_extraction() -> None:
    result = analyzed((FIXTURES / "empty.7z").read_bytes())
    assert result.analysis_status is None
    members = [node for node in nodes(result) if node.name == "member"]
    assert [node.display_name for node in members] == ["directory", "empty"]
    assert result.analysis_context.members == 2
    assert [node.decoded for node in decoded(result)] == [b""]


@pytest.mark.parametrize("name", ["encrypted", "header-encrypted"])
def test_encrypted_archives_are_explicitly_unsupported(name: str) -> None:
    result = analyzed((FIXTURES / f"{name}.7z").read_bytes())
    assert result.analysis_status == "unsupported"
    assert "password" in (result.analysis_message or "").lower()
    assert not decoded(result)
    assert any(node.name == "next_header" for node in nodes(result))


@pytest.mark.parametrize("length", [0, 6, 31, 32, 50, 100])
def test_truncated_archives_never_publish_decoded_content(length: int) -> None:
    result = analyzed((FIXTURES / "copy.7z").read_bytes()[:length])
    assert result.analysis_status == "invalid"
    assert not decoded(result)


@pytest.mark.parametrize("offset", [0, 8, 12, 28, 40, -1])
def test_corruption_is_reported_without_partial_decoded_children(offset: int) -> None:
    data = bytearray((FIXTURES / "copy.7z").read_bytes())
    data[offset] ^= 1
    result = analyzed(bytes(data))
    assert result.analysis_status == "invalid"
    assert not decoded(result)


def test_valid_checksums_do_not_hide_out_of_bounds_next_headers() -> None:
    data = bytearray((FIXTURES / "copy.7z").read_bytes())
    struct.pack_into("<Q", data, 12, (1 << 64) - 1)
    struct.pack_into("<I", data, 8, zlib.crc32(data[12:32]))
    result = analyzed(bytes(data))
    assert result.analysis_status == "invalid"
    assert "outside" in (result.analysis_message or "")


@pytest.mark.parametrize("limits", [AnalysisLimits(max_depth=0), AnalysisLimits(max_members=0)])
def test_admission_precedes_decoder_startup(
    limits: AnalysisLimits,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*args: object, **kwargs: object) -> bytes:
        pytest.fail("7z helper started before admission")

    monkeypatch.setattr(sevenzipmatcher, "run_helper", unexpected)
    result = analyzed((FIXTURES / "solid.7z").read_bytes(), limits)
    assert result.analysis_status == "limited"
    assert not decoded(result)
    assert any(node.name == "next_header" for node in nodes(result))


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_members", 1),
        ("max_member_bytes", 14),
        ("max_total_bytes", 29),
    ],
)
def test_declared_members_are_admitted_before_payload_decoding(field: str, value: int) -> None:
    result = analyzed((FIXTURES / "nonsolid.7z").read_bytes(), AnalysisLimits(**{field: value}))
    assert result.analysis_status == "limited"
    assert not decoded(result)


def test_exact_member_count_and_byte_boundaries_are_admitted() -> None:
    limits = AnalysisLimits(max_members=2, max_member_bytes=15, max_total_bytes=30)
    result = analyzed((FIXTURES / "nonsolid.7z").read_bytes(), limits)
    assert result.analysis_status is None
    assert [node.decoded for node in decoded(result)] == [FIRST, OTHER]
    assert result.analysis_context.members == 2
    assert result.analysis_context.total_bytes == 30


def test_nested_analysis_can_exhaust_budget_before_later_archive_members() -> None:
    result = analyzed((FIXTURES / "solid.7z").read_bytes(), AnalysisLimits(max_total_bytes=170))
    later = next(node for node in nodes(result) if node.display_name == "other.json")
    assert later.analysis_status == "limited"
    assert not decoded(later)
    assert result.analysis_context.total_bytes <= 170
    assert FIRST in [node.decoded for node in decoded(result)]


def test_helper_timeout_is_a_limited_result() -> None:
    result = analyzed((FIXTURES / "copy.7z").read_bytes(), AnalysisLimits(helper_timeout=0.0001))
    assert result.analysis_status == "limited"
    assert "timeout" in (result.analysis_message or "")
    assert not decoded(result)


def test_hard_codec_memory_control_follows_platform_policy() -> None:
    result = analyzed((FIXTURES / "copy.7z").read_bytes(), AnalysisLimits(max_codec_memory=1))
    assert result.analysis_status == ("limited" if sys.platform == "linux" else "unsupported")
    assert not decoded(result)


def test_duplicate_names_remain_distinct_members() -> None:
    data = (FIXTURES / "nonsolid.7z").read_bytes()
    header = next_header(data).replace(
        "other.json".encode("utf-16le"), "first.json".encode("utf-16le")
    )
    result = analyzed(rewritten(data, header))
    assert result.analysis_status is None
    members = [node for node in nodes(result) if node.name == "member"]
    assert [node.display_name for node in members] == ["first.json", "first.json"]
    assert [node.decoded for node in decoded(result)] == [FIRST, OTHER]


@pytest.mark.parametrize("name", ["../escape/", "/tmp/a.txt"])
def test_archive_paths_are_metadata_only(name: str, tmp_path: Path) -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    header = next_header(data).replace("first.json".encode("utf-16le"), name.encode("utf-16le"))
    result = analyzed(rewritten(data, header))
    assert result.analysis_status is None
    assert [node.decoded for node in decoded(result)] == [FIRST]
    assert next(node for node in nodes(result) if node.name == "member").display_name == name
    assert list(tmp_path.iterdir()) == []


def test_unknown_codec_is_unsupported() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    header = next_header(data).replace(
        b"\x07\x0b\x01\x00\x01\x01\x00", b"\x07\x0b\x01\x00\x01\x01\xff"
    )
    result = analyzed(rewritten(data, header))
    assert result.analysis_status == "unsupported"
    assert not decoded(result)


def test_error_content_cannot_spoof_the_helper_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def failure(*args: object, **kwargs: object) -> bytes:
        raise DecodeError("external decoder failed: invalid: filename 'unsupported:limited:'")

    monkeypatch.setattr(sevenzipmatcher, "run_helper", failure)
    result = analyzed((FIXTURES / "copy.7z").read_bytes())
    assert result.analysis_status == "invalid"


def test_optional_packed_stream_crc_is_validated() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    pattern = b"\x06\x00\x01\x09\x0f\x00"
    checksum = struct.pack("<I", zlib.crc32(FIRST))
    header = next_header(data).replace(pattern, pattern[:-1] + b"\x0a\x01" + checksum + b"\x00")
    assert analyzed(rewritten(data, header)).analysis_status is None
    header = header.replace(checksum, bytes(4), 1)
    result = analyzed(rewritten(data, header))
    assert result.analysis_status == "invalid"
    assert "packed-stream checksum" in (result.analysis_message or "")
    assert not decoded(result)


def encoded_header(data: bytes, header: bytes) -> bytes:
    """Build a reference-compatible LZMA2 header with a packed-stream CRC."""
    compressed = lzma.compress(
        header,
        format=lzma.FORMAT_RAW,
        filters=[
            {
                "id": lzma.FILTER_LZMA2,
                "dict_size": 4096,
            }
        ],
    )
    crc = struct.pack("<I", zlib.crc32(compressed))
    descriptor = (
        b"\x17\x06"
        + bytes([len(FIRST)])
        + b"\x01\x09"
        + bytes([len(compressed)])
        + b"\x0a\x01"
        + crc
        + b"\x00\x07\x0b\x01\x00\x01\x21\x21\x01\x00\x0c"
        + bytes([len(header)])
        + b"\x00\x00"
    )
    signature = bytearray(data[:32])
    struct.pack_into("<Q", signature, 12, len(FIRST) + len(compressed))
    combined = bytes(signature) + FIRST + compressed + descriptor
    return rewritten(combined, descriptor)


def test_encoded_header_packed_crc_is_validated_and_mapped() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    good = encoded_header(data, next_header(data))
    assert analyzed(good).analysis_status is None
    descriptor = next_header(good)
    crc_position = descriptor.index(b"\x0a\x01") + 2
    crc_end = crc_position + 4
    bad = descriptor[:crc_position] + bytes(4) + descriptor[crc_end:]
    result = analyzed(rewritten(good, bad))
    assert result.analysis_status == "invalid"
    assert not decoded(result)


def test_nonzero_pack_position_uses_the_declared_stream_start() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    header = next_header(data).replace(b"\x06\x00\x01\x09", b"\x06\x01\x01\x09", 1)
    shifted = bytearray(data[:32] + b"P" + data[32:])
    struct.pack_into("<Q", shifted, 12, struct.unpack_from("<Q", data, 12)[0] + 1)
    result = analyzed(rewritten(bytes(shifted), header))
    assert result.analysis_status is None
    assert [node.decoded for node in decoded(result)] == [FIRST]
    packed = next(node for node in nodes(result) if node.name == "packed_stream")
    assert packed.offset == 33


@pytest.mark.parametrize("compressed", [False, True])
def test_standard_unhandled_archive_properties_report_unsupported(compressed: bool) -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    header = next_header(data)
    header = header[:1] + b"\x02\x00" + header[1:]
    result = analyzed(encoded_header(data, header) if compressed else rewritten(data, header))
    assert result.analysis_status == "unsupported"
    assert "archive properties" in (result.analysis_message or "")
    assert not decoded(result)


def test_zero_member_archive_with_no_next_header_succeeds() -> None:
    header = bytearray(b"7z\xbc\xaf\x27\x1c\x00\x04" + bytes(24))
    struct.pack_into("<I", header, 8, zlib.crc32(header[12:]))
    result = analyzed(bytes(header))
    assert result.analysis_status is None
    assert result.analysis_context.members == 0
    assert not decoded(result)


def test_corrupt_compressed_header_stream_is_invalid() -> None:
    data = bytearray((FIXTURES / "solid.7z").read_bytes())
    valid = analyzed(bytes(data))
    packed = next(node for node in nodes(valid) if node.name == "packed_header")
    data[packed.offset] ^= 0x80
    result = analyzed(bytes(data))
    assert result.analysis_status == "invalid"
    assert not decoded(result)


def test_nonempty_directory_stream_is_rejected_before_extraction() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    header = bytearray(next_header(data))
    offset = header.index(b"\x15\x06\x01\x00") + 4
    attributes = struct.unpack_from("<I", header, offset)[0]
    struct.pack_into("<I", header, offset, attributes | 0x10)
    result = analyzed(rewritten(data, bytes(header)))
    assert result.analysis_status == "invalid"
    assert "directory" in (result.analysis_message or "")
    assert not decoded(result)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX descriptor resource controls")
def test_many_empty_members_use_a_fixed_number_of_file_descriptors() -> None:
    code = """
import resource
import sys
from polyfile.analysis import AnalysisLimits
from polyfile.polyfile import Matcher
resource.setrlimit(resource.RLIMIT_NOFILE, (48, 48))
matches = list(Matcher(limits=AnalysisLimits(max_total_bytes=0)).match(sys.argv[1]))
root = next(node for node in matches if node.name == 'application/x-7z-compressed')
assert root.analysis_status is None, root.analysis_message
print(root.analysis_context.members)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(FIXTURES / "many-empty.7z")],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert result.stdout.strip() == "100"


def test_helper_reports_missing_backend_without_a_traceback() -> None:
    helper = Path(sevenzipmatcher.__file__).with_name("_sevenzip_helper.py")
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(helper), "metadata", "none", "none", "none"],
        input=(FIXTURES / "copy.7z").read_bytes(),
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stderr.startswith(b"unsupported: install py7zr==1.1.4")
    assert b"Traceback" not in result.stderr


def test_unqualified_backend_version_reports_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sevenzipmatcher, "version", lambda name: "0.0.0")
    result = analyzed((FIXTURES / "copy.7z").read_bytes())
    assert result.analysis_status == "unsupported"
    assert "py7zr==1.1.4" in (result.analysis_message or "")
    assert not decoded(result)


def test_registered_parser_recurses_without_suppressing_other_root_formats() -> None:
    data = (FIXTURES / "copy.7z").read_bytes()
    matches = list(Matcher().match(data))
    assert any(node.name == MIME and node.parent is None for node in matches)
    assert any(node.name == "application/json" and node.source != "file" for node in matches)


def test_fixture_provenance_hashes_are_current() -> None:
    import hashlib

    provenance = json.loads((FIXTURES / "provenance.json").read_text())
    for record in provenance["files"]:
        assert (
            hashlib.sha256((FIXTURES / record["file"]).read_bytes()).hexdigest() == record["sha256"]
        )
