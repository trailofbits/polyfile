"""Byte windows retain their coordinates across text rendering boundaries."""

from pathlib import Path

from polyfile.explorer.model import ByteRange, ByteSource
from polyfile.explorer.rendering import text_units


def test_utf8_glyphs_keep_byte_spans_and_escape_controls() -> None:
    data = "Aé界\u0301".encode() + b"\x00\x1b\x7f\xff"
    source = ByteSource("decoded:0", len(data), data=data)
    units = text_units(source, 0, len(data))
    assert [unit.text for unit in units] == ["A", "é", "界", "◌́", "␀", "␛", "␡", "�"]
    assert [(unit.range.start, unit.range.length) for unit in units] == [
        (0, 1),
        (1, 2),
        (3, 3),
        (6, 2),
        (8, 1),
        (9, 1),
        (10, 1),
        (11, 1),
    ]
    assert units[2].range == ByteRange("decoded:0", 3, 3)


def test_windows_do_not_duplicate_multibyte_glyphs() -> None:
    data = b"a" * 15 + "😀é".encode() + b"tail"
    source = ByteSource("file", len(data), data=data)
    first = text_units(source, 0, 16)
    second = text_units(source, 16, len(data) - 16)
    assert first[-1].text == "😀"
    assert first[-1].range == ByteRange("file", 15, 4)
    assert second[0].text == "é"
    assert second[0].range == ByteRange("file", 19, 2)
    assert "".join(unit.text for unit in first + second) == "a" * 15 + "😀étail"


def test_malformed_utf8_groups_partial_sequences_without_losing_bytes() -> None:
    data = b"\xe2\x82A\xed\xa0\x80\xf0\x9f"
    source = ByteSource("file", len(data), data=data)
    units = text_units(source, 0, len(data))
    assert "".join(unit.text for unit in units) == "�A����"
    assert sum(unit.range.length for unit in units) == len(data)
    assert text_units(source, 0, 0) == ()


def test_file_text_window_does_not_read_whole_source(tmp_path: Path) -> None:
    path = tmp_path / "large"
    with path.open("wb") as stream:
        stream.seek(1024**3)
        stream.write("é".encode())
    source = ByteSource("file", path.stat().st_size, path=path)
    units = text_units(source, 1024**3, 2)
    assert units[0].text == "é"
    assert units[0].range == ByteRange("file", 1024**3, 2)
