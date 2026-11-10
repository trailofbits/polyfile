"""LZ4 framing, integrity, recursion, and optional resource controls."""

import struct
import tarfile
from io import BytesIO
from random import Random
from unittest.mock import patch
from zipfile import ZipFile

import lz4.frame
import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.lz4matcher import decode_lz4, parse_lz4
from polyfile.polyfile import Match, Matcher, Submatch

PAYLOAD = b'{"lz4_member": true}\n'


def frame(data=PAYLOAD, **options):
    settings = {"content_checksum": True, "block_checksum": True}
    settings.update(options)
    return lz4.frame.compress(data, **settings)


def skip(data=b"metadata", variant=0):
    return struct.pack("<II", 0x184D2A50 + variant, len(data)) + data


def decode(data, **limits):
    with FileStream(data) as stream:
        return decode_lz4(stream, **limits)


def dictionary_frame(identifier):
    data = frame()
    header = data[:14]
    header = (
        header[:4] + bytes([header[4] | 1]) + header[5:] + struct.pack("<I", identifier)
    )
    for checksum in range(256):
        candidate = header + bytes([checksum]) + data[15:]
        try:
            lz4.frame.get_frame_info(candidate)
        except RuntimeError:
            continue
        return candidate
    raise AssertionError("could not construct a valid dictionary frame header")


def test_modern_frame_decodes():
    result = decode(frame())
    assert result.data == PAYLOAD
    assert result.member_count == 1


@pytest.mark.parametrize("size", [0, 1, 65_535, 65_536, 65_537, 131_073])
def test_incremental_round_trips_cover_chunk_boundaries(size):
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


def test_leading_skippable_frames_reach_recursive_dispatch():
    matches = list(Matcher().match(skip() + skip(variant=4) + frame()))
    wrapper = next(m for m in matches if m.name == "application/x-lz4")
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


@pytest.mark.parametrize("block_linked", [False, True])
@pytest.mark.parametrize("store_size", [False, True])
def test_block_modes_and_optional_content_size(block_linked, store_size):
    payload = bytes(range(256)) * 1024
    assert (
        decode(frame(payload, block_linked=block_linked, store_size=store_size)).data
        == payload
    )


def test_every_truncated_prefix_is_invalid():
    data = frame()
    for length in range(len(data)):
        with pytest.raises(DecodeError):
            decode(data[:length])


@pytest.mark.parametrize("offset", [14, -1, -9])
def test_header_block_and_content_checksums_are_validated(offset):
    data = bytearray(frame())
    data[offset] ^= 1
    with pytest.raises(DecodeError):
        decode(bytes(data))


@pytest.mark.parametrize(
    "data", [skip()[:-1], skip()[:4], frame() + b"junk", frame() + frame()[:-1]]
)
def test_malformed_streams_publish_no_decoded_children(data):
    with pytest.raises(DecodeError):
        decode(data)
    matches = list(Matcher().match(data))
    assert not any(m.name == "decoded_content" for m in matches)


def test_declared_dictionary_is_explicitly_unsupported():
    data = dictionary_frame(12345)
    with pytest.raises(DecodeError) as error:
        decode(data)
    assert error.value.status == "unsupported"


def test_zero_dictionary_identifier_needs_no_dictionary():
    assert decode(dictionary_frame(0)).data == PAYLOAD


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize("prefix", [b"", skip()])
def test_legacy_frames_are_explicitly_unsupported(version, prefix):
    data = prefix + bytes([version]) + b"\x21\x4c\x18" + bytes(20)
    with pytest.raises(DecodeError) as error:
        decode(data)
    assert error.value.status == "unsupported"
    matches = list(Matcher().match(data))
    wrapper = next(m for m in matches if m.name == "application/x-lz4")
    assert wrapper.analysis_status == "unsupported"


def test_output_and_entry_limits_include_concatenated_metadata():
    data = skip() + frame(PAYLOAD[:8]) + frame(PAYLOAD[8:])
    assert decode(data, max_output=len(PAYLOAD), max_members=3).data == PAYLOAD
    for limits in ({"max_output": len(PAYLOAD) - 1}, {"max_members": 2}):
        with pytest.raises(DecodeError) as error:
            decode(data, **limits)
        assert error.value.status == "limited"


def test_codec_memory_allowance_is_checked_before_decompression():
    data = frame(
        bytes(200_000), block_size=lz4.frame.BLOCKSIZE_MAX64KB, block_linked=True
    )
    memory = 2 * 64 * 1024 + 128 * 1024 + 4096
    assert decode(data, max_memory=memory).data == bytes(200_000)
    with pytest.raises(DecodeError) as error:
        decode(data, max_memory=memory - 1)
    assert error.value.status == "limited"


def test_expansion_limit_prevents_unbounded_output():
    with pytest.raises(DecodeError) as error:
        decode(frame(bytes(2_000_000), store_size=False), max_output=17)
    assert error.value.status == "limited"


def test_empty_frames_accept_zero_output_allowance():
    assert decode(frame(b""), max_output=0).data == b""


def test_missing_backend_is_explicitly_unsupported():
    with (
        patch(
            "polyfile.lz4matcher.importlib.import_module",
            side_effect=ImportError("missing"),
        ),
        pytest.raises(DecodeError) as error,
    ):
        decode(frame())
    assert error.value.status == "unsupported"


def test_analysis_limits_are_applied_before_publishing_content():
    matches = list(Matcher(limits=AnalysisLimits(max_member_bytes=2)).match(frame()))
    wrapper = next(m for m in matches if m.name == "application/x-lz4")
    assert wrapper.analysis_status == "limited"
    assert not any(m.name == "decoded_content" for m in matches)


def test_lz4_tar_json_keeps_tar_member_coordinates_in_the_decoded_buffer():
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        info = tarfile.TarInfo("document.json")
        info.size = len(PAYLOAD)
        archive.addfile(info, BytesIO(PAYLOAD))
    matches = list(Matcher().match(frame(buffer.getvalue())))
    archive = next(m for m in matches if m.name == "application/x-tar")
    document = next(m for m in matches if m.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert document.offset == 512


def test_failed_frames_consume_the_shared_entry_budget():
    parent = Match("root", None, matcher=Matcher(limits=AnalysisLimits(max_members=2)))
    first = Submatch("application/x-lz4", None, parent=parent)
    with FileStream(frame() + frame()[:-1]) as stream:
        list(parse_lz4(stream, first))
    assert first.analysis_status == "invalid"
    assert parent.analysis_context.members == 2
    second = Submatch("application/x-lz4", None, parent=parent)
    with FileStream(frame()) as stream:
        list(parse_lz4(stream, second))
    assert second.analysis_status == "limited"
    assert not second.children


def test_a_frame_limit_counts_only_entries_already_attempted():
    with pytest.raises(DecodeError) as error:
        decode(frame() + frame(), max_members=1)
    assert error.value.status == "limited"
    assert error.value.member_count == 1
