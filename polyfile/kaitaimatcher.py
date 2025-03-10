import base64
import re
from typing import Dict, Iterator, List, Tuple, Type

from kaitaistruct import KaitaiStruct, KaitaiStructError

from .kaitai.parser import ASTNode, KaitaiParser, RootNode
from .kaitai.parsers.gif import Gif
from .kaitai.parsers.jpeg import Jpeg
from .kaitai.parsers.png import Png
from .logger import getStatusLogger
from .polyfile import register_parser, InvalidMatch, Match, Parser, Submatch


log = getStatusLogger(__name__)

KAITAI_MIME_MAPPING: Dict[str, str] = {
    "image/gif": "image/gif.ksy",
    "image/png": "image/png.ksy",
    "image/jpeg": "image/jpeg.ksy",
    "image/vnd.microsoft.icon": "image/ico.ksy",
#    "image/wmf": "image/wmf.ksy",  # there is currently a problem with this parser in Python
    "application/vnd.nitf": "image/nitf.ksy",
    "application/vnd.tcpdump.pcap": "network/pcap.ksy",
    "application/x-sqlite3": "database/sqlite3.ksy",
    "application/x-rar": "archive/rar.ksy",
    "font/sfnt": "font/ttf.ksy",
    "application/x-pie-executable": "executable/elf.ksy",
    "application/gzip": "archive/gzip.ksy",
    "application/x-xar": "archive/xar.ksy",
    "application/x-python-code": "executable/python_pyc_27.ksy",
    "application/x-shockwave-flash": "executable/swf.ksy",
    "application/x-doom": "game/doom_wad.ksy",
    "image/x-dcx": "image/pcx_dcx.ksy",
    "model/gltf-binary": "3d/gltf_binary.ksy",
    "application/x-rpm": "archive/rpm.ksy",
    "application/x-cpio": "archive/cpio_old_le.ksy",
    "image/x-gimp-gbr": "image/gimp_brush.ksy",
#    "application/dicom": "image/dicom.ksy",  # there is currently a problem with this parser in Python
    "image/bmp": "image/bmp.ksy",
    "application/x-blender": "media/blender_blend.ksy",
    "audio/x-voc": "media/creative_voice_file.ksy",
    "audio/midi": "media/standard_midi_file.ksy",
    "application/dime": "network/dime_message.ksy",
    "application/bson": "serialization/bson.ksy",
    "application/x-ms-shortcut": "windows/windows_lnk_file.ksy",
    "application/x-java-applet": "executable/java_class.ksy",
    # Uncomment this when/if Kaitai fixes its upstream compilation bug for ICC
# (https://github.com/kaitai-io/kaitai_struct_formats/issues/347#ref-commit-fde2866)
#    "application/vnd.iccprofile": "image/icc_4.ksy"
}

IMAGE_MIMETYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/bmp",
}

MIME_BY_PARSER: Dict[Type[KaitaiStruct], str] = {}


def ast_to_matches(ast: RootNode, parent: Match) -> Iterator[Submatch]:
    stack: List[Tuple[Match, ASTNode]] = [(parent, ast)]
    while stack:
        parent, node = stack.pop()

        new_node = Submatch(
            name=node.name,
            match_obj=node.raw_value,
            relative_offset=node.start - parent.offset,
            length=len(node.segment),
            parent=parent
        )

        if node is ast and node.obj.__class__ in MIME_BY_PARSER:  # type: ignore
            mtype = MIME_BY_PARSER[node.obj.__class__]  # type: ignore
            if mtype in IMAGE_MIMETYPES:  # type: ignore
                # this is an image type, so create a preview
                new_node.img_data = f"data:{mtype};base64,{base64.b64encode(ast.raw_value).decode('utf-8')}"

        yield new_node
        stack.extend(reversed([(new_node, c) for c in node.children]))


for mimetype, kaitai_path in KAITAI_MIME_MAPPING.items():
    class parse_:
        kaitai_parser = KaitaiParser.load(kaitai_path)

        def __call__(self, stream, match):
            try:
                ast = self.kaitai_parser.parse(stream).ast
            except KaitaiStructError as e:
                log.warning(f"Error parsing {stream.name} using {self.kaitai_parser}: {e!s}")
                raise InvalidMatch()
            except Exception as e:
                log.error(f"Unexpected exception parsing {stream.name} using {self.kaitai_parser}: {e!s}")
                raise InvalidMatch()
            yield from ast_to_matches(ast, parent=match)

    func_name = mimetype.replace("/", "_").replace("-", "_")

    parse_.__name__ = f"{parse_.__name__}{func_name}"
    parse_.__qualname__ = f"{parse_.__qualname__}{func_name}"

    register_parser(mimetype)(parse_())

    MIME_BY_PARSER[parse_.kaitai_parser.struct_type] = mimetype

del func_name
del kaitai_path
del mimetype
del parse_
