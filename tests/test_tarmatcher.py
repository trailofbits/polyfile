"""TAR detection, physical mapping, and recursive content regressions for #3618."""

import tarfile
import zipfile
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest

from polyfile import AnalysisLimits
from polyfile.fileutils import FileStream
from polyfile.magic import MagicMatcher, MatchContext
from polyfile.polyfile import Match, Matcher
from polyfile.tarmatcher import TarMatcher, parse_tar

JSON = b'{"tar_member": true}'


def archive_bytes(
    *,
    members: list[tuple[tarfile.TarInfo, bytes]] | None = None,
    format: int = tarfile.USTAR_FORMAT,
) -> bytes:
    if members is None:
        info = tarfile.TarInfo("document.json")
        info.size = len(JSON)
        members = [(info, JSON)]
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=format) as archive:
        for info, data in members:
            archive.addfile(info, BytesIO(data))
    return output.getvalue()


def update_checksum(data: bytes | bytearray) -> bytes:
    result = bytearray(data)
    result[148:156] = b" " * 8
    result[148:156] = f"{sum(result[:512]):06o}\0 ".encode()
    return bytes(result)


def native_matches(data: bytes | bytearray, variant: str) -> bool:
    return bool(TarMatcher(variant).test(bytes(data), 0, None))


def parsed(
    data: bytes | bytearray,
    *,
    limits: AnalysisLimits | None = None,
    parent_offset: int = 0,
) -> tuple[Match, list[Match]]:
    matcher = Matcher(limits=limits)
    parent = Match("application/x-tar", None, parent_offset, len(data), matcher=matcher)
    with FileStream(bytes(data)) as stream:
        matches = list(parse_tar(stream, parent))
    return parent, matches


def descendants(parent: Match) -> Iterator[Match]:
    for child in parent:
        yield child
        yield from descendants(child)


@pytest.mark.parametrize(
    ("format", "variant"),
    [
        (tarfile.USTAR_FORMAT, "POSIX"),
        (tarfile.GNU_FORMAT, "GNU"),
    ],
)
def test_native_tar_variants(format: int, variant: str) -> None:
    assert native_matches(archive_bytes(format=format), variant)


def test_native_v7_header() -> None:
    data = bytearray(archive_bytes())
    data[257:512] = bytes(255)
    assert native_matches(update_checksum(data), "V7")


def test_control_byte_filename_is_detected() -> None:
    data = bytearray(archive_bytes())
    data[0] = 1
    assert native_matches(update_checksum(data), "POSIX")


@pytest.mark.parametrize("data", [b"", bytes(511), bytes(512), b" " * 512])
def test_native_rejects_non_headers(data: bytes) -> None:
    assert not any(native_matches(data, kind) for kind in ("V7", "POSIX", "GNU"))


def test_bad_checksum_is_not_a_native_match() -> None:
    data = bytearray(archive_bytes())
    data[0] ^= 1
    assert not native_matches(data, "POSIX")


@pytest.mark.parametrize("field", [b"        ", b"9999999\0", b"00000x\0 "])
def test_invalid_checksum_field_is_rejected(field: bytes) -> None:
    data = bytearray(archive_bytes())
    data[148:156] = field
    assert not native_matches(data, "POSIX")


def test_gpkg_native_exception_keeps_specialized_classification() -> None:
    info = tarfile.TarInfo("package/gpkg-1")
    data = archive_bytes(members=[(info, b"")])
    assert not native_matches(data, "POSIX")
    context = MatchContext(data, only_match_mime=True)
    mimetypes = {
        mime
        for match in MagicMatcher.DEFAULT_INSTANCE.match(context)
        for mime in match.mimetypes
    }
    assert "application/vnd.gentoo.gpkg" in mimetypes
    parent, _ = parsed(data)
    assert any(child.name == "TarMember" for child in parent)


def test_recursive_json_has_physical_offset() -> None:
    parent, _ = parsed(archive_bytes(), parent_offset=123)
    nested = [node for node in descendants(parent) if node.name == "application/json"]
    assert nested
    assert nested[0].offset == 123 + 512
    assert nested[0].length == len(JSON)
    assert nested[0].parent is not None
    assert nested[0].parent.name == "data"


