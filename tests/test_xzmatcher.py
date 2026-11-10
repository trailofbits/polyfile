"""XZ integrity, concatenation, padding, and bounded decoded-content regressions."""

import lzma
import sys
import tarfile
import zlib
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher
from polyfile.xzmatcher import decode_xz

JSON = b'{"xz_member": true}\n'
FILTERS = [{"id": lzma.FILTER_LZMA2, "dict_size": 4096}]


def encoded(data: bytes, *, check: int = lzma.CHECK_CRC64) -> bytes:
    return lzma.compress(data, format=lzma.FORMAT_XZ, filters=FILTERS, check=check)


def decode(
    data: bytes,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_xz(
            stream,
            max_output=max_output,
            max_memory=max_memory,
            max_members=max_members,
        )


def analyzed(data: bytes, *, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


@pytest.mark.parametrize(
    "check", [lzma.CHECK_NONE, lzma.CHECK_CRC32, lzma.CHECK_CRC64, lzma.CHECK_SHA256]
)
def test_supported_integrity_checks_and_physical_regions(check: int) -> None:
    if not lzma.is_check_supported(check):
        pytest.skip("the installed liblzma lacks this integrity check")
    data = encoded(JSON, check=check)
    result = decode(data)
    assert result.data == JSON
    assert result.member_count == 1
    stream = result.regions[0]
    assert (stream.offset, stream.length) == (0, len(data))
    fields = {region.name: region for region in stream.children}
    assert fields["xz_header"].offset == 0
    assert fields["blocks"].offset == 12
    assert fields["xz_footer"].offset == len(data) - 12
    index = fields["index"]
    end = index.offset + index.length
    assert end == len(data) - 12
    start = index.offset
    raw_index = data[start:end]
    assert raw_index[0] == 0
    assert zlib.crc32(raw_index[:-4]) == int.from_bytes(raw_index[-4:], "little")
    assert sum(region.length for region in stream.children) == len(data)


def test_empty_stream_accepts_zero_output_and_maps_empty_blocks() -> None:
    result = decode(encoded(b""), max_output=0)
    assert result.data == b""
    blocks = next(
        region for region in result.regions[0].children if region.name == "blocks"
    )
    assert blocks.length == 0


@pytest.mark.parametrize("padding", [0, 4, 8, 65_536, 65_540])
def test_legal_stream_padding_between_and_after_streams(padding: int) -> None:
    first = encoded(JSON[:8])
    second = encoded(JSON[8:])
    data = first + bytes(padding) + second + bytes(padding)
    result = decode(data)
    assert result.data == JSON
    assert result.member_count == 2
    streams = [region for region in result.regions if region.name == "xz_stream"]
    assert streams[1].offset == len(first) + padding
    assert sum(region.length for region in result.regions) == len(data)


@pytest.mark.parametrize("padding", [1, 2, 3, 5, 65_537])
def test_padding_must_have_four_byte_multiple_length(padding: int) -> None:
    with pytest.raises(DecodeError, match="multiple of four") as exc:
        decode(encoded(JSON) + bytes(padding))
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("data", [b"", b"\xfd7zXZ\0", bytes(4)])
def test_empty_truncated_or_leading_padding_is_invalid(data: bytes) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("cut", [1, 6, 11, 12, 17, -1, -4, -12, -16])
def test_truncated_stream_is_invalid(cut: int) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(encoded(JSON)[:cut])
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("offset", [6, 8, 12, 20, -16, -12, -2])
def test_header_block_index_and_footer_corruption_is_invalid(offset: int) -> None:
    data = bytearray(encoded(JSON))
    data[offset] ^= 1
    with pytest.raises(DecodeError) as exc:
        decode(bytes(data))
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("trailing", [b"junk", b"\xfd7z", b"\0\0\0\0junk"])
def test_trailing_garbage_does_not_publish_partial_output(trailing: bytes) -> None:
    matches = analyzed(encoded(JSON) + trailing)
    wrapper = next(node for node in matches if node.name == "application/x-xz")
    assert wrapper.analysis_status == "invalid"
    assert not any(node.name == "decoded_content" for node in matches)


def test_unknown_integrity_check_is_explicitly_unsupported() -> None:
    data = bytearray(encoded(JSON))
    data[7] = 2
    data[8:12] = zlib.crc32(data[6:8]).to_bytes(4, "little")
    with pytest.raises(DecodeError) as exc:
        decode(bytes(data))
    assert exc.value.status == "unsupported"
    assert "check ID 2" in str(exc.value)


def test_missing_stdlib_backend_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    data = encoded(JSON)
    monkeypatch.setitem(sys.modules, "lzma", None)
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "unsupported"


def test_output_limit_applies_to_combined_stream_output() -> None:
    data = encoded(JSON[:8]) + bytes(4) + encoded(JSON[8:])
    assert decode(data, max_output=len(JSON)).data == JSON
    with pytest.raises(DecodeError) as exc:
        decode(data, max_output=len(JSON) - 1)
    assert exc.value.status == "limited"


def test_high_expansion_output_is_limited() -> None:
    with pytest.raises(DecodeError) as exc:
        decode(encoded(bytes(2_000_000)), max_output=17)
    assert exc.value.status == "limited"


def test_stream_count_excludes_padding_and_counts_empty_streams() -> None:
    data = encoded(b"") + bytes(4) + encoded(b"") + bytes(8)
    assert decode(data, max_members=2).member_count == 2
    with pytest.raises(DecodeError) as exc:
        decode(data, max_members=1)
    assert exc.value.status == "limited"


def test_large_dictionary_uses_native_memory_limit_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = bytearray(encoded(JSON))
    assert data[13:16] == b"\0\x21\x01"
    data[16] = 40
    header_size = (data[12] + 1) * 4
    crc_start = 12 + header_size - 4
    crc_end = crc_start + 4
    data[crc_start:crc_end] = zlib.crc32(data[12:crc_start]).to_bytes(4, "little")
    factory = lzma.LZMADecompressor

    def guarded(*, format: int, memlimit: int | None = None) -> lzma.LZMADecompressor:
        assert memlimit == 1_048_576
        return factory(format=format, memlimit=memlimit)

    monkeypatch.setattr(lzma, "LZMADecompressor", guarded)
    with pytest.raises(DecodeError) as exc:
        decode(bytes(data), max_memory=1_048_576)
    assert exc.value.status == "limited"


def test_native_memory_admission_boundary_is_respected() -> None:
    data = encoded(JSON)
    low, high = 1, 2_000_000
    while low < high:
        middle = (low + high) // 2
        try:
            lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=middle).decompress(
                data
            )
        except lzma.LZMAError:
            low = middle + 1
        else:
            high = middle
    assert decode(data, max_memory=low).data == JSON
    with pytest.raises(DecodeError) as exc:
        decode(data, max_memory=low - 1)
    assert exc.value.status == "limited"


def test_split_json_has_its_own_decoded_source() -> None:
    matches = analyzed(encoded(JSON[:8]) + bytes(4) + encoded(JSON[8:]))
    wrapper = next(node for node in matches if node.name == "application/x-xz")
    document = next(node for node in matches if node.name == "application/json")
    assert wrapper.source == "file"
    assert document.source == "decoded:0"
    assert document.offset == 0
    assert wrapper.analysis_context.members == 2


@pytest.mark.parametrize("container", ["tar", "zip"])
def test_decoded_archives_are_recursively_analyzed(container: str) -> None:
    output = BytesIO()
    if container == "tar":
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.USTAR_FORMAT
        ) as archive:
            info = tarfile.TarInfo("document.json")
            info.size = len(JSON)
            archive.addfile(info, BytesIO(JSON))
    else:
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("document.json", JSON)
    matches = analyzed(encoded(output.getvalue()))
    document = next(node for node in matches if node.name == "application/json")
    assert document.source.startswith("decoded:")
    assert document.offset == (512 if container == "tar" else 0)


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_member_bytes=1),
        AnalysisLimits(max_total_bytes=1),
        AnalysisLimits(max_members=0),
    ],
)
def test_optional_limits_keep_wrapper_without_decoded_children(
    limits: AnalysisLimits,
) -> None:
    matches = analyzed(encoded(JSON), limits=limits)
    wrapper = next(node for node in matches if node.name == "application/x-xz")
    assert wrapper.analysis_status == "limited"
    assert not any(node.name == "decoded_content" for node in matches)


