"""Native lzip v1 framing, integrity, recursion, and optional resource controls."""

import lzma
import shutil
import struct
import subprocess
import tarfile
import zlib
from io import BytesIO
from random import Random
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.lzipmatcher import decode_lzip, parse_lzip
from polyfile.polyfile import Match, Matcher, Submatch

PAYLOAD = b'{"lzip_member": true}\n'


def member(payload=PAYLOAD, *, code=12, dictionary=4096):
    body = lzma.compress(
        payload,
        format=lzma.FORMAT_RAW,
        filters=[
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": dictionary,
                "lc": 3,
                "lp": 0,
                "pb": 2,
            }
        ],
    )
    trailer = struct.pack("<IQQ", zlib.crc32(payload), len(payload), 6 + len(body) + 20)
    return b"LZIP\x01" + bytes([code]) + body + trailer


def decode(data, **limits):
    with FileStream(data) as stream:
        return decode_lzip(stream, **limits)


def test_standard_raw_lzma_fixture_decodes():
    result = decode(member())
    assert result.data == PAYLOAD
    assert result.member_count == 1


@pytest.mark.skipif(
    shutil.which("xz") is None, reason="xz is an optional reference decoder"
)
def test_positive_fixture_agrees_with_xz_lzip_decoder():
    result = subprocess.run(
        ["xz", "--format=lzip", "-dc"], input=member(), capture_output=True, check=True
    )
    assert result.stdout == PAYLOAD


def test_raw_header_body_and_trailer_extents_are_exact():
    data = member()
    result = decode(data)
    region = result.regions[0]
    assert (region.offset, region.length) == (0, len(data))
    header, body, trailer = region.children
    assert (header.offset, header.length) == (0, 6)
    assert (body.offset, body.length) == (6, len(data) - 26)
    assert (trailer.offset, trailer.length) == (len(data) - 20, 20)
    assert [field.value for field in trailer.children] == [
        zlib.crc32(PAYLOAD),
        len(PAYLOAD),
        len(data),
    ]


def test_concatenated_members_form_one_decoded_json_file():
    first, second = member(PAYLOAD[:8]), member(PAYLOAD[8:])
    result = decode(first + second)
    assert result.data == PAYLOAD
    assert result.member_count == 2
    assert [(r.offset, r.length) for r in result.regions] == [
        (0, len(first)),
        (len(first), len(second)),
    ]
    matches = list(Matcher().match(first + second))
    document = next(m for m in matches if m.name == "application/json")
    assert document.source == "decoded:0"
    assert document.offset == 0


@pytest.mark.parametrize("size", [0, 1, 65_535, 65_536, 65_537, 131_073])
def test_incremental_round_trips_cover_chunk_boundaries(size):
    data = Random(size).randbytes(size)
    assert decode(member(data)).data == data
    assert decode(member(bytes(size))).data == bytes(size)


def test_fractional_dictionary_size_is_supported():
    assert decode(member(code=0xD3, dictionary=320 * 1024)).data == PAYLOAD


@pytest.mark.parametrize("version", [0, 2, 255])
def test_unsupported_versions_are_explicit(version):
    data = bytearray(member())
    data[4] = version
    with pytest.raises(DecodeError) as error:
        decode(bytes(data))
    assert error.value.status == "unsupported"


@pytest.mark.parametrize("code", [0, 11, 30, 31, 0x2C, 255])
def test_invalid_dictionary_is_rejected_before_native_allocation(code):
    data = b"LZIP\x01" + bytes([code]) + bytes(20)
    with (
        patch("polyfile.lzipmatcher.lzma.LZMADecompressor") as constructor,
        pytest.raises(DecodeError) as error,
    ):
        decode(data)
    assert error.value.status == "invalid"
    constructor.assert_not_called()


def test_memory_limit_is_checked_before_large_dictionary_allocation():
    data = b"LZIP\x01\x1d" + bytes(20)
    with (
        patch("polyfile.lzipmatcher.lzma.LZMADecompressor") as constructor,
        pytest.raises(DecodeError) as error,
    ):
        decode(data, max_memory=1_000_000)
    assert error.value.status == "limited"
    constructor.assert_not_called()