@pytest.mark.parametrize("size", [0, 1, 511, 512, 513])
def test_data_padding_and_next_header_boundaries(size: int) -> None:
    first = tarfile.TarInfo("first.bin")
    first.size = size
    second = tarfile.TarInfo("second.json")
    second.size = len(JSON)
    parent, _ = parsed(archive_bytes(members=[(first, b"x" * size), (second, JSON)]))
    members = [node for node in parent if node.name == "TarMember"]
    assert len(members) == 2
    assert members[1].offset == 512 + (size + 511) // 512 * 512
    assert next(node for node in members[0] if node.name == "data").length == size
    assert parent.analysis_status is None


def test_header_fields_cover_exactly_512_bytes() -> None:
    parent, _ = parsed(archive_bytes())
    header = next(node for node in descendants(parent) if node.name == "TarHeader")
    assert sum(field.length for field in header) == 512
    assert header.children[0].offset == header.offset
    assert (
        header.children[-1].offset + header.children[-1].length == header.offset + 512
    )


def test_nested_tar_and_zip_members_are_recursively_analyzed() -> None:
    zipped = BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("payload.json", JSON)
    info = tarfile.TarInfo("nested.zip")
    info.size = len(zipped.getvalue())
    inner = archive_bytes(members=[(info, zipped.getvalue())])
    outer = tarfile.TarInfo("nested.tar")
    outer.size = len(inner)
    parent, _ = parsed(archive_bytes(members=[(outer, inner)]))
    types = {node.name for node in descendants(parent)}
    assert {"application/x-tar", "application/zip", "application/json"} <= types


@pytest.mark.parametrize(
    "format", [tarfile.USTAR_FORMAT, tarfile.GNU_FORMAT, tarfile.PAX_FORMAT]
)
def test_long_names_preserve_physical_extension_records(format: int) -> None:
    name = "directory/" * 12 + "document.json"
    info = tarfile.TarInfo(name)
    info.size = len(JSON)
    parent, _ = parsed(archive_bytes(members=[(info, JSON)], format=format))
    members = [node for node in parent if node.name == "TarMember"]
    assert members[-1].match == repr(name)
    assert any(node.name == "application/json" for node in descendants(parent))
    assert members[-1].offset == (0 if format == tarfile.USTAR_FORMAT else 1024)


def test_pax_global_and_local_names() -> None:
    output = BytesIO()
    with tarfile.open(
        fileobj=output,
        mode="w",
        format=tarfile.PAX_FORMAT,
        pax_headers={"path": "global.json"},
    ) as archive:
        for name, path in (("one", "local.json"), ("two", None)):
            info = tarfile.TarInfo(name)
            info.size = len(JSON)
            if path:
                info.pax_headers = {"path": path}
            archive.addfile(info, BytesIO(JSON))
    parent, _ = parsed(output.getvalue())
    names = [node.match for node in parent if node.name == "TarMember"]
    assert repr("local.json") in names
    assert repr("global.json") in names


@pytest.mark.parametrize(
    "kind",
    [
        tarfile.DIRTYPE,
        tarfile.SYMTYPE,
        tarfile.LNKTYPE,
        tarfile.FIFOTYPE,
        tarfile.CHRTYPE,
    ],
)
def test_nonregular_members_do_not_recurse_or_follow_links(
    kind: bytes, tmp_path: Path
) -> None:
    victim = tmp_path / "outside.json"
    victim.write_bytes(JSON)
    info = tarfile.TarInfo("../../outside.json")
    info.type = kind
    info.linkname = str(victim)
    parent, _ = parsed(archive_bytes(members=[(info, b"")], format=tarfile.PAX_FORMAT))
    data_nodes = [node for node in descendants(parent) if node.name == "data"]
    assert data_nodes
    assert not any(node.children for node in data_nodes)
    assert victim.read_bytes() == JSON


def test_empty_tar_parser_maps_end_markers() -> None:
    parent, _ = parsed(archive_bytes(members=[]))
    assert parent.children[0].name == "end_markers"
    assert parent.children[0].length == 1024
    assert parent.analysis_status is None


