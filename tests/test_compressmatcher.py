"""UNIX compress real-helper fixtures, recursion, framing, and resource controls."""

import contextlib
import io
import json
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from tests.fixture_types import FixtureProvenance

from polyfile import AnalysisLimits
from polyfile.__main__ import main
from polyfile.compression import DecodeError, DecodeResult
from polyfile.compressmatcher import decode_compress
from polyfile.fileutils import FileStream
from polyfile.gziphelper import find_gnu_gzip
from polyfile.polyfile import Match, Matcher
from tests.compress_fixture import literal_lzw

FIXTURES = Path(__file__).parent / "fixtures" / "compress"
PAYLOAD = (FIXTURES / "document.json").read_bytes()
PROVENANCE = json.loads((FIXTURES / "provenance.json").read_text())


@pytest.fixture
def gnu_gzip() -> str:
    try:
        return find_gnu_gzip()
    except DecodeError as error:
        pytest.skip(str(error))


def decode(data: bytes, **limits: int | None) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_compress(stream, **limits)


def analyzed(data: bytes | Path, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


@pytest.mark.parametrize("item", PROVENANCE, ids=lambda item: item["fixture"])
def test_owned_fixtures_round_trip_and_have_verified_provenance(
    gnu_gzip: str, item: FixtureProvenance
) -> None:
    encoded = (FIXTURES / item["fixture"]).read_bytes()
    expected = (FIXTURES / item["payload"]).read_bytes()
    assert sha256(encoded).hexdigest() == item["encoded_sha256"]
    assert sha256(expected).hexdigest() == item["decoded_sha256"]
    assert decode(encoded).data == expected


@pytest.mark.parametrize("width", (10, 12, 16))
def test_nonblock_width_transitions_with_real_decoder(gnu_gzip: str, width: int) -> None:
    payload = bytes(range(256)) * 300
    assert decode(literal_lzw(payload, width)).data == payload


@pytest.mark.parametrize("block", (False, True))
def test_empty_stream_accepts_zero_output_allowance(gnu_gzip: str, block: bool) -> None:
    assert decode(b"\x1f\x9d" + bytes([16 | (0x80 if block else 0)]), max_output=0).data == b""


def test_physical_framing_uses_the_encoded_buffer(gnu_gzip: str) -> None:
    data = (FIXTURES / "document-block-16.Z").read_bytes()
    result = decode(data)
    header, body = result.regions
    assert (header.name, header.offset, header.length) == ("compress_header", 0, 3)
    assert [(child.name, child.offset, child.length) for child in header.children] == [
        ("magic", 0, 2),
        ("flags", 2, 1),
    ]
    assert (body.name, body.offset, body.length) == ("lzw_data", 3, len(data) - 3)


@pytest.mark.parametrize("name", ("document-block-16.Z", "document-nonblock-16.Z"))
def test_decoded_json_has_a_separate_source(gnu_gzip: str, name: str) -> None:
    matches = analyzed((FIXTURES / name).read_bytes())
    wrapper = next(match for match in matches if match.name == "application/x-compress")
    decoded = next(match for match in matches if match.name == "decoded_content")
    document = next(match for match in matches if match.name == "application/json")
    assert decoded.parent is wrapper
    assert wrapper.source == "file"
    assert decoded.source == document.source == "decoded:0"
    assert decoded.decoded == PAYLOAD
    assert (document.offset, document.length) == (0, len(PAYLOAD))
    assert wrapper.analysis_context.members == 1


@pytest.mark.parametrize("name", ("archive-block-16.Z", "archive-nonblock-16.Z"))
def test_decoded_tar_recursively_scans_its_member(gnu_gzip: str, name: str) -> None:
    matches = analyzed((FIXTURES / name).read_bytes())
    archive = next(match for match in matches if match.name == "application/x-tar")
    document = next(match for match in matches if match.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert (document.offset, document.length) == (512, len(PAYLOAD))


def test_path_rawbytes_and_cli_share_decoding(gnu_gzip: str) -> None:
    path = FIXTURES / "document-block-16.Z"
    raw_matches = analyzed(path.read_bytes())
    path_matches = analyzed(path)
    assert [(match.name, match.source, match.offset) for match in raw_matches] == [
        (match.name, match.source, match.offset) for match in path_matches
    ]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(
            [
                "polyfile",
                "--quiet",
                "--format",
                "json",
                "--helper-timeout",
                "10",
                str(path),
            ]
        )
    document = json.loads(output.getvalue())
    pending = document["struc"]
    while pending:
        element = pending.pop()
        if element["type"] == "application/json":
            assert (element["source"], element["offset"]) == ("decoded:0", 0)
            break
        pending.extend(element["subEls"])
    else:
        pytest.fail("CLI output has no recursively decoded JSON document")


@pytest.mark.parametrize("data", (b"", b"\x1f", b"\x1f\x9d", b"\x1f\x9d\x90\x00"))
def test_provably_truncated_framing_is_invalid(data: bytes) -> None:
    with pytest.raises(DecodeError, match="truncated") as error:
        decode(data)
    assert error.value.status == "invalid"
    assert error.value.regions


@pytest.mark.parametrize("flags", (0, 8, 0x30, 0x50, 0x70))
def test_invalid_code_widths_and_reserved_bits(flags: int) -> None:
    with pytest.raises(DecodeError) as error:
        decode(b"\x1f\x9d" + bytes([flags]))
    assert error.value.status == "invalid"


def test_unsupported_code_width_is_explicit() -> None:
    with pytest.raises(DecodeError) as error:
        decode(b"\x1f\x9d\x91")
    assert error.value.status == "unsupported"


def test_wrong_signature_is_invalid() -> None:
    with pytest.raises(DecodeError, match="signature"):
        decode(b"bad")


@pytest.mark.parametrize("flags", (10, 0x90))
def test_corrupt_codes_report_helper_error_without_decoded_content(
    gnu_gzip: str, flags: int
) -> None:
    data = b"\x1f\x9d" + bytes([flags]) + b"\xff\xff\x03"
    with pytest.raises(DecodeError, match="corrupt"):
        decode(data)
    matches = analyzed(data)
    wrapper = next(match for match in matches if match.name == "application/x-compress")
    assert wrapper.analysis_status == "invalid"
    assert not any(match.name == "decoded_content" for match in matches)


def test_complete_code_prefix_can_be_a_valid_shorter_file(gnu_gzip: str) -> None:
    assert decode(b"\x1f\x9d\x0a\x41\x00").data == b"A"


@pytest.mark.parametrize("limit", (0, len(PAYLOAD) - 1))
def test_decoded_size_limit_is_explicit(gnu_gzip: str, limit: int) -> None:
    data = (FIXTURES / "document-block-16.Z").read_bytes()
    with pytest.raises(DecodeError) as error:
        decode(data, max_output=limit)
    assert error.value.status == "limited"
    assert decode(data, max_output=len(PAYLOAD)).data == PAYLOAD


def test_member_limit_prevents_helper_decoding() -> None:
    with pytest.raises(DecodeError) as error:
        decode(b"\x1f\x9d\x90", max_members=0)
    assert error.value.status == "limited"


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_depth", 0),
        ("max_members", 0),
        ("max_total_bytes", 1),
        ("max_member_bytes", 1),
    ],
)
def test_recursive_limits_preserve_wrapper_and_reason(
    gnu_gzip: str, field: str, value: int
) -> None:
    matches = analyzed(FIXTURES / "document-block-16.Z", AnalysisLimits(**{field: value}))
    wrapper = next(match for match in matches if match.name == "application/x-compress")
    assert wrapper.analysis_status == "limited"
    assert wrapper.analysis_message
    assert not any(match.name == "decoded_content" for match in matches)


