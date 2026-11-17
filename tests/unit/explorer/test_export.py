"""Extraction writes exact bytes without risking the analyzed input or existing output."""

from concurrent.futures import CancelledError
from pathlib import Path

import pytest

from polyfile.explorer.export import export_range, selection_hex
from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel
from polyfile.explorer.search import search
from polyfile.polyfile import Analyzer
from tests.test_zipmatcher import PNG, build_zip
from tests.unit.pdf_fixtures import object_stream_pdf


def source_at(tmp_path: Path, data: bytes = bytes(range(256))) -> ByteSource:
    path = tmp_path / "input"
    path.write_bytes(data)
    return ByteSource("file", len(data), path=path)


def test_exact_binary_range_full_source_and_hex(tmp_path: Path) -> None:
    source = source_at(tmp_path)
    output = tmp_path / "out"
    assert source.path is not None
    selected = ByteRange("file", 100, 20)
    export_range(source, selected, output, input_path=source.path)
    assert output.read_bytes() == bytes(range(100, 120))
    assert selection_hex(source, selected) == bytes(range(100, 120)).hex(" ")
    export_range(source, ByteRange("file", 0, 256), output, input_path=source.path, overwrite=True)
    assert output.read_bytes() == bytes(range(256))
    export_range(source, ByteRange("file", 256, 0), output, input_path=source.path, overwrite=True)
    assert output.read_bytes() == b""
    assert list(tmp_path.glob(".polyfile-*")) == []


def test_decoded_zip_member_extracts_from_its_own_source(tmp_path: Path) -> None:
    path = tmp_path / "archive.zip"
    payload = b'{"stream-only-needle": true}'
    path.write_bytes(build_zip(members={"../../document.json": payload}))
    analyzer = Analyzer(path)
    try:
        model = ExplorerModel(path, list(analyzer.matches()))
    finally:
        analyzer.close()
    source = next(source for source in model.sources.values() if source.data == payload)
    output = tmp_path / "chosen.bin"
    export_range(source, ByteRange(source.identifier, 0, len(payload)), output, input_path=path)
    assert output.read_bytes() == payload
    assert sorted(p.name for p in tmp_path.iterdir()) == ["archive.zip", "chosen.bin"]


def test_compressed_pdf_search_extracts_decoded_coordinates(tmp_path: Path) -> None:
    data, decoded = object_stream_pdf([b"<< /Message (stream-only-needle) >>"])
    assert b"stream-only-needle" not in data
    path = tmp_path / "sample.pdf"
    path.write_bytes(data)
    analyzer = Analyzer(path)
    try:
        model = ExplorerModel(path, list(analyzer.matches()))
    finally:
        analyzer.close()
    source = next(source for source in model.sources.values() if source.data == decoded)
    hits = search(model, "stream-only-needle", mode="text", source=source.identifier)
    assert [hit.range.start for hit in hits] == [decoded.index(b"stream-only-needle")]
    output = tmp_path / "selected.bin"
    export_range(source, hits[0].range, output, input_path=path)
    assert output.read_bytes() == b"stream-only-needle"


def test_polyglot_search_preserves_physical_and_decoded_sources(tmp_path: Path) -> None:
    path = tmp_path / "polyglot.bin"
    payload = b"polyglot decoded needle"
    path.write_bytes(build_zip(prefix=PNG, members={"message.txt": payload}))
    analyzer = Analyzer(path)
    try:
        model = ExplorerModel(path, list(analyzer.matches()))
    finally:
        analyzer.close()
    assert {"image/png", "application/zip"} <= {node.type for node in model.nodes.values()}
    header = search(model, "89504e47", mode="hex")
    assert header[0].range == ByteRange("file", 0, 4)
    source = next(source for source in model.sources.values() if source.data == payload)
    hits = search(model, "needle", mode="text", source=source.identifier)
    assert hits[0].range == ByteRange(source.identifier, payload.index(b"needle"), 6)
    output = tmp_path / "selected.bin"
    export_range(source, hits[0].range, output, input_path=path)
    assert output.read_bytes() == b"needle"


def test_sparse_file_extracts_a_small_range_at_a_large_offset(tmp_path: Path) -> None:
    path = tmp_path / "sparse.bin"
    with path.open("wb") as stream:
        stream.seek(1024**3)
        stream.write(b"end")
    source = ByteSource("file", 1024**3 + 3, path=path)
    output = tmp_path / "selected.bin"
    export_range(source, ByteRange("file", 1024**3, 3), output, input_path=path)
    assert output.read_bytes() == b"end"


