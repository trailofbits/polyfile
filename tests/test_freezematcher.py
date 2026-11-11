"""Original freeze streams, legacy gzip framing, ambiguity, and recursive sources."""

import contextlib
import gzip
import io
import json
import random
import struct
import zlib
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile import AnalysisLimits
from polyfile.__main__ import main
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.freeze1 import FREEZE_MEMORY
from polyfile.freezematcher import FREEZE_MIME, decode_frozen
from polyfile.magic import MAGIC_DEFS, MagicMatcher, join_matches
from polyfile.polyfile import Match, Matcher

FIXTURES = Path(__file__).parent / "fixtures" / "freeze"
PAYLOAD = (FIXTURES / "document.json").read_bytes()


def decode(data: bytes, **limits: int | None) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_frozen(stream, **limits)


def analyzed(data: bytes | Path, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


def legacy_gzip(payload: bytes, *, optional: bool = False) -> bytes:
    if not optional:
        return b"\x1f\x9e" + gzip.compress(payload, mtime=0)[2:]
    header = b"\x1f\x9e\x08\x1c" + bytes(6)
    header += b"\x04\0AB\0\0document.json\0a comment\0"
    encoder = zlib.compressobj(wbits=-15)
    body = encoder.compress(payload) + encoder.flush()
    return header + body + struct.pack("<II", zlib.crc32(payload), len(payload))


@pytest.mark.parametrize("name", ("document.json", "archive.tar", "empty.bin"))
def test_original_encoder_fixtures(name: str) -> None:
    expected = b"" if name == "empty.bin" else (FIXTURES / name).read_bytes()
    data = (FIXTURES / (name + ".F")).read_bytes()
    result = decode(data)
    assert result.data == expected
    assert result.member_count == 1
    assert [
        (region.name, region.offset, region.length) for region in result.regions
    ] == [
        ("freeze_1_header", 0, 2),
        ("adaptive_huffman_data", 2, len(data) - 2),
    ]


def test_original_encoder_frequency_rebuild_fixture() -> None:
    data = (FIXTURES / "frequency-rebuild.bin.F").read_bytes()
    assert decode(data).data == random.Random(3631).randbytes(80000)


@pytest.mark.parametrize("name", ("initial-spaces", "ring-wrap", "method-collision"))
def test_original_encoder_history_and_ambiguous_method(name: str) -> None:
    data = (FIXTURES / (name + ".F")).read_bytes()
    assert decode(data).data == (FIXTURES / (name + ".decoded")).read_bytes()
    if name == "method-collision":
        assert data[:3] == b"\x1f\x9e\x08"


def test_fixture_provenance_hashes() -> None:
    provenance = json.loads((FIXTURES / "provenance.json").read_text())
    for fixture in provenance["fixtures"]:
        assert (
            sha256((FIXTURES / fixture["fixture"]).read_bytes()).hexdigest()
            == fixture["encoded_sha256"]
        )


@pytest.mark.parametrize("optional", (False, True))
def test_legacy_gzip_integrity_and_physical_header(optional: bool) -> None:
    data = legacy_gzip(PAYLOAD, optional=optional)
    result = decode(data)
    assert result.data == PAYLOAD
    assert result.member_count == 1
    member = result.regions[0]
    assert (member.name, member.offset, member.length) == (
        "gzip_0_5_member",
        0,
        len(data),
    )
    assert member.children[0].value == b"\x1f\x9e"
    names = {child.name for child in member.children}
    assert {"body_crc32", "len_uncompressed"} <= names
    if optional:
        assert {"extras", "name", "comment"} <= names


def test_legacy_gzip_concatenation_and_padding() -> None:
    first = legacy_gzip(PAYLOAD[:20], optional=True)
    second = legacy_gzip(PAYLOAD[20:])
    result = decode(first + second + b"\0" * 3)
    assert result.data == PAYLOAD
    assert result.member_count == 2
    assert [(region.offset, region.length) for region in result.regions] == [
        (0, len(first)),
        (len(first), len(second)),
        (len(first) + len(second), 3),
    ]
    assert result.regions[1].children[0].offset == len(first)


@pytest.mark.parametrize("legacy", (False, True))
def test_json_recursion_preserves_source_boundary(legacy: bool) -> None:
    data = (
        legacy_gzip(PAYLOAD) if legacy else (FIXTURES / "document.json.F").read_bytes()
    )
    matches = analyzed(data)
    wrapper = next(match for match in matches if match.name == FREEZE_MIME)
    decoded = next(match for match in matches if match.name == "decoded_content")
    document = next(match for match in matches if match.name == "application/json")
    assert wrapper.source == "file"
    assert decoded.source == document.source == "decoded:0"
    assert decoded.parent is wrapper
    assert decoded.decoded == PAYLOAD
    assert (document.offset, document.length) == (0, len(PAYLOAD))
    assert len([match for match in matches if match.name == FREEZE_MIME]) == 1


@pytest.mark.parametrize("legacy", (False, True))
def test_tar_members_are_recursively_analyzed(legacy: bool) -> None:
    data = (
        legacy_gzip((FIXTURES / "archive.tar").read_bytes())
        if legacy
        else (FIXTURES / "archive.tar.F").read_bytes()
    )
    matches = analyzed(data)
    archive = next(match for match in matches if match.name == "application/x-tar")
    document = next(match for match in matches if match.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert (document.offset, document.length) == (512, len(PAYLOAD))


def test_legacy_gzip_zip_creates_nested_decoded_source() -> None:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("document.json", PAYLOAD)
    matches = analyzed(legacy_gzip(stream.getvalue()))
    document = next(match for match in matches if match.name == "application/json")
    assert document.source == "decoded:1"
    assert document.offset == 0


@pytest.mark.parametrize("output_format", ("file", "mime", "json"))
def test_cli_dispatch_and_original_description(output_format: str) -> None:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "-q", "-r", output_format, str(FIXTURES / "document.json.F")])
    if output_format == "file":
        assert output.getvalue() == "frozen file 1.0 (or gzip 0.5)\n"
    elif output_format == "mime":
        assert output.getvalue() == FREEZE_MIME + "\n"
    else:
        wrapper = json.loads(output.getvalue())["struc"][0]
        assert wrapper["type"] == FREEZE_MIME
        decoded = next(
            child for child in wrapper["subEls"] if child["type"] == "decoded_content"
        )
        assert any(child["type"] == "application/json" for child in decoded["subEls"])


