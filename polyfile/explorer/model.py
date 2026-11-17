"""Byte sources and structure metadata shared by the terminal explorer."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import cast

from intervaltree import IntervalTree

from polyfile.polyfile import Match


@dataclass(frozen=True)
class ByteRange:
    """A byte interval in exactly one physical or decoded source."""

    source: str
    start: int
    length: int

    @property
    def end(self) -> int:
        return self.start + self.length


@dataclass(frozen=True)
class ByteSource:
    """A source with bounded reads and independent cursors for background work."""

    identifier: str
    length: int
    path: Path | None = field(default=None, kw_only=True)
    data: bytes | None = field(default=None, kw_only=True, repr=False)

    @property
    def available(self) -> bool:
        return self.path is not None or self.data is not None

    def read(self, start: int, length: int) -> bytes:
        """Read an exact bounded range, reporting unavailable or changed sources.

        Args:
            start: Source-relative offset, including EOF for an empty read.
            length: Number of bytes to read.

        Returns:
            The requested bytes, without moving another reader's cursor.

        Raises:
            ValueError: The range is outside the source.
            OSError: The source is unavailable or no longer contains the range.
        """
        self._check_range(start, length)
        if self.data is not None:
            end = start + length
            return self.data[start:end]
        if self.path is None:
            raise OSError(f"Source {self.identifier!r} has no decoded byte buffer")
        try:
            with self.path.open("rb") as stream:
                stream.seek(start)
                data = stream.read(length)
        except OSError as error:
            raise OSError(f"Cannot read source {self.identifier!r}: {error}") from error
        if len(data) != length:
            raise OSError(f"Source {self.identifier!r} changed; analyze the file again")
        return data

    def _check_range(self, start: int, length: int) -> None:
        if start < 0 or length < 0 or start + length > self.length:
            raise ValueError(
                f"Range {start}+{length} is outside source {self.identifier!r} "
                f"({self.length} bytes)"
            )

    def iter_chunks(
        self,
        start: int = 0,
        length: int | None = None,
        *,
        chunk_size: int = 65536,
    ) -> Iterator[tuple[int, bytes]]:
        """Yield source-relative offsets and exact chunks without unbounded reads."""
        length = self.length - start if length is None else length
        self._check_range(start, length)
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if self.path is not None:
            yield from self._file_chunks(start, length, chunk_size)
            return
        end = start + length
        while start < end:
            chunk = self.read(start, min(chunk_size, end - start))
            yield start, chunk
            start += len(chunk)

    def _file_chunks(self, start: int, length: int, chunk_size: int) -> Iterator[tuple[int, bytes]]:
        assert self.path is not None
        try:
            with self.path.open("rb") as stream:
                stream.seek(start)
                end = start + length
                while start < end:
                    size = min(chunk_size, end - start)
                    data = stream.read(size)
                    if len(data) != size:
                        raise OSError("source changed; analyze the file again")
                    yield start, data
                    start += size
        except OSError as error:
            raise OSError(f"Cannot read source {self.identifier!r}: {error}") from error


@dataclass(frozen=True)
class ExplorerNode:
    """A structure node without encoded copies of any byte source."""

    uid: int
    parent: int | None
    source: str
    offset: int
    size: int
    name: str
    type: str
    value: str | None
    analysis_status: str | None
    analysis_message: str | None
    extension: str | None
    children: tuple[int, ...]

    @property
    def range(self) -> ByteRange:
        return ByteRange(self.source, self.offset, self.size)


class ExplorerModel:
    """Retain a completed match tree and the original decoded byte objects.

    Args:
        path: Original file, kept file-backed rather than loaded or base64 encoded.
        matches: Completed top-level matches with their attached children.
        partial: Whether scanning stopped before completing the analysis.
    """

    def __init__(
        self,
        path: str | Path,
        matches: Iterable[Match],
        *,
        partial: bool = False,
    ) -> None:
        self.path = Path(path)
        self.partial = partial
        self.sources = {"file": ByteSource("file", self.path.stat().st_size, path=self.path)}
        self.nodes: dict[int, ExplorerNode] = {}
        self.roots: tuple[int, ...] = ()
        self._coverage: dict[str, tuple[ByteRange, ...]] = {}
        self._indexes: dict[str, IntervalTree] = {}
        self._load_nodes(matches)
        self._register_missing_sources()
        self._index_nodes()
        self.partial = partial or any(
            node.analysis_status == "limited" for node in self.nodes.values()
        )

    def _load_nodes(self, matches: Iterable[Match]) -> None:
        roots = list(matches)
        pending = [(match, None) for match in reversed(roots)]
        children: dict[int | None, list[int]] = {None: []}
        while pending:
            match, parent = pending.pop()
            uid = len(self.nodes)
            children.setdefault(parent, []).append(uid)
            value = match.description
            if value is None and match.match is not None:
                value = str(match.match)
            self.nodes[uid] = ExplorerNode(
                uid,
                parent,
                match.source,
                match.offset,
                match.length,
                match.display_name,
                match.name,
                value,
                match.analysis_status,
                match.analysis_message,
                match.extension,
                (),
            )
            if match.source != "file" and match.decoded is not None:
                self.sources[match.source] = ByteSource(
                    match.source,
                    len(match.decoded),
                    data=match.decoded,
                )
            pending.extend((child, uid) for child in reversed(match.children))
        self.roots = tuple(children[None])
        for uid, node in tuple(self.nodes.items()):
            self.nodes[uid] = replace(node, children=tuple(children.get(uid, ())))

    def _index_nodes(self) -> None:
        for node in self.nodes.values():
            if node.size > 0:
                index = self._indexes.setdefault(node.source, IntervalTree())
                index.addi(node.offset, node.offset + node.size, node.uid)

    def _register_missing_sources(self) -> None:
        for node in self.nodes.values():
            if node.source not in self.sources:
                length = max(0, node.offset + node.size)
                self.sources[node.source] = ByteSource(node.source, length)
            source = self.sources[node.source]
            if not source.available and node.offset + node.size > source.length:
                self.sources[node.source] = ByteSource(node.source, node.offset + node.size)

    def clamp_range(self, selected: ByteRange) -> ByteRange:
        """Clamp display ranges without inventing bytes outside their source."""
        source = self.sources[selected.source]
        start = max(0, min(source.length, selected.start))
        end = max(start, min(source.length, selected.start + max(0, selected.length)))
        return ByteRange(selected.source, start, end - start)

    def nodes_at(self, source: str, offset: int, length: int = 1) -> tuple[ExplorerNode, ...]:
        """Return every overlapping interpretation in stable structure order."""
        index = self._indexes.get(source)
        if index is None or length <= 0:
            return ()
        uids = sorted(
            cast(int, interval.data) for interval in index.overlap(offset, offset + length)
        )
        return tuple(self.nodes[uid] for uid in uids)

    def undescribed(self, source: str) -> tuple[ByteRange, ...]:
        """Find gaps using the HTML explorer's same-source leaf coverage rule."""
        if source not in self._coverage:
            leaves = []
            for node in self.nodes.values():
                if node.source != source:
                    continue
                if any(self.nodes[child].source == source for child in node.children):
                    continue
                selected = self.clamp_range(node.range)
                if selected.length:
                    leaves.append(selected)
            self._coverage[source] = self._gaps(source, leaves)
        return self._coverage[source]

    def _gaps(self, source: str, leaves: list[ByteRange]) -> tuple[ByteRange, ...]:
        gaps = []
        position = 0
        for selected in sorted(leaves, key=lambda selected: selected.start):
            if selected.start > position:
                gaps.append(ByteRange(source, position, selected.start - position))
            position = max(position, selected.end)
        length = self.sources[source].length
        if position < length:
            gaps.append(ByteRange(source, position, length - position))
        return tuple(gaps)
