"""LRZIP reference archives, recursive analysis, and explicit failure behavior."""

import contextlib
import io
import json
import os
import sys
from hashlib import md5, sha256
from pathlib import Path

import pytest

from polyfile import AnalysisLimits
from polyfile.__main__ import main
from polyfile.compression import DecodeError, DecodeResult
from polyfile.fileutils import FileStream
from polyfile.lrzipmatcher import decode_lrzip, find_lrzip
from polyfile.polyfile import Match, Matcher

FIXTURES = Path(__file__).parent / "fixtures" / "lrzip"
PAYLOAD = (FIXTURES / "document.json").read_bytes()
PROVENANCE = json.loads((FIXTURES / "provenance.json").read_text())
DOCUMENT = (FIXTURES / "document.json-0.7-none.lrz").read_bytes()


@pytest.fixture
def lrzip() -> str:
    try:
        return find_lrzip(helper_timeout=5)
    except DecodeError as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"CI requires its pinned LRZIP reference decoder: {error}")
        pytest.skip(str(error))


def decode(
    data: bytes, *, helper_timeout: float | None = None, **limits: int | None
) -> DecodeResult:
    with FileStream(data) as stream:
        return decode_lrzip(stream, helper_timeout=helper_timeout, **limits)


def analyzed(data: bytes | Path, limits: AnalysisLimits | None = None) -> list[Match]:
    return list(Matcher(limits=limits).match(data))


def replace(data: bytes, offset: int, value: bytes) -> bytes:
    end = offset + len(value)
    return data[:offset] + value + data[end:]


@pytest.mark.parametrize("item", PROVENANCE, ids=lambda item: item["fixture"])
def test_real_archives_round_trip_with_verified_provenance(
    lrzip: str, item: dict
) -> None:
    encoded = (FIXTURES / item["fixture"]).read_bytes()
    expected = (FIXTURES / item["payload"]).read_bytes()
    assert sha256(encoded).hexdigest() == item["encoded_sha256"]
    assert sha256(expected).hexdigest() == item["decoded_sha256"]
    assert decode(encoded, helper_timeout=5).data == expected


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_physical_framing_and_chunk_capacity(lrzip: str, version: str) -> None:
    data = (FIXTURES / f"archive.tar-{version}-none.lrz").read_bytes()
    result = decode(data)
    header, body, digest = result.regions
    assert (header.name, header.offset, header.length) == ("lrzip_header", 0, 24)
    fields = [(child.name, child.offset, child.length) for child in header.children]
    if version == "0.6":
        assert ("unused_14_15", 14, 2) in fields
        assert ("unused_23", 23, 1) in fields
        assert not any(name in ("streaming", "last_block") for name, _, _ in fields)
    else:
        assert ("streaming", 14, 1) in fields
        assert ("reserved", 15, 1) in fields
        assert ("last_block", 23, 1) in fields
    assert (body.name, body.offset, body.length) == ("lrzip_body", 24, len(data) - 40)
    capacity = body.children[0].children[-1]
    assert capacity.name == "chunk_capacity"
    assert isinstance(capacity.value, int)
    assert capacity.value >= len(result.data)
    assert (digest.name, digest.offset, digest.length) == ("md5", len(data) - 16, 16)


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_unknown_size_archive_and_exact_output_limit(lrzip: str, version: str) -> None:
    data = (FIXTURES / f"document.json-{version}-none.lrz").read_bytes()
    unknown = replace(data, 6, bytes(8))
    assert decode(unknown, max_output=len(PAYLOAD)).data == PAYLOAD
    with pytest.raises(DecodeError) as error:
        decode(unknown, max_output=len(PAYLOAD) - 1)
    assert error.value.status == "limited"


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_json_decoding_uses_separate_source(lrzip: str, version: str) -> None:
    matches = analyzed(FIXTURES / f"document.json-{version}-none.lrz")
    wrapper = next(match for match in matches if match.name == "application/x-lrzip")
    decoded = next(match for match in matches if match.name == "decoded_content")
    document = next(match for match in matches if match.name == "application/json")
    assert wrapper.source == "file"
    assert decoded.parent is wrapper
    assert decoded.source == document.source == "decoded:0"
    assert decoded.decoded == PAYLOAD
    assert (document.offset, document.length) == (0, len(PAYLOAD))
    assert wrapper.analysis_context.members == 1


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_tar_payload_recursively_scans_json(lrzip: str, version: str) -> None:
    matches = analyzed(FIXTURES / f"archive.tar-{version}-lzma.lrz")
    archive = next(match for match in matches if match.name == "application/x-tar")
    document = next(match for match in matches if match.name == "application/json")
    assert archive.source == document.source == "decoded:0"
    assert (document.offset, document.length) == (512, len(PAYLOAD))


