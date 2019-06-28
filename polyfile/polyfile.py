from json import dumps

from .fileutils import FileStream
from . import logger
from . import trid

CUSTOM_MATCHERS = {}

log = logger.getStatusLogger("polyfile")


class submatcher:
    def __init__(self, *filetypes):
        self.filetypes = filetypes

    def __call__(self, MatcherClass):
        if not hasattr(MatcherClass, 'submatch'):
            raise ValueError(f"Matcher class {MatcherClass} must implement the `submatch` function")
        for ft in self.filetypes:
            CUSTOM_MATCHERS[ft] = MatcherClass
        return MatcherClass


class Match:
    def __init__(self, name, match_obj, relative_offset=0, length=None, parent=None, matcher=None):
        if parent is not None:
            if not isinstance(parent, Match):
                raise ValueError("The parent must be an instance of a Match")
            parent._children.append(self)
            if matcher is None:
                matcher = parent.matcher
        if matcher is None:
            raise(ValueError("A Match must be initialized with `parent` and/or `matcher` not being None"))
        self.matcher = matcher
        self.name = name
        self.match = match_obj
        self._offset = relative_offset
        self._length = length
        self._parent = parent
        self._children = []

    @property
    def children(self):
        return tuple(self._children)

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return iter(self._children)

    def __getitem__(self, index):
        return self._children[index]

    @property
    def parent(self):
        return self._parent

    @property
    def offset(self):
        """The global offset of this match with respect to the original file"""
        if self.parent is not None:
            return self.parent.offset + self.relative_offset
        else:
            return self.relative_offset

    @property
    def relative_offset(self):
        """The offset of this match relative to its parent"""
        return self._offset

    @property
    def length(self):
        """The number of bytes in the match"""
        return self._length

    def to_obj(self):
        return {
            'relative_offset': self.relative_offset,
            'global_offset': self.offset,
            'length': self.length,
            'type': self.name,
            'match': str(self.match),
            'children': [c.to_obj() for c in self]
        }

    def json(self):
        return dumps(self.to_obj())

    def __repr__(self):
        return f"{self.__class__.__name__}(match={self.match!r}, relative_offset={self._offset}, parent={self._parent!r})"

    def __str__(self):
        return f"Match<{self.match}>@{self._offset}"


class Submatch(Match):
    pass


class Matcher:
    def __init__(self):
        self.trid_matcher = None

    def match(self, file_stream, parent=None):
        if self.trid_matcher is None:
            self.trid_matcher = trid.Matcher()
        for offset, tdef in self.trid_matcher.match(file_stream):
            if tdef.name in CUSTOM_MATCHERS:
                m = CUSTOM_MATCHERS[tdef.name](
                    tdef.name,
                    tdef,
                    offset,
                    length=len(file_stream) - offset,
                    parent=parent,
                    matcher=self
                )
                yield m
                with FileStream(file_stream)[offset:] as fs:
                    yield from m.submatch(fs)
            else:
                yield Match(
                    tdef.name,
                    tdef,
                    offset,
                    length=len(file_stream) - offset,
                    parent=parent,
                    matcher=self
                )
