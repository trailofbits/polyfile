"""Real SCO LZH decoding, signature dispatch, recursive sources, and failure results."""

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
from polyfile.fileutils import FileStream
from polyfile.gziphelper import find_gnu_gzip
from polyfile.magic import MAGIC_DEFS, MagicMatcher, join_matches
from polyfile.polyfile import Match, Matcher
from polyfile.scomatcher import SCO_MIME, decode_sco
from tests.sco_fixture import sco_codes

FIXTURES = Path(__file__).parent / "fixtures" / "sco"
PAYLOAD = (FIXTURES / "document.decoded").read_bytes()
PROVENANCE = json.loads((FIXTURES / "provenance.json").read_text())


@pytest.fixture
def gnu_gzip() -> str:
    try:
        return find_gnu_gzip()
    except DecodeError as error:
        pytest.skip(str(error))


def decode(data: bytes, **limits: int | None) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_sco(stream, **limits)


def analyzed(data: bytes | Path, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


@pytest.mark.parametrize("item", PROVENANCE, ids=lambda item: item["fixture"])
def test_owned_sco_fixtures_round_trip_with_reference_decoder(
    gnu_gzip: str, item: FixtureProvenance
) -> None:
    data = (FIXTURES / item["fixture"]).read_bytes()
    expected = (FIXTURES / item["payload"]).read_bytes()
    assert sha256(data).hexdigest() == item["encoded_sha256"]
    assert sha256(expected).hexdigest() == item["decoded_sha256"]
    assert decode(data).data == expected


def test_owned_backreference_generator_reproduces_fixture() -> None:
    assert sco_codes([65, 256]) == (FIXTURES / "backreference.lzh").read_bytes()


def test_physical_signature_and_body_regions(gnu_gzip: str) -> None:
    data = (FIXTURES / "document.lzh").read_bytes()
    result = decode(data)
    assert [(region.name, region.offset, region.length) for region in result.regions] == [
        ("sco_lzh_header", 0, 2),
        ("lzh_data", 2, len(data) - 2),
    ]


def test_json_uses_decoded_coordinates(gnu_gzip: str) -> None:
    matches = analyzed(FIXTURES / "document.lzh")
    wrapper = next(match for match in matches if match.name == SCO_MIME)
    decoded = next(match for match in matches if match.name == "decoded_content")
    document = next(match for match in matches if match.name == "application/json")
    assert decoded.parent is wrapper
    assert wrapper.source == "file"
    assert decoded.source == document.source == "decoded:0"
    assert decoded.decoded == PAYLOAD
    assert (document.offset, document.length) == (0, len(PAYLOAD))
    assert len([match for match in matches if match.name == SCO_MIME]) == 1


def test_tar_contents_are_recursively_scanned(gnu_gzip: str) -> None:
    matches = analyzed(FIXTURES / "archive.lzh")
    archive = next(match for match in matches if match.name == "application/x-tar")
    document = next(match for match in matches if match.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert (document.offset, document.length) == (512, len(PAYLOAD))


def test_path_and_rawbytes_have_equivalent_results(gnu_gzip: str) -> None:
    path = FIXTURES / "document.lzh"
    assert [(match.name, match.source, match.offset) for match in analyzed(path)] == [
        (match.name, match.source, match.offset) for match in analyzed(path.read_bytes())
    ]


@pytest.mark.parametrize("output_format", ("file", "mime", "json"))
def test_cli_file_mime_and_json_dispatch(gnu_gzip: str, output_format: str) -> None:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "-q", "-r", output_format, str(FIXTURES / "document.lzh")])
    if output_format == "file":
        assert output.getvalue() == "SCO compress -H (LZH) data\n"
    elif output_format == "mime":
        assert output.getvalue() == SCO_MIME + "\n"
    else:
        document = json.loads(output.getvalue())
        assert len(document["struc"]) == 1
        assert document["struc"][0]["type"] == SCO_MIME
        decoded = next(
            child for child in document["struc"][0]["subEls"] if child["type"] == "decoded_content"
        )
        assert any(child["type"] == "application/json" for child in decoded["subEls"])


def test_joined_description_has_no_duplicate_or_blank_alias() -> None:
    assert join_matches(Matcher().identify(FIXTURES / "document.lzh"), raw=True) == (
        "SCO compress -H (LZH) data"
    )


def test_standalone_bundled_definitions_keep_original_description() -> None:
    definitions = MagicMatcher.parse(next(path for path in MAGIC_DEFS if path.name == "compress"))
    matcher = Matcher(matcher=definitions)
    assert join_matches(matcher.identify(FIXTURES / "document.lzh"), raw=True) == (
        "SCO compress -H (LZH) data"
    )


