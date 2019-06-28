from collections import deque
from typing import IO, Sequence, Union


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
        if len(value) == 1:
            return value in self._children
        else:
            return self.find(value)

    def find(self, sequence):
        if len(sequence) == 0:
            return len(self._sources) > 0
        first = sequence[0]
        if first not in self:
            return False
        return self[first].find(sequence[1:])

    @property
    def children(self):
        return dict(self._children)

    @property
    def sources(self):
        return frozenset(self._sources)

    def _add_child(self, value, sources=None):
        new_child = TrieNode(value, sources)
        self._children[value] = new_child
        return new_child

    def _add(self, sequence, source):
        if len(sequence) == 0:
            self._sources.add(source)
            return self

        first = sequence[0]
        if first in self:
            return self[first]._add(sequence[1:], source)
        elif len(sequence) == 1:
            return self._add_child(first, {source})
        else:
            new_child = self._add_child(first)
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

    def bfs(self):
        queue = deque([self])
        while queue:
            head = queue.popleft()
            yield head
            queue.extend(head._children.values())


class ACNode(TrieNode):
    """A data structure for implementing the Aho-Corasick multi-string matching algorithm"""
    def __init__(self, value=None, sources=None, _children=None, parent=None):
        super().__init__(value=value, sources=sources, _children=_children)
        self._parent = parent
        self._fall = None

    @property
    def parent(self):
        return self._parent

    @property
    def fall(self):
        return self._fall

    def _add_child(self, value, sources=None):
        new_child = ACNode(value, sources, parent=self)
        self._children[value] = new_child
        return new_child

    def finalize(self):
        self._fall = self
        for n in self.bfs():
            if n is self:
                continue
            new_fall = n.parent.fall
            while n.value not in new_fall and new_fall is not self:
                new_fall = new_fall.fall
            if n.value not in new_fall:
                # there is no suffix
                n._fall = self
            else:
                n._fall = new_fall[n.value]
                if n.fall is n:
                    n._fall = self


class MultiStringSearch:
    """A datastructure for efficiently searching a sequence for multiple strings"""
    def __init__(self, *sequences_to_find):
        self.trie = ACNode()
        for seq in sequences_to_find:
            self.trie.add(seq)
        self.trie.finalize()

    def search(self, source_sequence: Union[Sequence, IO]):
        """The Aho-Corasick Algorithm"""
        if hasattr(source_sequence, 'read'):
            def iterator():
                while True:
                    b = source_sequence.read(1)
                    if not b:
                        return
                    yield b
        else:
            def iterator():
                return iter(source_sequence)

        state = self.trie
        for offset, c in enumerate(iterator()):
            n = state

            while c not in n and n is not self.trie:
                n = n.fall

            if n is self.trie:
                if c in n:
                    n = n[c]
            else:
                n = n[c]

            state = n

            while n is not self.trie:
                yield from ((offset - len(source) + 1, source) for source in n.sources)
                n = n.fall


if __name__ == '__main__':
    root = TrieNode()
    root.add('The quick brown fox jumps over the lazy dog')
    root.add('The quick person')
    root.add('The best')
    print(list(root.find_prefix('The')))
    print(list(root.find_prefix('The quick')))
    print(root.find('The'))
    print(root.find('The best'))

    mss = MultiStringSearch('hack', 'hacker', 'crack', 'ack', 'kool')
    to_search = 'This is a test to see if hack or hacker is in this string.'\
                'Can you crack it? If so, please ack, \'cause that would be kool.'
    for offset, match in mss.search(to_search):
        assert to_search[offset:offset+len(match)] == match
        print(offset, match)
