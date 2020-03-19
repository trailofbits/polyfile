import base64
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


class InvalidMatch(ValueError):
    pass


class Match:
    def __init__(self,
                 name,
                 match_obj,
                 relative_offset=0,
                 length=None,
                 parent=None,
                 matcher=None,
                 display_name=None,
                 img_data=None,
                 decoded=None):
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
        if display_name is None:
            self.display_name = name
        else:
            self.display_name = display_name
        self.match = match_obj
        self.img_data = img_data
        self.decoded = decoded
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
    def root(self):
        if self.parent is None:
            return self
        else:
            return self.parent.root

    @property
    def root_offset(self):
        return self.offset - self.root.offset

    @property
    def relative_offset(self):
        """The offset of this match relative to its parent"""
        return self._offset

    @property
    def length(self):
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

    def json(self):
        return dumps(self.to_obj())

    def __repr__(self):
        return f"{self.__class__.__name__}(match={self.match!r}, relative_offset={self._offset}, parent={self._parent!r})"

    def __str__(self):
        return f"Match<{self.match}>@{self._offset}"


class Submatch(Match):
    pass


class Matcher:
    def __init__(self, try_all_offsets=False, submatch=True):
        self.trid_matcher = None
        self.try_all_offsets = try_all_offsets
        self.submatch = submatch

    def match(self, file_stream, parent=None, progress_callback=None, trid_defs=None):
        if self.trid_matcher is None or\
            (self.trid_matcher.custom_defs and trid_defs is None) or\
                (not self.trid_matcher.custom_defs and trid_defs is not None):
            self.trid_matcher = trid.Matcher(try_all_offsets=self.try_all_offsets, defs=trid_defs)
        for offset, tdef in self.trid_matcher.match(file_stream, progress_callback=progress_callback):
            if self.submatch and tdef.name in CUSTOM_MATCHERS:
                display_name = tdef.name.upper()
                if display_name.endswith('.XML'):
                    display_name = display_name[:-4]
                if display_name.endswith('.TRID'):
                    display_name = display_name[:-5]
                m = CUSTOM_MATCHERS[tdef.name](
                    tdef.name,
                    tdef,
                    offset,
                    display_name=display_name,
                    length=len(file_stream) - offset,
                    parent=parent,
                    matcher=self
                )
                # Don't yield this custom match until we've tried its submatch function
                # (which may throw an InvalidMatch, meaning that this match is invalid)
                try:
                    with FileStream(file_stream)[offset:] as fs:
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
                    tdef.name,
                    tdef,
                    offset,
                    length=len(file_stream) - offset,
                    parent=parent,
                    matcher=self
                )
