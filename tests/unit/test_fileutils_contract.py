"""Bounded stream positions use parent, view, and backing coordinates consistently."""

from collections.abc import Iterator
from io import BytesIO, SEEK_CUR, SEEK_END, SEEK_SET
from pathlib import Path

import pytest

from polyfile.fileutils import FileStream

DATA = b"0123456789abcdef"


@pytest.fixture(params=("bytes", "memory", "file"))
def stream(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[FileStream]:
    """Provide the same nonzero-origin view over each supported backing."""
    source: bytes | BytesIO | Path = DATA
    if request.param == "memory":
        source = BytesIO(DATA)
        setattr(source, "name", "memory")
    elif request.param == "file":
        source = tmp_path / "backing.bin"
        source.write_bytes(DATA)
    view = FileStream(source, start=5, length=6)
    try:
        yield view
    finally:
        view.close()


def test_nested_origins_and_cursor_positions(stream: FileStream) -> None:
    child = FileStream(stream, start=2, length=3)
    assert child.start == 2
    assert child.offset() == 7
    assert child.tell() == 0
    assert stream.tell() == 2
    assert child.seek(2) == 2
    assert child.tell() == 2
    assert stream.tell() == 4
    assert child.root.tell() == 9
    assert child.read() == b"9"


@pytest.mark.parametrize("origin", (SEEK_SET, SEEK_CUR, SEEK_END))
def test_seek_returns_view_relative_position(stream: FileStream, origin: int) -> None:
    stream.seek(1)
    target = {SEEK_SET: 4, SEEK_CUR: 3, SEEK_END: -2}[origin]
    assert stream.seek(target, from_what=origin) == 4
    assert stream.tell() == 4
    assert stream.root.tell() == 9


@pytest.mark.parametrize("position", (-1, 7, 11))
def test_seek_rejects_positions_outside_view(stream: FileStream, position: int) -> None:
    stream.seek(2)
    with pytest.raises(IndexError, match="position|byte"):
        stream.seek(position)
    assert stream.tell() == 2


def test_seek_rejects_unknown_origin(stream: FileStream) -> None:
    stream.seek(2)
    with pytest.raises(ValueError, match="origin|whence"):
        stream.seek(0, from_what=99)
    assert stream.tell() == 2


def test_past_eof_start_is_clamped_for_raw_and_nested_views(stream: FileStream) -> None:
    child = FileStream(stream, start=100, length=3)
    assert child.start == len(stream)
    assert child.offset() == stream.offset() + len(stream)
    assert len(child) == 0
    assert child.seek(0) == 0
    assert child.read() == b""
    raw = FileStream(DATA, start=100)
    assert raw.start == len(DATA)
    assert raw.offset() == len(DATA)
    assert raw.read() == b""


@pytest.mark.parametrize("start,length", ((-1, None), (0, -1)))
def test_negative_constructor_arguments_are_rejected(
    stream: FileStream, start: int, length: int | None
) -> None:
    stream.seek(2)
    with pytest.raises(ValueError, match="nonnegative"):
        FileStream(stream, start=start, length=length)
    assert stream.tell() == 2


def test_save_pos_restores_root_position_outside_view(stream: FileStream) -> None:
    stream.root.seek(1)
    with pytest.raises(RuntimeError, match="inside context"):
        with stream.save_pos():
            stream.seek(3)
            raise RuntimeError("inside context")
    assert stream.root.tell() == 1
    assert stream.tell() == 0


def test_save_pos_snapshots_when_called(stream: FileStream) -> None:
    stream.seek(1)
    saved = stream.save_pos()
    stream.seek(3)
    with saved:
        stream.seek(5)
    assert stream.tell() == 1


def test_sibling_views_share_the_backing_cursor(stream: FileStream) -> None:
    first = FileStream(stream, start=1, length=2)
    second = FileStream(stream, start=4, length=2)
    assert first.tell() == len(first)
    assert first.read() == b""
    assert second.read(1) == b"9"
    assert stream.tell() == 5
    first.seek(0)
    assert second.tell() == 0
    assert second.read(1) == b"9"
