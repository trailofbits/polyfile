"""Behavioral regressions for native SIMH detection and tape record structure."""

import struct
from io import BytesIO

import pytest

from polyfile import AnalysisLimits
from polyfile.fileutils import FileStream
from polyfile.magic import MagicMatcher
from polyfile.polyfile import Match, Matcher
from polyfile.simh import END_OF_MEDIUM, MIME_TYPE, SIMHTest, parse_simh


def record(payload: bytes, *, flags: int = 0) -> bytes:
    word = len(payload) | flags
    return (
        struct.pack("<I", word)
        + payload
        + b"\0" * (len(payload) & 1)
        + struct.pack("<I", word)
    )


def detected(data: bytes) -> bool:
    return any(
        MIME_TYPE in match.mimetypes
        for match in MagicMatcher.DEFAULT_INSTANCE.match(data)
    )


@pytest.mark.parametrize("payload", [b"DATA", b"odd", b"x", b"a" * 512])
def test_native_record_lengths(payload: bytes) -> None:
    assert detected(record(payload) + struct.pack("<II", 0, END_OF_MEDIUM))


@pytest.mark.parametrize("flags", [0, 0x80000000, 0x10000000, 0xF0000000])
def test_native_record_flags(flags: int) -> None:
    assert detected(record(b"DATA", flags=flags))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\0" * 64,
        struct.pack("<I", END_OF_MEDIUM),
        struct.pack("<II", 0, END_OF_MEDIUM),
        struct.pack("<I", 4) + b"DATA",
        struct.pack("<I", 4) + b"DATA" + struct.pack("<I", 6),
        record(b"DATA", flags=0x01000000),
    ],
)
def test_non_images(data: bytes) -> None:
    assert not detected(data)


def test_native_probe_reads_raw_bytes_and_paths(tmp_path) -> None:
    data = record(b"DATA") + struct.pack("<II", 0, END_OF_MEDIUM)
    path = tmp_path / "sample.tap"
    path.write_bytes(data)
    matcher = MagicMatcher([SIMHTest()])
    for value in (data, BytesIO(data), path):
        assert [str(match) for match in matcher.match(value)] == ["SIMH tape data"]


def test_native_detector_retains_other_classifications() -> None:
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(record(b'{"tape": true}')))
    assert any(MIME_TYPE in match.mimetypes for match in matches)


def test_later_truncation_retains_native_identification() -> None:
    assert detected(record(b"DATA") + struct.pack("<I", 128) + b"partial")


def test_invalid_later_trailer_rejects_native_identification() -> None:
    assert not detected(record(b"DATA") + struct.pack("<III", 4, 0, 8))


def parse(
    data: bytes, *, limits: AnalysisLimits | None = None, base: int = 0
) -> list[Match]:
    parent = Match(
        MIME_TYPE,
        None,
        relative_offset=base,
        length=len(data),
        matcher=Matcher(limits=limits),
    )
    with FileStream(data) as stream:
        return [parent, *parse_simh(stream, parent)]


def test_physical_record_and_marker_offsets() -> None:
    data = record(b"odd") + struct.pack("<II", 0, END_OF_MEDIUM) + b"extra"
    nodes = parse(data, base=23)
    positions = [(node.name, node.offset, node.length) for node in nodes[1:]]
    assert ("record", 23, 12) in positions
    assert ("record_payload", 27, 3) in positions
    assert ("word_padding", 30, 1) in positions
    assert ("record_trailer", 31, 4) in positions
    assert ("tape_mark", 35, 4) in positions
    assert ("end_of_medium", 39, 4) in positions
    assert ("trailing_data", 43, 5) in positions


def test_record_payload_json_recursion() -> None:
    payload = b'{"simh": true}'
    nodes = list(Matcher().match(record(payload) + struct.pack("<I", END_OF_MEDIUM)))
    json_nodes = [node for node in nodes if node.name == "application/json"]
    assert len(json_nodes) == 1
    assert json_nodes[0].offset == 4
    assert json_nodes[0].parent.name == "record_payload"


def test_fragments_are_not_joined_into_files() -> None:
    nodes = parse(record(b'{"fragment": ') + record(b"true}"))
    assert not any(node.name == "application/json" for node in nodes)


def test_unrecognized_record_remains_generic_data() -> None:
    nodes = parse(record(b"DATA"))
    payload = next(node for node in nodes if node.name == "record_payload")
    assert payload.children
    assert all(
        child.name in {"application/octet-stream", "text/plain"} for child in payload
    )


def test_error_flag_preserves_bytes_without_claiming_valid_payload() -> None:
    nodes = parse(record(b'{"damaged": true}', flags=0x80000000))
    payload = next(node for node in nodes if node.name == "record_payload")
    assert payload.analysis_status == "invalid"
    assert payload.children == ()


@pytest.mark.parametrize(
    "suffix",
    [
        b"x",
        struct.pack("<I", 8),
        struct.pack("<I", 3) + b"abc",
        struct.pack("<I", 3) + b"abc\0" + struct.pack("<I", 4),
        struct.pack("<I", 0x01000000),
    ],
)
def test_truncated_or_invalid_tail_retains_prior_structure(suffix: bytes) -> None:
    nodes = parse(record(b"DATA") + suffix)
    assert nodes[0].analysis_status == "invalid"
    assert any(node.name == "record_payload" and node.offset == 4 for node in nodes)
    assert nodes[-1].name == "invalid_record"
    assert nodes[-1].offset == 12


def test_all_zero_direct_parser_maps_markers_without_detecting_image() -> None:
    assert [node.name for node in parse(b"\0" * 8)[1:]] == [
        "tape_mark",
        "record_word",
        "tape_mark",
        "record_word",
    ]


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_member_bytes=2),
        AnalysisLimits(max_total_bytes=2),
    ],
)
def test_payload_limits_preserve_record(limits: AnalysisLimits) -> None:
    nodes = parse(record(b'{"bounded": true}'), limits=limits)
    payload = next(node for node in nodes if node.name == "record_payload")
    assert payload.analysis_status == "limited"
    assert payload.children == ()


def test_member_limit_counts_markers_and_records() -> None:
    nodes = parse(
        struct.pack("<I", 0) + record(b"DATA"), limits=AnalysisLimits(max_members=1)
    )
    assert nodes[0].analysis_status == "limited"
    assert [node.name for node in nodes[1:]] == ["tape_mark", "record_word"]


def test_unlimited_by_default() -> None:
    nodes = parse(record(b'{"unlimited": true}'))
    assert nodes[0].analysis_status is None
    assert any(node.name == "application/json" for node in nodes)


def test_nested_zip_payload_recursion() -> None:
    from zipfile import ZIP_DEFLATED, ZipFile

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("document.json", b'{"nested": true}')
    nodes = list(Matcher().match(record(buffer.getvalue())))
    assert any(node.name == "application/zip" for node in nodes)
    assert any(node.name == "application/json" for node in nodes)


def test_entry_budget_is_not_charged_twice_for_a_payload() -> None:
    nodes = parse(record(b'{"one": true}'), limits=AnalysisLimits(max_members=1))
    assert any(node.name == "application/json" for node in nodes)
    assert nodes[0].analysis_context.members == 1


def test_generic_record_bytes_consume_cumulative_budget() -> None:
    nodes = parse(
        record(b"DATA") + record(b"MORE"), limits=AnalysisLimits(max_total_bytes=4)
    )
    payloads = [node for node in nodes if node.name == "record_payload"]
    assert payloads[0].analysis_status is None
    assert payloads[1].analysis_status == "limited"
    assert nodes[0].analysis_context.total_bytes == 4