def test_missing_helper_reports_unsupported_with_physical_framing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: None)
    matches = analyzed(FIXTURES / "document-block-16.Z")
    wrapper = next(match for match in matches if match.name == "application/x-compress")
    assert wrapper.analysis_status == "unsupported"
    assert wrapper.analysis_message is not None
    assert "GNU gzip 1.15" in wrapper.analysis_message
    assert any(match.name == "compress_header" for match in matches)
    assert not any(match.name == "decoded_content" for match in matches)


@pytest.mark.parametrize(
    "version",
    [
        b"Apple gzip 487.0.1\n",
        b"gzip 1.14\nFree Software Foundation, Inc.",
        b"gzip 1.15\n",
        b"uncompress 4.2.4.6\n",
    ],
)
def test_incompatible_helpers_are_explicit(monkeypatch: pytest.MonkeyPatch, version: bytes) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: sys.executable)
    monkeypatch.setattr("polyfile.gziphelper.run_helper", lambda *args, **kwargs: version)
    with pytest.raises(DecodeError) as error:
        find_gnu_gzip()
    assert error.value.status == "unsupported"


@pytest.mark.skipif(sys.platform == "linux", reason="other-platform configured-memory behavior")
def test_requested_hard_memory_limit_retains_unsupported_reason(gnu_gzip: str) -> None:
    matches = analyzed(FIXTURES / "document-block-16.Z", AnalysisLimits(max_codec_memory=128 << 20))
    wrapper = next(match for match in matches if match.name == "application/x-compress")
    assert wrapper.analysis_status == "unsupported"
    assert wrapper.analysis_message is not None
    assert "only on Linux" in wrapper.analysis_message


@pytest.mark.parametrize("minor", (15, 16, 99))
def test_current_and_newer_gnu_versions_are_supported(
    monkeypatch: pytest.MonkeyPatch, minor: int
) -> None:
    banner = f"gzip 1.{minor}\nCopyright (C) 2026 Free Software Foundation, Inc.\n".encode()
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: sys.executable)
    monkeypatch.setattr("polyfile.gziphelper.run_helper", lambda *args, **kwargs: banner)
    assert find_gnu_gzip() == str(Path(sys.executable).resolve())


def test_version_query_timeout_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> bytes:
        raise DecodeError("version query timeout", status="limited")

    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: sys.executable)
    monkeypatch.setattr("polyfile.gziphelper.run_helper", timeout)
    with pytest.raises(DecodeError) as error:
        find_gnu_gzip(helper_timeout=0.1)
    assert error.value.status == "limited"


def test_nine_bit_ceiling_reports_backend_limitation_before_helper_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: None)
    with pytest.raises(DecodeError, match="9-bit") as error:
        decode(b"\x1f\x9d\x09")
    assert error.value.status == "unsupported"
