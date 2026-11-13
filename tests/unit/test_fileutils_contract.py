"""Bounded stream positions use parent, view, and backing coordinates consistently."""

from collections.abc import Iterator
from io import BytesIO, SEEK_CUR, SEEK_END, SEEK_SET, StringIO, UnsupportedOperation
from pathlib import Path
from typing import BinaryIO, cast

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


@pytest.mark.parametrize(
    "origin,offset", ((SEEK_CUR, -3), (SEEK_CUR, 5), (SEEK_END, 1), (SEEK_END, -7))
)
def test_relative_seeks_reject_resolved_positions_outside_view(
    stream: FileStream, origin: int, offset: int
) -> None:
    stream.seek(2)
    with pytest.raises(IndexError):
        stream.seek(offset, origin)
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


@pytest.mark.parametrize("index", (-6, -5, -1, 0, 1, 5))
def test_integer_indexing_matches_bytes_and_preserves_cursor(
    stream: FileStream, index: int
) -> None:
    stream.seek(3)
    assert stream[index] == bytes((DATA[5:11][index],))
    assert stream.tell() == 3


@pytest.mark.parametrize("index", (-7, 6, 10))
def test_integer_indexing_rejects_missing_bytes(stream: FileStream, index: int) -> None:
    stream.seek(3)
    with pytest.raises(IndexError):
        stream[index]
    assert stream.tell() == 3


@pytest.mark.parametrize("start", (None, -10, -2, 0, 2, 6, 10))
@pytest.mark.parametrize("stop", (None, -10, -1, 0, 3, 6, 10))
def test_slices_match_bytes_and_move_the_shared_cursor(
    stream: FileStream, start: int | None, stop: int | None
) -> None:
    stream.seek(3)
    child = stream[start:stop]
    assert isinstance(child, FileStream)
    expected_start, _, _ = slice(start, stop).indices(len(stream))
    assert child.start == expected_start
    assert child.offset() == stream.offset() + expected_start
    assert stream.tell() == expected_start
    assert child.content == DATA[5:11][start:stop]
    assert stream.tell() == expected_start


@pytest.mark.parametrize("step", (0, -1, 2))
def test_slices_reject_nonunit_steps(stream: FileStream, step: int) -> None:
    stream.seek(3)
    with pytest.raises(ValueError, match="step"):
        stream[::step]
    assert stream.tell() == 3


def test_child_reads_preserve_parent_transformations() -> None:
    class UppercaseView(FileStream):
        def read(self, n: int | None = None) -> bytes:
            return super().read(n).upper()

    parent = UppercaseView(b"prefixabcdefsuffix", start=6, length=6)
    child = parent[1:-1]
    assert isinstance(child, FileStream)
    assert child.read() == b"BCDE"
    assert child.content == b"BCDE"


def test_indexing_and_content_restore_a_cursor_outside_the_view(stream: FileStream) -> None:
    stream.root.seek(1)
    assert stream[-1] == b"a"
    assert stream.content == DATA[5:11]
    assert stream.root.tell() == 1


def test_unnamed_binary_memory_is_supported() -> None:
    source = BytesIO(DATA)
    view = FileStream(source, start=2, length=3)
    assert view.name == "bytes"
    assert view.read() == b"234"


def test_text_streams_are_rejected_without_closing_them(tmp_path: Path) -> None:
    path = tmp_path / "text.txt"
    path.write_text("text", encoding="utf-8")
    with StringIO("text") as memory, path.open(encoding="utf-8") as disk:
        for source in (memory, disk):
            with pytest.raises(TypeError, match="binary"):
                FileStream(cast(BinaryIO, source))
            assert not source.closed
            assert source.tell() == 0


@pytest.mark.parametrize("mode", ("r", "rt", "w", "wb", "ab", "a+b"))
def test_invalid_path_modes_are_rejected_before_opening(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(DATA)
    with pytest.raises(ValueError, match="binary|read-only"):
        FileStream(path, mode=mode)
    assert path.read_bytes() == DATA


def test_readable_binary_update_mode_keeps_the_view_read_only(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(DATA)
    with FileStream(path, mode="r+b") as view:
        assert view.read(1) == b"0"
        assert not view.writable()
        with pytest.raises(UnsupportedOperation):
            view.write(b"changed")
    assert path.read_bytes() == DATA


def test_owned_paths_and_borrowed_streams_have_distinct_lifetimes(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(DATA)
    with FileStream(path) as owned:
        assert not owned.closed
    assert owned.closed
    source = BytesIO(DATA)
    with FileStream(source) as borrowed:
        borrowed.read(1)
    assert not source.closed
    assert source.tell() == 1
    borrowed.close()
    assert source.closed


def test_tempfile_preserves_the_shared_cursor(stream: FileStream) -> None:
    stream.seek(2)
    with stream.tempfile() as filename:
        path = Path(filename)
        assert path.read_bytes() == DATA[5:11]
        assert stream.tell() == 2
    assert not path.exists()


def test_nested_views_match_a_bytes_model(stream: FileStream) -> None:
    for start in range(len(stream) + 3):
        for length in (None, 0, 1, 10):
            child = FileStream(stream, start=start, length=length)
            expected = DATA[5:11][start:]
            if length is not None:
                expected = expected[:length]
            assert child.content == expected
            assert child.offset() == stream.offset() + min(start, len(stream))
            for position in range(len(child) + 1):
                assert child.seek(position) == position
                end = position + 2
                assert child.read(2) == expected[position:end]
                assert child.tell() == min(position + 2, len(child))


def test_three_levels_of_views_preserve_coordinate_domains(stream: FileStream) -> None:
    parent = FileStream(stream, start=1, length=4)
    child = parent[1:3]
    assert child.offset() == 7
    assert child.root is stream.root
    assert child.seek(-1, SEEK_END) == 1
    assert child.read() == b"8"
    assert stream.tell() == 4


@pytest.mark.parametrize(
    "operation",
    ("readline", "readlines", "truncate", "write", "writelines", "__iter__", "__next__"),
)
def test_unsupported_operations_leave_the_cursor_unchanged(
    stream: FileStream, operation: str
) -> None:
    stream.seek(2)
    arguments = {"write": (b"x",), "writelines": ([b"x"],)}
    with pytest.raises(UnsupportedOperation):
        getattr(stream, operation)(*arguments.get(operation, ()))
    assert stream.tell() == 2


@pytest.mark.parametrize("capability", ("seekable", "readable"))
def test_input_capabilities_are_checked_without_closing_the_input(
    capability: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = BytesIO(DATA)
    monkeypatch.setattr(source, capability, lambda: False)
    with pytest.raises(ValueError, match=capability):
        FileStream(source)
    assert not source.closed
    assert source.tell() == 0
