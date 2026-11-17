"""Source-aware terminal inspection of a completed file analysis."""

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Label, Select, Static, Tree

from polyfile.explorer.byteview import ByteView
from polyfile.explorer.dialogs import HelpDialog, OffsetDialog
from polyfile.explorer.model import ByteRange, ExplorerModel
from polyfile.explorer.tree import StructureTree
from polyfile.matchtree import literal


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
    ]

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__()
        self.model = model
        self.active_source = "file"
        self.selection = ByteRange("file", 0, min(1, model.sources["file"].length))
        self.selected_node: int | None = None
        self._show_tree = False

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
        self.screen.set_class(width < 110, "narrow")
        self.screen.set_class(self._show_tree, "show-tree")

    def select_node(self, uid: int) -> None:
        """Reveal a structure node and select its exact source-qualified range."""
        node = self.model.nodes[uid]
        self.selected_node = uid
        self.query_one(StructureTree).reveal(uid)
        self.select_range(node.range, node=uid)
        if self.size.width < 110:
            self._show_tree = False
            self._update_layout(self.size.width)

    def select_range(self, selected: ByteRange, *, node: int | None = None) -> None:
        """Select bytes from one source, clamping malformed display extents."""
        self.selection = self.model.clamp_range(selected)
        self.active_source = self.selection.source
        self.selected_node = node
        self.query_one("#source", Select).value = self.active_source
        self.query_one(ByteView).show_range(self.selection)
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

    def action_leave(self) -> None:
        self.exit(0)

    def action_interrupt(self) -> None:
        self.exit(130, return_code=130)
