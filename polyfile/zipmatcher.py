import zipfile

from .fileutils import Tempfile
from .polyfile import Match, matcher, match


@matcher('zip-vgm.trid.xml')
class ZipMatcher(Match):
    def submatch(self, file_stream):
        with zipfile.ZipFile(file_stream) as zf:
            for name in zf.namelist():
                with Tempfile(zf.read(name)) as f:
                    yield from match(f, parent=self)
