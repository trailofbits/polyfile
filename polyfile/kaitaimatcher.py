import base64
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from kaitaistruct import KaitaiStructError

from .fileutils import ExactNamedTempfile
from .kaitai.parser import ASTNode, KaitaiParser, RootNode
from .logger import getStatusLogger
from .magic import MagicMatcher, TestType
from .polyfile import register_parser, InvalidMatch, Match, Submatch


log = getStatusLogger(__name__)

# libmagic detects these formats but associates no MIME type with them, so PolyFile had no key on
# which to dispatch their Kaitai parsers. Defining the tests here rather than patching
# `polyfile/magic_defs/` keeps them from being clobbered the next time those definitions are
# refreshed from upstream Magdir. This is the same approach `polyfile/nitf.py` takes.
with ExactNamedTempfile(b"""# Doom WAD; see the description-only test in magic_defs/games.
0\tstring\t=IWAD\t\tDoom main IWAD data
!:mime application/x-doom
!:ext wad
0\tstring\t=PWAD\t\tDoom patch PWAD data
!:mime application/x-doom
!:ext wad
# Creative Voice File; see the description-only test in magic_defs/audio.
0\tstring\tCreative\\ Voice\\ File\tCreative Labs voice data
!:mime audio/x-voc
!:ext voc
""", name="KaitaiMimeMatchers") as t:
    MagicMatcher.DEFAULT_INSTANCE.add(Path(t), test_type=TestType.BINARY)

# Maps a MIME type to the Kaitai Struct specification that parses it. Several keys may share one
# specification, either because libmagic subtypes a container (OLE2) or because one spec covers a
# family (ELF, sfnt fonts).
#
# Every key must be a MIME type that some PolyFile matcher can emit, and every value must name an
# importable parser. `tests/test_kaitai.py` enforces both: dispatch is an exact lookup on the
# resolved MIME type, so a key nothing emits is dead code that fails silently.
KAITAI_MIME_MAPPING: Dict[str, str] = {
    # Images
    "image/gif": "image/gif.ksy",
    "image/png": "image/png.ksy",
    "image/jpeg": "image/jpeg.ksy",
    "image/bmp": "image/bmp.ksy",
    "image/webp": "image/webp.ksy",
    "image/vnd.microsoft.icon": "image/ico.ksy",
    "image/x-tga": "image/tga.ksy",
    "image/vnd.zbrush.pcx": "image/pcx.ksy",
    "image/x-dcx": "image/pcx_dcx.ksy",
    "image/x-gimp-gbr": "image/gimp_brush.ksy",
    "application/vnd.nitf": "image/nitf.ksy",
    "application/dicom": "image/dicom.ksy",
    # Only ICC v4 profiles parse; the spec validates the version field, so v2 profiles raise a
    # KaitaiStructError and fall through to the next parser.
    "application/vnd.iccprofile": "image/icc_4.ksy",
    # Only placeable metafiles parse; the spec's first field is the Aldus placeable header, so a
    # bare META_HEADER file raises a KaitaiStructError.
    "image/wmf": "image/wmf.ksy",

    # Audio and video
    "audio/midi": "media/standard_midi_file.ksy",
    "audio/x-voc": "media/creative_voice_file.ksy",
    "audio/x-wav": "media/wav.ksy",
    "audio/basic": "media/au.ksy",
    "audio/x-dec-basic": "media/au.ksy",
    "application/ogg": "media/ogg.ksy",
    "audio/ogg": "media/ogg.ksy",
    "video/ogg": "media/ogg.ksy",
    "video/x-msvideo": "media/avi.ksy",
    "video/quicktime": "media/quicktime_mov.ksy",
    "video/mp4": "media/quicktime_mov.ksy",
    # Executables
    "application/x-executable": "executable/elf.ksy",
    "application/x-pie-executable": "executable/elf.ksy",
    "application/x-sharedlib": "executable/elf.ksy",
    "application/x-object": "executable/elf.ksy",
    "application/x-coredump": "executable/elf.ksy",
    # A Mach-O file is either thin or universal, and libmagic reports both the same way, so both
    # parsers are registered and the one that does not apply raises a KaitaiStructError.
    "application/x-mach-binary": "executable/mach_o.ksy",
    "application/vnd.microsoft.portable-executable": "executable/microsoft_pe.ksy",
    "application/x-dosexec": "executable/microsoft_pe.ksy",
    "application/x-java-applet": "executable/java_class.ksy",
    "application/x-shockwave-flash": "executable/swf.ksy",
    # Only CPython 2.7 bytecode parses; other versions raise a KaitaiStructError.
    "application/x-bytecode.python": "executable/python_pyc_27.ksy",
    # Archives and filesystems
    "application/gzip": "archive/gzip.ksy",
    # application/vnd.rar is unmapped because archive/rar.ksy hangs on RAR5. Its `blocks`
    # field is `repeat: eos` over a switch whose v5 case, `block_v5`, is an empty stub that
    # consumes no bytes, so the loop never advances the stream and grows the block list until
    # memory runs out. A 76-byte RAR5 file is enough. RAR5 has been the default since 2013.
    "application/x-xar": "archive/xar.ksy",
    "application/x-rpm": "archive/rpm.ksy",
    "application/x-cpio": "archive/cpio_old_le.ksy",
    # Databases and serialization
    "application/vnd.sqlite3": "database/sqlite3.ksy",
    "application/geopackage+sqlite3": "database/sqlite3.ksy",
    "application/x-audacity-project+sqlite3": "database/sqlite3.ksy",
    "application/x-dbf": "database/dbf.ksy",
    "application/x-gettext-translation": "database/gettext_mo.ksy",
    "application/x-python-pickle": "serialization/python_pickle.ksy",
    "application/pkix-cert": "serialization/asn1/asn1_der.ksy",
    "application/pkcs10": "serialization/asn1/asn1_der.ksy",
    "application/pkcs7-mime": "serialization/asn1/asn1_der.ksy",
    # OLE2 compound files. This is a curated subset of the container types libmagic subtypes;
    # msword, vnd.ms-excel and vnd.ms-powerpoint are also emitted by non-OLE2 definitions
    # (magic_defs/rtf, magic_defs/msdos), where the parser raises a KaitaiStructError.
    "application/x-ole-storage": "serialization/microsoft_cfb.ksy",
    "application/msword": "serialization/microsoft_cfb.ksy",
    "application/vnd.ms-excel": "serialization/microsoft_cfb.ksy",
    "application/vnd.ms-powerpoint": "serialization/microsoft_cfb.ksy",
    "application/vnd.ms-project": "serialization/microsoft_cfb.ksy",
    "application/vnd.visio": "serialization/microsoft_cfb.ksy",
    "application/x-msi": "serialization/microsoft_cfb.ksy",
    "application/x-ms-msg": "serialization/microsoft_cfb.ksy",
    "application/x-ms-thumbnail": "serialization/microsoft_cfb.ksy",
    # Fonts
    "font/ttf": "font/ttf.ksy",
    "font/otf": "font/ttf.ksy",
    "application/vnd.ms-opentype": "font/ttf.ksy",
    # Everything else
    "application/vnd.tcpdump.pcap": "network/pcap.ksy",
    "application/x-ms-shortcut": "windows/windows_lnk_file.ksy",
    "application/x-apple-rsr": "macos/resource_fork.ksy",
    "application/x-blender": "media/blender_blend.ksy",
    "application/x-doom": "game/doom_wad.ksy",
    "model/gltf-binary": "3d/gltf_binary.ksy",
}

