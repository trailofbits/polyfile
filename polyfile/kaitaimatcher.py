import base64
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator

from kaitaistruct import KaitaiStructError

from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.kaitai.parser import ASTNode, CompoundNode, KaitaiParser, RootNode
from polyfile.logger import getStatusLogger
from polyfile.magic import MagicMatcher, TestType
from polyfile.polyfile import register_parser, InvalidMatch, Match, Submatch


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
KAITAI_MIME_MAPPING: dict[str, str] = {
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
EXTRA_PARSERS: tuple[tuple[str, str], ...] = (
    ("application/x-mach-binary", "executable/mach_o_fat.ksy"),
)

IMAGE_MIMETYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
}


def _mapped_nodes(
    ast: RootNode,
    parent: Match,
    mimetype: str,
) -> Iterator[tuple[Submatch, ASTNode]]:
    source_base = parent.offset
    stack: list[tuple[Match, ASTNode]] = [(parent, ast)]
    while stack:
        parent, node = stack.pop()
        new_node = Submatch(
            name=node.name,
            match_obj=node.raw_value,
            relative_offset=source_base + node.start - parent.offset,
            length=len(node.segment),
            parent=parent,
        )
        if node is ast and mimetype in IMAGE_MIMETYPES:
            encoded = base64.b64encode(ast.raw_value).decode("utf-8")
            new_node.img_data = f"data:{mimetype};base64,{encoded}"
        yield new_node, node
        stack.extend(reversed([(new_node, child) for child in node.children]))


def ast_to_matches(ast: RootNode, parent: Match, mimetype: str) -> Iterator[Submatch]:
    """Map view-local AST positions into the parser parent's analysis source.

    Args:
        ast: The tree whose offsets are relative to the parsed stream view.
        parent: The match at which that view starts within its analysis source.
        mimetype: The input's MIME type, used to render supported images.

    Yields:
        Each AST node positioned in the same source as the parser parent.
    """
    for match, _ in _mapped_nodes(ast, parent, mimetype):
        yield match


@dataclass(frozen=True, kw_only=True)
class _ContainerFormat:
    array: str
    offset: str
    length: str
    payload: str
    magic: bytes
    header_size: int
    entry_size: int


_CONTAINERS = {
    "image/ico.ksy": _ContainerFormat(
        array="images",
        offset="ofs_img",
        length="len_img",
        payload="img",
        magic=b"\0\0\1\0",
        header_size=6,
        entry_size=16,
    ),
    "executable/mach_o_fat.ksy": _ContainerFormat(
        array="fat_archs",
        offset="ofs_object",
        length="len_object",
        payload="object",
        magic=b"\xca\xfe\xba\xbe",
        header_size=8,
        entry_size=20,
    ),
}


def _container_ranges(
    ast: RootNode,
    container: _ContainerFormat,
) -> dict[ASTNode, tuple[int, int, tuple[str, str] | None]]:
    table = next(child for child in ast.children if child.name == container.array)
    ranges = []
    for entry in table.children:
        assert isinstance(entry, CompoundNode)
        offset = int(getattr(entry.obj, container.offset))
        length = int(getattr(entry.obj, container.length))
        ranges.append((offset, length, entry))
    result = {}
    previous_end = table.end
    for offset, length, entry in sorted(ranges, key=lambda item: item[0]):
        failure: tuple[str, str] | None = None
        if length == 0 or offset < table.end or offset + length > ast.size:
            failure = (
                "invalid",
                "Content range is empty, overlaps the directory, or exceeds the input",
            )
        elif offset < previous_end:
            failure = "unsupported", "Duplicate or overlapping content range is not analyzed again"
        else:
            previous_end = offset + length
        result[entry] = offset, length, failure
    return result


def _match_region(
    stream: FileStream,
    region: Match,
    offset: int,
    *,
    png: bool,
) -> Iterator[Match]:
    assert region.matcher is not None
    with FileStream(stream, start=offset, length=region.length) as view:
        if png and view.read(8) != b"\x89PNG\r\n\x1a\n":
            region.analysis_status = "unsupported"
            region.analysis_message = "ICO payload is not PNG; DIB decoding is not supported"
            return
        yield from region.matcher.match(view, parent=region)


