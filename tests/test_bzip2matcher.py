"""Bzip2 framing, integrity, recursive content, and optional resource controls."""

import bz2
import random
import sys
from collections.abc import Iterator
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.bzip2matcher import decode_bzip2
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher

JSON = b'{"bzip2_member": true}\n'


def decode(
    data: bytes,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_bzip2(
            stream,
            max_output=max_output,
            max_memory=max_memory,
            max_members=max_members,
        )


def analyzed(data: bytes, *, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


def descendants(parent: Match) -> Iterator[Match]:
    for child in parent:
        yield child
        yield from descendants(child)


@pytest.mark.parametrize("level", range(1, 10))
def test_block_sizes_decode_with_exact_header_offsets(level: int) -> None:
    data = bz2.compress(JSON, compresslevel=level)
    result = decode(data)
    assert result.data == JSON
    assert result.member_count == 1
    region = result.regions[0]
    assert (region.offset, region.length) == (0, len(data))
    fields = {field.name: field for field in region.children}
    assert (fields["magic"].offset, fields["magic"].length) == (0, 3)
    assert fields["block_size"].value == level * 100_000
    assert fields["block_crc32"].offset == 10
    assert sum(field.length for field in region.children) == len(data)


def test_empty_stream_is_valid_and_maps_its_aligned_trailer() -> None:
    result = decode(bz2.compress(b""), max_output=0)
    assert result.data == b""
    fields = {field.name: field for field in result.regions[0].children}
    assert fields["end_marker"].offset == 4
    assert fields["combined_crc32"].offset == 10
    assert fields["combined_crc32"].value == 0


def test_concatenated_streams_preserve_physical_boundaries() -> None:
    first = bz2.compress(JSON[:8], compresslevel=1)
    second = bz2.compress(JSON[8:], compresslevel=9)
    result = decode(first + second)
    assert result.data == JSON
    assert result.member_count == 2
    assert [region.offset for region in result.regions] == [0, len(first)]
    assert [region.length for region in result.regions] == [len(first), len(second)]


def test_multiblock_stream_is_validated_completely() -> None:
    payload = random.Random(3622).randbytes(240_000)
    result = decode(bz2.compress(payload, compresslevel=1))
    assert result.data == payload
    assert result.member_count == 1


@pytest.mark.parametrize("data", [b"", b"B", b"BZ", b"BZh", b"BZh0", b"BZh:", b"BZ00"])
def test_invalid_or_incomplete_header_is_rejected(data: bytes) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("cut", [4, 5, 9, 14, -1, -4, -10])
def test_truncated_data_is_rejected(cut: int) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(bz2.compress(JSON)[:cut])
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("offset", [4, 10, 11, -1, -3])
def test_corrupt_block_and_stream_integrity_is_rejected(offset: int) -> None:
    data = bytearray(bz2.compress(JSON))
    data[offset] ^= 0x80
    with pytest.raises(DecodeError) as exc:
        decode(bytes(data))
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("trailing", [b"junk", b"\0", b"BZh", b"BZh0"])
def test_trailing_bytes_are_not_silently_ignored(trailing: bytes) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(bz2.compress(JSON) + trailing)
    assert exc.value.status == "invalid"
    assert exc.value.regions[0].name == "bzip2_stream"


def test_optional_output_limit_applies_to_concatenated_decoded_content() -> None:
    data = bz2.compress(JSON[:8]) + bz2.compress(JSON[8:])
    assert decode(data, max_output=len(JSON)).data == JSON
    with pytest.raises(DecodeError) as exc:
        decode(data, max_output=len(JSON) - 1)
    assert exc.value.status == "limited"


def test_small_output_limit_stops_high_expansion_stream() -> None:
    with pytest.raises(DecodeError) as exc:
        decode(bz2.compress(bytes(3_000_000)), max_output=17)
    assert exc.value.status == "limited"


def test_optional_stream_limit_counts_empty_streams() -> None:
    data = bz2.compress(b"") * 2
    assert decode(data, max_members=2).member_count == 2
    with pytest.raises(DecodeError) as exc:
        decode(data, max_members=1)
    assert exc.value.status == "limited"


def test_memory_requirement_is_checked_before_codec_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = bz2.compress(JSON, compresslevel=1)

    def unexpected_constructor() -> None:
        pytest.fail(
            "the codec was constructed before its memory requirement was admitted"
        )

    monkeypatch.setattr(bz2, "BZ2Decompressor", unexpected_constructor)
    with pytest.raises(DecodeError) as exc:
        decode(data, max_memory=499_999)
    assert exc.value.status == "limited"
    assert "500000" in str(exc.value)


def test_memory_budget_applies_to_every_concatenated_header() -> None:
    first = bz2.compress(JSON[:8], compresslevel=1)
    second = bz2.compress(JSON[8:], compresslevel=9)
    assert decode(first, max_memory=500_000).data == JSON[:8]
    with pytest.raises(DecodeError) as exc:
        decode(first + second, max_memory=500_000)
    assert exc.value.status == "limited"
    assert "3700000" in str(exc.value)


def test_missing_stdlib_backend_is_explicitly_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = bz2.compress(JSON)
    monkeypatch.setitem(sys.modules, "bz2", None)
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "unsupported"
    assert "bz2 module" in str(exc.value)


def test_decoded_json_has_a_separate_zero_based_source() -> None:
    matches = analyzed(bz2.compress(JSON))
    wrapper = next(node for node in matches if node.name == "application/x-bzip2")
    decoded = next(node for node in matches if node.name == "decoded_content")
    document = next(node for node in matches if node.name == "application/json")
    assert wrapper.source == "file"
    assert decoded.source == document.source == "decoded:0"
    assert (decoded.offset, document.offset) == (0, 0)
    assert decoded.decoded == JSON
    assert wrapper.analysis_context.members == 1


def test_json_split_across_streams_is_recursively_recognized() -> None:
    matches = analyzed(bz2.compress(JSON[:8]) + bz2.compress(JSON[8:]))
    document = next(node for node in matches if node.name == "application/json")
    assert document.source == "decoded:0"
    assert document.analysis_context.members == 2


def test_bzip2_zip_json_recursion_preserves_source_boundaries() -> None:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("document.json", JSON)
    matches = analyzed(bz2.compress(output.getvalue()))
    archive = next(node for node in matches if node.name == "application/zip")
    document = next(node for node in matches if node.name == "application/json")
    assert archive.source == "decoded:0"
    assert document.source != archive.source
    assert document.offset == 0


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_member_bytes=1),
        AnalysisLimits(max_members=0),
    ],
)
def test_limits_keep_wrapper_and_publish_no_incomplete_decoded_child(
    limits: AnalysisLimits,
) -> None:
    matches = analyzed(bz2.compress(JSON), limits=limits)
    wrapper = next(node for node in matches if node.name == "application/x-bzip2")
    assert wrapper.analysis_status == "limited"
    assert not any(node.name == "decoded_content" for node in matches)


def test_corruption_keeps_raw_wrapper_and_no_decoded_children(
    caplog: pytest.LogCaptureFixture,
) -> None:
    data = bytearray(bz2.compress(JSON))
    data[10] ^= 1
    matches = analyzed(bytes(data))
    wrapper = next(node for node in matches if node.name == "application/x-bzip2")
    assert wrapper.analysis_status == "invalid"
    assert any(node.name == "block_size" for node in descendants(wrapper))
    assert not any(node.name == "decoded_content" for node in matches)
    assert not caplog.records
