"""ICO and universal Mach-O members retain bounded source ranges and shared limits."""

import base64
import gzip
from io import BytesIO
import struct
import tarfile
from typing import Literal

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.fileutils import FileStream
from polyfile.kaitaimatcher import LazyKaitaiParser
from polyfile.polyfile import Match, Matcher, Submatch
from tests.test_parser_coordinates import parser_parent, parser_stream
from tests.test_zipmatcher import PNG

Kind = Literal["ico", "fat"]
THIN = struct.pack(">IIIIIII", 0xFEEDFACE, 7, 3, 2, 0, 0, 0)
CASES: tuple[tuple[Kind, bytes, str, str, str], ...] = (
    ("ico", PNG, "image/vnd.microsoft.icon", "image/png", "Png"),
    ("fat", THIN, "application/x-mach-binary", "application/x-mach-binary", "MachO"),
)


def container_bytes(
    kind: Kind,
    payloads: list[bytes],
    *,
    ranges: list[tuple[int, int]] | None = None,
) -> bytes:
    count = len(payloads) if ranges is None else len(ranges)
    offset = (6 + count * 16) if kind == "ico" else (8 + count * 20)
    if ranges is None:
        ranges = []
        for payload in payloads:
            ranges.append((offset, len(payload)))
            offset += len(payload)
    if kind == "ico":
        header = struct.pack("<HHH", 0, 1, count)
        table = b"".join(
            struct.pack("<BBBBHHII", 1, 1, 0, 0, 1, 32, size, start) for start, size in ranges
        )
    else:
        header = struct.pack(">II", 0xCAFEBABE, count)
        table = b"".join(struct.pack(">IIIII", 7, 3, start, size, 2) for start, size in ranges)
    return header + table + b"".join(payloads)


def members(nodes: list[Match], mimetype: str) -> list[Match]:
    return [
        node
        for node in nodes
        if not isinstance(node, Submatch)
        and node.name == mimetype
        and node.parent is not None
        and node.parent.name in ("img", "object")
    ]


def parsed_nodes(kind: Kind, data: bytes) -> list[Match]:
    path = "image/ico.ksy" if kind == "ico" else "executable/mach_o_fat.ksy"
    parent = Match("container", None, length=len(data), matcher=Matcher())
    with FileStream(data) as stream:
        return [parent, *LazyKaitaiParser(path, "container")(stream, parent)]


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
def test_members_are_classified_and_parsed_beneath_their_entries(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
) -> None:
    data = container_bytes(kind, [payload])
    nodes = list(Matcher().match(data))
    container = next(node for node in nodes if node.name == outer and node.parent is None)
    (member,) = members(nodes, inner)
    assert member.parent is not None and member.parent.parent is not None
    assert member.parent.name == ("img" if kind == "ico" else "object")
    assert member.parent.parent.name == ("images[0]" if kind == "ico" else "fat_archs[0]")
    assert (member.offset, member.length) == (len(data) - len(payload), len(payload))
    assert member.source == container.source == "file"
    parsed = next(node for node in member.children if node.name == root)
    assert len(parsed.children) > 1
    if kind == "ico":
        assert parsed.img_data is not None
        assert base64.b64decode(parsed.img_data.split(",", 1)[1]) == payload
    else:
        fields = {node.name: node.match for node in member.parent.parent.children}
        assert fields["cpu_type"] == struct.pack(">I", 7)
        assert fields["cpu_subtype"] == struct.pack(">I", 3)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
def test_multiple_members_keep_independent_boundaries(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
) -> None:
    data = container_bytes(kind, [payload, payload])
    nodes = list(Matcher().match(data))
    found = members(nodes, inner)
    start = len(data) - 2 * len(payload)
    assert [(node.offset, node.length) for node in found] == [
        (start, len(payload)),
        (start + len(payload), len(payload)),
    ]
    assert found[0].analysis_context.members == 2
    assert found[0].analysis_context.total_bytes == 2 * len(payload)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("overlap", [False, True])