def test_raw_bytes_path_and_cli_share_decoding(lrzip: str) -> None:
    path = FIXTURES / "document.json-0.7-lzma.lrz"
    assert [(m.name, m.source, m.offset) for m in analyzed(path)] == [
        (m.name, m.source, m.offset) for m in analyzed(path.read_bytes())
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
                "5",
                str(path),
            ]
        )
    pending = json.loads(output.getvalue())["struc"]
    documents = []
    while pending:
        element = pending.pop()
        if element["type"] == "application/json":
            documents.append(element)
        pending.extend(element["subEls"])
    assert [(item["source"], item["offset"]) for item in documents] == [
        ("decoded:0", 0)
    ]


@pytest.mark.parametrize("length", (1, 4, 23, 24, 25, 26, 39))
def test_truncated_framing_is_invalid_without_helper(length: int) -> None:
    with pytest.raises(DecodeError) as error:
        decode(DOCUMENT[:length])
    assert error.value.status == "invalid"
    assert error.value.regions


@pytest.mark.parametrize(
    "offset,value,status",
    [
        (0, b"NOPE", "invalid"),
        (4, b"\x01", "unsupported"),
        (5, b"\x05", "unsupported"),
        (5, b"\x08", "unsupported"),
        (6, b"\xff" * 8, "invalid"),
        (14, b"\x02", "invalid"),
        (15, b"\x01", "invalid"),
        (21, b"\x02", "invalid"),
        (22, b"\x01", "unsupported"),
        (22, b"\x03", "unsupported"),
        (23, b"\x02", "invalid"),
        (23, b"\x00", "invalid"),
        (24, b"\x00", "invalid"),
        (24, b"\x09", "invalid"),
        (25, b"\x03", "invalid"),
        (26, b"\x02", "invalid"),
    ],
)
def test_invalid_and_unsupported_headers_precede_helper_discovery(
    monkeypatch: pytest.MonkeyPatch, offset: int, value: bytes, status: str
) -> None:
    def forbidden(**kwargs: object) -> str:
        pytest.fail("invalid or unsupported framing must precede helper discovery")

    monkeypatch.setattr("polyfile.lrzipmatcher.find_lrzip", forbidden)
    with pytest.raises(DecodeError) as error:
        decode(replace(DOCUMENT, offset, value))
    assert error.value.status == status
    assert error.value.regions


def test_streaming_flag_disagreement_is_invalid() -> None:
    data = replace(replace(DOCUMENT, 14, b"\x01"), 26, b"\x00")
    with pytest.raises(DecodeError, match="disagree"):
        decode(data)


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_corrupt_integrity_and_truncated_body_have_no_decoded_child(
    lrzip: str, version: str
) -> None:
    data = (FIXTURES / f"document.json-{version}-none.lrz").read_bytes()
    corruptions = [replace(data, len(data) - 1, bytes([data[-1] ^ 1])), data[:-20]]
    for corrupted in corruptions:
        matches = analyzed(corrupted, AnalysisLimits(helper_timeout=5))
        wrapper = next(
            match for match in matches if match.name == "application/x-lrzip"
        )
        assert wrapper.analysis_status == "invalid"
        assert wrapper.analysis_message
        assert not any(match.name == "decoded_content" for match in matches)


def test_invalid_backward_reference_is_rejected(lrzip: str) -> None:
    data = (FIXTURES / "repeated.json-0.7-none.lrz").read_bytes()
    width = data[24]
    initial = 27 + width
    pointer_start, pointer_end = initial + 1 + 2 * width, initial + 1 + 3 * width
    next_header = int.from_bytes(data[pointer_start:pointer_end], "little")
    tokens = initial + next_header + 1 + 3 * width
    token_end = tokens + 6
    assert data[tokens:token_end] == b"\x00\x27\x00\x01\xff\xff"
    corrupted = replace(data, tokens + 6, b"\xff" * width)
    with pytest.raises(DecodeError, match="Match offset|corrupt") as error:
        decode(corrupted, helper_timeout=5, max_output=220000)
    assert error.value.status == "invalid"


