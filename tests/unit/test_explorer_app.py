"""Drive the terminal inspector through its keyboard and source controls."""

import asyncio
from pathlib import Path

from textual.widgets import Input, Select, Static

from polyfile.explorer.app import ExplorerApp
from polyfile.explorer.byteview import ByteView
from polyfile.explorer.dialogs import HelpDialog, OffsetDialog
from polyfile.explorer.model import ByteRange, ExplorerModel
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