def test_standalone_bundled_definition_keeps_description() -> None:
    definitions = MagicMatcher.parse(
        next(path for path in MAGIC_DEFS if path.name == "compress")
    )
    result = Matcher(matcher=definitions).identify(FIXTURES / "document.json.F")
    assert join_matches(result, raw=True) == "frozen file 1.0 (or gzip 0.5)"


def test_alias_keeps_overlapping_afx_description() -> None:
    with FileStream(b"\x1f\x9e-afx-") as stream:
        descriptions = {str(match) for match in Matcher().identify(stream)}
    assert descriptions == {"frozen file 1.0 (or gzip 0.5)", "AFX compressed file data"}


@pytest.mark.parametrize("data", (b"", b"\x1f", b"\x1f\x9e", b"wrong", b"\x1f\x9f\x8a"))
def test_missing_or_wrong_signature_is_invalid(data: bytes) -> None:
    with pytest.raises(DecodeError) as error:
        decode(data)
    assert error.value.status == "invalid"


@pytest.mark.parametrize("legacy", (False, True))
def test_truncated_prefixes_require_a_complete_supported_variant(legacy: bool) -> None:
    data = (
        legacy_gzip(PAYLOAD) if legacy else (FIXTURES / "document.json.F").read_bytes()
    )
    for end in range(len(data)):
        if legacy and data[:end] == (FIXTURES / "dual-prefix.F").read_bytes():
            assert (
                decode(data[:end]).data
                == (FIXTURES / "dual-prefix.decoded").read_bytes()
            )
            continue
        with pytest.raises(DecodeError) as error:
            decode(data[:end])
        assert error.value.status == "invalid", end


@pytest.mark.parametrize("offset", (-8, -4))
def test_legacy_gzip_rejects_crc_and_size_corruption(offset: int) -> None:
    data = bytearray(legacy_gzip(PAYLOAD))
    data[offset] ^= 1
    with pytest.raises(DecodeError) as error:
        decode(bytes(data))
    assert error.value.status == "invalid"
    matches = analyzed(bytes(data))
    wrapper = next(match for match in matches if match.name == FREEZE_MIME)
    assert wrapper.analysis_status == "invalid"
    assert not any(match.name == "decoded_content" for match in matches)


@pytest.mark.parametrize("legacy", (False, True))
def test_trailing_bytes_are_invalid(legacy: bool) -> None:
    data = (
        legacy_gzip(PAYLOAD) if legacy else (FIXTURES / "document.json.F").read_bytes()
    )
    with pytest.raises(DecodeError) as error:
        decode(data + b"trailing")
    assert error.value.status == "invalid"