@pytest.mark.parametrize("limit", (0, len(PAYLOAD) - 1))
def test_known_size_preflights_output_before_helper(
    monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    monkeypatch.setattr("polyfile.lrzipmatcher.shutil.which", lambda name: None)
    with pytest.raises(DecodeError) as error:
        decode(DOCUMENT, max_output=limit)
    assert error.value.status == "limited"


def test_empty_and_member_budget_do_not_attempt_an_archive() -> None:
    for data, allowance, status in ((b"", None, "invalid"), (DOCUMENT, 0, "limited")):
        with pytest.raises(DecodeError) as error:
            decode(data, max_members=allowance)
        assert (error.value.status, error.value.member_count) == (status, 0)


@pytest.mark.parametrize(
    "field", ("max_depth", "max_members", "max_total_bytes", "max_member_bytes")
)
def test_recursive_limits_preserve_wrapper(lrzip: str, field: str) -> None:
    matches = analyzed(DOCUMENT, AnalysisLimits(**{field: 0}))
    wrapper = next(match for match in matches if match.name == "application/x-lrzip")
    assert wrapper.analysis_status == "limited"
    assert not any(match.name == "decoded_content" for match in matches)


def test_missing_helper_retains_framing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("polyfile.lrzipmatcher.shutil.which", lambda name: None)
    matches = analyzed(DOCUMENT)
    wrapper = next(match for match in matches if match.name == "application/x-lrzip")
    assert wrapper.analysis_status == "unsupported"
    assert "0.7.3" in str(wrapper.analysis_message)
    assert any(match.name == "lrzip_header" for match in matches)
    assert not any(match.name == "decoded_content" for match in matches)


@pytest.mark.parametrize(
    "banner", (b"lrzip version 0.7.2\n", b"lrzip version 0.651\n", b"gzip 1.15\n")
)
def test_incompatible_helper_is_explicit(
    monkeypatch: pytest.MonkeyPatch, banner: bytes
) -> None:
    monkeypatch.setattr(
        "polyfile.lrzipmatcher.shutil.which", lambda name: sys.executable
    )
    monkeypatch.setattr(
        "polyfile.lrzipmatcher.run_helper", lambda *args, **kwargs: banner
    )
    with pytest.raises(DecodeError) as error:
        find_lrzip()
    assert error.value.status == "unsupported"


def test_fixed_helper_invocations_disable_inherited_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands = []

    def helper(stream: FileStream, command: tuple[str, ...], **kwargs: object) -> bytes:
        commands.append(command)
        assert kwargs["environment"] == {"LRZIP": "NOCONFIG"}
        if command[1:] == ("--version",):
            return b"lrzip version 0.7.3\n"
        assert stream.read() == DOCUMENT
        assert kwargs["max_output"] is None
        assert kwargs["max_memory"] is None
        return PAYLOAD

    monkeypatch.setattr(
        "polyfile.lrzipmatcher.shutil.which", lambda name: sys.executable
    )
    monkeypatch.setattr("polyfile.lrzipmatcher.run_helper", helper)
    assert decode(DOCUMENT).data == PAYLOAD
    assert commands == [
        (str(Path(sys.executable).resolve()), "--version"),
        (str(Path(sys.executable).resolve()), "-Q", "-d", "-o", "-", "-p", "1"),
    ]


@pytest.mark.parametrize(
    "payload,message", ((b"short", "size mismatch"), (b"x" * len(PAYLOAD), "MD5"))
)
def test_successful_helper_still_requires_size_and_digest(
    monkeypatch: pytest.MonkeyPatch, payload: bytes, message: str
) -> None:
    monkeypatch.setattr(
        "polyfile.lrzipmatcher.find_lrzip", lambda **kwargs: sys.executable
    )
    monkeypatch.setattr(
        "polyfile.lrzipmatcher.run_helper", lambda *args, **kwargs: payload
    )
    with pytest.raises(DecodeError, match=message):
        decode(DOCUMENT)


def test_helper_query_timeout_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> bytes:
        raise DecodeError("version query timeout", status="limited")

    monkeypatch.setattr(
        "polyfile.lrzipmatcher.shutil.which", lambda name: sys.executable
    )
    monkeypatch.setattr("polyfile.lrzipmatcher.run_helper", timeout)
    with pytest.raises(DecodeError) as error:
        find_lrzip(helper_timeout=0.1)
    assert error.value.status == "limited"


def test_requested_memory_ceiling_is_applied_or_explicitly_unsupported(
    lrzip: str,
) -> None:
    with pytest.raises(DecodeError) as error:
        decode(DOCUMENT, max_memory=1, helper_timeout=5)
    assert error.value.status == (
        "limited" if sys.platform == "linux" else "unsupported"
    )
    assert error.value.regions


def test_legacy_crc_only_integrity_variant(lrzip: str) -> None:
    data = (FIXTURES / "document.json-0.6-none.lrz").read_bytes()
    crc_only = replace(data[:-16], 21, b"\x00")
    result = decode(crc_only)
    assert result.data == PAYLOAD
    assert [region.name for region in result.regions] == ["lrzip_header", "lrzip_body"]
    width = data[24]
    initial = 26 + width
    pointer_start, pointer_end = initial + 1 + 2 * width, initial + 1 + 3 * width
    actual = initial + int.from_bytes(data[pointer_start:pointer_end], "little")
    token_start = actual + 1 + 3 * width
    crc_start = token_start + 6
    corrupted = replace(crc_only, crc_start, bytes([crc_only[crc_start] ^ 1]))
    with pytest.raises(DecodeError, match="CRC|checksum"):
        decode(corrupted, helper_timeout=5)


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_known_size_mismatch_is_invalid(lrzip: str, version: str) -> None:
    data = (FIXTURES / f"document.json-{version}-none.lrz").read_bytes()
    for size in (len(PAYLOAD) - 1, len(PAYLOAD) + 1):
        with pytest.raises(DecodeError) as error:
            decode(replace(data, 6, size.to_bytes(8, "little")), helper_timeout=5)
        assert error.value.status == "invalid"


def test_decode_timeout_retains_framing_without_partial_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> bytes:
        raise DecodeError("decoder timed out", status="limited")

    monkeypatch.setattr(
        "polyfile.lrzipmatcher.find_lrzip", lambda **kwargs: sys.executable
    )
    monkeypatch.setattr("polyfile.lrzipmatcher.run_helper", timeout)
    matches = analyzed(DOCUMENT, AnalysisLimits(helper_timeout=0.01))
    wrapper = next(match for match in matches if match.name == "application/x-lrzip")
    assert wrapper.analysis_status == "limited"
    assert wrapper.analysis_context.members == 1
    assert any(match.name == "lrzip_header" for match in matches)
    assert not any(match.name == "decoded_content" for match in matches)


@pytest.mark.parametrize("version", ("0.6", "0.7"))
def test_valid_empty_archives_accept_zero_output_limit(
    lrzip: str, version: str
) -> None:
    data = (FIXTURES / f"empty-{version}.lrz").read_bytes()
    result = decode(data, max_output=0, max_members=1)
    assert result.data == b""
    assert result.member_count == 1


@pytest.mark.parametrize("offset", (14, 15, 23))
def test_legacy_unused_header_bytes_are_not_modern_flags(
    lrzip: str, offset: int
) -> None:
    data = (FIXTURES / "document.json-0.6-none.lrz").read_bytes()
    assert decode(replace(data, offset, b"\x55")).data == PAYLOAD


def continuation_archive() -> bytes:
    """Join genuine 0.7 chunk bodies with an LRZC header and whole-archive digest."""
    header = bytearray(DOCUMENT[:24])
    payload = PAYLOAD * 2
    header[6:14] = len(payload).to_bytes(8, "little")
    header[14], header[23] = 1, 0
    first = bytearray(DOCUMENT[24:-16])
    first[2] = 0
    second = DOCUMENT[24:-16]
    continuation = (
        b"LRZC"
        + len(PAYLOAD).to_bytes(8, "little")
        + len(second).to_bytes(8, "little")
        + b"\x01\x00\x00\x00"
    )
    return (
        bytes(header)
        + bytes(first)
        + continuation
        + second
        + md5(payload, usedforsecurity=False).digest()
    )


def test_streaming_continuation_chunks_are_one_archive(lrzip: str) -> None:
    data = continuation_archive()
    result = decode(data, max_members=1, max_output=2 * len(PAYLOAD), helper_timeout=5)
    assert result.data == PAYLOAD * 2
    assert result.member_count == 1
    with pytest.raises(DecodeError) as error:
        decode(data, max_output=2 * len(PAYLOAD) - 1)
    assert error.value.status == "limited"


@pytest.mark.parametrize("relative_offset", (0, 20, 21))
def test_corrupt_continuation_headers_are_invalid(
    lrzip: str, relative_offset: int
) -> None:
    data = continuation_archive()
    offset = data.index(b"LRZC") + relative_offset
    corrupted = replace(data, offset, bytes([data[offset] ^ 0x80]))
    with pytest.raises(DecodeError) as error:
        decode(corrupted, helper_timeout=5)
    assert error.value.status == "invalid"