@pytest.mark.parametrize(
    ("cut", "message"), [(20, "truncated header"), (520, "payload"), (550, "padding")]
)
def test_truncated_archive_reports_invalid_region(cut: int, message: str) -> None:
    parent, _ = parsed(archive_bytes()[:cut])
    assert parent.analysis_status == "invalid"
    assert message in (parent.analysis_message or "")


def test_invalid_later_header_preserves_preceding_member() -> None:
    data = bytearray(archive_bytes())
    data[1024] = 1
    parent, _ = parsed(data)
    assert parent.analysis_status == "invalid"
    assert any(node.name == "application/json" for node in descendants(parent))


def test_missing_second_end_block_is_invalid() -> None:
    parent, _ = parsed(archive_bytes()[:1536])
    assert parent.analysis_status == "invalid"
    assert "two zero" in (parent.analysis_message or "")


@pytest.mark.parametrize("format", [tarfile.GNU_FORMAT, tarfile.PAX_FORMAT])
def test_sparse_content_is_unsupported_without_reconstruction(format: int) -> None:
    info = tarfile.TarInfo("sparse.bin")
    if format == tarfile.GNU_FORMAT:
        info.type = tarfile.GNUTYPE_SPARSE
    else:
        info.pax_headers = {"GNU.sparse.size": str(10**12)}
    parent, _ = parsed(archive_bytes(members=[(info, b"")], format=format))
    assert parent.analysis_status == "unsupported"
    assert "sparse" in (parent.analysis_message or "")
    assert not any(
        node.name == "application/octet-stream" for node in descendants(parent)
    )


def test_depth_limit_keeps_member_structure() -> None:
    parent, _ = parsed(archive_bytes(), limits=AnalysisLimits(max_depth=0))
    data = next(node for node in descendants(parent) if node.name == "data")
    assert data.analysis_status == "limited"
    assert not data.children
    assert any(node.name == "TarHeader" for node in descendants(parent))


def test_member_limit_counts_directories() -> None:
    infos = [tarfile.TarInfo(f"directory{number}") for number in range(3)]
    for info in infos:
        info.type = tarfile.DIRTYPE
    parent, _ = parsed(
        archive_bytes(members=[(info, b"") for info in infos]),
        limits=AnalysisLimits(max_members=1),
    )
    assert parent.analysis_status == "limited"
    assert len([node for node in parent if node.name == "TarMember"]) == 1


def test_large_member_is_not_read_for_recursion_when_limited() -> None:
    parent, _ = parsed(archive_bytes(), limits=AnalysisLimits(max_member_bytes=1))
    data = next(node for node in descendants(parent) if node.name == "data")
    assert data.analysis_status == "limited"
    assert not data.children


def test_pax_size_override_locates_payload_and_following_header() -> None:
    info = tarfile.TarInfo("document.json")
    info.size = len(JSON)
    info.pax_headers = {"size": str(len(JSON))}
    data = bytearray(archive_bytes(members=[(info, JSON)], format=tarfile.PAX_FORMAT))
    start, end = 1024 + 124, 1024 + 136
    data[start:end] = b"00000000000\0"
    data = data[:1024] + update_checksum(data[1024:])
    parent, _ = parsed(data)
    assert parent.analysis_status is None
    nested = next(
        node for node in descendants(parent) if node.name == "application/json"
    )
    assert nested.offset == 1536
    assert nested.length == len(JSON)


@pytest.mark.parametrize(
    "payload", [b"bad", b"0 x=y\n", b"50 path=long\n", b"6 x=y!", b"5 =x\n"]
)
def test_malformed_pax_records_are_invalid(payload: bytes) -> None:
    info = tarfile.TarInfo("pax")
    info.type = tarfile.XHDTYPE
    info.size = len(payload)
    parent, _ = parsed(archive_bytes(members=[(info, payload)]))
    assert parent.analysis_status == "invalid"
    assert "PAX" in (parent.analysis_message or "")


@pytest.mark.parametrize("value", ["-1", "not-a-size", "1.5"])
def test_invalid_pax_size_is_rejected(value: str) -> None:
    info = tarfile.TarInfo("document.json")
    info.size = len(JSON)
    info.pax_headers = {"size": value}
    parent, _ = parsed(archive_bytes(members=[(info, JSON)], format=tarfile.PAX_FORMAT))
    assert parent.analysis_status == "invalid"
    assert "PAX size" in (parent.analysis_message or "")