def _container_matches(
    ast: RootNode,
    stream: FileStream,
    parent: Match,
    mimetype: str,
    container: _ContainerFormat,
) -> Iterator[Match]:
    ranges = _container_ranges(ast, container)
    source_base = parent.offset
    for match, node in _mapped_nodes(ast, parent, mimetype):
        yield match
        if node not in ranges:
            continue
        offset, length, failure = ranges[node]
        if failure is not None:
            match.analysis_status, match.analysis_message = failure
            continue
        region = Submatch(
            container.payload,
            None,
            relative_offset=source_base + offset - match.offset,
            length=length,
            parent=match,
        )
        yield region
        yield from _match_region(stream, region, offset, png=container.payload == "img")


def _truncated_table(stream: FileStream, container: _ContainerFormat) -> bool:
    header = stream[: container.header_size].content
    if not header.startswith(container.magic):
        return False
    if len(header) < container.header_size:
        return True
    byteorder = "little" if container.payload == "img" else "big"
    magic_size = len(container.magic)
    count = int.from_bytes(header[magic_size:], byteorder)
    return container.header_size + count * container.entry_size > len(stream)


def _map_truncated_table(
    stream: FileStream,
    parent: Match,
    container: _ContainerFormat,
) -> Iterator[Match]:
    parent.analysis_status = "invalid"
    parent.analysis_message = "Container directory is truncated"
    header_size = min(container.header_size, len(stream))
    yield Submatch(
        "header",
        stream[:header_size].content,
        length=header_size,
        parent=parent,
    )
    table = Submatch(
        container.array,
        None,
        relative_offset=header_size,
        length=len(stream) - header_size,
        parent=parent,
    )
    yield table
    for index, offset in enumerate(range(header_size, len(stream), container.entry_size)):
        length = min(container.entry_size, len(stream) - offset)
        end = offset + length
        yield Submatch(
            f"{container.array}[{index}]",
            stream[offset:end].content,
            relative_offset=offset - header_size,
            length=length,
            parent=table,
        )


class LazyKaitaiParser:
    """Parser that lazily loads the Kaitai struct parser on first use."""

    __name__: str
    __qualname__: str

    def __init__(self, kaitai_path: str, mimetype: str):
        self.kaitai_path = kaitai_path
        self.mimetype = mimetype
        self._kaitai_parser: KaitaiParser | None = None

    @property
    def kaitai_parser(self):
        if self._kaitai_parser is None:
            self._kaitai_parser = KaitaiParser.load(self.kaitai_path)
        return self._kaitai_parser

    def __call__(self, stream, match):
        container = _CONTAINERS.get(self.kaitai_path)
        if container is not None and _truncated_table(stream, container):
            yield from _map_truncated_table(stream, match, container)
            return
        try:
            ast = self.kaitai_parser.parse(stream).ast
        except KaitaiStructError as e:
            # Several MIME types share a specification, and some specifications cover only part of
            # what their MIME type denotes, so this is an expected outcome rather than a problem.
            log.debug(f"Error parsing {stream.name} using {self.kaitai_parser}: {e!s}")
            raise InvalidMatch()
        except Exception as e:
            log.error(
                f"Unexpected exception parsing {stream.name} using {self.kaitai_parser}: {e!s}"
            )
            raise InvalidMatch()
        if container is None:
            yield from ast_to_matches(ast, parent=match, mimetype=self.mimetype)
        else:
            yield from _container_matches(ast, stream, match, self.mimetype, container)


def _register(mimetype: str, kaitai_path: str) -> None:
    parser = LazyKaitaiParser(kaitai_path, mimetype)
    func_name = f"parse_{Path(kaitai_path).stem}"
    parser.__name__ = func_name
    parser.__qualname__ = func_name
    register_parser(mimetype)(parser)


for _mimetype, _kaitai_path in tuple(KAITAI_MIME_MAPPING.items()) + EXTRA_PARSERS:
    _register(_mimetype, _kaitai_path)
