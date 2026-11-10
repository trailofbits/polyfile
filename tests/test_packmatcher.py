"""Real UNIX pack Huffman fixtures, explicit dispatch, recursion, and integrity errors."""

import contextlib
import io
import json
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from polyfile import AnalysisLimits
from polyfile.__main__ import main
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.gziphelper import find_gnu_gzip
from polyfile.magic import MAGIC_DEFS, MagicMatcher, join_matches
from polyfile.packmatcher import PACK_MIME, decode_pack
from polyfile.polyfile import Match, Matcher
from tests.pack_fixture import pack_fixture

FIXTURES = Path(__file__).parent / "fixtures" / "pack"
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
        return decode_pack(stream, **limits)


def analyzed(data: bytes | Path, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


@pytest.mark.parametrize("item", PROVENANCE, ids=lambda item: item["fixture"])
def test_owned_pack_fixtures_round_trip_with_real_decoder(gnu_gzip: str, item: dict) -> None:
    encoded = (FIXTURES / item["fixture"]).read_bytes()
    expected = (FIXTURES / item["payload"]).read_bytes()
    assert sha256(encoded).hexdigest() == item["encoded_sha256"]
    assert sha256(expected).hexdigest() == item["decoded_sha256"]
    assert decode(encoded).data == expected


def test_owned_generator_reproduces_all_bytes_fixture() -> None:
    assert pack_fixture(bytes(range(256))) == (FIXTURES / "all-bytes.z").read_bytes()


def test_raw_fields_have_exact_encoded_offsets(gnu_gzip: str) -> None:
    data = (FIXTURES / "document.z").read_bytes()
    result = decode(data)
    header, body = result.regions
    assert (header.name, header.offset, header.length) == ("pack_header", 0, 272)
    assert [(field.name, field.offset, field.length) for field in header.children] == [
        ("magic", 0, 2),
        ("decoded_size", 2, 4),
        ("max_code_length", 6, 1),
        ("leaves_per_length", 7, 9),
        ("literals", 16, 256),
    ]
    assert header.children[1].value == len(PAYLOAD)
    assert (body.name, body.offset, body.length) == ("huffman_data", 272, len(data) - 272)


def test_decoded_json_and_tar_use_separate_sources(gnu_gzip: str) -> None:
    for name, offset in (("document.z", 0), ("archive.z", 512)):
        matches = analyzed(FIXTURES / name)
        wrapper = next(match for match in matches if match.name == PACK_MIME)
        decoded = next(match for match in matches if match.name == "decoded_content")
        document = next(match for match in matches if match.name == "application/json")
        assert decoded.parent is wrapper
        assert wrapper.source == "file"
        assert decoded.source == document.source == "decoded:0"
        assert (document.offset, document.length) == (offset, len(PAYLOAD))
        assert not any(match.name == "application/octet-stream" for match in matches)


def test_path_and_rawbytes_are_equivalent(gnu_gzip: str) -> None:
    path = FIXTURES / "document.z"
    assert [(match.name, match.source, match.offset) for match in analyzed(path)] == [
        (match.name, match.source, match.offset) for match in analyzed(path.read_bytes())
    ]


@pytest.mark.parametrize("output_format", ("file", "mime", "json"))
def test_cli_file_mime_and_json_dispatch(gnu_gzip: str, output_format: str) -> None:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "-q", "-r", output_format, str(FIXTURES / "document.z")])
    if output_format == "file":
        assert output.getvalue() == "packed data, 50 characters originally\n"
    elif output_format == "mime":
        assert output.getvalue() == PACK_MIME + "\n"
    else:
        document = json.loads(output.getvalue())
        assert len(document["struc"]) == 1
        assert document["struc"][0]["type"] == PACK_MIME
        decoded = next(
            child for child in document["struc"][0]["subEls"] if child["type"] == "decoded_content"
        )
        assert any(child["type"] == "application/json" for child in decoded["subEls"])


@pytest.mark.parametrize(
    "name,description",
    [
        ("document.z", "packed data, 50 characters originally"),
        ("one-byte.z", "packed data, 1 character originally"),
        ("empty.z", "packed data"),
    ],
)
def test_joined_descriptions_keep_original_size_messages(name: str, description: str) -> None:
    assert join_matches(Matcher().identify(FIXTURES / name), raw=True) == description


def test_standalone_bundled_definitions_keep_generic_pack_classification() -> None:
    definitions = MagicMatcher.parse(next(path for path in MAGIC_DEFS if path.name == "compress"))
    matches = list(Matcher(matcher=definitions, parse=False).match(FIXTURES / "document.z"))
    assert [match.name for match in matches] == ["application/octet-stream"]


def test_old_pack_is_recognized_and_explicitly_unsupported() -> None:
    with pytest.raises(DecodeError, match="old UNIX pack") as error:
        decode(b"\x1f\x1f")
    assert error.value.status == "unsupported"
    matches = analyzed(b"\x1f\x1f")
    wrapper = next(match for match in matches if match.name == PACK_MIME)
    assert wrapper.analysis_status == "unsupported"
    with FileStream(b"\x1f\x1f") as stream:
        assert join_matches(Matcher().identify(stream), raw=True) == "old packed data"
    assert not any(match.name == "decoded_content" for match in matches)


@pytest.mark.parametrize("length", (0, 1, 2, 3, 5, 6, 7, 10, 15, 16, 100, 271))
def test_truncated_headers_and_tree_are_invalid(length: int) -> None:
    data = (FIXTURES / "document.z").read_bytes()[:length]
    with pytest.raises(DecodeError, match="truncated") as error:
        decode(data)
    assert error.value.status == "invalid"
    assert error.value.regions


