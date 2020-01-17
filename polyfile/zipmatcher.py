import zipfile

from .fileutils import Tempfile
from . import kaitai
from .kaitaimatcher import ast_to_matches
from .polyfile import InvalidMatch, Match, submatcher


@submatcher('zip-vgm.trid.xml')
@submatcher('ark-zip.trid.xml')
class ZipFile(Match):
    def submatch(self, file_stream):
        old_pos = file_stream.tell()
        try:
            ast = kaitai.parse_stream('zip', file_stream)
        except Exception as e:
            raise e
            raise InvalidMatch()
        if ast is None:
            raise InvalidMatch()
        yield from ast_to_matches(ast, parent=self)
        file_stream.seek(old_pos)
        try:
            with zipfile.ZipFile(file_stream) as zf:
                for name in zf.namelist():
                    with Tempfile(zf.read(name)) as f:
                        yield from self.matcher.match(f, parent=self)
        except zipfile.BadZipFile:
            raise InvalidMatch()