# A universal Mach-O binary shares `application/x-mach-binary` with a thin one, so its parser is
# registered separately rather than displacing the thin parser in the mapping above.
EXTRA_PARSERS: Tuple[Tuple[str, str], ...] = (
    ("application/x-mach-binary", "executable/mach_o_fat.ksy"),
)

IMAGE_MIMETYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
}


def ast_to_matches(ast: RootNode, parent: Match, mimetype: str) -> Iterator[Submatch]:
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

        if node is ast and mimetype in IMAGE_MIMETYPES:
            new_node.img_data = f"data:{mimetype};base64,{base64.b64encode(ast.raw_value).decode('utf-8')}"

        yield new_node
        stack.extend(reversed([(new_node, c) for c in node.children]))


class LazyKaitaiParser:
    """Parser that lazily loads the Kaitai struct parser on first use."""

    def __init__(self, kaitai_path: str, mimetype: str):
        self.kaitai_path = kaitai_path
        self.mimetype = mimetype
        self._kaitai_parser = None

    @property
    def kaitai_parser(self):
        if self._kaitai_parser is None:
            self._kaitai_parser = KaitaiParser.load(self.kaitai_path)
        return self._kaitai_parser

    def __call__(self, stream, match):
        try:
            ast = self.kaitai_parser.parse(stream).ast
        except KaitaiStructError as e:
            # Several MIME types share a specification, and some specifications cover only part of
            # what their MIME type denotes, so this is an expected outcome rather than a problem.
            log.debug(f"Error parsing {stream.name} using {self.kaitai_parser}: {e!s}")
            raise InvalidMatch()
        except Exception as e:
            log.error(f"Unexpected exception parsing {stream.name} using {self.kaitai_parser}: {e!s}")
            raise InvalidMatch()
        yield from ast_to_matches(ast, parent=match, mimetype=self.mimetype)


def _register(mimetype: str, kaitai_path: str) -> None:
    parser = LazyKaitaiParser(kaitai_path, mimetype)
    func_name = f"parse_{Path(kaitai_path).stem}"
    parser.__name__ = func_name
    parser.__qualname__ = func_name
    register_parser(mimetype)(parser)


for _mimetype, _kaitai_path in tuple(KAITAI_MIME_MAPPING.items()) + EXTRA_PARSERS:
    _register(_mimetype, _kaitai_path)

del _mimetype
del _kaitai_path
