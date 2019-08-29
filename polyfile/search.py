from collections import deque
import collections.abc
from typing import IO, Mapping, Sequence, Union

from . import serialization


class TrieNode:
    def __init__(self, value=None, sources=None, _children=None):
        if _children is None:
            self._children: Mapping[object, TrieNode] = {}
        else:
            self._children = _children
        self.value = value
        if sources is not None:
            self._sources = set(sources)
        else:
            self._sources = set()

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r}, sources={self.sources!r}, _children={self._children!r})"

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return iter(self._children.values())

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return not (self == other)

    def __getitem__(self, key):
        return self._children[key]

    def __contains__(self, value):
        if not isinstance(value, collections.abc.Sequence):
            first, remainder, n = value, (), 1
        else:
            first, remainder, n = self._car_cdr_len(value)
        if n == 1:
            return first in self._children
        else:
            return self._find(first, remainder, n)

    @staticmethod
    def _car_cdr_len(sequence):
        n = len(sequence)
        if n == 0:
            first = None
        else:
            first = sequence[0]
        return first, sequence[1:], n

    def _find(self, first, remainder, n):
        if n == 0:
            return len(self._sources) > 0
        if first not in self._children:
            return False
        return self[first]._find(*self._car_cdr_len(remainder))

    def find(self, key):
        if isinstance(key, collections.abc.Sequence):
            return self._find(*self._car_cdr_len(key))
        else:
            return self._find(key, (), 1)

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
        node = self
        while True:
            first, sequence, n = self._car_cdr_len(sequence)
            if n == 0:
                break
            if first in node:
                node = node[first]
            else:
                node = node._add_child(first)
        node._sources.add(source)
        return node

    def add(self, sequence, source=None):
        if source is None:
            source = sequence
        return self._add(sequence, source)

    def find_prefix(self, prefix):
        first, remainder, n = self._car_cdr_len(prefix)
        if n == 0:
            yield from iter(self._sources)
            for child in self:
                yield from child.find_prefix(prefix)
        else:
            if first in self._children:
                yield from self[first].find_prefix(remainder)

    def bfs(self):
        queue = deque([self])
        while queue:
            head = queue.popleft()
            yield head
            queue.extend(head._children.values())

    def dfs(self):
        stack = [self]
        visited = set()
        while stack:
            tail = stack.pop()
            yield tail
            children = tail._children.values()
            stack.extend(child for child in children if id(child) not in visited)
            visited |= set(id(c) for c in children)

    def _serialize_node(self):
        value_encoding = None
        ret = {
            'sources': list(self._sources),
            'children': []
        }
        if self.value is not None:
            ret['value'] = self.value
        if value_encoding is not None:
            ret['value_encoding'] = value_encoding
        return ret

    def _serialize(self):
        ret = self._serialize_node()
        nodes = [(self, ret)]
        while nodes:
            node, serialized = nodes.pop()
            for child in node._children.values():
                child_serialized = child._serialize_node()
                serialized['children'].append(child_serialized)
                nodes.append((child, child_serialized))
        return ret

    def serialize(self):
        """Serializes this Trie as a JSON file. All node values and sources must be JSON serializable."""
        return serialization.dumps(self._serialize())

    @staticmethod
    def _deserialize_value_and_sources(serialized: dict):
        value = None
        if 'value' in serialized:
            value = serialized['value']
        sources = [source for source in serialized['sources']]
        return value, sources

    @staticmethod
    def _deserialize_node(serialized: dict, parent=None):
        value, sources = TrieNode._deserialize_value_and_sources(serialized)
        node = TrieNode(value=value, sources=sources)
        if parent is not None:
            parent._children[node.value] = node
        for child in serialized['children']:
            TrieNode._deserialize_node(child, parent=node)
        return node

    @staticmethod
    def load(serialized):
        serialized = serialization.loads(serialized)
        return TrieNode._deserialize_node(serialized)


