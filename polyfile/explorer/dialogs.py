"""Offset navigation and keyboard help screens."""

import re

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class OffsetDialog(ModalScreen[int | None]):
    """Validate decimal and hexadecimal navigation in the active source."""

    DEFAULT_CSS = """
    OffsetDialog { align: center middle; }
    OffsetDialog > Vertical { width: 56; max-width: 95%; height: auto;
        padding: 1 2; border: thick $accent; background: $surface; }
    OffsetDialog #offset-error { color: $error; height: auto; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, length: int) -> None:
        super().__init__()
        self.length = length

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Go to byte offset (decimal or 0x hexadecimal)")
            yield Input(placeholder="0x0000", id="offset")
            yield Static("", id="offset-error", markup=False)
            yield Button("Go", id="offset-go", variant="primary")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def _submit(self) -> None:
        value = self.query_one(Input).value.strip()
        if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)", value):
            message = "Enter a decimal offset or hexadecimal beginning with 0x."
        elif not self.length:
            message = "This source has no bytes to navigate."
        else:
            base = 16 if value.lower().startswith("0x") else 10
            digits = (value[2:] if base == 16 else value).lstrip("0") or "0"
            maximum = f"{self.length - 1:x}" if base == 16 else str(self.length - 1)
            offset = self.length if len(digits) > len(maximum) else int(digits, base)
            if offset < self.length:
                self.dismiss(offset)
                return
            message = f"Enter an offset from 0 to {self.length - 1} (0x{self.length - 1:x})."
        self.query_one("#offset-error", Static).update(message)

    def on_input_submitted(self) -> None:
        self._submit()

    def on_button_pressed(self) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpDialog(ModalScreen[None]):
    """Display controls without leaving the explorer."""

    DEFAULT_CSS = """
    HelpDialog { align: center middle; }
    HelpDialog > Vertical { width: 66; max-width: 95%; height: auto; max-height: 95%;
        overflow-y: auto; padding: 1 2; border: thick $accent; background: $surface; }
    """
    BINDINGS = [("escape,enter,f1", "close", "Close help")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                "PolyFile explorer\n\n"
                "Tab / Shift+Tab   Move between controls\n"
                "Tree arrows       Navigate; Right expands, Left collapses\n"
                "Enter / click     Inspect a structure node\n"
                "Byte arrows       Move the byte cursor\n"
                "Shift+arrows      Extend byte selection\n"
                "Mouse drag        Select a byte range\n"
                "Home / End        First / last byte in the row\n"
                "Ctrl+Home / End   First / last byte in the source\n"
                "Page Up / Down    Move a page of bytes\n"
                "g                 Go to a decimal or 0x byte offset\n"
                "t                 Toggle hexadecimal / UTF-8 text\n"
                "s                 Choose a physical or decoded source\n"
                "/                 Search bytes or structure\n"
                "n / Shift+N       Next / previous search result\n"
                "Enter / Shift+Enter  Next / previous while searching\n"
                "e / Shift+E       Extract selection / complete source\n"
                "y / o             Copy selection as hex / copy offset\n"
                "Ctrl+G            Cancel background search, extraction, or copy\n"
                "F2                Switch structure / bytes on narrow screens\n"
                "q / Ctrl+Q        Quit    Ctrl+C interrupts\n\n"
                "Underlined dim bytes have no describing leaf node.\n"
                "Yellow bytes and tree nodes match the current search.\n"
                "Every displayed offset belongs to its named source.\n"
                "Escape returns to the explorer.",
                markup=False,
            )

    def action_close(self) -> None:
        self.dismiss(None)
