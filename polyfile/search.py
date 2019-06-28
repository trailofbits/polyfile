class TrieNode:
    def __init__(self, value=None, sources=None, _children=None):
        if _children is None:
            self._children = {}
        else:
            self._children = _children
        self._value = value
        if sources is not None:
            self._sources = set(sources)
        else:
            self._sources = set()

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r}, sources={self.sources!r}, _children={self._children!r})"

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return iter(self._children.values())

    def __hash__(self):
        return hash(self._value)

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return not (self == other)

    def __getitem__(self, key):
        return self._children[key]

    def __contains__(self, value):
        return value in self._children

    @property
    def children(self):
        return dict(self._children)

    @property
    def sources(self):
        return frozenset(self._sources)

    def _add(self, sequence, source):
        if len(sequence) == 0:
            self._sources.add(source)
            return self

        first = sequence[0]
        if first in self:
            return self[first]._add(sequence[1:], source)
        elif len(sequence) == 1:
            new_child = TrieNode(first, {source})
            self._children[first] = new_child
            return new_child
        else:
            new_child = TrieNode(first)
            self._children[first] = new_child
            return new_child._add(sequence[1:], source)

    def add(self, sequence):
        return self._add(sequence, sequence)

    def find_prefix(self, prefix):
        if len(prefix) == 0:
            yield from iter(self._sources)
            for child in self:
                yield from child.find_prefix(prefix)
        else:
            first = prefix[0]
            if first in self:
                yield from self[first].find_prefix(prefix[1:])


if __name__ == '__main__':
    root = TrieNode()
    root.add('The quick brown fox jumps over the lazy dog')
    root.add('The quick person')
    root.add('The best')
    print(list(root.find_prefix('The')))
    print(list(root.find_prefix('The quick')))
