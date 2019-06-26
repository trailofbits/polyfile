from .fileutils import FileStream
from . import trid

CUSTOM_MATCHERS = {}


class matcher:
    def __init__(self, *filetypes):
        self.filetypes = filetypes

    def __call__(self, MatcherClass):
        if not hasattr(MatcherClass, 'submatch'):
            raise ValueError(f"Matcher class {MatcherClass} must implement the `submatch` function")
        for ft in self.filetypes:
            CUSTOM_MATCHERS[ft] = MatcherClass
        return MatcherClass


class Match:
    def __init__(self, filetype, relative_offset=0, parent=None):
        self.filetype = filetype
        self._offset = relative_offset
        self._parent = parent

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

    def __repr__(self):
        return f"{self.__class__.__name__}(filetype={self.filetype!r}, relative_offset={self._offset}, parent={self._parent!r})"

    def __str__(self):
        return f"Match<{self.filetype}>@{self._offset}"


def match(file_stream, parent=None):
    for offset, tdef in trid.match(file_stream, try_all_offsets=True):
        if tdef.name in CUSTOM_MATCHERS:
            m = CUSTOM_MATCHERS[tdef.name](tdef, offset, parent=parent)
            yield m
            with FileStream(file_stream)[offset:] as fs:
                yield from m.submatch(fs)
        else:
            yield Match(tdef, offset, parent=parent)
