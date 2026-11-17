"""Extraction writes exact bytes without risking the analyzed input or existing output."""

from concurrent.futures import CancelledError
from pathlib import Path

import pytest

from polyfile.explorer.export import export_range, selection_hex
from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel
from polyfile.polyfile import Analyzer
from tests.test_zipmatcher import build_zip


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
