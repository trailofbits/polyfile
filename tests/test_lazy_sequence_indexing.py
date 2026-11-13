"""Lazy collections obey Sequence indexes without eagerly reading positive indexes."""

from collections.abc import Iterator, Sequence

import pytest

from polyfile.iterators import LazyIterableSequence, LazyIterableSet


@pytest.mark.parametrize("index", [-5, -1, 0, 4])
def test_integer_indexes_agree_with_lists(index: int) -> None:
    values = list(range(5))
    sequence = LazyIterableSequence(iter(values))
    assert isinstance(sequence, Sequence)
    assert sequence[index] == values[index]


@pytest.mark.parametrize("index", [-6, 5])
def test_integer_indexes_outside_sequence_raise(index: int) -> None:
    sequence = LazyIterableSequence(iter(range(5)))
    with pytest.raises(IndexError):
        sequence[index]


@pytest.mark.parametrize(
    "index",
    [slice(None), slice(1, 4), slice(-3, None), slice(None, None, -1), slice(0, 5, 2)],
)
@pytest.mark.parametrize("cached", [False, True])
def test_slices_agree_with_lists(index: slice, cached: bool) -> None:
    values = list(range(5))
    sequence = LazyIterableSequence(iter(values))
    if cached:
        assert sequence[1] == 1
    assert sequence[index] == values[index]


def test_positive_index_reads_only_the_required_prefix() -> None:
    visited: list[int] = []

    def source() -> Iterator[int]:
        for value in range(5):
            visited.append(value)
            yield value

    sequence = LazyIterableSequence(source())
    assert sequence[1] == 1
    assert visited == [0, 1]
    assert sequence[-1] == 4
    assert visited == list(range(5))


def test_empty_sequences_and_invalid_slice_steps() -> None:
    empty = LazyIterableSequence(iter(()))
    assert empty[:] == []
    with pytest.raises(IndexError):
        empty[-1]
    with pytest.raises(ValueError):
        empty[::0]


def test_lazy_unique_set_retains_sequence_operations() -> None:
    sequence = LazyIterableSet(iter([3, 1, 3, 2, 1]))
    assert sequence[-1] == 2
    assert sequence[:] == [3, 1, 2]