@pytest.mark.parametrize("format", [tarfile.GNU_FORMAT, tarfile.PAX_FORMAT])
def test_long_link_target_is_retained_without_following_it(format: int) -> None:
    info = tarfile.TarInfo("link")
    info.type = tarfile.SYMTYPE
    info.linkname = "../" * 50 + "outside.json"
    parent, _ = parsed(archive_bytes(members=[(info, b"")], format=format))
    link = next(
        node for node in descendants(parent) if node.name == "effective_linkname"
    )
    assert link.match == repr(info.linkname)
    assert not any(node.name == "application/json" for node in descendants(parent))


def test_orphaned_longname_extension_is_invalid() -> None:
    info = tarfile.TarInfo("longname")
    info.type = tarfile.GNUTYPE_LONGNAME
    payload = b"long-name.json\0"
    info.size = len(payload)
    parent, _ = parsed(archive_bytes(members=[(info, payload)]))
    assert parent.analysis_status == "invalid"
    assert "no following member" in (parent.analysis_message or "")


def test_nonregular_payload_is_invalid() -> None:
    info = tarfile.TarInfo("link")
    info.type = tarfile.SYMTYPE
    info.size = 1
    parent, _ = parsed(archive_bytes(members=[(info, b"x")]))
    assert parent.analysis_status == "invalid"
    assert "non-file" in (parent.analysis_message or "")


def test_non_utf8_name_is_escaped_in_metadata() -> None:
    data = bytearray(archive_bytes())
    data[0] = 0xFF
    parent, _ = parsed(update_checksum(data))
    member = next(node for node in parent if node.name == "TarMember")
    assert "\\udcff" in str(member.match)
    assert member.display_name.encode("utf-8")


def test_full_matcher_handles_file_and_byte_stream_entry_points(tmp_path: Path) -> None:
    data = archive_bytes()
    path = tmp_path / "sample.tar"
    path.write_bytes(data)
    matcher = Matcher()
    for stream in (FileStream(data), FileStream(path)):
        with stream:
            roots = [node for node in matcher.match(stream) if node.parent is None]
        assert any(node.name == "application/x-tar" for node in roots)
        assert any(
            node.name == "application/json"
            for root in roots
            for node in descendants(root)
        )


def test_bad_checksum_keeps_soft_magic_but_marks_structure_invalid() -> None:
    data = bytearray(archive_bytes())
    data[0] ^= 1
    roots = [
        node for node in Matcher().match(FileStream(bytes(data))) if node.parent is None
    ]
    tar_roots = [node for node in roots if node.name == "application/x-ustar"]
    assert tar_roots
    assert all(root.analysis_status == "invalid" for root in tar_roots)


def test_nested_tar_structure_grows_linearly() -> None:
    data = JSON
    for depth in range(8):
        info = tarfile.TarInfo(f"level-{depth}.bin")
        info.size = len(data)
        data = archive_bytes(members=[(info, data)])
    roots = [node for node in Matcher().match(FileStream(data)) if node.parent is None]
    nodes = [node for root in roots for node in descendants(root)]
    assert [root.name for root in roots] == ["application/x-tar"]
    assert sum(node.name == "TarMember" for node in nodes) == 8
    assert sum(node.name == "application/json" for node in nodes) == 1


def test_filtered_soft_tar_alias_still_parses_without_native_detector() -> None:
    magic = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes={"application/x-ustar"})
    roots = [
        node
        for node in Matcher(matcher=magic).match(FileStream(archive_bytes()))
        if node.parent is None
    ]
    assert [root.name for root in roots] == ["application/x-ustar"]
    assert any(node.name == "TarHeader" for node in descendants(roots[0]))


def test_specialized_tar_verdict_is_preserved_with_native_match() -> None:
    info = tarfile.TarInfo("machine.ovf")
    info.size = len(JSON)
    roots = [
        node
        for node in Matcher().match(FileStream(archive_bytes(members=[(info, JSON)])))
        if node.parent is None
    ]
    assert {"application/x-tar", "application/x-virtualbox-ova"} <= {
        root.name for root in roots
    }
