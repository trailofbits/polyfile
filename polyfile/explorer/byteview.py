"""A viewport-sized hex and UTF-8 display with source-aware selections."""

from bisect import bisect_right
from collections.abc import Iterable

from rich.cells import cell_len
from rich.segment import Segment
from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip

from polyfile.explorer.model import ByteRange, ExplorerModel
from polyfile.explorer.rendering import text_units
from polyfile.matchtree import literal


class ByteView(ScrollView, can_focus=True):
    """Read and render only the currently visible byte rows."""

    DEFAULT_CSS = """
    ByteView { height: 1fr; width: 1fr; overflow-x: hidden; border: solid $primary; }
    ByteView:focus { border: double $accent; }
    """
    BINDINGS = [
        Binding("left", "move('left')", show=False),
        Binding("right", "move('right')", show=False),
        Binding("up", "move('up')", show=False),
        Binding("down", "move('down')", show=False),
        Binding("shift+left", "move('left', True)", show=False),
        Binding("shift+right", "move('right', True)", show=False),
        Binding("shift+up", "move('up', True)", show=False),
        Binding("shift+down", "move('down', True)", show=False),
        Binding("home", "move('home')", show=False),
        Binding("end", "move('end')", show=False),
        Binding("ctrl+home", "move('first')", show=False),
        Binding("ctrl+end", "move('last')", show=False),
        Binding("pageup", "move('pageup')", show=False),
        Binding("pagedown", "move('pagedown')", show=False),
    ]

    class RangeSelected(Message):
        """A user selected a source-qualified byte range."""

        def __init__(self, selected: ByteRange) -> None:
            super().__init__()
            self.selected = selected

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__(id="bytes")
        self.model = model
        self.source_id = "file"
        self.selection = ByteRange("file", 0, 0)
        self.text_mode = False
        self.bytes_per_row = 16
        self.cursor = 0
        self.selection_anchor = 0
        self.selection_anchor_end = 0
        self._cells: dict[int, list[tuple[int, int, ByteRange]]] = {}
        self._gaps: tuple[ByteRange, ...] = ()
        self._gap_starts: tuple[int, ...] = ()
        self._dragging = False
        self._search_ranges: dict[str, tuple[ByteRange, ...]] = {}
        self._search_starts: dict[str, tuple[int, ...]] = {}

    def set_search_ranges(self, ranges: Iterable[ByteRange]) -> None:
        """Highlight merged search intervals without scanning every hit for every byte."""
        grouped: dict[str, list[ByteRange]] = {}
        for selected in ranges:
            selected = self.model.clamp_range(selected)
            if selected.length:
                grouped.setdefault(selected.source, []).append(selected)
        self._search_ranges = {}
        for source, selections in grouped.items():
            merged: list[ByteRange] = []
            for selected in sorted(selections, key=lambda value: value.start):
                if merged and selected.start <= merged[-1].end:
                    previous = merged[-1]
                    merged[-1] = ByteRange(
                        source, previous.start, max(previous.end, selected.end) - previous.start
                    )
                else:
                    merged.append(selected)
            self._search_ranges[source] = tuple(merged)
        self._search_starts = {
            source: tuple(selected.start for selected in selections)
            for source, selections in self._search_ranges.items()
        }
        self.refresh()

    def on_resize(self) -> None:
        self._update_size()

    def _update_size(self) -> None:
        width = max(1, self.scrollable_content_region.width)
        digits = max(4, len(f"{self.model.sources[self.source_id].length:x}"))
        if self.text_mode:
            self.bytes_per_row = max(4, width - digits - 3)
        else:
            self.bytes_per_row = max(1, min(16, (width - digits - 5) // 4))
        length = self.model.sources[self.source_id].length
        rows = max(1, (length + self.bytes_per_row - 1) // self.bytes_per_row)
        self.virtual_size = Size(width, rows)
        self._cells.clear()
        self.refresh()

    def show_range(self, selected: ByteRange, *, reveal: bool = True) -> None:
        """Display a selection, keeping its cursor and source in byte coordinates."""
        changed = selected.source != self.source_id
        self.source_id = selected.source
        self.selection = selected
        self.selection_anchor = selected.start
        self.selection_anchor_end = selected.end
        self.cursor = selected.start
        self._gaps = self.model.undescribed(self.source_id)
        self._gap_starts = tuple(gap.start for gap in self._gaps)
        if changed:
            self.scroll_to(y=0, animate=False, immediate=True)
        self._update_size()
        if reveal:
            self._reveal_cursor()

    def _reveal_cursor(self) -> None:
        row = self.cursor // self.bytes_per_row
        height = max(1, self.scrollable_content_region.height)
        if row < self.scroll_offset.y or row >= self.scroll_offset.y + height:
            top = max(0, row - (1 if self.text_mode else 0))
            self.scroll_to(y=top, animate=False, immediate=True)

    def _style(self, selected: ByteRange) -> str:
        if selected.start < self.selection.end and selected.end > self.selection.start:
            return "reverse bold"
        ranges = self._search_ranges.get(self.source_id, ())
        starts = self._search_starts.get(self.source_id, ())
        if self._overlaps(ranges, starts, selected):
            return "bold yellow"
        if self._overlaps(self._gaps, self._gap_starts, selected):
            return "dim underline"
        return ""

    @staticmethod
    def _overlaps(
        ranges: tuple[ByteRange, ...],
        starts: tuple[int, ...],
        selected: ByteRange,
    ) -> bool:
        index = bisect_right(starts, selected.start) - 1
        return (index >= 0 and ranges[index].end > selected.start) or (
            index + 1 < len(ranges) and ranges[index + 1].start < selected.end
        )

    def render_line(self, y: int) -> Strip:
        row = y + self.scroll_offset.y
        start = row * self.bytes_per_row
        source = self.model.sources[self.source_id]
        width = self.scrollable_content_region.width
        if not source.available:
            return Strip([Segment("Source bytes are unavailable", self.rich_style)]).crop_extend(
                0, width, self.rich_style
            )
        if start >= source.length:
            label = "Empty source" if source.length == 0 and row == 0 else ""
            return Strip([Segment(label, self.rich_style)]).crop_extend(0, width, self.rich_style)
        count = min(self.bytes_per_row, source.length - start)
        try:
            text = (
                self._render_text(row, start, count)
                if self.text_mode
                else self._render_hex(row, start, source.read(start, count))
            )
        except OSError as error:
            text = Text(literal(error), style="bold red")
        return (
            Strip(text.render(self.app.console))
            .apply_style(self.rich_style)
            .crop_extend(0, width, self.rich_style)
        )

    def _new_row(self, row: int, start: int) -> Text:
        self._cells[row] = []
        height = max(1, self.scrollable_content_region.height)
        self._cells = {
            key: cells
            for key, cells in self._cells.items()
            if self.scroll_offset.y <= key < self.scroll_offset.y + height
        }
        digits = max(4, len(f"{self.model.sources[self.source_id].length:x}"))
        text = Text(f"{start:0{digits}x}  ")
        text.stylize("dim")
        return text

    def _append_cell(self, text: Text, row: int, glyph: str, selected: ByteRange) -> None:
        column = text.cell_len
        text.append(glyph, style=self._style(selected))
        self._cells[row].append((column, column + cell_len(glyph), selected))

    def _render_hex(self, row: int, start: int, data: bytes) -> Text:
        text = self._new_row(row, start)
        for index, byte in enumerate(data):
            self._append_cell(text, row, f"{byte:02x}", ByteRange(self.source_id, start + index, 1))
            text.append(" ")
        text.append("   " * (self.bytes_per_row - len(data)) + " ")
        for index, byte in enumerate(data):
            glyph = chr(byte) if 32 <= byte < 127 else "·"
            self._append_cell(text, row, glyph, ByteRange(self.source_id, start + index, 1))
        return text

    def _render_text(self, row: int, start: int, count: int) -> Text:
        text = self._new_row(row, start)
        for unit in text_units(self.model.sources[self.source_id], start, count):
            self._append_cell(text, row, unit.text, unit.range)
        return text

    def action_move(self, direction: str, extend: bool = False) -> None:
        length = self.model.sources[self.source_id].length
        if not length:
            return
        row = self.cursor // self.bytes_per_row
        page = self.bytes_per_row * max(1, self.scrollable_content_region.height - 1)
        targets = {
            "left": self.cursor - 1,
            "right": self.cursor + 1,
            "up": self.cursor - self.bytes_per_row,
            "down": self.cursor + self.bytes_per_row,
            "home": row * self.bytes_per_row,
            "end": (row + 1) * self.bytes_per_row - 1,
            "first": 0,
            "last": length - 1,
            "pageup": self.cursor - page,
            "pagedown": self.cursor + page,
        }
        self._choose(max(0, min(length - 1, targets[direction])), extend)

    def _choose(self, offset: int, extend: bool, length: int = 1) -> None:
        if not extend:
            self.selection_anchor = offset
            self.selection_anchor_end = offset + length
        self.cursor = offset
        start = min(self.selection_anchor, offset)
        end = max(self.selection_anchor_end, offset + length)
        self.selection = ByteRange(self.source_id, start, end - start)
        self._reveal_cursor()
        self.refresh()
        self.post_message(self.RangeSelected(self.selection))

    def _mouse_range(self, event: events.MouseEvent) -> ByteRange | None:
        offset = event.get_content_offset(self)
        if offset is None:
            return None
        row = offset.y + self.scroll_offset.y
        for start, end, selected in self._cells.get(row, ()):
            if start <= offset.x < end:
                return selected
        return None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        selected = self._mouse_range(event)
        if event.button == 1 and selected is not None:
            self.focus()
            self._dragging = True
            self.capture_mouse()
            self._choose(selected.start, event.shift, selected.length)
            event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        selected = self._mouse_range(event)
        if self._dragging and selected is not None:
            self._choose(selected.start, True, selected.length)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()
