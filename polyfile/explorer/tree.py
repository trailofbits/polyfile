"""Lazily materialize structure widgets from the completed analysis."""

from rich.text import Text
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from polyfile.explorer.model import ExplorerModel
from polyfile.matchtree import literal


class StructureTree(Tree[int]):
    """Add children only when their parent is expanded or explicitly revealed."""

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__(Text(literal(model.path.name)), id="structure")
        self.model = model
        self.entries: dict[int, TreeNode[int]] = {}
        self.loaded: set[int] = set()
        self.search_nodes: set[int] = set()
        self.auto_expand = False

    def on_mount(self) -> None:
        for uid in self.model.roots:
            self._append_entry(self.root, uid)
        self.root.expand()
        if self.model.roots:
            self.reveal(self.model.roots[0])

    def _append_entry(self, parent: TreeNode[int], uid: int) -> None:
        node = self.model.nodes[uid]
        self.entries[uid] = parent.add(self._label(uid), data=uid, allow_expand=bool(node.children))

    def _label(self, uid: int) -> Text:
        node = self.model.nodes[uid]
        label = Text(literal(node.name))
        label.append(f"  @{node.offset:x} +{node.size}", style="dim")
        if node.analysis_status:
            label.append(f" [{literal(node.analysis_status)}]", style="yellow")
        if uid in self.search_nodes:
            label.stylize("bold yellow")
        return label

    def set_search_nodes(self, nodes: set[int]) -> None:
        """Mark matching nodes, retaining lazy population of their descendants."""
        self.search_nodes = nodes
        for uid, entry in self.entries.items():
            entry.set_label(self._label(uid))

    def _populate(self, uid: int) -> None:
        if uid not in self.loaded:
            for child in self.model.nodes[uid].children:
                self._append_entry(self.entries[uid], child)
            self.loaded.add(uid)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[int]) -> None:
        if event.node.data is not None:
            self._populate(event.node.data)

    def reveal(self, uid: int) -> None:
        """Expand the ancestry of a result without eagerly building other branches."""
        ancestry = []
        parent = self.model.nodes[uid].parent
        while parent is not None:
            ancestry.append(parent)
            parent = self.model.nodes[parent].parent
        for parent in reversed(ancestry):
            self._populate(parent)
            self.entries[parent].expand()
        entry = self.entries[uid]
        self.move_cursor(entry)
        self.scroll_to_node(entry, animate=False)
