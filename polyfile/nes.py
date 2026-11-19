import base64
from collections.abc import Iterator
from io import BytesIO
from typing import TYPE_CHECKING, cast

from polyfile.fileutils import FileStream
from polyfile.polyfile import register_parser, InvalidMatch, Match, Submatch
from polyfile.provenance import SourceSpan

if TYPE_CHECKING:
    from PIL import Image as PILImage


def _get_pil():
    """Lazy import PIL only when needed (for NES ROM CHR bank rendering)."""
    from PIL import Image, ImageDraw
    return Image, ImageDraw


def _is_nes2(header: bytes) -> bool:
    return header[7] & 0x0C == 0x08


def _nes2_ram_size(shift: int) -> int:
    return 64 << shift if shift else 0


def _nes2_header_fields(header: bytes, parent: Match) -> Iterator[Submatch]:
    mapper = ((header[8] & 0x0F) << 8) | (header[7] & 0xF0) | (header[6] >> 4)
    yield Submatch(
        name="MapperMSBAndSubmapper", match_obj=header[8], relative_offset=8, length=1,
        parent=parent, description=f"Mapper {mapper}, submapper {header[8] >> 4}",
        dependencies=(SourceSpan(parent.source, parent.offset + 6, 3),),
    )

    console_type = header[7] & 3
    console_details = header[13]
    if console_type == 1:
        console_name = "VsSystemType"
        console_value = f"PPU type {console_details & 0x0F}, hardware type {console_details >> 4}"
    elif console_type == 3:
        console_name = "ExtendedConsoleType"
        console_value = str(console_details & 0x0F)
    else:
        console_name = "Reserved"
        console_value = str(console_details)

    fields = (
        ("ROMSizeMSBs", f"PRG-ROM {header[9] & 0x0F}, CHR-ROM {header[9] >> 4}"),
        ("PRGRAMAndNVRAMSize",
         f"{_nes2_ram_size(header[10] & 0x0F)} bytes volatile, "
         f"{_nes2_ram_size(header[10] >> 4)} bytes nonvolatile"),
        ("CHRRAMAndNVRAMSize",
         f"{_nes2_ram_size(header[11] & 0x0F)} bytes volatile, "
         f"{_nes2_ram_size(header[11] >> 4)} bytes nonvolatile"),
        ("CPUPPUTiming", str(header[12] & 3)),
        (console_name, console_value),
        ("MiscellaneousROMCount", str(header[14] & 3)),
        ("DefaultExpansionDevice", str(header[15] & 0x3F)),
    )
    for offset, (name, description) in enumerate(fields, start=9):
        yield Submatch(
            name=name, match_obj=header[offset], relative_offset=offset, length=1,
            parent=parent, description=description,
        )


def parse_ines_header(header: bytes, parent: Match | None = None) -> Iterator[Submatch]:
    """Map an iNES or NES 2.0 header and its fields under the parent ROM match.

    Args:
        header: The header bytes, starting at the ROM signature.
        parent: The parent ROM match.

    Yields:
        The header match followed by its child fields in byte order.

    Raises:
        InvalidMatch: The signature is incorrect or the header is incomplete.
        ValueError: The header match has no parent.
    """
    magic = header[:4]
    if magic != b"NES\x1a":
        raise InvalidMatch(
            f'Expected "NES\\x1A" magic at the beginning of the file, but found {magic!r}'
        )
    if len(header) < 16:
        raise InvalidMatch(
            f"Expected a 16 byte iNES header, but the file only contains {len(header)} bytes"
        )
    parent = Submatch(
        name="iNESHeader", match_obj=header, relative_offset=0, length=16, parent=parent,
    )
    yield parent
    yield Submatch(
        name="iNESMagic", match_obj="NES", relative_offset=0, length=4, parent=parent,
    )
    is_nes2 = _is_nes2(header)
    fields: tuple[tuple[int, str, str | None], ...] = (
        (4, "PRGSize", None), (5, "CHRSize", None), (6, "Flags", "Flags6"), (7, "Flags", "Flags7"),
    )
    if not is_nes2:
        fields += ((8, "PRGRAMSize", None), (9, "Flags", "Flags9"), (10, "Flags", "Flags10"))
    for offset, name, display_name in fields:
        yield Submatch(
            name=name, display_name=display_name, match_obj=header[offset],
            relative_offset=offset, length=1, parent=parent,
        )
    if is_nes2:
        yield from _nes2_header_fields(header, parent)
    else:
        yield Submatch(
            name="UnusedPadding", match_obj=header[11:], relative_offset=11, length=5,
            parent=parent,
        )


def _rom_size(low: int, high: int, bank_size: int) -> int:
    if high == 0x0F:
        return (1 << (low >> 2)) * (2 * (low & 3) + 1)
    return ((high << 8) | low) * bank_size


def _rom_banks(header: bytes) -> Iterator[tuple[str, int, int]]:
    if header[6] & 4:
        yield "Trainer", 512, 512
    high = header[9] if _is_nes2(header) else 0
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