def test_repeated_or_overlapping_ranges_are_not_analyzed_twice(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    overlap: bool,
) -> None:
    start = 38 if kind == "ico" else 48
    second = (start + 1, len(payload) - 1) if overlap else (start, len(payload))
    data = container_bytes(kind, [payload], ranges=[(start, len(payload)), second])
    nodes = list(Matcher().match(data))
    assert len(members(nodes, inner)) == 1
    rejected = next(node for node in nodes if node.analysis_status == "unsupported")
    assert rejected.name.endswith("[1]")
    assert rejected.analysis_message is not None and "overlapping" in rejected.analysis_message
    assert rejected.analysis_context.members == 1


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
def test_directory_order_can_differ_from_payload_order(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
) -> None:
    start = 38 if kind == "ico" else 48
    ranges = [(start + len(payload), len(payload)), (start, len(payload))]
    nodes = parsed_nodes(kind, container_bytes(kind, [payload, payload], ranges=ranges))
    assert [node.offset for node in members(nodes, inner)] == [ranges[0][0], ranges[1][0]]


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("bad_range", [(0, 1), (0xFFFFFFFF, 1), (22, 0), (22, 0xFFFFFFFF)])
def test_malformed_ranges_retain_their_directory_entries(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    bad_range: tuple[int, int],
) -> None:
    data = container_bytes(kind, [payload], ranges=[bad_range])
    nodes = parsed_nodes(kind, data)
    assert not members(nodes, inner)
    entry = next(node for node in nodes if node.name.endswith("[0]"))
    assert entry.analysis_status == "invalid"
    assert entry.children
    assert all(0 <= node.offset <= node.offset + node.length <= len(data) for node in nodes)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
def test_truncated_members_retain_their_entry_fields(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
) -> None:
    nodes = list(Matcher().match(container_bytes(kind, [payload])[:-1]))
    entry = next(node for node in nodes if node.name.endswith("[0]"))
    assert entry.analysis_status == "invalid"
    assert entry.children
    assert not members(nodes, inner)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("truncation", [4, 5, 12, 30])
def test_truncated_directories_keep_available_framing(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    truncation: int,
) -> None:
    data = container_bytes(kind, [payload, payload])[:truncation]
    path = "image/ico.ksy" if kind == "ico" else "executable/mach_o_fat.ksy"
    parent = Match(outer, None, length=len(data), matcher=Matcher())
    with FileStream(data) as stream:
        nodes = list(LazyKaitaiParser(path, outer)(stream, parent))
    assert parent.analysis_status == "invalid"
    assert nodes[0].name == "header"
    assert nodes[0].match == data[: nodes[0].length]
    assert any(node.name in ("images", "fat_archs") for node in nodes)
    assert all(0 <= node.offset <= node.offset + node.length <= len(data) for node in nodes)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_members=0),
        AnalysisLimits(max_member_bytes=0),
        AnalysisLimits(max_total_bytes=0),
    ],
)
def test_refused_members_keep_framing_without_classification(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    limits: AnalysisLimits,
) -> None:
    nodes = list(Matcher(limits=limits).match(container_bytes(kind, [payload])))
    assert not members(nodes, inner)
    region = next(node for node in nodes if node.name in ("img", "object"))
    assert region.analysis_status == "limited"
    assert region.parent is not None and region.parent.children
    assert region.decoded is None


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
def test_exact_boundaries_charge_only_payload_bytes(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
) -> None:
    limits = AnalysisLimits(
        max_depth=1,
        max_members=1,
        max_member_bytes=len(payload),
        max_total_bytes=len(payload),
    )
    nodes = list(Matcher(limits=limits).match(container_bytes(kind, [payload])))
    (member,) = members(nodes, inner)
    assert any(node.name == root for node in member.children)
    assert member.analysis_context.members == 1
    assert member.analysis_context.total_bytes == len(payload)
    assert not any(node.analysis_status == "limited" for node in nodes)


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("limit", ["bytes", "members"])
def test_members_share_one_analysis_budget(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    limit: str,
) -> None:
    limits = (
        AnalysisLimits(max_total_bytes=len(payload))
        if limit == "bytes"
        else (AnalysisLimits(max_members=1))
    )
    nodes = list(Matcher(limits=limits).match(container_bytes(kind, [payload, payload])))
    assert len(members(nodes, inner)) == 1
    assert sum(node.analysis_status == "limited" for node in nodes) == 1


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("decoded", [False, True])
@pytest.mark.parametrize("backing_base", [0, 37])
def test_members_use_parent_source_coordinates_through_nested_views(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    decoded: bool,
    backing_base: int,
) -> None:
    data = container_bytes(kind, [payload])
    parent = parser_parent(data, 117, decoded)
    parent.matcher = Matcher()
    path = "image/ico.ksy" if kind == "ico" else "executable/mach_o_fat.ksy"
    with parser_stream(data, backing_base, True) as stream:
        nodes = list(LazyKaitaiParser(path, outer)(stream, parent))
    (member,) = members(nodes, inner)
    assert member.offset == 117 + len(data) - len(payload)
    assert member.source == parent.source
    parsed = next(node for node in member.children if node.name == root)
    assert parsed.offset == member.offset
    assert parsed.source == parent.source
    assert parsed.match == payload


