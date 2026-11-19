import base64
from collections.abc import Iterator
from io import BytesIO
from typing import TYPE_CHECKING, cast

from polyfile.fileutils import FileStream
from polyfile.polyfile import register_parser, InvalidMatch, Match, Submatch

if TYPE_CHECKING:
    from PIL import Image as PILImage


def _get_pil():
    """Lazy import PIL only when needed (for NES ROM CHR bank rendering)."""
    from PIL import Image, ImageDraw
    return Image, ImageDraw


def parse_ines_header(header, parent=None):
    magic = header[:4]
    if magic != b'NES\x1A':
        raise InvalidMatch(f"Expected \"NES\\x1A\" magic at the beginning of the file, but found {magic!r}")
    if len(header) < 16:
        raise InvalidMatch(f"Expected a 16 byte iNES header, but the file only contains {len(header)} bytes")
    parent = Submatch(
        name='iNESHeader',
        match_obj=header,
        relative_offset=0,
        length=16,
        parent=parent
    )
    yield parent
    yield Submatch(
        name='iNESMagic',
        match_obj="NES",
        relative_offset=0,
        length=4,
        parent=parent
    )
    prg_size = header[4]
    yield Submatch(
        name='PRGSize',
        match_obj=prg_size,
        relative_offset=4,
        length=1,
        parent=parent
    )
    chr_size = header[5]
    yield Submatch(
        name='CHRSize',
        match_obj=chr_size,
        relative_offset=5,
        length=1,
        parent=parent
    )
    for i in range(6,8):
        yield Submatch(
            name='Flags',
            display_name=f'Flags{i}',
            match_obj=header[i],
            relative_offset=i,
            length=1,
            parent=parent
        )
    yield Submatch(
        name='PRGRAMSize',
        match_obj=header[8],
        relative_offset=8,
        length=1,
        parent=parent
    )
    for i in range(9,11):
        yield Submatch(
            name='Flags',
            display_name=f'Flags{i}',
            match_obj=header[i],
            relative_offset=i,
            length=1,
            parent=parent
        )
    yield Submatch(
        name='UnusedPadding',
        match_obj=header[11:],
        relative_offset=11,
        length=5,
        parent=parent
    )


def _rom_size(low: int, high: int, bank_size: int) -> int:
    if high == 0x0F:
        return (1 << (low >> 2)) * (2 * (low & 3) + 1)
    return ((high << 8) | low) * bank_size


def _rom_banks(header: bytes) -> Iterator[tuple[str, int, int]]:
    if header[6] & 4:
        yield "Trainer", 512, 512
    high = header[9] if header[7] & 0x0C == 8 else 0
    yield "PRGBank", _rom_size(header[4], high & 0x0F, 16384), 16384
    yield "CHRBank", _rom_size(header[5], high >> 4, 8192), 8192


def _chr_preview(data: bytes) -> str:
    with BytesIO() as image:
        render_chr(data).save(image, "PNG")
        return "data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii")


@register_parser("application/x-nes-rom")
def parse_ines(file_stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map the trainer and ROM banks available in an iNES or NES 2.0 file."""
    header = file_stream.read(16)
    yield from parse_ines_header(header, parent)
    for name, size, unit in _rom_banks(header):
        for index, start in enumerate(range(0, size, unit)):
            expected = min(unit, size - start)
            offset = file_stream.tell()
            data = file_stream.read(expected)
            complete = len(data) == expected
            if not complete:
                parent.analysis_status = "invalid"
                parent.analysis_message = (
                    f"Truncated {name}: expected {expected} bytes, got {len(data)}"
                )
            if data:
                preview = None
                if name == "CHRBank" and complete and len(data) % 16 == 0:
                    preview = _chr_preview(data)
                yield Submatch(
                    name=name, display_name=name if name == "Trainer" else f"{name}{index}",
                    match_obj=data if name == "Trainer" else "", parent=parent,
                    relative_offset=offset, length=len(data), img_data=preview,
                )
            if not complete:
                return


def chr_values(chr_bytes: bytes):
    for i, offset in enumerate(range(0, len(chr_bytes), 16)):
        base_x = (i % 16) * 8
        base_y = (i // 16) * 8
        for y in range(8):
            for x in range(8):
                shift = 7 - x
                yield base_x + x,\
                      base_y + y,\
                      ((((chr_bytes[offset + y + 8] >> shift) & 0b1)) << 1) | ((chr_bytes[offset + y] >> shift) & 0b1)


def render_chr(chr_bytes: bytes) -> "PILImage.Image":
    Image, ImageDraw = _get_pil()
    img = cast("PILImage.Image", Image.new(mode='L', size=(8*16, 8*32)))
    d = ImageDraw.Draw(img)
    for x, y, pixel in chr_values(chr_bytes):
        if pixel == 1:
            pixel = 0xFF//3
        elif pixel == 2:
            pixel = 0xFF//3*2
        elif pixel == 3:
            pixel = 0xFF
        d.point((x, y), pixel)
    return img
