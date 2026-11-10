"""Integrity, framing, and recursion tests for zlib streams."""

import zlib

import pytest

from polyfile.compression import DecodeError
from polyfile.fileutils import FileStream
from polyfile.polyfile import Matcher
from polyfile.zlibmatcher import ZLIB_MEMORY, decode_zlib

PAYLOAD = b'{"zlib_member": true}'


def decode(data: bytes, **limits):
    with FileStream(data) as stream:
        return decode_zlib(stream, **limits)


def test_decoded_bytes_and_physical_regions() -> None:
    data = zlib.compress(PAYLOAD)
    result = decode(data)
    assert result.data == PAYLOAD
    assert result.member_count == 1
    assert [
        (region.name, region.offset, region.length) for region in result.regions
    ] == [
        ("zlib_header", 0, 2),
        ("compressed_data", 2, len(data) - 6),
        ("adler32", len(data) - 4, 4),
    ]


@pytest.mark.parametrize("cut", range(len(zlib.compress(PAYLOAD))))
def test_truncated_stream(cut: int) -> None:
    with pytest.raises(DecodeError):
        decode(zlib.compress(PAYLOAD)[:cut])


@pytest.mark.parametrize("header", [b"\x88\x00", b"\x79\x00", b"\x78\x00"])
def test_invalid_header(header: bytes) -> None:
    with pytest.raises(DecodeError, match="zlib"):
        decode(header + zlib.compress(PAYLOAD)[2:])


def test_integrity_failure() -> None:
    data = bytearray(zlib.compress(PAYLOAD))
    data[-1] ^= 1
    with pytest.raises(DecodeError, match="Adler"):
        decode(bytes(data))


def test_preset_dictionary_is_explicitly_unsupported() -> None:
    compressor = zlib.compressobj(zdict=b"zlib_member")
    data = compressor.compress(PAYLOAD) + compressor.flush()
    with pytest.raises(DecodeError, match="dictionary") as failure:
        decode(data)
    assert failure.value.status == "unsupported"
    assert failure.value.regions[0].children[-1].name == "dictionary_id"


@pytest.mark.parametrize("trailing", [b"\0", b"extra", zlib.compress(PAYLOAD)])
def test_trailing_bytes_are_invalid(trailing: bytes) -> None:
    with pytest.raises(DecodeError, match="trailing") as failure:
        decode(zlib.compress(PAYLOAD) + trailing)
    assert failure.value.regions[-1].name == "trailing_data"


def test_output_limit_at_boundary() -> None:
    assert decode(zlib.compress(PAYLOAD), max_output=len(PAYLOAD)).data == PAYLOAD
    with pytest.raises(DecodeError) as failure:
        decode(zlib.compress(PAYLOAD), max_output=len(PAYLOAD) - 1)
    assert failure.value.status == "limited"


def test_incremental_output_limit_on_high_ratio_stream() -> None:
    with pytest.raises(DecodeError) as failure:
        decode(zlib.compress(b"A" * 100_000), max_output=1024)
    assert failure.value.status == "limited"


def test_codec_memory_limit() -> None:
    assert decode(zlib.compress(PAYLOAD), max_memory=ZLIB_MEMORY).data == PAYLOAD
    with pytest.raises(DecodeError) as failure:
        decode(zlib.compress(PAYLOAD), max_memory=ZLIB_MEMORY - 1)
    assert failure.value.status == "limited"


def test_member_limit() -> None:
    with pytest.raises(DecodeError) as failure:
        decode(zlib.compress(PAYLOAD), max_members=0)
    assert failure.value.status == "limited"


def test_empty_decoded_payload() -> None:
    assert decode(zlib.compress(b"")).data == b""


def test_recursive_json_has_its_own_source() -> None:
    nodes = list(Matcher().match(zlib.compress(PAYLOAD)))
    decoded = next(node for node in nodes if node.name == "decoded_content")
    child = next(node for node in nodes if node.name == "application/json")
    assert decoded.decoded == PAYLOAD
    assert child.source == decoded.source
    assert child.source != "file"
    assert child.offset == 0
    assert child.parent is decoded


def test_integrity_failure_publishes_no_decoded_children() -> None:
    data = bytearray(zlib.compress(PAYLOAD))
    data[-1] ^= 1
    nodes = list(Matcher().match(bytes(data)))
    parent = next(node for node in nodes if node.name == "application/zlib")
    assert parent.analysis_status == "invalid"
    assert not any(node.name == "decoded_content" for node in nodes)


def test_nested_gzip_uses_distinct_decoded_sources() -> None:
    import gzip

    nodes = list(Matcher().match(zlib.compress(gzip.compress(PAYLOAD, mtime=0))))
    buffers = [node for node in nodes if node.name == "decoded_content"]
    assert len(buffers) == 2
    assert len({node.source for node in buffers}) == 2
    child = next(node for node in nodes if node.name == "application/json")
    assert child.source == buffers[-1].source
    assert child.offset == 0


def test_required_dictionary_preserves_wrapper_without_fabricated_content() -> None:
    compressor = zlib.compressobj(zdict=b"zlib_member")
    data = compressor.compress(PAYLOAD) + compressor.flush()
    nodes = list(Matcher().match(data))
    parent = next(node for node in nodes if node.name == "application/zlib")
    assert parent.analysis_status == "unsupported"
    assert not any(node.name == "decoded_content" for node in nodes)
