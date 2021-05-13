import zipfile

from kaitaistruct import KaitaiStructError

from .fileutils import Tempfile
from .kaitai.parser import KaitaiParser
from .kaitai.parsers.zip import Zip
from .kaitaimatcher import ast_to_matches
from .polyfile import InvalidMatch, Match, submatcher


@submatcher("application/zip")
class ZipFile(Match):
    def submatch(self, file_stream):
        yielded = False
        try:
            file_stream.seek(0)
            ast = KaitaiParser(Zip).parse(file_stream).ast
            yield from ast_to_matches(ast, parent=self)
            yielded = True
        except (KaitaiStructError, EOFError):
            pass
        try:
            file_stream.seek(0)
            with zipfile.ZipFile(file_stream) as zf:
                for name in zf.namelist():
                    with Tempfile(zf.read(name)) as f:
                        yield from self.matcher.match(f, parent=self)
            yielded = True
        except (zipfile.BadZipFile, EOFError):
            pass
        if not yielded:
            raise InvalidMatch()
