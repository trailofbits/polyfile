"""Terminal searches preserve byte coordinates, ordering, and cancellation."""

from concurrent.futures import CancelledError
from pathlib import Path

import pytest

from polyfile.explorer.model import ByteRange, ExplorerModel
from polyfile.explorer.search import hex_bytes, search
from polyfile.polyfile import Match, Matcher, Submatch


def model_for(path: Path, data: bytes, *, decoded: bytes | None = None) -> ExplorerModel:
    path.write_bytes(data)
    root = Match("root", None, length=len(data), matcher=Matcher(False))
    if decoded is not None:
        Submatch("decoded", None, source="decoded:0", length=len(decoded),
                 decoded=decoded, parent=root)
    return ExplorerModel(path, [root])


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 4, 65536])
def test_overlaps_and_chunk_boundaries(tmp_path: Path, chunk_size: int) -> None:
    model = model_for(tmp_path / "input", b".ababa..aba")
    hits = search(model, "aba", mode="text", chunk_size=chunk_size)
    assert [hit.range for hit in hits] == [ByteRange("file", n, 3) for n in (1, 3, 8)]


def test_combined_merges_kinds_nodes_and_orders_numeric_offsets(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_bytes(b"AB ab 4142")
    root = Match("root", None, length=10, matcher=Matcher(False))
    Submatch("4142", None, length=2, parent=root)
    Submatch("4142", None, length=2, parent=root)
    model = ExplorerModel(path, [root])
    hits = search(model, "4142", chunk_size=1)
    assert [hit.range for hit in hits] == [ByteRange("file", 0, 2), ByteRange("file", 6, 4)]
    assert hits[0].kinds == ("hex", "structure")
    assert hits[0].nodes == (1, 2)
    assert hits[1].kinds == ("text",)


def test_source_scope_order_case_and_utf8_byte_offsets(tmp_path: Path) -> None:
    model = model_for(tmp_path / "input", "éNEEDLE needle".encode(), decoded=b"_Needle")
    hits = search(model, "needle", mode="text", chunk_size=3)
    assert [hit.range for hit in hits] == [
        ByteRange("file", 2, 6), ByteRange("file", 9, 6), ByteRange("decoded:0", 1, 6),
    ]
    assert [hit.range for hit in search(model, "needle", mode="text", match_case=True)] == [
        ByteRange("file", 9, 6),
    ]
    assert [hit.range for hit in search(model, "Needle", mode="text", source="decoded:0")] == [
        ByteRange("decoded:0", 1, 6),
    ]
    assert search(model, "absent", mode="text") == []
    assert search(model, "") == []


def test_ascii_folding_does_not_casefold_non_ascii(tmp_path: Path) -> None:
    model = model_for(tmp_path / "input", "ÄA äa Äa".encode())
    assert [hit.range.start for hit in search(model, "Äa", mode="text")] == [0, 8]


def test_structure_search_includes_status_and_unavailable_sources(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_bytes(b"file")
    root = Match("root", None, length=4, matcher=Matcher(False))
    missing = Submatch("metadata", None, source="decoded:9", length=12, parent=root)
    missing.analysis_status = "unsupported"
    missing.analysis_message = "Missing HELPER"
    model = ExplorerModel(path, [root])
    hits = search(model, "helper", mode="structure")
    assert hits[0].range == ByteRange("decoded:9", 0, 12)
    assert hits[0].nodes == (1,)
    assert search(model, "helper", mode="structure", match_case=True) == []
    assert search(model, "anything", mode="text") == []


@pytest.mark.parametrize("query", ["0x", "abc", "gg", "-1", "ab,cd", "0 x41"])
def test_invalid_explicit_hex_is_actionable(tmp_path: Path, query: str) -> None:
    model = model_for(tmp_path / "input", b"file")
    with pytest.raises(ValueError, match="hexadecimal byte pairs"):
        search(model, query, mode="hex")
    assert search(model, query, mode="combined") == []


@pytest.mark.parametrize("query", ["4142", "0x4142", "0X41 42", " 41\n42\t "])
def test_hex_syntax_and_case_independence(tmp_path: Path, query: str) -> None:
    assert hex_bytes(query) == b"AB"
    model = model_for(tmp_path / "input", b"ABab")
    assert [hit.range for hit in search(model, query, mode="hex")] == [ByteRange("file", 0, 2)]


def test_cancelled_search_never_returns_partial_hits(tmp_path: Path) -> None:
    model = model_for(tmp_path / "input", b"a" * 100)
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls > 6

    with pytest.raises(CancelledError):
        search(model, "a", mode="text", cancelled=cancelled, chunk_size=2)
    with pytest.raises(CancelledError):
        search(model, "", cancelled=lambda: True)


def test_invalid_source_chunk_and_changed_file(tmp_path: Path) -> None:
    model = model_for(tmp_path / "input", b"file")
    with pytest.raises(ValueError, match="Unknown analysis source"):
        search(model, "f", source="missing")
    with pytest.raises(ValueError, match="positive chunk"):
        search(model, "f", chunk_size=0)
    model.path.write_bytes(b"f")
    with pytest.raises(OSError, match="changed"):
        search(model, "f", mode="text")
