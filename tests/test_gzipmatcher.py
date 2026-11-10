"""Gzip framing, integrity, nested-content, and resource-bound regressions."""

import gzip
import struct
import zlib

import pytest

from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.gzipmatcher import GZIP_MEMORY, decode_gzip

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
