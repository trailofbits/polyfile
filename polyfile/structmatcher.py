from typing import Iterator, Optional

from .fileutils import Tempfile
from .polyfile import InvalidMatch, Match, Matcher, Submatch
from .structs import Field, Struct, StructError


class PolyFileStruct(Struct):
    __name__: Optional[str] = None

    @property
    def match_name(self) -> str:
        if self.__name__ is not None:
            return self.__name__
        else:
            return self.__class__.__name__

    def match(self, matcher: Matcher, parent: Optional[Match] = None) -> Iterator[Submatch]:
        m = Submatch(
            self.match_name,
            match_obj=self,
            relative_offset=self.start_offset,
            length=self.num_bytes,
            parent=parent,
            matcher=matcher
        )
        yield m
        for field_name in self.fields.keys():
            value: Field = getattr(self, field_name)
            s = Submatch(
                field_name,
                match_obj=value,
                relative_offset=value.start_offset - self.start_offset,
                length=value.num_bytes,
                parent=m,
                matcher=matcher
            )
            yield s
            try:
                if isinstance(value, PolyFileStruct):
                    yield from value.match(matcher, s)
                elif isinstance(value, bytes):
                    with Tempfile(value) as tmp:
                        yield from matcher.match(tmp, parent=s)
            except (InvalidMatch, StructError):
                pass
