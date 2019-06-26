from . import trid


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


def match(file_stream):
    for offset, tdef in trid.match(file_stream, try_all_offsets=True):
        yield Match(tdef, offset)
