from abc import ABC, abstractmethod
from collections.abc import Container
import re
from typing import Iterable, List


class Wildcard(ABC):
    @abstractmethod
    def match(self, to_test: str) -> bool:
        raise NotImplementedError()

    def is_contained_in(self, items: Iterable[str]) -> bool:
        for item in items:
            if self.match(item):
                return True
        return False

    @staticmethod
    def parse(to_test: str) -> "Wildcard":
        if "*" in to_test or "?" in to_test:
            return SimpleWildcard(to_test)
        else:
            return ConstantMatch(to_test)


class ConstantMatch(Wildcard):
    def __init__(self, to_match: str):
        self.to_match: str = to_match

    def match(self, to_test: str) -> bool:
        return self.to_match == to_test

    def is_contained_in(self, items: Iterable[str]) -> bool:
        if isinstance(items, Container):
            return self.to_match in items
        return super().is_contained_in(items)


class SimpleWildcard(Wildcard):
    def __init__(self, pattern: str):
        self.raw_pattern: str = pattern
        self.pattern = re.compile(self.escaped_pattern)

    @property
    def escaped_pattern(self) -> str:
        components: List[str] = []
        component: str = ""
        for last_c, c in zip((None,) + tuple(self.raw_pattern), self.raw_pattern):
            escaped = last_c is not None and last_c == "\\"
            if not escaped and (c == "*" or c == "?"):
                if component:
                    components.append(re.escape(component))
                    component = ""
                components.append(f".{c}")
            else:
                component = f"{component}{c}"
        if component:
            components.append(re.escape(component))
        return "".join(components)

    def match(self, to_test: str) -> bool:
        return bool(self.pattern.match(to_test))
