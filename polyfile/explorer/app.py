"""Source-aware terminal inspection of a completed file analysis."""

from concurrent.futures import CancelledError
from functools import partial
from pathlib import Path
from typing import Literal

from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Footer, Label, Select, Static, Tree
from textual.worker import get_current_worker

from polyfile.explorer.byteview import ByteView
from polyfile.explorer.dialogs import HelpDialog, OffsetDialog
from polyfile.explorer.export import export_range, selection_hex
from polyfile.explorer.model import ByteRange, ExplorerModel
from polyfile.explorer.searchpanel import SearchPanel
from polyfile.explorer.tools_dialogs import CopyScreen, ExportScreen, ReplaceScreen
from polyfile.explorer.tree import StructureTree
from polyfile.matchtree import literal


class OperationFinished(Message):
    """Deliver completed extraction or clipboard work to the UI thread."""

    def __init__(
        self,
        generation: int,
        text: str,
        *,
        kind: Literal["export", "copy"],
        error: bool = False,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.text = text
        self.kind = kind
        self.error = error


class ExplorerApp(App[int]):
    """Inspect completed matches without serializing their byte buffers."""

    CSS = """
    Screen { layout: vertical; }
    #title { height: 1; background: $primary; color: $text; padding: 0 1; }
    #toolbar { height: 3; }
    #toolbar Label { width: 8; padding: 1 0; }
    #source { width: 1fr; }
    #toolbar Button { min-width: 10; width: auto; }
    #workspace { height: 1fr; }
    #structure { width: 32%; height: 1fr; border: solid $primary; }
    #structure:focus { border: double $accent; }
    #byte-pane { width: 1fr; height: 1fr; }
    #details { height: 6; padding: 0 1; overflow-y: auto; }
    #interpretations { height: 3; }
    #status { height: 1; padding: 0 1; }
    .compact #details { height: 3; }
    .short #details { height: 1; }
    .narrow #structure { display: none; width: 1fr; }
    .narrow.show-tree #structure { display: block; }
    .narrow.show-tree #byte-pane { display: none; }
    """
    BINDINGS = [
        Binding("q", "leave", "Quit"),
        Binding("ctrl+q", "leave", show=False, priority=True),
        Binding("ctrl+c", "interrupt", show=False, priority=True),
        Binding("g", "goto", "Go to"),
        Binding("t", "toggle_mode", "Hex/Text"),
        Binding("s", "sources", "Sources"),
        Binding("f2", "switch_pane", "Pane"),
        Binding("f1", "show_help", "Help"),
        Binding("slash", "search", "Search"),
        Binding("n", "next_result", "Next hit", show=False),
        Binding("shift+n", "previous_result", "Previous hit", show=False),
        Binding("e", "export_selection", "Extract"),
        Binding("shift+e", "export_source", "Extract source", show=False),
        Binding("y", "copy_hex", "Copy hex", show=False),
        Binding("o", "copy_offset", "Copy offset", show=False),
        Binding("ctrl+g", "cancel_work", "Cancel work", show=False, priority=True),
    ]

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__()
        self.model = model
        self.active_source = "file"
        self.selection = ByteRange("file", 0, min(1, model.sources["file"].length))
        self.selected_node: int | None = None
        self._show_tree = False
        self._selecting_search = False
        self._operation_generation = 0

    def compose(self) -> ComposeResult:
        outcome = "Partial analysis" if self.model.partial else "Analysis complete"
        title = Text(f"PolyFile | {literal(self.model.path.name)} | {outcome}")
        yield Static(title, id="title")
        with Horizontal(id="toolbar"):
            yield Label("Source")
            options = [(Text(literal(name)), name) for name in self.model.sources]
            yield Select(options, value="file", allow_blank=False, id="source")
            yield Button("Text", id="mode")
            yield Button("Go to", id="goto")
        yield SearchPanel(self.model, id="search-panel")
        with Horizontal(id="workspace"):
            yield StructureTree(self.model)
            with Vertical(id="byte-pane"):
                yield ByteView(self.model)
                yield Static("", id="details", markup=False)
                yield Select(
                    [(Text("Reveal a containing node…"), -1)],
                    value=-1,
                    allow_blank=False,
                    id="interpretations",
                )
        yield Static("", id="status", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(StructureTree).border_title = "Structure"
        self.query_one(ByteView).border_title = "Bytes"
        self.select_range(self.selection)
        self._update_layout(self.size.width)
        self.query_one(ByteView).focus()

    def on_resize(self, event: events.Resize) -> None:
        self._update_layout(event.size.width)

    def _update_layout(self, width: int) -> None:
        screen = self.screen_stack[0]
        screen.set_class(width < 110, "narrow")
        screen.set_class(self.size.height < 30, "compact")
        screen.set_class(self.size.height < 24, "short")
        screen.set_class(self._show_tree, "show-tree")

    def select_node(self, uid: int) -> None:
        """Reveal a structure node and select its exact source-qualified range."""
        node = self.model.nodes[uid]
        self.selected_node = uid
        self.query_one(StructureTree).reveal(uid)
        self.select_range(node.range, node=uid)
        if self.size.width < 110:
            self._show_tree = False
            self._update_layout(self.size.width)
            self.query_one(ByteView).focus()

    def select_range(self, selected: ByteRange, *, node: int | None = None) -> None:
        """Select bytes from one source, clamping malformed display extents."""
        self.selection = self.model.clamp_range(selected)
        self.active_source = self.selection.source
        self.selected_node = node
        self.query_one("#source", Select).value = self.active_source
        self.query_one(ByteView).show_range(self.selection)
        self.query_one(SearchPanel).set_source(
            self.active_source, preserve_search=self._selecting_search
        )
        self._update_details()

    def _update_details(self) -> None:
        selected = self.selection
        source = self.model.sources[self.active_source]
        text = Text(
            f"Source: {literal(selected.source)}   Offset: 0x{selected.start:x} "
            f"({selected.start})   Length: {selected.length:,} bytes\n"
        )
        if self.selected_node is not None:
            node = self.model.nodes[self.selected_node]
            text.append(f"{literal(node.name)} | {literal(node.type)}\n", style="bold")
            if node.value is not None:
                text.append(
                    f"Value: {literal(node.value[:1024])}{'…' if len(node.value) > 1024 else ''}\n"
                )
            if node.analysis_status:
                text.append(
                    f"{literal(node.analysis_status)}: {literal(node.analysis_message or '')}\n",
                    style="yellow",
                )
        if not source.available:
            text.append("Decoded byte buffer is unavailable.\n", style="bold red")
        self.query_one("#details", Static).update(text)
        self._update_interpretations()
        gaps = sum(gap.length for gap in self.model.undescribed(self.active_source))
        status = f"{source.length:,} source bytes | {gaps:,} undescribed | F1 for controls"
        self.query_one("#status", Static).update(status)

    def _update_interpretations(self) -> None:
        nodes = self.model.nodes_at(self.active_source, self.selection.start)
        options: list[tuple[Text, int]] = [(Text(f"Reveal a containing node ({len(nodes)})…"), -1)]
        for node in nodes:
            options.append(
                (Text(f"{literal(node.name)} @ 0x{node.offset:x} +{node.size}"), node.uid)
            )
        chooser = self.query_one("#interpretations", Select)
        chooser.set_options(options)
        chooser.value = -1

    def on_tree_node_selected(self, event: Tree.NodeSelected[int]) -> None:
        if event.node.data is not None:
            self.select_node(event.node.data)

    def on_byte_view_range_selected(self, event: ByteView.RangeSelected) -> None:
        if event.selected is not self.query_one(ByteView).selection:
            return
        if event.selected.source != self.active_source:
            return
        self.selection = event.selected
        self.selected_node = None
        self._update_details()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value != event.select.value:
            return
        if event.select.id == "source" and isinstance(event.value, str):
            if event.value != self.active_source:
                length = self.model.sources[event.value].length
                self.select_range(ByteRange(event.value, 0, min(1, length)))
        elif event.select.id == "interpretations" and isinstance(event.value, int):
            if event.value >= 0:
                self.select_node(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mode":
            self.action_toggle_mode()
        elif event.button.id == "goto":
            self.action_goto()

    def action_toggle_mode(self) -> None:
        view = self.query_one(ByteView)
        view.text_mode = not view.text_mode
        view.border_title = "UTF-8 text" if view.text_mode else "Bytes"
        self.query_one("#mode", Button).label = "Hex" if view.text_mode else "Text"
        view.show_range(self.selection)

    def action_goto(self) -> None:
        self.push_screen(OffsetDialog(self.model.sources[self.active_source].length), self._goto)

    def _goto(self, offset: int | None) -> None:
        if offset is not None:
            self.select_range(ByteRange(self.active_source, offset, 1))
            self.query_one(ByteView).focus()

    def action_sources(self) -> None:
        self.query_one("#source", Select).focus()

    def action_switch_pane(self) -> None:
        self._show_tree = not self._show_tree
        self._update_layout(self.size.width)
        target = self.query_one(StructureTree) if self._show_tree else self.query_one(ByteView)
        target.focus()

    def action_show_help(self) -> None:
        self.push_screen(HelpDialog())

    def action_search(self) -> None:
        self.query_one(SearchPanel).query_one("#search-query").focus()

    def action_next_result(self) -> None:
        self.query_one(SearchPanel).next_result()

    def action_previous_result(self) -> None:
        self.query_one(SearchPanel).next_result(-1)

    def on_search_panel_results_changed(self, event: SearchPanel.ResultsChanged) -> None:
        if event.generation != self.query_one(SearchPanel).generation:
            return
        self.query_one(ByteView).set_search_ranges(hit.range for hit in event.hits)
        self.query_one(StructureTree).set_search_nodes(
            {uid for hit in event.hits for uid in hit.nodes}
        )

    def on_search_panel_result_selected(self, event: SearchPanel.ResultSelected) -> None:
        if event.generation != self.query_one(SearchPanel).generation:
            return
        focused = self.focused
        self._selecting_search = True
        try:
            if event.hit.nodes:
                self.select_node(event.hit.nodes[0])
            else:
                self.select_range(event.hit.range)
        finally:
            self._selecting_search = False
        if self.size.width < 110:
            self._show_tree = False
            self._update_layout(self.size.width)
        if focused is not None and self.query_one(SearchPanel) in focused.ancestors:
            focused.focus()

    def action_export_selection(self) -> None:
        self._request_export(self.selection)

    def action_export_source(self) -> None:
        self._request_export(
            ByteRange(self.active_source, 0, self.model.sources[self.active_source].length)
        )

    def _request_export(self, selection: ByteRange) -> None:
        if not self.model.sources[selection.source].available:
            self._tools_status("The selected source's bytes are unavailable.")
            return
        label = f"{selection.source} @ 0x{selection.start:x} · {selection.length:,} bytes"
        self.push_screen(ExportScreen(label), partial(self._export_destination, selection))

    def _export_destination(self, selection: ByteRange, destination: Path | None) -> None:
        if destination is None:
            return
        try:
            exists = destination.exists() or destination.is_symlink()
        except (OSError, ValueError) as error:
            self._tools_status(f"Cannot inspect destination: {error}")
            return
        if exists:
            self.push_screen(
                ReplaceScreen(destination), partial(self._confirm_export, selection, destination)
            )
        else:
            self._start_export(selection, destination)

    def _confirm_export(
        self,
        selection: ByteRange,
        destination: Path,
        approved: bool | None,
    ) -> None:
        if approved:
            self._start_export(selection, destination, overwrite=True)

    def _start_export(
        self,
        selection: ByteRange,
        destination: Path,
        *,
        overwrite: bool = False,
    ) -> None:
        self._operation_generation += 1
        self._tools_status("Exporting… · Ctrl+G cancels background work")
        self._export(
            selection, destination, overwrite=overwrite, generation=self._operation_generation
        )

    @work(thread=True, exclusive=True, group="operation")
    def _export(
        self,
        selection: ByteRange,
        destination: Path,
        *,
        overwrite: bool,
        generation: int,
    ) -> None:
        worker = get_current_worker()
        try:
            export_range(
                self.model.sources[selection.source],
                selection,
                destination,
                input_path=self.model.path,
                overwrite=overwrite,
                cancelled=lambda: worker.is_cancelled,
            )
        except CancelledError:
            return
        except (OSError, ValueError) as error:
            self.post_message(OperationFinished(generation, str(error), kind="export", error=True))
        else:
            self.post_message(OperationFinished(generation, str(destination), kind="export"))

    def action_copy_offset(self) -> None:
        self.push_screen(CopyScreen("Copy offset", f"0x{self.selection.start:x}"))

    def action_copy_hex(self) -> None:
        self._operation_generation += 1
        self._tools_status("Preparing hexadecimal bytes… · Ctrl+G cancels background work")
        self._copy_hex(self.selection, generation=self._operation_generation)

    @work(thread=True, exclusive=True, group="operation")
    def _copy_hex(self, selection: ByteRange, *, generation: int) -> None:
        worker = get_current_worker()
        try:
            text = selection_hex(
                self.model.sources[selection.source],
                selection,
                cancelled=lambda: worker.is_cancelled,
            )
        except CancelledError:
            return
        except (OSError, ValueError) as error:
            self.post_message(OperationFinished(generation, str(error), kind="copy", error=True))
        else:
            self.post_message(OperationFinished(generation, text, kind="copy"))

    def on_operation_finished(self, message: OperationFinished) -> None:
        if message.generation != self._operation_generation:
            return
        if message.error:
            self._tools_status(message.text)
        elif message.kind == "copy":
            self._tools_status("Hexadecimal bytes are ready to copy.")
            self.push_screen(CopyScreen("Copy bytes as hex", message.text))
        else:
            self._tools_status(f"Saved exact bytes to {message.text}")

    def _tools_status(self, text: str) -> None:
        self.query_one("#status", Static).update(literal(text))

    def action_cancel_work(self) -> None:
        self._operation_generation += 1
        self.workers.cancel_group(self, "operation")
        self.query_one(SearchPanel).cancel_search()
        self._tools_status("Background work cancelled.")

    def action_leave(self) -> None:
        self.exit(0)

    def action_interrupt(self) -> None:
        self.exit(130, return_code=130)
