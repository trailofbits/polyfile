from .kaitai import DEFS, load, KaitaiStream
from .polyfile import ast_to_matches, Match, submatcher
from .logger import getStatusLogger

log = getStatusLogger('wasm')


def parse_wasm(file_stream, parent):
    if 'webassembly' not in DEFS:
        load()
    ast = DEFS['webassembly'].parse(KaitaiStream(file_stream))
    try:
        ast = DEFS['webassembly'].parse(KaitaiStream(file_stream))
    except Exception as e:
        log.error(str(e))
        ast = None
    if ast is not None:
        iterator = ast_to_matches(ast, parent=parent)
        try:
            wasm_match = next(iterator)
            yield wasm_match
            yield from iterator
        except StopIteration:
            pass


@submatcher('wasm.trid.xml')
class WASM(Match):
    def submatch(self, file_stream):
        yield from parse_wasm(file_stream, parent=self)
