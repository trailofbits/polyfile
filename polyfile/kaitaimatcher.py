from typing import Dict, Iterator, List, Tuple, Type

from .kaitai.parser import ASTNode, KaitaiParser, KaitaiStruct, RootNode
from .kaitai.parsers.jpeg import Jpeg
from .polyfile import submatcher, InvalidMatch, Match, Submatch

KAITAI_TRID_MAPPING: Dict[str, Type[KaitaiStruct]] = {
    "bitmap-jpeg.trid.xml": Jpeg
}


def ast_to_matches(ast: RootNode, parent: Match) -> Iterator[Submatch]:
    stack: List[Tuple[Match, ASTNode]] = [(parent, ast)]
    while stack:
        parent, node = stack.pop()

        new_node = Submatch(
            name=node.name,
            match_obj=node.raw_value,
            relative_offset=node.start,
            length=len(node.segment),
            parent=parent
        )
        yield new_node
        stack.extend(reversed([(new_node, c) for c in node.children]))


for trid_def, kaitai_def in KAITAI_TRID_MAPPING.items():
    @submatcher(trid_def)
    class KaitaiMatcher(Match):
        def submatch(self, file_stream):
            try:
                ast = KaitaiParser(kaitai_def).parse(file_stream).ast
            except Exception:
                raise InvalidMatch()
            yield from ast_to_matches(ast, parent=self)
