"""Saved search tries retain their matching behavior after loading."""

import subprocess
import sys
from io import BytesIO
from itertools import product

import pytest

from polyfile import serialization
from polyfile.search import MultiSequenceSearch

ROUND_TRIP = """
from io import BytesIO
import sys
from polyfile import serialization
from polyfile.search import MultiSequenceSearch

search = MultiSequenceSearch(*serialization.loads(sys.stdin.buffer.read()))
for _ in range(int(sys.argv[1])):
    output = BytesIO()
    search.save(output)
    output.seek(0)
    search = MultiSequenceSearch.load(output)
sys.stdout.buffer.write(output.getvalue())
"""


def _round_trip(patterns: tuple[bytes | str, ...], repeats: int = 1) -> MultiSequenceSearch:
    """Bound saving so a serialization cycle cannot hang the test process."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", ROUND_TRIP, str(repeats)],
            input=serialization.dumps(patterns),
            capture_output=True,
            check=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "Saving/loading a search trie did not finish within five seconds", pytrace=False
        )
    assert result.stderr == b""
    return MultiSequenceSearch.load(BytesIO(result.stdout))


def test_single_pattern_round_trip_finishes() -> None:
    search = _round_trip((b"a",))
    assert list(search.search(b"aba")) == [(0, b"a"), (2, b"a")]


@pytest.mark.parametrize("stream_input", [False, True])
@pytest.mark.parametrize("repeats", [1, 3])
def test_round_trip_preserves_overlapping_patterns(stream_input: bool, repeats: int) -> None:
    patterns = (b"he", b"she", b"his", b"hers", b"s", b"he")
    data = b"ushershishe"
    search = _round_trip(patterns, repeats)
    expected = sorted(
        (offset, pattern)
        for offset in range(len(data))
        for pattern in set(patterns)
        if data.startswith(pattern, offset)
    )
    source = BytesIO(data) if stream_input else data
    assert sorted(search.search(source)) == expected


def test_round_trip_preserves_unicode_sequence_offsets() -> None:
    patterns = ("é", "été", "té", "t")
    data = "été été"
    search = _round_trip(patterns)
    expected = sorted(
        (offset, pattern)
        for offset in range(len(data))
        for pattern in patterns
        if data.startswith(pattern, offset)
    )
    assert sorted(search.search(data)) == expected


@pytest.mark.parametrize("stream_input", [False, True])
def test_empty_search_survives_repeated_round_trips(stream_input: bool) -> None:
    search = _round_trip((), repeats=3)
    source = BytesIO(b"anything") if stream_input else b"anything"
    assert list(search.search(source)) == []


def test_round_trip_matches_all_short_binary_sequences() -> None:
    patterns = tuple(
        bytes(symbols) for length in range(1, 4) for symbols in product((0, 255), repeat=length)
    )
    search = _round_trip(patterns)
    for length in range(7):
        for symbols in product((0, 255), repeat=length):
            data = bytes(symbols)
            expected = sorted(
                (offset, pattern)
                for offset in range(len(data))
                for pattern in patterns
                if data.startswith(pattern, offset)
            )
            assert sorted(search.search(data)) == expected
