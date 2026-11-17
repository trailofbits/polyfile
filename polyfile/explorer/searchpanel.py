"""Search controls and cancellable workers for the terminal explorer."""

from concurrent.futures import CancelledError
from typing import cast

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Checkbox, Input, Select, Static
from textual.worker import get_current_worker

from polyfile.explorer.model import ExplorerModel
from polyfile.explorer.search import SearchHit, SearchMode, search
from polyfile.matchtree import literal


class SearchFinished(Message):
    """Deliver a worker result to its search panel's UI thread."""

    def __init__(self, generation: int, hits: list[SearchHit], error: str = "") -> None:
        super().__init__()
        self.generation = generation
        self.hits = hits
        self.error = error


class SearchPanel(Vertical):
    """Search bytes and structure while keeping the main explorer interactive."""

    DEFAULT_CSS = """
    SearchPanel { height: auto; }
    SearchPanel > Horizontal { height: 3; }
    SearchPanel Input { width: 1fr; }
    SearchPanel Button { min-width: 5; width: 5; }
    SearchPanel Select { width: 1fr; }
    SearchPanel Checkbox { width: 18; }
    SearchPanel #search-status { height: 1; padding: 0 1; }
    """
    BINDINGS = [("shift+enter", "previous", "Previous result")]

    class ResultSelected(Message):
        """Request source-qualified navigation without restarting the search."""

        def __init__(self, hit: SearchHit, generation: int) -> None:
            super().__init__()
            self.hit = hit
            self.generation = generation

    class ResultsChanged(Message):
        """Update highlight ranges, including when a query is cleared."""

        def __init__(self, hits: list[SearchHit], generation: int) -> None:
            super().__init__()
            self.hits = hits
            self.generation = generation

    def __init__(self, model: ExplorerModel, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.model = model
        self.active_source = "file"
        self.results: list[SearchHit] = []
        self.current = 0
        self.generation = 0

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="Search bytes or structure…", id="search-query")
            yield Button("↑", id="search-previous", tooltip="Previous result")
            yield Button("↓", id="search-next", tooltip="Next result")
        with Horizontal():
            yield Select(
                [
                    ("Combined", "combined"),
                    ("Text", "text"),
                    ("Hex bytes", "hex"),
                    ("Structure", "structure"),
                ],
                value="combined",
                allow_blank=False,
                id="search-mode",
            )
            yield Select(
                [("All sources", "all"), ("Current source", "current")],
                value="all",
                allow_blank=False,
                id="search-scope",
            )
            yield Checkbox("Match case", id="search-case")
        yield Static("", id="search-status", markup=False)

    def start_search(self) -> None:
        """Replace the query atomically; older worker results cannot update the UI."""
        if not self.is_mounted:
            return
        self.cancel_search()
        query = self.query_one("#search-query", Input).value
        if not query:
            self._status("")
            return
        self._status("Searching… · Ctrl+G cancels background work")
        mode = cast(SearchMode, self.query_one("#search-mode", Select).value)
        scope = self.query_one("#search-scope", Select).value
        self._search(
            query,
            mode=mode,
            source=self.active_source if scope == "current" else None,
            match_case=self.query_one(Checkbox).value,
            generation=self.generation,
        )

    def cancel_search(self) -> None:
        """Discard results and request cooperative cancellation of active searches."""
        self.generation += 1
        self.workers.cancel_group(self, "search")
        self.results = []
        self.current = 0
        self.post_message(self.ResultsChanged([], self.generation))
        if self.is_mounted:
            self._status("Search cancelled")
            self._navigation_enabled(False)

    @work(thread=True, exclusive=True, group="search")
    def _search(
        self,
        query: str,
        *,
        mode: SearchMode,
        source: str | None,
        match_case: bool,
        generation: int,
    ) -> None:
        worker = get_current_worker()
        cancelled = lambda: worker.is_cancelled or generation != self.generation
        try:
            hits = search(
                self.model,
                query,
                mode=mode,
                source=source,
                match_case=match_case,
                cancelled=cancelled,
            )
        except CancelledError:
            return
        except (OSError, ValueError, UnicodeError) as error:
            if not cancelled():
                self.post_message(SearchFinished(generation, [], str(error)))
        else:
            if not cancelled():
                self.post_message(SearchFinished(generation, hits))

    def on_search_finished(self, message: SearchFinished) -> None:
        message.stop()
        if message.generation != self.generation:
            return
        self.results = message.hits
        self.current = 0
        self.post_message(self.ResultsChanged(self.results, self.generation))
        self._navigation_enabled(bool(self.results))
        if message.error:
            self._status(message.error)
        elif not self.results:
            self._status("0 results" + self._buffer_note())
        else:
            self._show_result()

    def _navigation_enabled(self, enabled: bool) -> None:
        for button in self.query(Button):
            button.disabled = not enabled

    def _status(self, message: str) -> None:
        self.query_one("#search-status", Static).update(literal(message))

    def _show_result(self) -> None:
        hit = self.results[self.current]
        self._status(
            f"{self.current + 1} of {len(self.results)} · "
            f"{hit.range.source} @ 0x{hit.range.start:x} · {', '.join(hit.kinds)}"
            + self._buffer_note()
        )
        self.post_message(self.ResultSelected(hit, self.generation))

    def _buffer_note(self) -> str:
        sources = self.model.sources
        if self.query_one("#search-scope", Select).value == "current":
            sources = {self.active_source: sources[self.active_source]}
        missing = sum(not source.available for source in sources.values())
        return f" · {missing} source buffer(s) unavailable" if missing else ""

    def next_result(self, step: int = 1) -> None:
        """Navigate results cyclically, preserving their original scope and ordering."""
        if self.results:
            self.current = (self.current + step) % len(self.results)
            self._show_result()

    def action_previous(self) -> None:
        self.next_result(-1)

    def set_source(self, source: str, *, preserve_search: bool = False) -> None:
        """Rerun current-source queries only after manual source changes."""
        changed = self.active_source != source
        self.active_source = source
        if changed and not preserve_search and self.is_mounted:
            if self.query_one("#search-scope", Select).value == "current":
                self.start_search()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if event.value == event.input.value:
            self.start_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.next_result()

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        if event.value == event.select.value:
            self.start_search()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.stop()
        if event.value == event.checkbox.value:
            self.start_search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.next_result(-1 if event.button.id == "search-previous" else 1)
