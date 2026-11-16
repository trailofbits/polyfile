"""Standalone trie and multi-pattern search utilities retained for library use.

PolyFile's analyzer does not currently call this module. Its APIs remain tested
for external callers and future reuse. See ``docs/search_serialization.md`` for
matching semantics, persistence guarantees, and the former TRiD integration.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Iterable, Iterator, Sequence
import reprlib
from typing import BinaryIO, TextIO, cast

import graphviz

from polyfile import serialization

_Pattern = Sequence[Hashable]
_SymbolInput = Iterable[Hashable] | BinaryIO | TextIO


def _validate_pattern(pattern: object) -> None:
    if not isinstance(pattern, Sequence):
        raise TypeError("Search patterns must be sequences, such as bytes, text, or tuples")
    try:
        hash(pattern)
    except TypeError as error:
        raise TypeError(
            "Search patterns must be hashable; use a tuple instead of a list"
        ) from error


def _symbols(source: _SymbolInput) -> Iterator[Hashable]:
    if not hasattr(source, "read"):
        yield from cast(Iterable[Hashable], source)
        return
    reader = cast(BinaryIO | TextIO, source)
    while True:
        chunk = reader.read(1)
        if not isinstance(chunk, (bytes, str)):
            raise TypeError("Search streams must return bytes or text from read(1)")
        if not chunk:
            return
        if len(chunk) != 1:
            raise ValueError("Search stream read(1) returned more than one symbol")
        yield chunk[0]


def _path(key: object) -> Iterable[Hashable]:
    if isinstance(key, Sequence):
        return cast(Sequence[Hashable], key)
    if not isinstance(key, Hashable):
        raise TypeError("Trie keys must be hashable symbols or sequences of hashable symbols")
    return (key,)


def _same_symbol(left: Hashable | None, right: Hashable | None) -> bool:
    return left is right or left == right


def _symbol_label(value: Hashable | None) -> str:
    if isinstance(value, int) and 0 <= value < 256:
        return chr(value) if 32 <= value <= 126 else f"\\x{value:02x}"
    if isinstance(value, str) and value.isprintable():
        return value
    return reprlib.repr(value)


@serialization.serializable
class TrieNode:
    """A trie node with hashable child keys and associated source labels.

    Args:
        value: This node's symbol; the root conventionally uses None.
        sources: Hashable labels associated with the path ending at this node.
        _children: An existing child dictionary, primarily used during loading.
    """

    def __init__(
        self,
        value: Hashable | None = None,
        sources: Iterable[Hashable] | None = None,
        _children: dict[Hashable, TrieNode] | None = None,
    ) -> None:
        if _children is not None and not isinstance(_children, dict):
            raise TypeError("Trie children must be a dictionary of symbols to trie nodes")
        self._children = {} if _children is None else _children
        self.value = value
        self._sources: set[Hashable] = set() if sources is None else set(sources)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(value={reprlib.repr(self.value)}, "
            f"sources={len(self._sources)}, children={len(self._children)})"
        )

    def __len__(self) -> int:
        return len(self._children)

    def __iter__(self) -> Iterator[TrieNode]:
        return iter(self._children.values())

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrieNode):
            return NotImplemented
        return self.value == other.value

    def __ne__(self, other: object) -> bool:
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal

    def __getitem__(self, key: Hashable) -> TrieNode:
        return self._children[key]

    def __contains__(self, value: object) -> bool:
        """Interpret sequences as paths and other operands as child keys."""
        if isinstance(value, Sequence):
            if len(value) == 1:
                return value[0] in self._children
            return self.find(value)
        return value in self._children

    def _follow(self, path: Iterable[Hashable]) -> TrieNode | None:
        node = self
        for symbol in path:
            child = node._children.get(symbol)
            if child is None:
                return None
            node = child
        return node

    def find(self, key: Hashable | Sequence[Hashable]) -> bool:
        """Return whether a complete path has an associated source.

        Args:
            key: A sequence path, or a single non-sequence symbol.

        Returns:
            True for an inserted path, including an inserted empty path.
            A prefix without associated sources returns False.
        """
        node = self._follow(_path(key))
        return node is not None and bool(node._sources)

    @property
    def children(self) -> dict[Hashable, TrieNode]:
        """Return a shallow copy of the child dictionary."""
        return dict(self._children)

    @property
    def sources(self) -> frozenset[Hashable]:
        """Return an immutable copy of the associated source labels."""
        return frozenset(self._sources)

    def _add_child(self, value: Hashable, sources: Iterable[Hashable] | None = None) -> TrieNode:
        child = TrieNode(value, sources)
        self._children[value] = child
        return child

    def _add(self, sequence: Iterable[Hashable], source: Hashable) -> TrieNode:
        node = self
        for symbol in sequence:
            child = node._children.get(symbol)
            node = child if child is not None else node._add_child(symbol)
        node._sources.add(source)
        return node

    def add(self, sequence: Iterable[Hashable], source: Hashable | None = None) -> TrieNode:
        """Insert a path and return its terminal node.

        Args:
            sequence: Hashable symbols forming the path.
            source: A hashable label. None uses the sequence itself, which must
                then be hashable, such as bytes, text, or a tuple.

        Returns:
            The terminal node, with the source added to its label set.
        """
        label = sequence if source is None else source
        try:
            hash(label)
        except TypeError as error:
            raise TypeError("Trie source labels must be hashable") from error
        return self._add(sequence, cast(Hashable, label))

    def find_prefix(self, prefix: Iterable[Hashable]) -> Iterator[Hashable]:
        """Yield source labels below a prefix without recursion.

        Args:
            prefix: Symbols shared by the paths whose labels are requested.

        Yields:
            Each matching node's source labels. Missing prefixes yield nothing.
            Label order within a node is unspecified.
        """
        node = self._follow(prefix)
        if node is None:
            return
        stack = [node]
        visited: set[int] = set()
        while stack:
            node = stack.pop()
            if id(node) not in visited:
                visited.add(id(node))
                yield from node._sources
                stack.extend(reversed(tuple(node)))

    def bfs(self) -> Iterator[TrieNode]:
        """Yield each reachable node once in breadth-first order."""
        queue = deque([self])
        visited: set[int] = set()
        while queue:
            node = queue.popleft()
            if id(node) not in visited:
                visited.add(id(node))
                yield node
                queue.extend(node)

    def dfs(self) -> Iterator[TrieNode]:
        """Yield each reachable node once, visiting later children first."""
        stack = [self]
        visited: set[int] = set()
        while stack:
            node = stack.pop()
            if id(node) not in visited:
                visited.add(id(node))
                yield node
                stack.extend(node)

    def serialize(self) -> tuple[object, ...]:
        """Return the value, source labels, and children for the binary codec."""
        return self.value, self._sources, self._children


@serialization.serializable
class ACNode(TrieNode):
    """An Aho–Corasick trie node with derived parent and failure links.

    Args:
        value: This node's symbol.
        sources: Source patterns ending at this node.
        _children: An existing child dictionary.
        parent: The parent node, retained in the constructor contract.
        _fall: A supplied failure link. Finalization reconstructs these links.
    """

    def __init__(
        self,
        value: Hashable | None = None,
        sources: Iterable[Hashable] | None = None,
        _children: dict[Hashable, TrieNode] | None = None,
        parent: ACNode | None = None,
        _fall: ACNode | None = None,
    ) -> None:
        super().__init__(value, sources, _children)
        self.parent = parent
        self.fall = _fall

    def serialize(
        self,
    ) -> tuple[Hashable | None, set[Hashable], dict[Hashable, TrieNode], None, None]:
        """Return five established fields with empty derived-link slots.

        Parent and failure links are reconstructed by MultiSequenceSearch.load().
        Keeping their slots preserves the existing ACNode record shape.
        """
        return self.value, self._sources, self._children, None, None

    def __getitem__(self, key: Hashable) -> ACNode:
        child = super().__getitem__(key)
        if not isinstance(child, ACNode):
            raise ValueError("Aho–Corasick children must be ACNode instances")
        return child

    def _add_child(self, value: Hashable, sources: Iterable[Hashable] | None = None) -> ACNode:
        child = ACNode(value, sources, parent=self)
        self._children[value] = child
        return child

    def _validated_children(self, visited: set[int]) -> Iterator[ACNode]:
        for symbol, child in self._children.items():
            if not isinstance(child, ACNode):
                raise ValueError("Search trie children must be ACNode instances")
            if not _same_symbol(child.value, symbol):
                raise ValueError("Search trie child values must match their dictionary keys")
            if id(child) in visited:
                raise ValueError("Search trie contains a cycle or a node with multiple parents")
            visited.add(id(child))
            yield child

    def _failure_link(self, child: ACNode) -> ACNode:
        if self.parent is None:
            return self
        fallback = self.fall
        if fallback is None:
            raise ValueError("Finalize the search trie before using failure links")
        while child.value not in fallback._children and fallback.parent is not None:
            fallback = cast(ACNode, fallback.fall)
        return cast(ACNode, fallback._children.get(child.value, fallback))

    def finalize(self) -> None:
        """Validate a structural tree and reconstruct parent and failure links.

        Raises:
            ValueError: If a child has the wrong type/value, a cycle exists, or
                multiple paths share a node. These structures are not tries.
        """
        self.parent = None
        self.fall = self
        queue: deque[ACNode] = deque([self])
        visited = {id(self)}
        while queue:
            node = queue.popleft()
            for child in node._validated_children(visited):
                child.parent = node
                child.fall = node._failure_link(child)
                queue.append(child)

    def to_dot(self, include_falls: bool = False) -> str:
        """Return DOT source for this subtree without invoking a renderer.

        Args:
            include_falls: Include dashed failure edges whose targets are within
                this subtree. Parent and failure edges outside it are omitted.

        Returns:
            A directed graph with literal labels for byte, text, and other symbols.
        """
        nodes = list(self.bfs())
        node_ids = {id(node): f"node{index}" for index, node in enumerate(nodes)}
        dot = graphviz.Digraph("G")
        for node in nodes:
            label = "Root" if node is self else _symbol_label(node.value)
            dot.node(node_ids[id(node)], label=graphviz.escape(label))
            if isinstance(node, ACNode):
                self._dot_edges(dot, node, node_ids, include_falls)
        return dot.source

    @staticmethod
    def _dot_edges(
        dot: graphviz.Digraph,
        node: ACNode,
        node_ids: dict[int, str],
        include_falls: bool,
    ) -> None:
        if node.parent is not None and id(node.parent) in node_ids:
            dot.edge(node_ids[id(node.parent)], node_ids[id(node)])
        if (
            include_falls
            and node.fall is not None
            and node.fall is not node
            and id(node.fall) in node_ids
        ):
            dot.edge(node_ids[id(node)], node_ids[id(node.fall)], style="dashed", label="fall")


class MultiSequenceSearch:
    """Find all occurrences of hashable sequence patterns with Aho–Corasick.

    Args:
        *sequences_to_find: Patterns such as bytes, text, or tuples of hashable
            symbols. Duplicate patterns are reported once per occurrence.

    Raises:
        TypeError: If a pattern is not a hashable sequence.
    """

    def __init__(self, *sequences_to_find: _Pattern) -> None:
        self.trie = ACNode()
        for sequence in sequences_to_find:
            _validate_pattern(sequence)
            self.trie.add(sequence)
        self.trie.finalize()

    def save(self, output_stream: serialization.BinaryWriter) -> None:
        """Write a reusable trie cache without changing the live search.

        Args:
            output_stream: A writable binary stream, positioned for the record.

        Raises:
            serialization.EncodingError: If trie fields cannot be encoded.
        """
        serialization.dump(self.trie, output_stream)

    @staticmethod
    def load(input_stream: serialization.BinaryReader) -> MultiSequenceSearch:
        """Load a cache and rebuild derived links, including old acyclic records.

        Args:
            input_stream: A readable binary stream at the start of a cache.

        Returns:
            A usable search with reconstructed parent and failure links.

        Raises:
            serialization.EncodingError: If the encoded object is malformed.
            ValueError: If the root or structural trie is invalid.
        """
        root = serialization.load(input_stream)
        if not isinstance(root, ACNode):
            raise ValueError(f"Cannot load search root: expected ACNode, got {type(root).__name__}")
        root.finalize()
        try:
            for node in root.bfs():
                for pattern in node.sources:
                    _validate_pattern(pattern)
                    if not MultiSequenceSearch._pattern_matches(
                        cast(ACNode, node),
                        cast(_Pattern, pattern),
                        root,
                    ):
                        raise ValueError("Search trie source pattern does not match its node path")
        except TypeError as error:
            raise ValueError(f"Invalid search trie source pattern: {error}") from error
        search = MultiSequenceSearch()
        search.trie = root
        return search

    @staticmethod
    def _pattern_matches(node: ACNode, pattern: _Pattern, root: ACNode) -> bool:
        for symbol in reversed(pattern):
            if node is root or not _same_symbol(node.value, symbol):
                return False
            if node.parent is None:
                return False
            node = node.parent
        return node is root

    def _matches(self, state: ACNode, end: int) -> Iterator[tuple[int, _Pattern]]:
        node = state
        while node is not self.trie:
            for source in node._sources:
                pattern = cast(_Pattern, source)
                yield end - len(pattern), pattern
            if node.fall is None:
                raise ValueError("Finalize the search trie before searching")
            node = node.fall
        for source in self.trie._sources:
            yield end, cast(_Pattern, source)

    def search(self, source_sequence: _SymbolInput) -> Iterator[tuple[int, _Pattern]]:
        """Yield zero-based start offsets and original matching patterns.

        Args:
            source_sequence: Symbols, or a binary/text reader consumed from its
                current position. Stream offsets are relative to that position.

        Yields:
            Matches in input-consumption order; ties have unspecified order.
            Empty patterns match every boundary, including zero and the end.

        Raises:
            TypeError: If input symbols are unhashable or a reader is not binary/text.
            ValueError: If read(1) returns multiple symbols or the trie needs finalization.
        """
        state = self.trie
        yield from self._matches(state, 0)
        for end, symbol in enumerate(_symbols(source_sequence), 1):
            while symbol not in state._children and state is not self.trie:
                if state.fall is None:
                    raise ValueError("Finalize the search trie before searching")
                state = state.fall
            state = cast(ACNode, state._children.get(symbol, self.trie))
            yield from self._matches(state, end)


class StartsWithMatcher:
    """Match hashable sequence patterns only at input position zero.

    Args:
        *sequences_to_find: Patterns such as bytes, text, or tuples of symbols.

    Raises:
        TypeError: If a pattern is not a hashable sequence.
    """

    def __init__(self, *sequences_to_find: _Pattern) -> None:
        self.trie = TrieNode()
        for sequence in sequences_to_find:
            _validate_pattern(sequence)
            self.trie.add(sequence)

    def search(self, source_sequence: _SymbolInput) -> Iterator[tuple[int, _Pattern]]:
        """Yield matching prefixes as offset-zero, original-pattern pairs.

        Args:
            source_sequence: Symbols or a binary/text stream. A stream is read
                through the first mismatching symbol or the end of input.

        Yields:
            Prefixes as they are completed, including empty patterns at zero.
            Ties have unspecified order.

        Raises:
            TypeError: If input symbols are unhashable or a reader is not binary/text.
            ValueError: If read(1) returns multiple symbols.
        """
        state = self.trie
        yield from ((0, cast(_Pattern, source)) for source in state._sources)
        for symbol in _symbols(source_sequence):
            child = state._children.get(symbol)
            if child is None:
                return
            state = child
            yield from ((0, cast(_Pattern, source)) for source in state._sources)
