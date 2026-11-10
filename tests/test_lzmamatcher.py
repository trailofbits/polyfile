"""LZMA-alone ending, property, allocation-bound, and recursive-content regressions."""

import lzma
import sys
import tarfile
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.lzmamatcher import decode_lzma_alone
from polyfile.polyfile import Match, Matcher

JSON = b'{"lzma_member": true}\n'
FILTERS = [{"id": lzma.FILTER_LZMA1, "dict_size": 65536}]


def encoded(data: bytes, *, known_size: bool = False) -> bytes:
    result = lzma.compress(data, format=lzma.FORMAT_ALONE, filters=FILTERS)
    if known_size:
        result = result[:5] + len(data).to_bytes(8, "little") + result[13:]
    return result


def decode(
    data: bytes,
    *,
    max_output: int | None = None,
    max_memory: int | None = None,
    max_members: int | None = None,
) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_lzma_alone(
            stream,
            max_output=max_output,
            max_memory=max_memory,
            max_members=max_members,
        )


def analyzed(data: bytes, *, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


@pytest.mark.parametrize("known_size", [False, True])
def test_streamed_and_known_size_payloads_have_physical_header_fields(
    known_size: bool,
) -> None:
    data = encoded(JSON, known_size=known_size)
    result = decode(data)
    assert result.data == JSON
    assert result.member_count == 1
    stream = result.regions[0]
    assert (stream.offset, stream.length) == (0, len(data))
    header, body = stream.children
    fields = {field.name: field for field in header.children}
    assert (header.offset, header.length, body.offset) == (0, 13, 13)
    assert fields["properties"].value == 93
    assert fields["dictionary_size"].value == 65536
    assert fields["uncompressed_size"].value == (len(JSON) if known_size else "unknown")
    assert sum(region.length for region in stream.children) == len(data)


def test_known_size_empty_payload_without_end_marker_is_legal() -> None:
    header = encoded(b"")[:5] + bytes(8)
    data = header + bytes(5)
    native = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert native.decompress(data) == b""
    assert native.eof
    assert decode(data, max_output=0).data == b""


def test_streamed_empty_payload_requires_an_end_marker() -> None:
    data = encoded(b"")[:13] + bytes(5)
    with pytest.raises(DecodeError, match="truncated") as exc:
        decode(data)
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("known_size", [False, True])
def test_valid_empty_payload_with_marker_accepts_zero_output_limit(
    known_size: bool,
) -> None:
    assert decode(encoded(b"", known_size=known_size), max_output=0).data == b""


@pytest.mark.parametrize("dictionary", [0, 1, 4095, 4096, 5000, 6144, 65536])
def test_all_uint32_dictionary_values_use_explicit_alone_framing(
    dictionary: int,
) -> None:
    data = encoded(JSON)
    data = data[:1] + dictionary.to_bytes(4, "little") + data[5:]
    result = decode(data, max_memory=1_000_000)
    assert result.data == JSON
    header = result.regions[0].children[0]
    assert (
        next(
            field for field in header.children if field.name == "dictionary_size"
        ).value
        == dictionary
    )


@pytest.mark.parametrize("properties", [225, 250, 255])
def test_properties_outside_format_range_are_invalid(properties: int) -> None:
    data = bytes([properties]) + encoded(JSON)[1:]
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("properties", [8, 17, 224])
def test_valid_properties_beyond_liblzma_capability_are_unsupported(
    properties: int,
) -> None:
    data = bytes([properties]) + encoded(JSON)[1:]
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "unsupported"
    assert "lc+lp<=4" in str(exc.value)


def test_nondefault_supported_properties_decode() -> None:
    filters = [{"id": lzma.FILTER_LZMA1, "dict_size": 4096, "lc": 2, "lp": 2, "pb": 1}]
    data = lzma.compress(JSON, format=lzma.FORMAT_ALONE, filters=filters)
    assert decode(data).data == JSON


@pytest.mark.parametrize("cut", [0, 1, 4, 5, 12, 13, 14, -1, -5, -10])
def test_incomplete_header_payload_or_end_marker_is_invalid(cut: int) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(encoded(JSON)[:cut])
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("declared", [0, 1, len(JSON) - 1, len(JSON) + 1])
def test_incorrect_declared_sizes_are_rejected(declared: int) -> None:
    data = encoded(JSON)
    data = data[:5] + declared.to_bytes(8, "little") + data[13:]
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "invalid"


@pytest.mark.parametrize("trailing", [b"\0", b"junk", encoded(JSON)])
def test_trailing_data_and_concatenated_legacy_files_are_rejected(
    trailing: bytes,
) -> None:
    with pytest.raises(DecodeError, match="trailing") as exc:
        decode(encoded(JSON) + trailing)
    assert exc.value.status == "invalid"


def test_corrupt_range_coder_payload_is_invalid() -> None:
    data = bytearray(encoded(JSON))
    data[13] = 1
    with pytest.raises(DecodeError) as exc:
        decode(bytes(data))
    assert exc.value.status == "invalid"


def test_declared_size_limit_is_checked_before_codec_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = encoded(JSON, known_size=True)

    def unexpected_constructor() -> None:
        pytest.fail(
            "the decoder was allocated despite its rejected declared output size"
        )

    monkeypatch.setattr(lzma, "LZMADecompressor", unexpected_constructor)
    with pytest.raises(DecodeError) as exc:
        decode(data, max_output=len(JSON) - 1)
    assert exc.value.status == "limited"
    assert "declared" in str(exc.value)


def test_large_dictionary_is_admitted_by_native_memory_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = encoded(JSON)
    data = data[:1] + (0xFFFFFFFF).to_bytes(4, "little") + data[5:]
    factory = lzma.LZMADecompressor

    def guarded(*, format: int, memlimit: int | None = None) -> lzma.LZMADecompressor:
        assert memlimit == 1_000_000
        return factory(format=format, memlimit=memlimit)

    monkeypatch.setattr(lzma, "LZMADecompressor", guarded)
    with pytest.raises(DecodeError) as exc:
        decode(data, max_memory=1_000_000)
    assert exc.value.status == "limited"


@pytest.mark.parametrize("known_size", [False, True])
def test_exact_output_allowance_succeeds_and_smaller_allowance_fails(
    known_size: bool,
) -> None:
    data = encoded(JSON, known_size=known_size)
    assert decode(data, max_output=len(JSON)).data == JSON
    with pytest.raises(DecodeError) as exc:
        decode(data, max_output=len(JSON) - 1)
    assert exc.value.status == "limited"


def test_unknown_size_high_expansion_stream_obeys_output_limit() -> None:
    with pytest.raises(DecodeError) as exc:
        decode(encoded(bytes(2_000_000)), max_output=17)
    assert exc.value.status == "limited"


def test_single_stream_count_allowance_is_respected() -> None:
    assert decode(encoded(JSON), max_members=1).member_count == 1
    with pytest.raises(DecodeError) as exc:
        decode(encoded(JSON), max_members=0)
    assert exc.value.status == "limited"


def test_missing_native_backend_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    data = encoded(JSON)
    monkeypatch.setitem(sys.modules, "lzma", None)
    with pytest.raises(DecodeError) as exc:
        decode(data)
    assert exc.value.status == "unsupported"


def test_json_uses_a_separate_zero_based_decoded_source() -> None:
    matches = analyzed(encoded(JSON))
    wrapper = next(node for node in matches if node.name == "application/x-lzma")
    document = next(node for node in matches if node.name == "application/json")
    assert wrapper.source == "file"
    assert document.source == "decoded:0"
    assert document.offset == 0
    assert wrapper.analysis_context.members == 1


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
    assert document.offset == (512 if container == "tar" else 0)
    assert document.source.startswith("decoded:")


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
    wrapper = next(node for node in matches if node.name == "application/x-lzma")
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


def test_unknown_size_native_output_is_bounded_before_allocation(
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


@pytest.mark.parametrize("empty", [False, True])
def test_no_codec_attempt_is_charged_before_entry_admission(empty: bool) -> None:
    with pytest.raises(DecodeError) as exc:
        decode(b"" if empty else encoded(JSON), max_members=0)
    assert exc.value.member_count == 0


def test_failed_lzma_alone_stream_consumes_one_shared_entry() -> None:
    data = encoded(JSON)[:-5]
    matches = analyzed(data, limits=AnalysisLimits(max_members=2))
    wrapper = next(node for node in matches if node.name == "application/x-lzma")
    assert wrapper.analysis_context.members == 1
    assert wrapper.analysis_status == "invalid"
    assert not any(node.name == "decoded_content" for node in matches)
