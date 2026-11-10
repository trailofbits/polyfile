"""Gzip framing, integrity, nested-content, and resource-bound regressions."""

import gzip
import struct
import tarfile
import zlib
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.gzipmatcher import GZIP_MEMORY, decode_gzip
from polyfile.polyfile import Matcher
from tests.test_pdf import WELL_FORMED_PDF

PAYLOAD = b'{"gzip_member": true}\n'


def member(payload: bytes, *, optional: bool = False) -> bytes:
    header = b"\x1f\x8b\x08" + bytes([0x1E if optional else 0]) + bytes(6)
    if optional:
        header += b"\x04\x00AB\x00\x00document.json\x00a comment\x00"
        header += struct.pack("<H", zlib.crc32(header) & 0xFFFF)
    encoder = zlib.compressobj(wbits=-15)
    data = encoder.compress(payload) + encoder.flush()
    return header + data + struct.pack("<II", zlib.crc32(payload), len(payload))


def decode(data: bytes, *, limit: int | None = None):
    with FileStream(data) as stream:
        return decode_gzip(stream, max_output=limit)


def test_standard_library_gzip_decodes():
    assert decode(gzip.compress(PAYLOAD, mtime=0)).data == PAYLOAD


def test_optional_fields_have_exact_physical_offsets():
    data = member(PAYLOAD, optional=True)
    result = decode(data)
    assert result.data == PAYLOAD
    assert len(result.regions) == 1
    region = result.regions[0]
    assert (region.offset, region.length) == (0, len(data))
    fields = {field.name: field for field in region.children}
    assert fields["name"].value == b"document.json\0"
    assert fields["comment"].value == b"a comment\0"
    assert fields["extras"].value == b"AB\0\0"
    assert fields["body_crc32"].offset == len(data) - 8
    assert fields["len_uncompressed"].value == len(PAYLOAD)
    for field in region.children:
        assert 0 <= field.offset <= field.offset + field.length <= len(data)


def test_concatenated_members_form_one_decoded_file():
    first = member(PAYLOAD[:8])
    second = member(PAYLOAD[8:], optional=True)
    result = decode(first + second)
    assert result.data == PAYLOAD
    assert [(r.offset, r.length) for r in result.regions] == [
        (0, len(first)),
        (len(first), len(second)),
    ]


def test_zero_padding_is_mapped():
    data = member(PAYLOAD)
    result = decode(data + bytes(513))
    assert result.data == PAYLOAD
    assert result.regions[-1].name == "padding"
    assert (result.regions[-1].offset, result.regions[-1].length) == (len(data), 513)


@pytest.mark.parametrize("suffix", [b"junk", b"\0junk", b"\x1f\x8b"])
def test_trailing_garbage_and_truncated_following_members_are_invalid(suffix):
    with pytest.raises(DecodeError):
        decode(member(PAYLOAD) + suffix)


@pytest.mark.parametrize("length", [0, 1, 2, 3, 9, 10, 11])
def test_truncated_headers_and_data_are_invalid(length):
    with pytest.raises(DecodeError):
        decode(member(PAYLOAD)[:length])


@pytest.mark.parametrize("distance", [1, 4, 8, 9])
def test_truncated_payloads_and_trailers_are_invalid(distance):
    with pytest.raises(DecodeError):
        decode(member(PAYLOAD)[:-distance])


@pytest.mark.parametrize("offset", [3, -8, -4])
def test_reserved_flags_and_integrity_errors_are_invalid(offset):
    data = bytearray(member(PAYLOAD))
    data[offset] ^= 0x20 if offset == 3 else 1
    with pytest.raises(DecodeError):
        decode(bytes(data))


def test_header_checksum_is_validated():
    data = bytearray(member(PAYLOAD, optional=True))
    data[4] ^= 1
    with pytest.raises(DecodeError, match="header crc"):
        decode(bytes(data))


def test_unterminated_optional_names_are_invalid():
    data = b"\x1f\x8b\x08\x08" + bytes(6) + b"unterminated"
    with pytest.raises(DecodeError, match="unterminated"):
        decode(data)


def test_truncated_extra_field_is_invalid():
    data = b"\x1f\x8b\x08\x04" + bytes(6) + b"\xff\xffshort"
    with pytest.raises(DecodeError, match="extra field"):
        decode(data)


def test_unsupported_method_is_explicit():
    data = bytearray(member(PAYLOAD))
    data[2] = 12
    with pytest.raises(DecodeError) as error:
        decode(bytes(data))
    assert error.value.status == "unsupported"


def test_decoded_limit_checks_aggregate_concatenated_output():
    data = member(PAYLOAD[:8]) + member(PAYLOAD[8:])
    assert decode(data, limit=len(PAYLOAD)).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(data, limit=len(PAYLOAD) - 1)
    assert error.value.status == "limited"


def test_expansion_limit_is_checked_before_large_output_is_stored():
    data = gzip.compress(bytes(2_000_000), mtime=0)
    with pytest.raises(DecodeError) as error:
        decode(data, limit=17)
    assert error.value.status == "limited"


def test_empty_payload_accepts_a_zero_output_limit():
    assert decode(member(b""), limit=0).data == b""


