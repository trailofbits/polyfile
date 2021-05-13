from collections.abc import Sequence as AbstractSequence, Set as AbstractSet
from typing import Generic, TypeVar, Iterable, Iterator, List, Optional, Sequence, Set

T = TypeVar("T")


class LazyIterableSequence(Generic[T], Sequence[T], AbstractSequence):
    """A thread-safe list lazily generated from an iterator"""
    def __init__(self, source: Iterable[T]):
        self._source_iter: Optional[Iterator[T]] = iter(source)
        self._items: List[T] = []

    def _get_next_source_item(self) -> T:
        if self._source_iter is None:
            raise StopIteration()
        return next(self._source_iter)

    def _complete(self):
        """Finishes reading all source items from the input iterator"""
        while self._source_iter is not None:
            try:
                _ = self[len(self._items)]
            except IndexError:
                assert self._source_iter is None

    def __getitem__(self, index: int) -> T:
        while self._source_iter is not None and len(self._items) <= index:
            # we have not yet read enough items
            try:
                self._items.append(next(self._source_iter))
            except StopIteration:
                self._source_iter = None
                break
        return self._items[index]

    def __len__(self) -> int:
        self._complete()
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        i = 0
        while True:
            try:
                yield self[i]
                i += 1
            except IndexError:
                break


def unique(iterator: Iterator[T], elements: Optional[Set[T]] = None) -> Iterator[T]:
    """Yields all of the unique elements of the input sequence"""
    if elements is None:
        elements = set()
    for t in iterator:
        if t not in elements:
            yield t
            elements.add(t)


class LazyIterableSet(Generic[T], AbstractSet, LazyIterableSequence[T]):
    """
    A collection that is both a set and a sequence that
    """
    def __init__(self, source: Iterable[T]):
        self._set: Set[T] = set()
        super().__init__(unique(iter(source), elements=self._set))

    def __contains__(self, x: object) -> bool:
        return x in self._set