def test_codec_memory_boundary_includes_decoder_state():
    required = 4096 + 64 * 1024
    assert decode(member(), max_memory=required).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(member(), max_memory=required - 1)
    assert error.value.status == "limited"


@pytest.mark.parametrize(
    "offset,reason", [(-20, "CRC32"), (-16, "decoded size"), (-8, "member size")]
)
def test_each_trailer_integrity_factor_is_validated(offset, reason):
    data = bytearray(member())
    data[offset] ^= 1
    with pytest.raises(DecodeError, match=reason):
        decode(bytes(data))


def test_every_truncated_prefix_is_invalid():
    data = member()
    for length in range(len(data)):
        with pytest.raises(DecodeError):
            decode(data[:length])


@pytest.mark.parametrize("suffix", [b"junk", bytes(4), b"LZIP", member()[:-1]])
def test_trailing_garbage_and_incomplete_following_members_publish_no_content(suffix):
    data = member() + suffix
    with pytest.raises(DecodeError):
        decode(data)
    matches = list(Matcher().match(data))
    wrapper = next(m for m in matches if m.name == "application/x-lzip")
    assert wrapper.analysis_status == "invalid"
    assert not any(m.name == "decoded_content" for m in matches)


def test_corrupt_lzma_stream_is_invalid():
    data = bytearray(member())
    data[6] = 255
    with pytest.raises(DecodeError):
        decode(bytes(data))


def test_empty_member_accepts_zero_output_but_is_invalid_in_multimember_files():
    assert decode(member(b""), max_output=0).data == b""
    for data in (member(b"") + member(), member() + member(b"")):
        with pytest.raises(DecodeError, match="empty members"):
            decode(data)


def test_output_and_member_limits_apply_to_concatenated_content():
    data = member(PAYLOAD[:8]) + member(PAYLOAD[8:])
    assert decode(data, max_output=len(PAYLOAD), max_members=2).data == PAYLOAD
    for limits in ({"max_output": len(PAYLOAD) - 1}, {"max_members": 1}):
        with pytest.raises(DecodeError) as error:
            decode(data, **limits)
        assert error.value.status == "limited"


def test_expansion_limit_prevents_an_unbounded_output_buffer():
    with pytest.raises(DecodeError) as error:
        decode(member(bytes(2_000_000)), max_output=17)
    assert error.value.status == "limited"


def test_nested_zip_json_recursion():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("document.json", PAYLOAD)
    matches = list(Matcher().match(member(buffer.getvalue())))
    archive = next(m for m in matches if m.name == "application/zip")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == "decoded:0"
    assert document.source != archive.source
    assert document.offset == 0


def test_nested_tar_member_uses_decoded_source_coordinates():
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        info = tarfile.TarInfo("document.json")
        info.size = len(PAYLOAD)
        archive.addfile(info, BytesIO(PAYLOAD))
    matches = list(Matcher().match(member(buffer.getvalue())))
    archive = next(m for m in matches if m.name == "application/x-tar")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert document.offset == 512


def test_failed_members_consume_the_shared_entry_budget():
    parent = Match("root", None, matcher=Matcher(limits=AnalysisLimits(max_members=2)))
    first = Submatch("application/x-lzip", None, parent=parent)
    with FileStream(member() + member()[:-1]) as stream:
        list(parse_lzip(stream, first))
    assert first.analysis_status == "invalid"
    assert parent.analysis_context.members == 2
    second = Submatch("application/x-lzip", None, parent=parent)
    with FileStream(member()) as stream:
        list(parse_lzip(stream, second))
    assert second.analysis_status == "limited"
    assert not second.children


def test_member_limit_counts_only_attempted_members():
    with pytest.raises(DecodeError) as error:
        decode(member() + member(), max_members=1)
    assert error.value.member_count == 1
