import base64
from typing import Dict, Iterator, List, Tuple, Type

from .kaitai.parser import ASTNode, KaitaiParser, KaitaiStruct, RootNode
from .kaitai.parsers.gif import Gif
from .kaitai.parsers.jpeg import Jpeg
from .polyfile import submatcher, InvalidMatch, Match, Submatch

KAITAI_TRID_MAPPING: Dict[str, Type[KaitaiStruct]] = {
    "bitmap-jpeg.trid.xml": Jpeg,
    "bitmap-gif.trid.xml": Gif,
    "bitmap-gif-anim.trid.xml": Gif,
}
IMAGE_MIMETYPES: Dict[Type[KaitaiStruct], str] = {
    Gif: "image/gif",
    Jpeg: "image/jpeg"
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

        if node is ast and node.obj.__class__ in IMAGE_MIMETYPES:  # type: ignore
            # this is an image type, so create a preview
            new_node.img_data = f"data:{IMAGE_MIMETYPES[kaitai_def]};base64," \
                                f"{base64.b64encode(ast.raw_value).decode('utf-8')}"

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
