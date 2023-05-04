from typing import Any, Iterable, Iterator, List, Optional, Tuple, Union

from .polyfile import Match, Submatch


class Node:
    def __init__(self,
                 name: str,
                 value: Optional[bytes] = None,
                 offset: Optional[int] = None,
                 length: Optional[int] = None,
                 older_sibling: Optional["Node"] = None,
                 children: Iterable["Node"] = ()
    ):
        self.name: str = name
        self.value: Optional[bytes] = value
        self._offset: Optional[int] = offset
        self._length: Optional[int] = length
        self.older_sibling: Optional[Node] = older_sibling
        self.children: Tuple[Node, ...] = tuple(children)

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

    def to_matches(self, parent: Optional[Match] = None) -> Iterator[Submatch]:
        stack: List[Tuple["Node", Optional[Match]]] = [(self, parent)]
        while stack:
            node, parent = stack.pop()
            if parent is None:
                parent_offset = 0
            else:
                parent_offset = parent.offset
            match = Submatch(
                name=node.name,
                match_obj=node.value,
                relative_offset=node.offset - parent_offset,
                length=node.length,
                parent=parent
            )
            yield match
            for child in reversed(node.children):
                stack.append((child, match))

    @classmethod
    def load(cls, obj: Any) -> "Node":
        ancestors: List[Tuple[Any, Optional[Tuple[Node, ...]]]] = [
            (obj, None)
        ]
        children: Optional[Tuple[Node, ...]]
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
                value: Union[Optional[bytes], str] = obj.value
            else:
                value = None
            if isinstance(value, str):
                value = value.encode("utf-8")
            if hasattr(obj, "offset"):
                offset: Optional[int] = obj.offset
            else:
                offset = None
            if hasattr(obj, "length") and (value is None or obj.length >= len(value)):
                length: Optional[int] = obj.length
            else:
                length = None
            older_sibling: Optional[Node] = None
            for reversed_parent_index, (parent, siblings) in enumerate(reversed(ancestors)):
                if siblings is not None:
                    if siblings:
                        older_sibling: Optional[Node] = siblings[-1]
                    break
            else:
                assert not ancestors
            node = cls(name=name, value=value, offset=offset, length=length, older_sibling=older_sibling,
                       children=children)
            if not ancestors:
                return node
            ancestors[len(ancestors) - reversed_parent_index - 1] = parent, siblings + (node,)
