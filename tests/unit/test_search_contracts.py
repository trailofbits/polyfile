"""Typed search traversals preserve sequence and binary-stream behavior."""

from io import BytesIO

import pytest

from polyfile.search import MultiSequenceSearch, StartsWithMatcher, TrieNode


@pytest.mark.parametrize("stream_input", (False, True))
def test_multi_sequence_search_matches_an_overlapping_bytes_model(stream_input: bool) -> None:
    patterns = (b"aa", b"aaa", b"ba")
    data = b"baaaaba"
    expected = sorted(
        (offset, pattern)
        for offset in range(len(data))
        for pattern in patterns
        if data.startswith(pattern, offset)
    )
    source = BytesIO(data) if stream_input else data
    assert sorted(MultiSequenceSearch(*patterns).search(source)) == expected


@pytest.mark.parametrize("stream_input", (False, True))
def test_prefix_search_keeps_empty_and_overlapping_matches(stream_input: bool) -> None:
    data = b"alphabet"
    source = BytesIO(data) if stream_input else data
    matches = StartsWithMatcher(b"", b"a", b"alpha", b"beta").search(source)
    assert set(matches) == {(0, b""), (0, b"a"), (0, b"alpha")}


def test_tree_traversals_include_all_descendants() -> None:
    tree = TrieNode()
    tree.add("ab")
    tree.add("ac")
    assert [node.value for node in tree.bfs()] == [None, "a", "b", "c"]
    assert [node.value for node in tree.dfs()] == [None, "a", "c", "b"]
