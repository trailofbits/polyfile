"""A bounded live view and complete final view of discovered file types."""

from dataclasses import dataclass
from threading import RLock

from rich.text import Text
from rich.tree import Tree


def literal(value: object, *, multiline: bool = False, encoding: str = "utf-8") -> str:
    """Escape terminal controls without interpreting markup in input-derived text."""
    text = "".join(
        char
        if (char.isprintable() or (multiline and char == "\n"))
        else ascii(char)[1:-1]
        for char in str(value)
    )
    return text.encode(encoding, "backslashreplace").decode(encoding)


@dataclass(frozen=True)
class Discovery:
    """One file-type verdict in its physical or decoded coordinate source."""

    key: str
    name: str
    parent: str | None = None
    member: str = ""
    offset: int = 0
    size: int = 0
    source: str = "file"

    def label(self, *, compact: bool, encoding: str) -> Text:
        """Render one line without treating file contents as terminal markup."""
        text = Text(
            literal(self.name, encoding=encoding),
            style="bold cyan",
            no_wrap=compact,
            overflow="ellipsis" if compact else "fold",
        )
        if self.member:
            text.append(f"  {literal(self.member, encoding=encoding)}", style="magenta")
        source = literal(self.source, encoding=encoding)
        text.append(
            f"  @ 0x{self.offset:x} | {self.size:,} bytes | {source}",
            style="dim",
        )
        return text


class MatchTree:
    """Retain every discovery while restricting live rendering to a screenful."""

    def __init__(self) -> None:
        self._nodes: dict[str, Discovery] = {}
        self._notes: dict[str, list[str]] = {}
        self._lock = RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

    def add(self, discovery: Discovery) -> None:
        """Add or update a verdict without counting replayed results twice."""
        with self._lock:
            self._nodes[discovery.key] = discovery

    def annotate(self, key: str, message: str) -> None:
        """Attach a parser limitation or failure to its containing file type."""
        with self._lock:
            notes = self._notes.setdefault(key, [])
            if message not in notes:
                notes.append(message)

    def _selection(self, nodes: dict[str, Discovery], limit: int | None) -> set[str]:
        if limit is None:
            return set(nodes)
        selected: set[str] = set()
        for key in reversed(nodes):
            ancestry: set[str] = set()
            current: str | None = key
            while (
                current is not None
                and current in nodes
                and current not in ancestry
                and len(ancestry) < limit
            ):
                ancestry.add(current)
                current = nodes[current].parent
            if not selected or len(selected | ancestry) <= limit:
                selected.update(ancestry)
            if len(selected) >= limit:
                break
        return selected

    def render(self, *, limit: int | None = None, encoding: str = "utf-8") -> Tree:
        """Build a file-type tree with recent matches and ancestors when bounded."""
        with self._lock:
            nodes = self._nodes.copy()
            notes = {key: tuple(value) for key, value in self._notes.items()}
        selected = self._selection(nodes, limit)
        tree = Tree(Text("Matches", style="bold"), guide_style="dim")
        if not nodes:
            tree.add(Text("No matches found", style="dim"))
        omitted = len(nodes) - len(selected)
        if omitted:
            tree.add(
                Text(f"{omitted:,} earlier matches hidden while scanning", style="dim")
            )
        branches: dict[str, Tree] = {}
        for key, discovery in nodes.items():
            if key in selected:
                label = discovery.label(compact=limit is not None, encoding=encoding)
                for note in notes.get(key, ()):
                    label.append(
                        f" | {literal(note, encoding=encoding)}", style="yellow"
                    )
                parent = (
                    branches.get(discovery.parent, tree)
                    if discovery.parent is not None
                    else tree
                )
                branches[key] = parent.add(label)
        return tree