@pytest.mark.parametrize("legacy", (False, True))
def test_output_limit_exact_boundary_and_no_fallback_after_limit(legacy: bool) -> None:
    data = (
        legacy_gzip(PAYLOAD) if legacy else (FIXTURES / "document.json.F").read_bytes()
    )
    assert decode(data, max_output=len(PAYLOAD)).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(data, max_output=len(PAYLOAD) - 1)
    assert error.value.status == "limited"
    assert error.value.member_count == 1


def test_empty_zero_output_and_memory_boundaries() -> None:
    data = (FIXTURES / "empty.bin.F").read_bytes()
    assert decode(data, max_output=0, max_memory=FREEZE_MEMORY).data == b""
    with pytest.raises(DecodeError) as error:
        decode(data, max_memory=FREEZE_MEMORY - 1)
    assert error.value.status == "limited"
    assert error.value.member_count == 0


def test_legacy_gzip_member_limit_and_failed_attempt_counts() -> None:
    first = legacy_gzip(PAYLOAD[:20])
    second = legacy_gzip(PAYLOAD[20:])
    assert decode(first + second, max_members=2).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(first + second, max_members=1)
    assert error.value.status == "limited"
    assert error.value.member_count == 1
    assert not any(
        match.name == "decoded_content"
        for match in analyzed(first + second, AnalysisLimits(max_members=1))
    )


def test_failed_legacy_gzip_tail_counts_attempted_member() -> None:
    data = legacy_gzip(PAYLOAD) + b"\x1f\x9e\x08"
    with pytest.raises(DecodeError) as error:
        decode(data)
    assert error.value.status == "invalid"
    assert error.value.member_count == 2


def test_legacy_gzip_multipart_is_explicitly_unsupported() -> None:
    data = bytearray(legacy_gzip(PAYLOAD))
    data[3] |= 2
    with pytest.raises(DecodeError) as error:
        decode(bytes(data))
    assert error.value.status == "unsupported"
    assert "multipart" in str(error.value)


@pytest.mark.parametrize(
    "name", ("max_depth", "max_member_bytes", "max_total_bytes", "max_members")
)
def test_recursive_limits_report_status_without_decoded_children(name: str) -> None:
    matches = analyzed(
        (FIXTURES / "document.json.F").read_bytes(), AnalysisLimits(**{name: 0})
    )
    wrapper = next(match for match in matches if match.name == FREEZE_MIME)
    assert wrapper.analysis_status == "limited"
    assert not any(match.name == "decoded_content" for match in matches)


def test_invalid_shared_signature_charges_one_attempt() -> None:
    matches = analyzed(b"\x1f\x9e\x08", AnalysisLimits(max_members=2))
    wrapper = next(match for match in matches if match.name == FREEZE_MIME)
    assert wrapper.analysis_status == "invalid"
    assert wrapper.analysis_context.remaining_members == 1


def test_zero_member_limit_does_not_attempt_either_variant() -> None:
    with pytest.raises(DecodeError) as error:
        decode((FIXTURES / "document.json.F").read_bytes(), max_members=0)
    assert error.value.status == "limited"
    assert error.value.member_count == 0


def test_failed_gzip_tail_preserves_global_member_count() -> None:
    matches = analyzed(
        legacy_gzip(PAYLOAD) + b"\x1f\x9e\x08", AnalysisLimits(max_members=2)
    )
    wrapper = next(match for match in matches if match.name == FREEZE_MIME)
    assert wrapper.analysis_status == "invalid"
    assert wrapper.analysis_context.remaining_members == 0


def test_invalid_candidates_preserve_each_physical_interpretation() -> None:
    first = legacy_gzip(PAYLOAD)
    data = first + b"\x1f\x9e\x08"
    with pytest.raises(DecodeError) as error:
        decode(data)
    gzip_candidate, freeze_candidate = error.value.regions
    assert (gzip_candidate.name, freeze_candidate.name) == (
        "gzip_0_5_candidate",
        "freeze_1_candidate",
    )
    assert gzip_candidate.offset == freeze_candidate.offset == 0
    assert gzip_candidate.length == freeze_candidate.length == len(data)
    assert gzip_candidate.children[0].name == "gzip_0_5_member"
    assert gzip_candidate.children[0].length == len(first)
    assert gzip_candidate.children[0].children[-1].name == "len_uncompressed"
    assert freeze_candidate.children[0].name == "freeze_1_header"
    matches = analyzed(data)
    assert {match.source for match in matches} == {"file"}
    assert not any(match.name == "decoded_content" for match in matches)
