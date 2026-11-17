"""Destination, replacement, and clipboard dialogs for explorer actions."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static, TextArea

from polyfile.matchtree import literal


class ExportScreen(ModalScreen[Path | None]):
    """Ask for an explicit destination without deriving paths from member names."""

    DEFAULT_CSS = """
    ExportScreen { align: center middle; }
    ExportScreen > Vertical { width: 76; max-width: 95%; height: auto;
        padding: 1 2; background: $panel; border: round $accent; }
    ExportScreen Input { margin: 1 0; }
    ExportScreen Horizontal { height: auto; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"Export {literal(self.label)}", markup=False)
            yield Input(placeholder="Destination path", id="export-path")
            with Horizontal():
                yield Button("Export", variant="primary", id="export-confirm")
                yield Button("Cancel", id="export-cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def _submit(self) -> None:
        value = self.query_one(Input).value.strip()
        if value:
            self.dismiss(Path(value).expanduser())
        else:
            self.notify("Enter a destination path.", severity="error")

    def on_input_submitted(self) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export-confirm":
            self._submit()
        else:
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ReplaceScreen(ModalScreen[bool]):
    """Confirm replacement of the exact destination selected by the user."""

    DEFAULT_CSS = """
    ReplaceScreen { align: center middle; }
    ReplaceScreen > Vertical { width: 76; max-width: 95%; height: auto;
        padding: 1 2; background: $panel; border: round $warning; }
    ReplaceScreen Horizontal { height: auto; margin-top: 1; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, destination: Path) -> None:
        super().__init__()
        self.destination = destination

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"Replace existing file?\n{literal(self.destination)}", markup=False)
            with Horizontal():
                yield Button("Replace", variant="warning", id="replace-confirm")
                yield Button("Cancel", id="replace-cancel")

    def on_mount(self) -> None:
        self.query_one("#replace-cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "replace-confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)


class CopyScreen(ModalScreen[None]):
    """Keep prepared text available even without terminal clipboard integration."""

    DEFAULT_CSS = """
    CopyScreen { align: center middle; }
    CopyScreen > Vertical { width: 90; max-width: 95%; height: 70%; min-height: 12;
        padding: 1 2; background: $panel; border: round $accent; }
    CopyScreen TextArea { height: 1fr; margin: 1 0; }
    CopyScreen Horizontal { height: auto; }
    """
    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, title: str, text: str) -> None:
        super().__init__()
        self.heading = title
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.heading, markup=False)
            yield Static("Select the text and use your terminal's copy command if needed.",
                         markup=False)
            yield TextArea(self.text, read_only=True, id="copy-text")
            with Horizontal():
                yield Button("Copy to clipboard", variant="primary", id="copy-confirm")
                yield Button("Close", id="copy-close")

    def on_mount(self) -> None:
        self.query_one(TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-confirm":
            self.app.copy_to_clipboard(self.text)
            self.notify("Clipboard requested; terminal support varies.")
        else:
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)