class ACNode(TrieNode):
    """A data structure for implementing the Aho-Corasick multi-string matching algorithm"""
    def __init__(self, value=None, sources=None, _children=None, parent=None):
        super().__init__(value=value, sources=sources, _children=_children)
        self.parent = parent
        self.fall = None

    def _add_child(self, value, sources=None):
        new_child = ACNode(value, sources, parent=self)
        self._children[value] = new_child
        return new_child

    def finalize(self):
        self.fall = self
        for n in self.bfs():
            if n is self:
                continue
            new_fall = n.parent.fall
            while n.value not in new_fall and new_fall is not self:
                new_fall = new_fall.fall
            if n.value not in new_fall:
                # there is no suffix
                n.fall = self
            else:
                n.fall = new_fall[n.value]
                if n.fall is n:
                    n.fall = self

    def to_dot(self, include_falls=False):
        """Returns a Graphviz/Dot representation of this Trie"""
        dot = "digraph G {\n"
        node_ids = {}
        falls = {}
        for node in self.dfs():
            assert node not in node_ids
            nid = len(node_ids)
            node_ids[id(node)] = nid
            dot += f"    node{nid}"
            if node.value is None:
                dot += f"[label=\"Root\"]"
            else:
                if node.value == ord('"'):
                    c = '\\"'
                elif node.value == ord('\\'):
                    c = '\\\\'
                elif 32 <= node.value <= 126:
                    c = chr(node.value)
                else:
                    c = f"\\\\x{hex(node.value)[2:]}"
                dot += f"[label=\"{c}\"]"
            dot += ";\n"
            if node.parent is not None:
                dot += f"    node{node_ids[id(node.parent)]} -> node{nid};\n"
            if include_falls and node.fall is not None and node.fall is not node:
                falls[id(node)] = id(node.fall)

        for nodeid, fallid in falls.items():
            dot += f"    node{node_ids[nodeid]} -> node{node_ids[fallid]} [style=dashed,label=\"fall\"];\n"
        dot += "}\n"
        return dot

    @staticmethod
    def _deserialize_node(serialized: dict, nodes_by_uid: dict, parent=None):
        value, sources = TrieNode._deserialize_value_and_sources(serialized)
        node = ACNode(value=value, sources=sources, parent=parent)
        nodes_by_uid[serialized['uid']] = (node, serialized)
        if parent is not None:
            parent._children[node.value] = node
        for child in serialized['children']:
            ACNode._deserialize_node(child, nodes_by_uid, parent=node)
        return node

    @staticmethod
    def load(serialized):
        serialized = serialization.loads(serialized)
        nodes_by_uid = {}
        root = ACNode._deserialize_node(serialized, nodes_by_uid)
        # Construct the falls
        for node, serialized in nodes_by_uid.values():
            if 'fall' in serialized:
                node.fall = nodes_by_uid[serialized['fall']][0]
        return root

    def _serialize_node(self):
        serialized = super()._serialize_node()
        serialized['uid'] = id(self)
        if self.fall is not None:
            serialized['fall'] = id(self.fall)
        return serialized


class MultiSequenceSearch:
    """A datastructure for efficiently searching a sequence for multiple strings"""
    def __init__(self, *sequences_to_find):
        self.trie = ACNode()
        for seq in sequences_to_find:
            self.trie.add(seq)
        self.trie.finalize()

    def save(self, output_stream: IO):
        output_stream.write(self.trie.serialize())

    @staticmethod
    def load(input_stream: IO):
        mss = MultiSequenceSearch()
        mss.trie = ACNode.load(input_stream.read())
        return mss

    def search(self, source_sequence: Union[Sequence, IO]):
        """The Aho-Corasick Algorithm"""
        if hasattr(source_sequence, 'read'):
            def iterator():
                while True:
                    b = source_sequence.read(1)
                    if not b:
                        return
                    yield b[0]
        else:
            def iterator():
                return iter(source_sequence)

        state = self.trie
        for stream_offset, c in enumerate(iterator()):
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
                yield from ((stream_offset - len(source) + 1, source) for source in n.sources)
                n = n.fall


class StartsWithMatcher:
    def __init__(self, *sequences_to_find):
        self.trie = TrieNode()
        for seq in sequences_to_find:
            self.trie.add(seq)

    def search(self, source_sequence: Union[Sequence, IO]):
        if hasattr(source_sequence, 'read'):
            def iterator():
                while True:
                    b = source_sequence.read(1)
                    if not b:
                        return
                    yield b[0]
        else:
            def iterator():
                return iter(source_sequence)

        state = self.trie
        yield from ((0, s) for s in state.sources)

        for c in iterator():
            if c not in state:
                return

            state = state[c]
            yield from ((0, s) for s in state.sources)


if __name__ == '__main__':
    root = TrieNode()
    root.add('The quick brown fox jumps over the lazy dog')
    root.add('The quick person')
    root.add('The best')
    assert len(list(root.find_prefix('The'))) == 3
    assert len(list(root.find_prefix('The quick'))) == 2
    assert not root.find('The')
    assert root.find('The best')

    mss = MultiSequenceSearch(b'hack', b'hacker', b'crack', b'ack', b'kool')
    to_search = b'This is a test to see if hack or hacker is in this string.'\
                b'Can you crack it? If so, please ack, \'cause that would be kool.'
    for offset, match in mss.search(to_search):
        print(offset, match)
        assert to_search[offset:offset+len(match)] == match

    swm = StartsWithMatcher(b'hack', b'hacker', b'crack', b'ack', b'kool')
    for match in swm.search(b'hacker'):
        print(match)

    print(ACNode.load(mss.trie.serialize()))
