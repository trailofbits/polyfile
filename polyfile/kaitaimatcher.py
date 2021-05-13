import base64
from typing import Dict, Iterator, List, Tuple, Type

from kaitaistruct import KaitaiStructError

from .kaitai.parser import ASTNode, KaitaiParser, KaitaiStruct, RootNode
from .kaitai.parsers.gif import Gif
from .kaitai.parsers.jpeg import Jpeg
from .kaitai.parsers.pcap import Pcap
from .kaitai.parsers.png import Png
from .kaitai.parsers.sqlite3 import Sqlite3
from .polyfile import submatcher, InvalidMatch, Match, Submatch


KAITAI_MIME_MAPPING: Dict[str, str] = {
    "image/gif": "image/gif.ksy",
    "image/png": "image/png.ksy",
    "image/jpeg": "image/jpeg.ksy",
    "image/vnd.microsoft.icon": "image/ico.ksy",
#    "image/wmf": "image/wmf.ksy",  # there is currently a problem with this parser in Python
    "application/vnd.tcpdump.pcap": "network/pcap.ksy",
    "application/x-sqlite3": "database/sqlite3.ksy",
    "application/x-rar": "archive/rar.ksy",
    "font/sfnt": "font/ttf.ksy"
}

IMAGE_MIMETYPES: Dict[Type[KaitaiStruct], str] = {
    Gif: "image/gif",
    Jpeg: "image/jpeg",
    Png: "image/png"
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
            new_node.img_data = f"data:{IMAGE_MIMETYPES[node.obj.__class__]};base64," \
                                f"{base64.b64encode(ast.raw_value).decode('utf-8')}"

        yield new_node
        stack.extend(reversed([(new_node, c) for c in node.children]))


for mimetype, kaitai_path in KAITAI_MIME_MAPPING.items():
    @submatcher(mimetype)
    class KaitaiMatcher(Match):
        kaitai_parser = KaitaiParser.load(kaitai_path)

        def submatch(self, file_stream):
            try:
                ast = self.kaitai_parser.parse(file_stream).ast
            except (Exception, KaitaiStructError):
                raise InvalidMatch()
            yield from ast_to_matches(ast, parent=self)
