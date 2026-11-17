"""Dialog actions keep destination and clipboard decisions under user control."""

import asyncio
from pathlib import Path

from textual.app import App
from textual.widgets import Input, TextArea

from polyfile.explorer.tools_dialogs import CopyScreen, ExportScreen, ReplaceScreen


def test_destination_submission_and_escape(tmp_path: Path) -> None:
    async def check() -> None:
        app = App[None]()
        results: list[Path | None] = []
        async with app.run_test() as pilot:
            app.push_screen(ExportScreen("file @ 0x0"), results.append)
            await pilot.pause()
            app.screen.query_one(Input).value = str(tmp_path / "chosen.bin")
            await pilot.press("enter")
            await pilot.pause()
            assert results == [tmp_path / "chosen.bin"]
            app.push_screen(ExportScreen("selection"), results.append)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [tmp_path / "chosen.bin", None]

    asyncio.run(check())


def test_replace_defaults_to_cancel_and_requires_explicit_choice(tmp_path: Path) -> None:
    async def check() -> None:
        app = App[None]()
        results: list[bool | None] = []
        async with app.run_test() as pilot:
            app.push_screen(ReplaceScreen(tmp_path / "existing"), results.append)
            await pilot.pause()
            assert app.screen.focused is app.screen.query_one("#replace-cancel")
            await pilot.press("escape")
            await pilot.pause()
            assert results == [False]
            app.push_screen(ReplaceScreen(tmp_path / "existing"), results.append)
            await pilot.pause()
            await pilot.click("#replace-confirm")
            await pilot.pause()
            assert results == [False, True]

    asyncio.run(check())


def test_copy_keeps_literal_read_only_text_and_clipboard_action() -> None:
    async def check() -> None:
        app = App[None]()
        async with app.run_test(size=(60, 20)) as pilot:
            app.push_screen(CopyScreen("Copy bytes as hex", "00 41 ff"))
            await pilot.pause()
            area = app.screen.query_one(TextArea)
            assert area.read_only
            assert area.text == "00 41 ff"
            await pilot.click("#copy-confirm")
            assert app.clipboard == "00 41 ff"
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, CopyScreen)

    asyncio.run(check())
