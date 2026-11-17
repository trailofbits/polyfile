"""Drive the terminal inspector through its keyboard and source controls."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Input, Select, Static

from polyfile.explorer.app import ExplorerApp
from polyfile.explorer.byteview import ByteView
from polyfile.explorer.dialogs import HelpDialog, OffsetDialog
from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel
from polyfile.explorer.tree import StructureTree
from polyfile.polyfile import Match, Matcher, Submatch


def model(path: Path) -> ExplorerModel:
    path.write_bytes(bytes(range(128)))
    root = Match("application/test", None, length=128, matcher=Matcher(False))
    child = Submatch("[bold]literal\x1b[2J", b"value", length=12, parent=root)
    Submatch("nested", None, relative_offset=2, length=2, parent=child)
    Submatch("decoded", None, length=6, parent=root, source="decoded:0", decoded=b"needle")
    return ExplorerModel(path, [root])


def test_tree_reveal_switches_to_decoded_source(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test(size=(130, 32)) as pilot:
            tree = app.query_one(StructureTree)
            assert set(tree.entries) == {0}
            app.select_node(2)
            await pilot.pause()
            assert app.selection == ByteRange("file", 2, 2)
            assert set(tree.entries) == {0, 1, 2, 3}
            app.select_node(3)
            await pilot.pause()
            assert app.active_source == "decoded:0"
            assert app.selection == ByteRange("decoded:0", 0, 6)
            assert app.query_one("#source", Select).value == "decoded:0"
            assert "needle" in app.query_one(ByteView).render_line(0).text

    asyncio.run(check())


def test_keyboard_selection_and_offset_validation(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test() as pilot:
            await pilot.press("right", "shift+right", "shift+right")
            assert app.selection == ByteRange("file", 1, 3)
            await pilot.press("g")
            assert isinstance(app.screen, OffsetDialog)
            app.screen.query_one(Input).value = "128"
            await pilot.press("enter")
            assert "0 to 127" in str(app.screen.query_one("#offset-error", Static).render())
            app.screen.query_one(Input).value = "0x20"
            await pilot.press("enter")
            assert app.selection == ByteRange("file", 32, 1)
            await pilot.press("ctrl+end")
            assert app.selection == ByteRange("file", 127, 1)
            await pilot.press("ctrl+home")
            assert app.selection == ByteRange("file", 0, 1)

    asyncio.run(check())


def test_narrow_panes_help_and_literal_details(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test(size=(60, 24)) as pilot:
            assert app.screen.has_class("narrow")
            assert not app.query_one(StructureTree).display
            await pilot.press("f2")
            assert app.query_one(StructureTree).display
            app.select_node(1)
            await pilot.pause()
            assert not app.query_one(StructureTree).display
            details = str(app.query_one("#details", Static).render())
            assert "[bold]literal\\x1b[2J" in details
            await pilot.press("f1")
            assert isinstance(app.screen, HelpDialog)
            await pilot.press("escape")
            assert not isinstance(app.screen, HelpDialog)
            await pilot.press("q")
        assert app.return_value == 0

    asyncio.run(check())


def test_empty_and_unavailable_sources_remain_navigable(tmp_path: Path) -> None:
    async def check() -> None:
        path = tmp_path / "empty"
        path.touch()
        root = Match("missing", None, length=6, source="decoded:9", matcher=Matcher(False))
        app = ExplorerApp(ExplorerModel(path, [root]))
        async with app.run_test() as pilot:
            assert "Empty source" in app.query_one(ByteView).render_line(0).text
            await pilot.press("g", "enter")
            assert isinstance(app.screen, OffsetDialog)
            await pilot.press("escape")
            app.select_node(0)
            await pilot.pause()
            assert "unavailable" in app.query_one(ByteView).render_line(0).text
            await pilot.press("ctrl+c")
        assert app.return_value == 130

    asyncio.run(check())


def test_rapid_source_changes_ignore_queued_stale_events(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test() as pilot:
            app.select_node(3)
            app.select_node(1)
            app.select_node(3)
            app.select_node(2)
            await pilot.pause()
            assert app.active_source == "file"
            assert app.selection == ByteRange("file", 2, 2)
            assert app.query_one("#source", Select).value == "file"

    asyncio.run(check())


def test_unbounded_offset_input_displays_error_instead_of_crashing(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test() as pilot:
            await pilot.press("g")
            app.screen.query_one(Input).value = "9" * 5000
            await pilot.press("enter")
            assert "0 to 127" in str(app.screen.query_one("#offset-error", Static).render())
            app.screen.query_one(Input).value = "0" * 5000 + "12"
            await pilot.press("enter")
            assert app.selection == ByteRange("file", 12, 1)

    asyncio.run(check())


def test_scrolled_mouse_selection_uses_source_offsets(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test(size=(80, 20)) as pilot:
            view = app.query_one(ByteView)
            view.scroll_to(y=3, animate=False, immediate=True)
            await pilot.pause()
            assert view.scroll_offset.y == 3
            await pilot.click("#bytes", offset=(7, 1))
            assert app.selection == ByteRange("file", 3 * view.bytes_per_row, 1)
            await pilot.click("#bytes", offset=(13, 1), shift=True)
            assert app.selection == ByteRange("file", 3 * view.bytes_per_row, 3)

    asyncio.run(check())


def test_text_coverage_marks_gap_inside_multibyte_character(tmp_path: Path) -> None:
    async def check() -> None:
        path = tmp_path / "utf8"
        path.write_bytes("éX".encode())
        root = Match("first byte", None, length=1, matcher=Matcher(False))
        app = ExplorerApp(ExplorerModel(path, [root]))
        async with app.run_test() as pilot:
            app.select_range(ByteRange("file", 2, 1))
            await pilot.press("t")
            view = app.query_one(ByteView)
            segments = list(view.render_line(0))
            accented = [segment for segment in segments if "é" in segment.text]
            assert accented and accented[0].style is not None
            assert accented[0].style.underline

    asyncio.run(check())


def test_byte_view_reads_only_a_viewport_of_a_large_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def check() -> None:
        path = tmp_path / "large"
        with path.open("wb") as stream:
            stream.seek(1024**3)
            stream.write(b"end")
        sizes = []
        read = ByteSource.read

        def bounded_read(source: ByteSource, start: int, length: int) -> bytes:
            sizes.append(length)
            assert length <= 128
            return read(source, start, length)

        monkeypatch.setattr(ByteSource, "read", bounded_read)
        app = ExplorerApp(ExplorerModel(path, []))
        async with app.run_test() as pilot:
            await pilot.press("ctrl+end", "t")
            assert app.selection.start == 1024**3 + 2
            assert app.query_one(ByteView).virtual_size.height > 1000000
        assert sizes

    asyncio.run(check())


@pytest.mark.parametrize("modal_key", ["f1", "g"])
def test_resize_while_modal_is_open_updates_explorer_layout(
    tmp_path: Path,
    modal_key: str,
) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test(size=(130, 32)) as pilot:
            await pilot.press(modal_key)
            assert isinstance(app.screen, (HelpDialog, OffsetDialog))
            await pilot.resize_terminal(60, 24)
            assert app.screen_stack[0].has_class("narrow")
            assert not app.screen.has_class("narrow")
            await pilot.press("escape")
            assert not app.query_one(StructureTree).display
            assert app.query_one(ByteView).display
            await pilot.press(modal_key)
            await pilot.resize_terminal(130, 32)
            assert not app.screen_stack[0].has_class("narrow")
            await pilot.press("escape")
            assert app.query_one(StructureTree).display
            assert app.query_one(ByteView).display

    asyncio.run(check())


@pytest.mark.parametrize("method", ["drag", "shift_click"])
def test_backward_text_selection_keeps_entire_anchor_glyph(
    tmp_path: Path,
    method: str,
) -> None:
    async def check() -> None:
        path = tmp_path / "utf8"
        path.write_bytes("A😀B".encode())
        app = ExplorerApp(ExplorerModel(path, []))
        async with app.run_test() as pilot:
            await pilot.press("t")
            if method == "drag":
                await pilot.mouse_down("#bytes", offset=(8, 1))
                assert app.selection == ByteRange("file", 1, 4)
                await pilot.hover("#bytes", offset=(7, 1))
                await pilot.mouse_up("#bytes", offset=(7, 1))
            else:
                await pilot.click("#bytes", offset=(8, 1))
                assert app.selection == ByteRange("file", 1, 4)
                await pilot.click("#bytes", offset=(7, 1), shift=True)
            assert app.selection == ByteRange("file", 0, 5)
            assert (
                app.model.sources["file"].read(
                    app.selection.start,
                    app.selection.length,
                )
                == "A😀".encode()
            )
            await pilot.press("right", "shift+right", "shift+right")
            assert app.selection == ByteRange("file", 1, 3)

    asyncio.run(check())


def test_narrow_tree_selection_transfers_keyboard_focus_to_bytes(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model(tmp_path / "sample"))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("f2", "down", "enter")
            assert not app.query_one(StructureTree).display
            assert app.focused is app.query_one(ByteView)
            assert app.selection == ByteRange("file", 0, 128)
            await pilot.press("right")
            assert app.selection == ByteRange("file", 1, 1)

    asyncio.run(check())
