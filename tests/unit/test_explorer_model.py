"""Source-qualified structure inspection without serialized byte copies."""

from pathlib import Path

import pytest

from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel
from polyfile.polyfile import Match, Matcher, Submatch
from tests.test_zipmatcher import MEMBERS, PNG, build_zip
from pdf_fixtures import object_stream_pdf


def structure() -> Match:
    root = Match("root", None, length=16, matcher=Matcher(False))
    Submatch("first", None, length=4, parent=root)
    Submatch("last", None, relative_offset=12, length=4, parent=root)
    decoded = Submatch(
        "decoded", None, source="decoded:0", length=12, parent=root, decoded=b"decoded data"
    )
    Submatch("middle", None, relative_offset=4, length=4, parent=decoded)
    return root


def test_sources_preserve_offsets_and_decoded_buffers(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(bytes(16))
    root = structure()
    model = ExplorerModel(path, [root])
    decoded = root.children[2]
    assert model.sources["decoded:0"].data is decoded.decoded
    assert model.sources["file"].data is None
    assert model.nodes[4].range == ByteRange("decoded:0", 4, 4)
    assert model.undescribed("file") == (ByteRange("file", 4, 8),)
    assert model.undescribed("decoded:0") == (
        ByteRange("decoded:0", 0, 4),
        ByteRange("decoded:0", 8, 4),
    )
    assert model.sources["decoded:0"].read(4, 4) == b"ded "


def test_overlapping_interpretations_and_clamped_coverage(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(bytes(16))
    first = Match("first", None, length=30, matcher=Matcher(False))
    second = Match("second", None, relative_offset=4, length=8, matcher=Matcher(False))
    model = ExplorerModel(path, [first, second], partial=True)
    assert [node.type for node in model.nodes_at("file", 5)] == ["first", "second"]
    assert model.undescribed("file") == ()
    assert model.clamp_range(ByteRange("file", -3, 8)) == ByteRange("file", 0, 5)
    assert model.clamp_range(ByteRange("file", 40, 8)) == ByteRange("file", 16, 0)
    assert model.partial


def test_missing_decoded_source_remains_visible(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(b"file")
    missing = Match("missing", None, source="decoded:1", length=8, matcher=Matcher(False))
    model = ExplorerModel(path, [missing])
    source = model.sources["decoded:1"]
    assert not source.available
    with pytest.raises(OSError, match="no decoded byte buffer"):
        source.read(0, 1)


def test_empty_source_and_out_of_bounds_reads(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.touch()
    model = ExplorerModel(path, [])
    assert model.undescribed("file") == ()
    assert model.sources["file"].read(0, 0) == b""
    source = ByteSource("decoded:0", 3, data=b"abc")
    for start, length in [(-1, 1), (0, -1), (2, 2), (4, 0)]:
        with pytest.raises(ValueError, match="outside source"):
            source.read(start, length)
    with pytest.raises(ValueError, match="positive"):
        list(source.iter_chunks(chunk_size=0))


def test_chunked_reads_detect_changed_file(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(b"abcdefgh")
    source = ByteSource("file", 8, path=path)
    assert list(source.iter_chunks(1, 5, chunk_size=2)) == [(1, b"bc"), (3, b"de"), (5, b"f")]
    path.write_bytes(b"abc")
    with pytest.raises(OSError, match="changed"):
        source.read(0, 8)
    path.unlink()
    with pytest.raises(OSError, match="Cannot read source"):
        source.read(0, 1)


def test_sparse_file_stays_file_backed(tmp_path: Path) -> None:
    path = tmp_path / "large.bin"
    with path.open("wb") as stream:
        stream.seek(1024**3)
        stream.write(b"end")
    source = ExplorerModel(path, []).sources["file"]
    assert source.data is None
    assert source.read(1024**3, 3) == b"end"


def test_real_zip_polyglot_keeps_embedded_sources_distinct(tmp_path: Path) -> None:
    path = tmp_path / "png-zip.bin"
    data = build_zip(prefix=PNG)
    path.write_bytes(data)
    matches = list(Matcher().match(data))
    roots = [match for match in matches if match.parent is None]
    model = ExplorerModel(path, roots)
    assert {node.type for node in model.nodes.values()} >= {"image/png", "application/zip"}
    decoded = [source.data for source in model.sources.values() if source.data is not None]
    assert set(MEMBERS.values()) <= set(decoded)
    assert model.sources["file"].read(0, len(PNG)) == PNG
    assert all(source.identifier != "file" for source in model.sources.values() if source.data)


def test_compressed_pdf_object_sources_keep_their_own_coordinates(tmp_path: Path) -> None:
    data, decoded = object_stream_pdf([b"[1 (hello)]"])
    path = tmp_path / "compressed.pdf"
    path.write_bytes(data)
    matches = list(Matcher().match(data))
    model = ExplorerModel(path, [match for match in matches if match.parent is None])
    buffers = [source for source in model.sources.values() if source.data == decoded]
    assert buffers
    assert buffers[0].read(0, len(decoded)) == decoded
    assert any(
        node.type == "PDFList" and node.source == buffers[0].identifier
        for node in model.nodes.values()
    )