def test_specialized_custom_description_is_preserved(tmp_path: Path) -> None:
    custom = tmp_path / "custom.magic"
    custom.write_text("0 string \\037\\240 custom SCO variant\n!:mime application/x-custom-sco\n")
    definitions = MagicMatcher(list(MagicMatcher.DEFAULT_INSTANCE))
    definitions.add(custom)
    descriptions = [
        str(match) for match in Matcher(matcher=definitions).identify(FIXTURES / "document.lzh")
    ]
    assert set(descriptions) == {"SCO compress -H (LZH) data", "custom SCO variant"}


@pytest.mark.parametrize("data", (b"", b"\x1f", b"\x1f\xa0", b"\x1f\xa0\0"))
def test_truncated_framing_is_invalid(data: bytes) -> None:
    with pytest.raises(DecodeError, match="truncated") as error:
        decode(data)
    assert error.value.status == "invalid"
    assert error.value.regions


def test_wrong_signature_is_invalid() -> None:
    with pytest.raises(DecodeError, match="signature"):
        decode(b"bad")


def test_malformed_huffman_table_publishes_no_partial_content(gnu_gzip: str) -> None:
    data = b"\x1f\xa0\x00\x01\x09"
    with pytest.raises(DecodeError, match="Bad table"):
        decode(data)
    matches = analyzed(data)
    wrapper = next(match for match in matches if match.name == SCO_MIME)
    assert wrapper.analysis_status == "invalid"
    assert not any(match.name == "decoded_content" for match in matches)


def test_output_limit_and_empty_zero_boundary(gnu_gzip: str) -> None:
    data = (FIXTURES / "document.lzh").read_bytes()
    assert decode(data, max_output=len(PAYLOAD)).data == PAYLOAD
    assert decode(sco_codes([]), max_output=0).data == b""
    with pytest.raises(DecodeError) as error:
        decode(data, max_output=len(PAYLOAD) - 1)
    assert error.value.status == "limited"


@pytest.mark.parametrize(
    "field,value",
    [("max_depth", 0), ("max_members", 0), ("max_member_bytes", 1), ("max_total_bytes", 1)],
)
def test_optional_recursive_limits_keep_wrapper(gnu_gzip: str, field: str, value: int) -> None:
    matches = analyzed(FIXTURES / "document.lzh", AnalysisLimits(**{field: value}))
    wrapper = next(match for match in matches if match.name == SCO_MIME)
    assert wrapper.analysis_status == "limited"
    assert wrapper.analysis_message
    assert not any(match.name == "decoded_content" for match in matches)


def test_member_preflight_is_explicit() -> None:
    with pytest.raises(DecodeError) as error:
        decode(sco_codes([]), max_members=0)
    assert error.value.status == "limited"


def test_missing_helper_keeps_format_recognition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: None)
    matches = analyzed(FIXTURES / "document.lzh")
    wrapper = next(match for match in matches if match.name == SCO_MIME)
    assert wrapper.analysis_status == "unsupported"
    assert wrapper.analysis_message is not None and "GNU gzip 1.15" in wrapper.analysis_message
    assert any(match.name == "lzh_data" for match in matches)
    assert not any(match.name == "decoded_content" for match in matches)


def test_generic_data_does_not_dispatch_sco_decoder() -> None:
    assert not any(match.name == SCO_MIME for match in analyzed(b"arbitrary binary\xff\0data"))


@pytest.mark.skipif(sys.platform == "linux", reason="configured memory limit outside Linux")
def test_requested_hard_memory_ceiling_is_explicitly_unsupported(gnu_gzip: str) -> None:
    matches = analyzed(FIXTURES / "document.lzh", AnalysisLimits(max_codec_memory=128 << 20))
    wrapper = next(match for match in matches if match.name == SCO_MIME)
    assert wrapper.analysis_status == "unsupported"
    assert wrapper.analysis_message is not None and "only on Linux" in wrapper.analysis_message


def test_alias_does_not_suppress_overlapping_afx_description() -> None:
    with FileStream(b"\x1f\xa0-afx-") as stream:
        descriptions = {str(match) for match in Matcher().identify(stream)}
    assert descriptions == {"SCO compress -H (LZH) data", "AFX compressed file data"}


def test_custom_mime_without_native_signature_alias_keeps_bundled_verdict(tmp_path: Path) -> None:
    custom = tmp_path / "custom.magic"
    custom.write_text("0 string NOTSCO unrelated custom rule\n!:mime application/x-sco-compress\n")
    definitions = MagicMatcher.parse(*MAGIC_DEFS)
    definitions.add(custom)
    with FileStream(b"\x1f\xa0") as stream:
        descriptions = [str(match) for match in Matcher(matcher=definitions).identify(stream)]
    assert descriptions == ["SCO compress -H (LZH) data"]