class _RecordingDecoder:
    def __init__(self, decoder: lzma.LZMADecompressor, requests: list[int]):
        self.decoder = decoder
        self.requests = requests

    @property
    def eof(self) -> bool:
        return self.decoder.eof

    @property
    def needs_input(self) -> bool:
        return self.decoder.needs_input

    @property
    def unused_data(self) -> bytes:
        return self.decoder.unused_data

    def decompress(self, data: bytes, max_length: int = -1) -> bytes:
        self.requests.append(max_length)
        return self.decoder.decompress(data, max_length=max_length)


def test_native_output_requests_respect_the_configured_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = encoded(bytes(2_000_000))
    factory = lzma.LZMADecompressor
    requests: list[int] = []

    def recording(*, format: int, memlimit: int | None = None) -> _RecordingDecoder:
        return _RecordingDecoder(factory(format=format, memlimit=memlimit), requests)

    monkeypatch.setattr(lzma, "LZMADecompressor", recording)
    with pytest.raises(DecodeError) as exc:
        decode(data, max_output=17)
    assert exc.value.status == "limited"
    assert requests
    assert all(0 < request <= 18 for request in requests)


def test_large_memory_allowance_does_not_overflow_native_integer() -> None:
    assert decode(encoded(JSON), max_memory=1 << 100).data == JSON
