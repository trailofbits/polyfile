from typing import Iterator, Optional

from .fileutils import Tempfile
from .polyfile import InvalidMatch, Match, Matcher, Submatch
from .structs import Constant, Field, Struct, StructError


class PolyFileStruct(Struct):
    __name__: Optional[str] = None

    @property
    def match_name(self) -> str:
        if self.__name__ is not None:
            return self.__name__
        else:
            return self.__class__.__name__

    def match(self, matcher: Matcher, parent: Optional[Match] = None) -> Iterator[Submatch]:
        """Yields a match for this struct, one for each of its fields, and any embedded files.

        A field holding raw bytes can itself contain a file, so it is written to a temporary
        file and handed back to `matcher`. :class:`polyfile.structs.Constant` fields are
        exempt: their contents are the fixed signature that identified this struct, so
        matching them only rediscovers the struct's own file type at the offset of its magic.

        Args:
            matcher: The matcher to use for fields that may contain embedded files.
            parent: The match that contains this struct, if any.

        Yields:
            The match for this struct, followed by the matches for its fields and their
            contents, depth first.
        """
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
                elif isinstance(value, bytes) and not isinstance(value, Constant):
                    with Tempfile(value) as tmp:
                        yield from matcher.match(tmp, parent=s)
            except (InvalidMatch, StructError):
                pass
