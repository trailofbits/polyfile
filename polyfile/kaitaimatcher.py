from . import kaitai
from .polyfile import submatcher, InvalidMatch, Match, Submatch

KAITAI_TRID_MAPPING = {
    'jpeg': 'bitmap-jpeg.trid.xml'
}


def ast_to_matches(ast: kaitai.AST, parent: Match):
    stack = [(parent, ast)]
    while stack:
        parent, node = stack.pop()
        if not hasattr(node.obj, 'uid'):
            continue
        if len(node.children) == 1 and not hasattr(node.children[0], 'uid'):
            match = node.children[0].obj
        else:
            match = ''
        new_node = Submatch(
            name=node.obj.uid,
            match_obj=match,
            relative_offset=node.relative_offset,
            length=node.length,
            parent=parent
        )
        yield new_node
        stack.extend(reversed([(new_node, c) for c in node.children]))


for kaitai_def, trid_def in KAITAI_TRID_MAPPING.items():
    @submatcher(trid_def)
    class KaitaiMatcher(Match):
        def submatch(self, file_stream):
            try:
                ast = kaitai.parse_stream(kaitai_def, file_stream)
            except Exception as e:
                raise InvalidMatch()
            if ast is None:
                raise InvalidMatch()
            yield from ast_to_matches(ast, parent=self)
