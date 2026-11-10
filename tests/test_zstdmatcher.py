"""Zstandard framing, integrity, recursion, and explicitly selected limits."""

import struct
import sys
from io import BytesIO
from random import Random
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.polyfile import Matcher
from polyfile.zstdmatcher import decode_zstd

if sys.version_info >= (3, 14):
    from compression import zstd
else:
    from backports import zstd

PAYLOAD = b'{"zstandard_member": true}\n'


def frame(data=PAYLOAD, *, checksum=True, content_size=True):
    return zstd.compress(
        data,
        options={
            zstd.CompressionParameter.checksum_flag: checksum,
            zstd.CompressionParameter.content_size_flag: content_size,
        },
    )


def skip(data=b"metadata", variant=0):
    return struct.pack("<II", 0x184D2A50 + variant, len(data)) + data


def decode(data, **limits):
    with FileStream(data) as stream:
        return decode_zstd(stream, **limits)


def test_modern_frame_decodes():
    result = decode(frame())
    assert result.data == PAYLOAD
    assert result.member_count == 1


@pytest.mark.parametrize("size", [0, 1, 65_535, 65_536, 65_537, 131_073])
def test_incremental_round_trips_cover_output_chunk_boundaries(size):
    payload = Random(size).randbytes(size)
    assert decode(frame(payload)).data == payload
    assert decode(frame(bytes(size))).data == bytes(size)


def test_concatenated_and_skippable_frames_have_exact_extents():
    parts = [skip(), frame(PAYLOAD[:8]), skip(b"", 15), frame(PAYLOAD[8:]), skip()]
    result = decode(b"".join(parts))
    assert result.data == PAYLOAD
    assert result.member_count == len(parts)
    offset = 0
    for part, region in zip(parts, result.regions):
        assert (region.offset, region.length) == (offset, len(part))
        offset += len(part)


def test_leading_skippable_frames_reach_recursive_parser_dispatch():
    data = skip() + skip(variant=2) + frame()
    matches = list(Matcher().match(data))
    wrapper = next(m for m in matches if m.name == "application/zstd")
    document = next(m for m in matches if m.name == "application/json")
    assert wrapper.source == "file"
    assert document.source == "decoded:0"
    assert document.offset == 0
    assert wrapper.analysis_context.members == 3


def test_nested_zip_json_recursion():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("document.json", PAYLOAD)
    matches = list(Matcher().match(frame(buffer.getvalue())))
    archive = next(m for m in matches if m.name == "application/zip")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == "decoded:0"
    assert document.source != archive.source
    assert document.offset == 0


@pytest.mark.parametrize("checksum", [False, True])
@pytest.mark.parametrize("content_size", [False, True])
def test_frames_with_optional_checksum_and_size(checksum, content_size):
    assert decode(frame(checksum=checksum, content_size=content_size)).data == PAYLOAD


def test_every_truncated_prefix_is_invalid():
    data = frame()
    for length in range(len(data)):
        with pytest.raises(DecodeError):
            decode(data[:length])


def test_corrupt_checksum_is_invalid():
    data = bytearray(frame())
    data[-1] ^= 1
    with pytest.raises(DecodeError, match="invalid"):
        decode(bytes(data))


@pytest.mark.parametrize(
    "data", [skip()[:-1], skip()[:4], frame() + b"junk", frame() + frame()[:-1]]
)
def test_malformed_following_frames_publish_no_decoded_children(data):
    with pytest.raises(DecodeError):
        decode(data)
    matches = list(Matcher().match(data))
    assert not any(m.name == "decoded_content" for m in matches)


def test_dictionary_requirement_is_explicitly_unsupported():
    samples = [
        b'{"item":' + str(i).encode() + b',"payload":"' + PAYLOAD * 10 + b'"}'
        for i in range(64)
    ]
    dictionary = zstd.train_dict(samples, 512)
    data = zstd.compress(PAYLOAD, zstd_dict=dictionary)
    assert zstd.decompress(data, zstd_dict=dictionary) == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(data)
    assert error.value.status == "unsupported"


def test_output_and_member_limits_include_concatenated_metadata_frames():
    data = skip() + frame(PAYLOAD[:8]) + frame(PAYLOAD[8:])
    assert decode(data, max_output=len(PAYLOAD), max_members=3).data == PAYLOAD
    for limit in ({"max_output": len(PAYLOAD) - 1}, {"max_members": 2}):
        with pytest.raises(DecodeError) as error:
            decode(data, **limit)
        assert error.value.status == "limited"


def test_window_limit_checks_exact_single_segment_size():
    data = frame()
    assert decode(data, max_memory=len(PAYLOAD)).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(data, max_memory=len(PAYLOAD) - 1)
    assert error.value.status == "limited"


def test_window_descriptor_limit_checks_non_single_segment_frames():
    data = frame(content_size=False)
    assert decode(data, max_memory=1024).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(data, max_memory=1023)
    assert error.value.status == "limited"


def test_non_power_of_two_window_limit_accepts_its_exact_boundary():
    data = bytearray(frame(content_size=False))
    data[5] = 4
    assert zstd.decompress(data) == PAYLOAD
    assert decode(bytes(data), max_memory=1536).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(bytes(data), max_memory=1535)
    assert error.value.status == "limited"


def test_valid_empty_frames_accept_zero_output_allowance():
    assert decode(frame(b""), max_output=0).data == b""


def test_skippable_only_input_is_valid_for_the_explicit_decoder():
    result = decode(skip())
    assert result.data == b""
    assert result.member_count == 1


def test_expansion_limit_prevents_an_unbounded_output_buffer():
    with pytest.raises(DecodeError) as error:
        decode(frame(bytes(2_000_000)), max_output=17)
    assert error.value.status == "limited"


def test_missing_backend_is_explicitly_unsupported():
    with (
        patch(
            "polyfile.zstdmatcher.importlib.import_module",
            side_effect=ImportError("missing"),
        ),
        pytest.raises(DecodeError) as error,
    ):
        decode(frame())
    assert error.value.status == "unsupported"


@pytest.mark.parametrize("version", range(0x22, 0x28))
def test_legacy_frames_are_explicitly_unsupported(version):
    with pytest.raises(DecodeError) as error:
        decode(bytes([version]) + b"\xb5\x2f\xfd" + bytes(20))
    assert error.value.status == "unsupported"


def test_analysis_limits_are_applied_before_publishing_decoded_content():
    data = frame()
    matches = list(Matcher(limits=AnalysisLimits(max_member_bytes=2)).match(data))
    wrapper = next(m for m in matches if m.name == "application/zstd")
    assert wrapper.analysis_status == "limited"
    assert not any(m.name == "decoded_content" for m in matches)
