import base64
from json import dumps
from pathlib import Path
from typing import Any, Dict, IO, Iterator, List, Optional, Set, Tuple, Type, Union

from .fileutils import FileStream
from . import logger
from .magic import MagicMatcher

CUSTOM_MATCHERS: Dict[str, Type["Match"]] = {}

log = logger.getStatusLogger("polyfile")


class submatcher:
    def __init__(self, *filetypes):
        self.filetypes = filetypes

    def __call__(self, MatcherClass: Type["Match"]):
        if not hasattr(MatcherClass, 'submatch'):
            raise ValueError(f"Matcher class {MatcherClass} must implement the `submatch` function")
        for ft in self.filetypes:
            CUSTOM_MATCHERS[ft] = MatcherClass
        return MatcherClass


class InvalidMatch(ValueError):
    pass


class Match:
    def __init__(self,
                 name: str,
                 match_obj: Any,
                 relative_offset: int = 0,
                 length: Optional[int] = None,
                 parent: Optional["Match"] = None,
                 matcher: Optional["Matcher"] = None,
                 display_name: Optional[str] = None,
                 img_data: Optional[str] = None,
                 decoded: Optional[bytes] = None
    ):
        if parent is not None:
            if not isinstance(parent, Match):
                raise ValueError("The parent must be an instance of a Match")
            parent._children.append(self)
            if matcher is None:
                matcher = parent.matcher
        if matcher is None:
            raise(ValueError("A Match must be initialized with `parent` and/or `matcher` not being None"))
        self.matcher: Optional[Matcher] = matcher
        self.name: str = name
        if display_name is None:
            self.display_name: str = name
        else:
            self.display_name = display_name
        self.match = match_obj
        self.img_data: Optional[str] = img_data
        self.decoded: Optional[bytes] = decoded
        self._offset: int = relative_offset
        self._length: Optional[int] = length
        self._parent: Optional[Match] = parent
        self._children: List[Match] = []

    @property
    def children(self) -> Tuple["Match", ...]:
        return tuple(self._children)

    def __len__(self):
        return len(self._children)

    def __iter__(self) -> Iterator["Match"]:
        return iter(self._children)

    def __getitem__(self, index: int) -> "Match":
        return self._children[index]

    @property
    def parent(self) -> Optional["Match"]:
        return self._parent

    @property
    def offset(self) -> int:
        """The global offset of this match with respect to the original file"""
        if self.parent is not None:
            return self.parent.offset + self.relative_offset
        else:
            return self.relative_offset

    @property
    def root(self) -> "Match":
        if self.parent is None:
            return self
        else:
            return self.parent.root

    @property
    def root_offset(self) -> int:
        return self.offset - self.root.offset

    @property
    def relative_offset(self) -> int:
        """The offset of this match relative to its parent"""
        return self._offset

    @property
    def length(self) -> int:
        """The number of bytes in the match"""
        return self._length

    def to_obj(self):
        ret = {
            'relative_offset': self.relative_offset,
            'offset': self.offset,
            'size': self.length,
            'type': self.name,
            'name': self.display_name,
            'value': str(self.match),
            'subEls': [c.to_obj() for c in self]
        }
        if self.img_data is not None:
            ret['img_data'] = self.img_data
        if self.decoded is not None:
            ret['decoded'] = base64.b64encode(self.decoded).decode('utf-8')
        return ret

    def json(self) -> str:
        return dumps(self.to_obj())

    def __repr__(self):
        return f"{self.__class__.__name__}(match={self.match!r}, relative_offset={self._offset}, parent={self._parent!r})"

    def __str__(self):
        return f"Match<{self.match}>@{self._offset}"


class Submatch(Match):
    pass


class Matcher:
    def __init__(self, try_all_offsets: bool = False, submatch: bool = True, matcher: Optional[MagicMatcher] = None):
        if matcher is None:
            self.magic_matcher: MagicMatcher = MagicMatcher.DEFAULT_INSTANCE
        else:
            self.magic_matcher = matcher
        self.try_all_offsets: bool = try_all_offsets
        self.submatch: bool = submatch

    def handle_mimetype(self, mimetype: str, match_obj: Any, data: bytes, file_stream: Union[str, Path, IO, FileStream],
                        parent: Optional[Match] = None) -> Iterator[Match]:
        if self.submatch and mimetype in CUSTOM_MATCHERS:
            m = CUSTOM_MATCHERS[mimetype](
                mimetype,
                match_obj,
                0,
                length=len(data),
                parent=parent,
                matcher=self
            )
            # Don't yield this custom match until we've tried its submatch function
            # (which may throw an InvalidMatch, meaning that this match is invalid)
            try:
                with FileStream(file_stream) as fs:
                    submatch_iter = m.submatch(fs)
                    try:
                        first_submatch = next(submatch_iter)
                        has_first = True
                    except StopIteration:
                        has_first = False
                    yield m
                    if has_first:
                        yield first_submatch
                        yield from submatch_iter
            except InvalidMatch:
                pass
        else:
            yield Match(
                mimetype,
                match_obj,
                0,
                length=len(data),
                parent=parent,
                matcher=self
            )

    def match(self, file_stream: Union[str, Path, IO, FileStream], parent: Optional[Match] = None) -> Iterator[Match]:
        with FileStream(file_stream) as f:
            matched_mimetypes: Set[str] = set()
            data = f.read()
            for magic_match in self.magic_matcher.match(data, only_match_mime=True):
                for mimetype in magic_match.mimetypes:
                    if mimetype in matched_mimetypes:
                        continue
                    matched_mimetypes.add(mimetype)
                    yield from self.handle_mimetype(mimetype, magic_match, data, file_stream, parent)
