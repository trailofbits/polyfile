import zipfile

from .fileutils import Tempfile
from .polyfile import InvalidMatch, Match, submatcher


@submatcher('zip-vgm.trid.xml')
class ZipFile(Match):
    def submatch(self, file_stream):
        try:
            with zipfile.ZipFile(file_stream) as zf:
                for name in zf.namelist():
                    with Tempfile(zf.read(name)) as f:
                        yield from self.matcher.match(f, parent=self)
        except zipfile.BadZipFile:
            raise InvalidMatch()
