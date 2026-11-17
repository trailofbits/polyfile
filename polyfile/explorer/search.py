"""Cancellable, source-qualified searches for the terminal explorer."""

from collections.abc import Callable, Iterator
from concurrent.futures import CancelledError
from dataclasses import dataclass, replace
import re
from typing import Literal

from polyfile.explorer.model import ByteRange, ByteSource, ExplorerModel, ExplorerNode


SearchMode = Literal["combined", "text", "hex", "structure"]
Cancellation = Callable[[], bool]
_ASCII_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


@dataclass(frozen=True)
class SearchHit:
    """One byte range, combining every matching search kind and structure node."""

    range: ByteRange
    kinds: tuple[str, ...]
    nodes: tuple[int, ...] = ()


def check_cancelled(cancelled: Cancellation | None) -> None:
    """Stop background work after its caller cancels or replaces the operation."""
    if cancelled is not None and cancelled():
        raise CancelledError("Explorer operation cancelled")


def hex_bytes(query: str) -> bytes | None:
    """Parse the HTML viewer's optional-0x, whitespace-separated byte-pair syntax."""
    compact = re.sub(r"^0x", "", query.strip(), flags=re.IGNORECASE)
    compact = "".join(compact.split())
    if not compact or len(compact) % 2 or re.fullmatch(r"[0-9a-fA-F]+", compact) is None:
        return None
    return bytes.fromhex(compact)


def _needles(query: str, mode: SearchMode, match_case: bool) -> list[tuple[bytes, str, bool]]:
    needles = []
    if mode in ("combined", "text"):
        needles.append((query.encode("utf-8"), "text", not match_case))
    if mode in ("combined", "hex"):
        value = hex_bytes(query)
        if value is not None:
            needles.append((value, "hex", False))
        elif mode == "hex":
            raise ValueError("Enter hexadecimal byte pairs, such as 0x48 65 6c 6c 6f.")
    return needles


def _byte_offsets(
    source: ByteSource, needle: bytes, *, fold: bool,
    cancelled: Cancellation | None, chunk_size: int,
) -> Iterator[int]:
    tail = b""
    needle = needle.lower() if fold else needle
    for offset, chunk in source.iter_chunks(chunk_size=chunk_size):
        check_cancelled(cancelled)
        block = tail + chunk
        haystack = block.lower() if fold else block
        position = haystack.find(needle)
        while position >= 0:
            check_cancelled(cancelled)
            yield offset - len(tail) + position
            position = haystack.find(needle, position + 1)
        tail = block[-(len(needle) - 1):] if len(needle) > 1 else b""


def _add_hit(hits: dict[ByteRange, SearchHit], hit: SearchHit) -> None:
    previous = hits.get(hit.range)
    if previous is None:
        hits[hit.range] = hit
        return
    hits[hit.range] = replace(
        previous,
        kinds=tuple(dict.fromkeys(previous.kinds + hit.kinds)),
        nodes=tuple(dict.fromkeys(previous.nodes + hit.nodes)),
    )


def _node_matches(node: ExplorerNode, query: str, match_case: bool) -> bool:
    text = " ".join((node.name, node.type, node.analysis_status or "",
                     node.analysis_message or ""))
    if match_case:
        return query in text
    return query.translate(_ASCII_FOLD) in text.translate(_ASCII_FOLD)


def _scan_source(
    source: ByteSource, needles: list[tuple[bytes, str, bool]],
    hits: dict[ByteRange, SearchHit], *, cancelled: Cancellation | None, chunk_size: int,
) -> None:
    for needle, kind, fold in needles:
        for offset in _byte_offsets(source, needle, fold=fold,
                                    cancelled=cancelled, chunk_size=chunk_size):
            _add_hit(hits, SearchHit(ByteRange(source.identifier, offset, len(needle)), (kind,)))


def _scan_nodes(
    model: ExplorerModel, query: str, hits: dict[ByteRange, SearchHit], *,
    sources: set[str], match_case: bool, cancelled: Cancellation | None,
) -> None:
    for node in model.nodes.values():
        check_cancelled(cancelled)
        if node.source in sources and _node_matches(node, query, match_case):
            _add_hit(hits, SearchHit(node.range, ("structure",), (node.uid,)))


def search(
    model: ExplorerModel, query: str, *, mode: SearchMode = "combined",
    source: str | None = None, match_case: bool = False,
    cancelled: Cancellation | None = None, chunk_size: int = 65536,
) -> list[SearchHit]:
    """Find ordered, overlapping byte and structure matches without whole-file reads.

    Args:
        model: Completed analysis and its physical and decoded sources.
        query: Literal UTF-8 text, hexadecimal bytes, or structure metadata.
        mode: Which search kinds to include; combined merges identical ranges.
        source: One source ID, or None to search all sources in model order.
        match_case: Whether text and structure matching distinguishes ASCII case.
        cancelled: Optional cooperative cancellation predicate.
        chunk_size: Maximum source bytes read at once.

    Returns:
        Hits ordered by source, byte offset, and range length. Unavailable source
        buffers retain structure hits but are skipped by byte searches.

    Raises:
        ValueError: If the mode, hexadecimal query, source, or chunk size is invalid.
        CancelledError: If the caller cancels the search.
        OSError: If an available source cannot be read completely.
    """
    if mode not in ("combined", "text", "hex", "structure") or chunk_size <= 0:
        raise ValueError("Choose a valid search mode and a positive chunk size.")
    if source is not None and source not in model.sources:
        raise ValueError(f"Unknown analysis source: {source!r}")
    check_cancelled(cancelled)
    if not query:
        return []
    sources = [source] if source is not None else list(model.sources)
    needles = _needles(query, mode, match_case)
    hits: dict[ByteRange, SearchHit] = {}
    for identifier in sources:
        buffer = model.sources[identifier]
        if buffer.available:
            _scan_source(buffer, needles, hits, cancelled=cancelled, chunk_size=chunk_size)
    if mode in ("combined", "structure"):
        _scan_nodes(model, query, hits, sources=set(sources),
                    match_case=match_case, cancelled=cancelled)
    check_cancelled(cancelled)
    order = {identifier: index for index, identifier in enumerate(sources)}
    return sorted(hits.values(), key=lambda hit: (
        order[hit.range.source], hit.range.start, hit.range.length,
    ))