def test_wrong_signature_is_invalid() -> None:
    with pytest.raises(DecodeError, match="signature"):
        decode(b"invalid")


@pytest.mark.parametrize(
    "data,message",
    [
        (b"\x1f\x1e\0\0\0\1\0", "zero"),
        (b"\x1f\x1e\0\0\0\1\1\1", "oversubscribed"),
        (b"\x1f\x1e\0\0\0\1\2\0\0", "incomplete"),
        (b"\x1f\x1e\0\0\0\1\2\xff\1", "too many literals"),
    ],
)
def test_invalid_huffman_tree_is_rejected_before_helper(data: bytes, message: str) -> None:
    with pytest.raises(DecodeError, match=message) as error:
        decode(data)
    assert error.value.status == "invalid"


def test_code_length_above_backend_support_is_explicit() -> None:
    with pytest.raises(DecodeError) as error:
        decode(b"\x1f\x1e\0\0\0\1\x1a")
    assert error.value.status == "unsupported"


@pytest.mark.parametrize("mutation", ("size", "truncated-body"))
def test_helper_integrity_error_publishes_no_partial_output(gnu_gzip: str, mutation: str) -> None:
    data = bytearray((FIXTURES / "document.z").read_bytes())
    if mutation == "size":
        data[5] ^= 1
    else:
        data = data[:-1]
    with pytest.raises(DecodeError):
        decode(bytes(data))
    matches = analyzed(bytes(data))
    wrapper = next(match for match in matches if match.name == PACK_MIME)
    assert wrapper.analysis_status == "invalid"
    assert not any(match.name == "decoded_content" for match in matches)


def test_declared_output_limit_is_checked_before_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: None)
    with pytest.raises(DecodeError, match="declared") as error:
        decode((FIXTURES / "document.z").read_bytes(), max_output=len(PAYLOAD) - 1)
    assert error.value.status == "limited"


def test_exact_output_boundary_and_empty_zero_limit(gnu_gzip: str) -> None:
    assert decode((FIXTURES / "document.z").read_bytes(), max_output=len(PAYLOAD)).data == PAYLOAD
    assert decode((FIXTURES / "empty.z").read_bytes(), max_output=0).data == b""


@pytest.mark.parametrize(
    "field,value",
    [("max_depth", 0), ("max_members", 0), ("max_member_bytes", 1), ("max_total_bytes", 1)],
)
def test_configured_recursive_limits_are_explicit(gnu_gzip: str, field: str, value: int) -> None:
    matches = analyzed(FIXTURES / "document.z", AnalysisLimits(**{field: value}))
    wrapper = next(match for match in matches if match.name == PACK_MIME)
    assert wrapper.analysis_status == "limited"
    assert not any(match.name == "decoded_content" for match in matches)


def test_direct_member_allowance_zero_is_limited() -> None:
    with pytest.raises(DecodeError) as error:
        decode((FIXTURES / "empty.z").read_bytes(), max_members=0)
    assert error.value.status == "limited"


def test_missing_helper_preserves_signature_and_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("polyfile.gziphelper.shutil.which", lambda name: None)
    matches = analyzed(FIXTURES / "document.z")
    wrapper = next(match for match in matches if match.name == PACK_MIME)
    assert wrapper.analysis_status == "unsupported"
    assert any(match.name == "literals" for match in matches)
    assert not any(match.name == "decoded_content" for match in matches)


def test_arbitrary_octet_stream_data_is_not_decoded_as_pack() -> None:
    assert not any(match.name == PACK_MIME for match in analyzed(b"arbitrary\0binary\xffdata"))


@pytest.mark.skipif(sys.platform == "linux", reason="hard memory limit outside Linux")
def test_requested_hard_memory_ceiling_is_unsupported_outside_linux(gnu_gzip: str) -> None:
    matches = analyzed(FIXTURES / "document.z", AnalysisLimits(max_codec_memory=128 << 20))
    wrapper = next(match for match in matches if match.name == PACK_MIME)
    assert wrapper.analysis_status == "unsupported"
    assert wrapper.analysis_message is not None and "only on Linux" in wrapper.analysis_message


@pytest.mark.parametrize("signature", (b"\x1f\x1e", b"\x1f\x1f"))
def test_pack_alias_preserves_overlapping_afx_description(signature: bytes) -> None:
    with FileStream(signature + b"-afx-") as stream:
        descriptions = [str(match) for match in Matcher().identify(stream)]
    assert "AFX compressed file data" in descriptions
    assert len(descriptions) == 2


def test_explicit_generic_mime_filter_retains_original_pack_verdict() -> None:
    definitions = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes=("application/octet-stream",))
    matches = list(Matcher(matcher=definitions).match(FIXTURES / "document.z"))
    assert [match.name for match in matches] == ["application/octet-stream"]
    assert not any(match.name == "decoded_content" for match in matches)


def test_successful_helper_still_requires_exact_declared_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("polyfile.packmatcher.find_gnu_gzip", lambda **kwargs: sys.executable)
    monkeypatch.setattr("polyfile.packmatcher.run_helper", lambda *args, **kwargs: b"short")
    with pytest.raises(DecodeError, match="declared size") as error:
        decode((FIXTURES / "document.z").read_bytes())
    assert error.value.status == "invalid"