@pytest.mark.parametrize(("kind", "payload", "outer", "inner", "root"), CASES, ids=("ico", "fat"))
@pytest.mark.parametrize("compressed", [False, True])
def test_members_inside_physical_and_decoded_tar_containers(
    kind: Kind,
    payload: bytes,
    outer: str,
    inner: str,
    root: str,
    *,
    compressed: bool,
) -> None:
    data = container_bytes(kind, [payload])
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        entry = tarfile.TarInfo("nested")
        entry.size = len(data)
        archive.addfile(entry, BytesIO(data))
    archive_data = output.getvalue()
    nodes = list(Matcher().match(gzip.compress(archive_data) if compressed else archive_data))
    (member,) = members(nodes, inner)
    assert member.offset == 512 + len(data) - len(payload)
    assert member.source.startswith("decoded:") if compressed else member.source == "file"
    assert any(node.name == root for node in member.children)


def test_nested_universal_members_are_not_deduplicated_by_mime() -> None:
    data = container_bytes("fat", [container_bytes("fat", [THIN])])
    nodes = list(Matcher().match(data))
    found = members(nodes, "application/x-mach-binary")
    assert [(node.offset, node.length, node.analysis_depth) for node in found] == [
        (28, len(THIN) + 28, 1),
        (56, len(THIN), 2),
    ]


def test_cpu_types_and_subtypes_remain_distinct_for_each_architecture() -> None:
    arm = struct.pack(">IIIIIII", 0xFEEDFACE, 12, 9, 2, 0, 0, 0)
    data = bytearray(container_bytes("fat", [THIN, arm]))
    data[28:36] = struct.pack(">II", 12, 9)
    nodes = list(Matcher().match(bytes(data)))
    architectures = [node for node in nodes if node.name.startswith("fat_archs[")]
    labels = [
        {child.name: child.match for child in architecture.children}
        for architecture in architectures
    ]
    assert [label["cpu_type"] for label in labels] == [struct.pack(">I", 7), struct.pack(">I", 12)]
    assert [label["cpu_subtype"] for label in labels] == [
        struct.pack(">I", 3),
        struct.pack(">I", 9),
    ]
    assert len(members(nodes, "application/x-mach-binary")) == 2


@pytest.mark.parametrize("payload", [struct.pack("<I", 40) + bytes(36), b"not a PNG"])
def test_ico_dib_and_other_non_png_payloads_are_not_complete_bmp_files(payload: bytes) -> None:
    nodes = list(Matcher().match(container_bytes("ico", [payload])))
    region = next(node for node in nodes if node.name == "img")
    assert region.analysis_status == "unsupported"
    assert not region.children
    assert not any(node.name == "image/bmp" for node in nodes)


@pytest.mark.parametrize("kind", ["ico", "fat"])
def test_empty_directories_have_no_recursive_members(kind: Kind) -> None:
    data = container_bytes(kind, [])
    path = "image/ico.ksy" if kind == "ico" else "executable/mach_o_fat.ksy"
    parent = Match("container", None, length=len(data), matcher=Matcher())
    with FileStream(data) as stream:
        nodes = list(LazyKaitaiParser(path, "container")(stream, parent))
    assert not any(node.name in ("img", "object") for node in nodes)
    assert parent.analysis_context.members == 0
