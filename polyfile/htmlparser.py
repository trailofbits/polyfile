from html.parser import HTMLParser

from .polyfile import submatcher, InvalidMatch, Match, Submatch
from .logger import getStatusLogger

log = getStatusLogger("HTML")


class Tag:
    def __init__(self, tag, attrs, line, offset, global_offset, parent=None):
        self.tag = tag
        self.attrs = attrs
        self.line = line
        self.offset = offset
        self.global_offset = global_offset
        self.parent = parent
        self.children = []
        self.end_offset = None
        self.data = None
        if self.parent is not None:
            self.parent.children.append(self)

    def to_match(self, parent):
        m = Submatch(
            name=self.tag,
            match_obj=self,
            relative_offset=self.global_offset - parent.offset,
            length=self.end_offset - self.global_offset,
            parent=parent
        )
        yield m
        if self.attrs:
            print(self.attrs)
            breakpoint()
        if self.data is not None:
            pass
        for c in self.children:
            yield from c.to_match(m)

    @property
    def root(self):
        if self.parent is None:
            return self
        else:
            return self.parent.root

    def __repr__(self):
        return f"{self.__class__.__name__!s}(tag={self.tag!r}, attrs={self.attrs!r}, line={self.line!r}, offset={self.offset!r}, global_offset={self.global_offset!r}, parent={self.parent!r})"


class PolyFileHTMLParser(HTMLParser):
    def __init__(self, matcher):
        super().__init__()
        self.matcher = matcher
        self._line_starts: [int] = []
        self._error: InvalidMatch = None
        self.root: Tag = None
        self._tags: [Tag] = []

    def error(self, message):
        if self._error is None:
            self._error = InvalidMatch(message)

    def parse(self, file_stream):
        html: str = file_stream.read().decode('utf-8')
        self._line_starts = [0]
        i = 0
        while i < len(html):
            i = html.find('\n', i)
            if i < 0:
                break
            i += 1
            self._line_starts.append(i)
        self._error = None
        self._tags = []
        self.root = None
        self.feed(html)
        if self._error is not None:
            raise self._error
        if self.root is not None:
            yield from self.root.to_match(self.matcher)

    def handle_starttag(self, tag, attrs):
        if self._tags:
            parent = self._tags[-1]
        else:
            parent = None
        self._tags.append(Tag(tag, attrs, self.getpos()[0], self.getpos()[1], self.get_offset(), parent))
        if self.root is None:
            self.root = self._tags[-1]

    def get_offset(self):
        line, index = self.getpos()
        return self._line_starts[line - 1] + index

    def match_starttag(self, tag):
        while self._tags and self._tags[-1].tag != tag:
            broken_tag = self._tags[-1]
            log.warn(f"Expected end tag at line {self.getpos()[0]} offset {self.getpos()[1]} "
                     + f"for start tag <{broken_tag.tag}> at line {broken_tag.line} offset {broken_tag.offset}")
            broken_tag.end_offset = self.get_offset()
            self._tags.pop()
        if self._tags:
            return self._tags.pop()
        else:
            return None

    def handle_endtag(self, tag):
        t = self.match_starttag(tag)
        if t is None:
            log.warn(f"Unexpected end tag </{tag}> at line {self.getpos()[0]} offset {self.getpos()[1]}")
        else:
            t.end_offset = self.get_offset()

    def handle_data(self, data):
        if self._tags:
            if self._tags[-1].data is None:
                self._tags[-1].data = data
            else:
                self._tags[-1].data += data


#@submatcher('html.trid.xml')
#class HTMLMatcher(Match):
#    def submatch(self, file_stream):
#        yield from PolyFileHTMLParser(self).parse(file_stream)
