from typing import Any, Optional, Union
from collections.abc import Iterable, Iterator

from .polyfile import Match, Submatch


class Node:
    def __init__(self,
                 name: str,
                 value: bytes | None = None,
                 offset: int | None = None,
                 length: int | None = None,
                 older_sibling: Optional["Node"] = None,
                 children: Iterable["Node"] = ()
    ):
        self.name: str = name
        self.value: bytes | None = value
        self._offset: int | None = offset
        self._length: int | None = length
        self.older_sibling: Node | None = older_sibling
        self.children: tuple[Node, ...] = tuple(children)

    def __repr__(self):
        r = f"{self.__class__.__name__}(name={self.name!r}"
        if self.value is not None:
            r = f"{r}, value={self.value!r}"
        r = f"{r}, offset={self.offset!r}, length={self.length!r}, older_sibling={self.older_sibling!r}, " \
            f"children={self.children!r})"
        return r

    @property
    def offset(self) -> int:
        if self._offset is None:
            if self.children:
                self._offset = self.children[0].offset
            elif self.older_sibling is not None:
                self._offset = self.older_sibling.offset + self.older_sibling.length
            else:
                raise ValueError(f"{self!r} must either have an explicit offset, an older sibling, or a child!")
        return self._offset

    @property
    def length(self) -> int:
        if self._length is None:
            if self.value is not None:
                self._length = len(self.value)
            elif not self.children:
                self._length = 0
            else:
                self._length = self.children[-1].offset + self.children[-1].length - self.offset
        return self._length

    def to_matches(self, parent: Match | None = None) -> Iterator[Submatch]:
        """Map parser-local AST positions into the containing analysis source.

        Args:
            parent: The match whose beginning is the parser input's source origin.

        Yields:
            Structural matches translated by the original parent's source offset. Descendant
            offsets remain relative to their own parents; backing-stream origins are irrelevant.
        """
        source_base = 0 if parent is None else parent.offset
        stack: list[tuple["Node", Match | None]] = [(self, parent)]
        while stack:
            node, parent = stack.pop()
            if parent is None:
                parent_offset = 0
            else:
                parent_offset = parent.offset
            match = Submatch(
                name=node.name,
                match_obj=node.value,
                relative_offset=source_base + node.offset - parent_offset,
                length=node.length,
                parent=parent
            )
            yield match
            for child in reversed(node.children):
                stack.append((child, match))

    @classmethod
    def load(cls, obj: Any) -> "Node":
        ancestors: list[tuple[Any, tuple[Node, ...] | None]] = [
            (obj, None)
        ]
        children: tuple[Node, ...] | None
        while True:
            obj, children = ancestors.pop()
            if children is None:
                if hasattr(obj, "children") and obj.children:
                    ancestors.append((obj, ()))
                    ancestors.extend((child, None) for child in reversed(obj.children))
                    continue
                children = ()
            if not hasattr(obj, "name"):
                raise ValueError(f"{obj!r} does not have a `name` attribute!")
            name: str = obj.name
            if hasattr(obj, "value"):
                value: bytes | None | str = obj.value
            else:
                value = None
            if isinstance(value, str):
                value = value.encode("utf-8")
            if hasattr(obj, "offset"):
                offset: int | None = obj.offset
            else:
                offset = None
            if hasattr(obj, "length") and (value is None or obj.length >= len(value)):
                length: int | None = obj.length
            else:
                length = None
            older_sibling: Node | None = None
            parent_index = None
            for index in range(len(ancestors) - 1, -1, -1):
                parent, siblings = ancestors[index]
                if siblings is not None:
                    parent_index = index
                    if siblings:
                        older_sibling: Node | None = siblings[-1]
                    break
            node = cls(name=name, value=value, offset=offset, length=length, older_sibling=older_sibling,
                       children=children)
            if parent_index is None:
                assert not ancestors
                return node
            parent, siblings = ancestors[parent_index]
            assert siblings is not None
            ancestors[parent_index] = parent, siblings + (node,)