def test_input_symlink_and_hardlink_are_protected(tmp_path: Path) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    symlink = tmp_path / "symlink"
    hardlink = tmp_path / "hardlink"
    symlink.symlink_to(source.path)
    hardlink.hardlink_to(source.path)
    for output in (source.path, symlink, hardlink):
        with pytest.raises(ValueError, match="input file"):
            export_range(
                source, ByteRange("file", 0, 1), output, input_path=source.path, overwrite=True
            )
    assert source.path.read_bytes() == bytes(range(256))


def test_replacement_requires_confirmation_including_dangling_symlink(tmp_path: Path) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    output = tmp_path / "out"
    output.write_bytes(b"keep")
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing")
    for destination in (output, dangling):
        with pytest.raises(FileExistsError, match="already exists"):
            export_range(source, ByteRange("file", 0, 1), destination, input_path=source.path)
    assert output.read_bytes() == b"keep"
    assert dangling.is_symlink()


def test_cancel_preserves_destination_and_cleans_partial_export(tmp_path: Path) -> None:
    source = source_at(tmp_path, b"a" * 200000)
    assert source.path is not None
    output = tmp_path / "out"
    output.write_bytes(b"keep")
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 3

    with pytest.raises(CancelledError):
        export_range(
            source,
            ByteRange("file", 0, source.length),
            output,
            input_path=source.path,
            overwrite=True,
            cancelled=cancelled,
        )
    assert output.read_bytes() == b"keep"
    assert list(tmp_path.glob(".polyfile-*")) == []
    with pytest.raises(CancelledError):
        selection_hex(source, ByteRange("file", 0, 1), cancelled=lambda: True)


def test_read_failure_preserves_existing_destination(tmp_path: Path) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    output = tmp_path / "out"
    output.write_bytes(b"keep")
    source.path.write_bytes(b"short")
    with pytest.raises(OSError, match="changed"):
        export_range(
            source,
            ByteRange("file", 0, source.length),
            output,
            input_path=source.path,
            overwrite=True,
        )
    assert output.read_bytes() == b"keep"
    assert list(tmp_path.glob(".polyfile-*")) == []


@pytest.mark.parametrize(
    "selected",
    [
        ByteRange("other", 0, 1),
        ByteRange("file", -1, 1),
        ByteRange("file", 0, -1),
        ByteRange("file", 255, 2),
    ],
)
def test_invalid_ranges_do_not_create_outputs(tmp_path: Path, selected: ByteRange) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    with pytest.raises(ValueError, match="source"):
        export_range(source, selected, tmp_path / "out", input_path=source.path)
    assert not (tmp_path / "out").exists()


def test_unavailable_source_and_unwritable_destination(tmp_path: Path) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    with pytest.raises(OSError, match="unavailable"):
        selection_hex(ByteSource("missing", 1), ByteRange("missing", 0, 1))
    with pytest.raises(OSError):
        export_range(
            source, ByteRange("file", 0, 1), tmp_path / "absent" / "out", input_path=source.path
        )
    assert list(tmp_path.glob(".polyfile-*")) == []


def test_publication_failure_preserves_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    output = tmp_path / "out"
    output.write_bytes(b"keep")

    def deny_replacement(temporary: Path, destination: Path) -> None:
        raise PermissionError("Destination is read-only")

    monkeypatch.setattr("polyfile.explorer.export.os.replace", deny_replacement)
    with pytest.raises(PermissionError, match="read-only"):
        export_range(
            source, ByteRange("file", 0, 1), output, input_path=source.path, overwrite=True
        )
    assert output.read_bytes() == b"keep"
    assert list(tmp_path.glob(".polyfile-*")) == []


def test_destination_created_during_export_is_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = source_at(tmp_path)
    assert source.path is not None
    output = tmp_path / "out"

    def competing_writer(temporary: Path, destination: Path) -> None:
        destination.write_bytes(b"another writer")
        raise FileExistsError("Destination was created during extraction")

    monkeypatch.setattr("polyfile.explorer.export.os.link", competing_writer)
    with pytest.raises(FileExistsError, match="created during"):
        export_range(source, ByteRange("file", 0, 1), output, input_path=source.path)
    assert output.read_bytes() == b"another writer"
    assert list(tmp_path.glob(".polyfile-*")) == []