def test_codec_memory_limit_is_optional():
    data = member(PAYLOAD)
    with FileStream(data) as stream:
        assert decode_gzip(stream, max_memory=GZIP_MEMORY).data == PAYLOAD
    with FileStream(data) as stream, pytest.raises(DecodeError) as error:
        decode_gzip(stream, max_memory=GZIP_MEMORY - 1)
    assert error.value.status == "limited"


def analyzed(data, limits=None):
    return list(Matcher(limits=limits).match(data))


def test_decoded_json_has_its_own_zero_based_source():
    matches = analyzed(member(PAYLOAD))
    wrapper = next(m for m in matches if m.name == "application/gzip")
    decoded = next(m for m in matches if m.name == "decoded_content")
    document = next(m for m in matches if m.name == "application/json")
    assert wrapper.source == "file"
    assert decoded.source == document.source == "decoded:0"
    assert decoded.parent is wrapper
    assert decoded.decoded == PAYLOAD
    assert (decoded.offset, document.offset, document.length) == (0, 0, len(PAYLOAD))
    assert wrapper.analysis_context.members == 1


def test_split_json_across_members_is_recursively_recognized():
    matches = analyzed(member(PAYLOAD[:8]) + member(PAYLOAD[8:]))
    document = next(m for m in matches if m.name == "application/json")
    assert document.source == "decoded:0"
    assert document.analysis_context.members == 2


def test_nested_gzip_sources_are_distinct_and_deterministic():
    data = member(member(PAYLOAD))
    for _ in range(2):
        matches = analyzed(data)
        decoded = [m for m in matches if m.name == "decoded_content"]
        assert [m.source for m in decoded] == ["decoded:0", "decoded:1"]
        document = next(m for m in matches if m.name == "application/json")
        assert document.source == "decoded:1"
        assert document.offset == 0


def test_gzip_zip_json_recursion_keeps_all_coordinate_spaces():
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("document.json", PAYLOAD)
    matches = analyzed(member(buffer.getvalue()))
    archive = next(m for m in matches if m.name == "application/zip")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == "decoded:0"
    assert document.source != archive.source
    assert document.offset == 0
    compressed = document.parent.parent
    assert compressed.name == "compressed_data"
    assert compressed.source == archive.source
    assert compressed.offset > 0


def test_invalid_data_publishes_no_decoded_child(caplog):
    data = bytearray(member(PAYLOAD))
    data[-8] ^= 1
    matches = analyzed(bytes(data))
    wrapper = next(m for m in matches if m.name == "application/gzip")
    assert wrapper.analysis_status == "invalid"
    assert not any(m.name == "decoded_content" for m in matches)
    assert not [record for record in caplog.records if record.levelno >= 30]


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_member_bytes", 4),
        ("max_total_bytes", 4),
        ("max_depth", 0),
        ("max_members", 0),
    ],
)
def test_configured_limits_are_explicit_and_do_not_publish_decoded_content(
    field, value
):
    matches = analyzed(member(PAYLOAD), AnalysisLimits(**{field: value}))
    wrapper = next(m for m in matches if m.name == "application/gzip")
    assert wrapper.analysis_status == "limited"
    assert wrapper.analysis_message
    assert not any(m.name == "decoded_content" for m in matches)


def test_nested_depth_limit_stops_at_the_selected_content_transition():
    matches = analyzed(member(member(PAYLOAD)), AnalysisLimits(max_depth=1))
    wrappers = [m for m in matches if m.name == "application/gzip"]
    assert len(wrappers) == 2
    assert wrappers[0].analysis_status is None
    assert wrappers[1].analysis_status == "limited"
    assert not any(m.name == "application/json" for m in matches)


def test_member_limit_counts_each_gzip_member():
    matches = analyzed(
        member(PAYLOAD[:8]) + member(PAYLOAD[8:]), AnalysisLimits(max_members=1)
    )
    wrapper = next(m for m in matches if m.name == "application/gzip")
    assert wrapper.analysis_status == "limited"
    assert not any(m.name == "decoded_content" for m in matches)


def test_default_analysis_does_not_impose_an_output_limit():
    payload = b'{"content":"' + b"x" * 200_000 + b'"}'
    matches = analyzed(member(payload))
    decoded = next(m for m in matches if m.name == "decoded_content")
    assert decoded.decoded == payload


def test_a_decoded_pdf_keeps_its_structure_in_the_decoded_source(caplog):
    matches = analyzed(member(WELL_FORMED_PDF))
    document = next(m for m in matches if m.name == "application/pdf")
    assert document.source == "decoded:0"
    objects = [m for m in matches if m.name == "PDFObject"]
    assert objects
    assert all(m.source == "decoded:0" for m in objects)
    assert not [record for record in caplog.records if record.levelno >= 30]


def test_gzip_tar_json_keeps_tar_member_offsets_in_the_decoded_buffer():
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        info = tarfile.TarInfo("document.json")
        info.size = len(PAYLOAD)
        archive.addfile(info, BytesIO(PAYLOAD))
    matches = analyzed(member(buffer.getvalue()))
    archive = next(m for m in matches if m.name == "application/x-tar")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert document.offset == 512
    assert document.length == len(PAYLOAD)
