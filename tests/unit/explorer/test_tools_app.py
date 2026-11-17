"""Drive source-qualified search, extraction, and clipboard actions in the UI."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from threading import Event

import pytest
from textual.pilot import Pilot
from textual.widgets import Input, Select, Static, TextArea

from polyfile.explorer.app import ExplorerApp
from polyfile.explorer.byteview import ByteView
from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel
from polyfile.explorer.search import SearchHit
from polyfile.explorer.searchpanel import SearchFinished, SearchPanel
from polyfile.explorer.tools_dialogs import CopyScreen, ExportScreen, ReplaceScreen
from polyfile.explorer.tree import StructureTree
from polyfile.polyfile import Match, Matcher
from tests.unit.explorer.test_search import model_for


async def settle(app: ExplorerApp, pilot: Pilot[int]) -> None:
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def test_search_navigation_sources_scope_and_clear(tmp_path: Path) -> None:
    async def check() -> None:
        model = model_for(tmp_path / "input", b"needle _needle", decoded=b"_needle")
        app = ExplorerApp(model)
        async with app.run_test(size=(100, 32)) as pilot:
            await pilot.press("slash")
            panel = app.query_one(SearchPanel)
            query = panel.query_one(Input)
            assert app.focused is query
            query.value = "needle"
            await settle(app, pilot)
            assert len(panel.results) == 3
            assert app.selection == ByteRange("file", 0, 6)
            await pilot.press("enter")
            assert app.selection == ByteRange("file", 8, 6)
            await pilot.press("shift+enter")
            assert app.selection == ByteRange("file", 0, 6)
            await pilot.press("enter")
            await pilot.click("#search-next")
            await pilot.pause()
            assert app.selection == ByteRange("decoded:0", 1, 6)
            app.query_one(ByteView).focus()
            await pilot.press("shift+n", "n")
            assert app.selection == ByteRange("decoded:0", 1, 6)
            panel.query_one("#search-scope", Select).value = "current"
            await settle(app, pilot)
            assert len(panel.results) == 1
            app.select_range(ByteRange("file", 0, 1))
            await settle(app, pilot)
            assert len(panel.results) == 2
            query.value = ""
            await settle(app, pilot)
            assert panel.results == []
            assert app.query_one(ByteView)._search_ranges == {}

    asyncio.run(check())


def test_invalid_hex_and_stale_worker_results_are_visible_or_ignored(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"file"))
        async with app.run_test(size=(80, 32)) as pilot:
            panel = app.query_one(SearchPanel)
            panel.query_one("#search-mode", Select).value = "hex"
            panel.query_one(Input).value = "abc"
            await settle(app, pilot)
            assert "hexadecimal byte pairs" in str(
                panel.query_one("#search-status", Static).render()
            )
            generation = panel.generation
            panel.post_message(SearchFinished(generation - 1, [], "stale result"))
            hit = SearchHit(ByteRange("file", 2, 1), ("text",))
            panel.post_message(SearchPanel.ResultSelected(hit, generation - 1))
            panel.post_message(SearchPanel.ResultsChanged([hit], generation - 1))
            await pilot.pause()
            assert "stale result" not in str(panel.query_one("#search-status", Static).render())
            assert app.selection == ByteRange("file", 0, 1)
            assert app.query_one(ByteView)._search_ranges == {}

    asyncio.run(check())


def test_replaced_query_cancels_slow_source_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = Event()
    release = Event()
    chunks = ByteSource._file_chunks

    def slow_chunks(
        source: ByteSource,
        start: int,
        length: int,
        chunk_size: int,
    ) -> Iterator[tuple[int, bytes]]:
        if not entered.is_set():
            entered.set()
            assert release.wait(5)
        yield from chunks(source, start, length, chunk_size)

    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"old new"))
        async with app.run_test(size=(80, 32)) as pilot:
            monkeypatch.setattr(ByteSource, "_file_chunks", slow_chunks)
            panel = app.query_one(SearchPanel)
            panel.query_one("#search-mode", Select).value = "text"
            panel.query_one(Input).value = "old"
            await pilot.pause()
            assert await asyncio.to_thread(entered.wait, 5)
            panel.query_one(Input).value = "new"
            await pilot.pause()
            release.set()
            await settle(app, pilot)
            assert [hit.range.start for hit in panel.results] == [4]
            assert app.selection == ByteRange("file", 4, 3)

    try:
        asyncio.run(check())
    finally:
        release.set()


def test_export_selection_replacement_and_copy_dialogs(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"abcdef", decoded=b"decoded"))
        output = tmp_path / "out"
        async with app.run_test(size=(100, 32)) as pilot:
            app.select_range(ByteRange("decoded:0", 1, 3))
            await pilot.pause()
            await pilot.press("e")
            assert isinstance(app.screen, ExportScreen)
            app.screen.query_one(Input).value = str(output)
            await pilot.press("enter")
            await settle(app, pilot)
            assert output.read_bytes() == b"eco"
            app.action_export_source()
            await pilot.pause()
            app.screen.query_one(Input).value = str(output)
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ReplaceScreen)
            await pilot.press("escape")
            assert output.read_bytes() == b"eco"
            app.action_copy_hex()
            await settle(app, pilot)
            assert isinstance(app.screen, CopyScreen)
            assert app.screen.query_one(TextArea).text == "65 63 6f"
            await pilot.press("escape")
            app.action_copy_offset()
            await pilot.pause()
            assert app.screen.query_one(TextArea).text == "0x1"

    asyncio.run(check())


def test_export_replacement_and_input_protection_in_ui(tmp_path: Path) -> None:
    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"abcdef"))
        output = tmp_path / "out"
        output.write_bytes(b"preserve")
        async with app.run_test(size=(100, 32)) as pilot:
            app.select_range(ByteRange("file", 1, 3))
            for destination in (output, app.model.path):
                app.action_export_selection()
                await pilot.pause()
                app.screen.query_one(Input).value = str(destination)
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, ReplaceScreen)
                await pilot.click("#replace-confirm")
                await settle(app, pilot)
            assert output.read_bytes() == b"bcd"
            assert app.model.path.read_bytes() == b"abcdef"
            assert "input file" in str(app.query_one("#status", Static).render())

    asyncio.run(check())


def test_missing_decoded_bytes_report_errors_without_opening_dialogs(tmp_path: Path) -> None:
    async def check() -> None:
        path = tmp_path / "input"
        path.write_bytes(b"file")
        missing = Match("missing", None, length=4, source="decoded:1", matcher=Matcher(False))
        app = ExplorerApp(ExplorerModel(path, [missing]))
        async with app.run_test(size=(100, 32)) as pilot:
            app.select_node(0)
            await pilot.pause()
            app.action_export_selection()
            assert "unavailable" in str(app.query_one("#status", Static).render())
            assert not isinstance(app.screen, ExportScreen)
            app.action_copy_hex()
            await settle(app, pilot)
            assert not isinstance(app.screen, CopyScreen)
            assert "unavailable" in str(app.query_one("#status", Static).render())
            panel = app.query_one(SearchPanel)
            panel.query_one(Input).value = "absent"
            await settle(app, pilot)
            assert "source buffer(s) unavailable" in str(
                panel.query_one("#search-status", Static).render()
            )

    asyncio.run(check())


def test_cancel_export_preserves_destination_in_ui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = Event()
    release = Event()
    chunks = ByteSource._file_chunks

    def slow_chunks(
        source: ByteSource,
        start: int,
        length: int,
        chunk_size: int,
    ) -> Iterator[tuple[int, bytes]]:
        entered.set()
        assert release.wait(5)
        yield from chunks(source, start, length, chunk_size)

    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"a" * 200000))
        output = tmp_path / "out"
        output.write_bytes(b"keep")
        async with app.run_test(size=(80, 32)) as pilot:
            monkeypatch.setattr(ByteSource, "_file_chunks", slow_chunks)
            app._start_export(ByteRange("file", 0, 200000), output, overwrite=True)
            await pilot.pause()
            assert await asyncio.to_thread(entered.wait, 5)
            await pilot.press("ctrl+g")
            release.set()
            await settle(app, pilot)
            assert output.read_bytes() == b"keep"
            assert list(tmp_path.glob(".polyfile-*")) == []

    try:
        asyncio.run(check())
    finally:
        release.set()


@pytest.mark.parametrize("size", [(60, 24), (80, 24), (130, 32)])
def test_search_controls_leave_visible_byte_rows(tmp_path: Path, size: tuple[int, int]) -> None:
    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"file"))
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            assert app.query_one(ByteView).scrollable_content_region.height >= 2
            app.query_one(SearchPanel).query_one(Input).value = "file"
            await settle(app, pilot)
            app.action_cancel_work()
            await pilot.pause()
            assert app.query_one(SearchPanel).results == []

    asyncio.run(check())


@pytest.mark.parametrize("query", ["root", "x"])
def test_narrow_search_shows_bytes_without_taking_input_focus(tmp_path: Path, query: str) -> None:
    async def check() -> None:
        app = ExplorerApp(model_for(tmp_path / "input", b"x"))
        async with app.run_test(size=(80, 24)) as pilot:
            app.action_switch_pane()
            assert app.query_one(StructureTree).display
            await pilot.press("slash")
            field = app.query_one(SearchPanel).query_one(Input)
            field.value = query
            await settle(app, pilot)
            assert app.focused is field
            assert not app.query_one(StructureTree).display
            assert app.query_one(ByteView).display

    asyncio.run(check())
