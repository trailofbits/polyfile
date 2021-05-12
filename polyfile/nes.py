import base64
from io import BytesIO

from PIL import Image, ImageDraw

from .polyfile import submatcher, InvalidMatch, Match, Submatch


def parse_ines_header(header, parent=None):
    magic = header[:4]
    if magic != b'NES\x1A':
        raise InvalidMatch(f"Expected \"NES\\x1A\" magic at the beginning of the file, but found {magic!r}")
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


def parse_ines(file_stream, parent=None):
    header = file_stream.read(16)
    yield from parse_ines_header(header, parent)
    has_trainer = (header[6] & 0b100) != 0
    if has_trainer:
        yield Submatch(
            name='Trainer',
            match_obj=file_stream.read(512),
            relative_offset=16,
            length=512,
            parent=parent
        )
    prg_size = header[4]
    for i in range(prg_size):
        offset = file_stream.tell()
        file_stream.read(16384)
        yield Submatch(
            name='PRGBank',
            display_name=f'PRGBank{i}',
            match_obj='',
            relative_offset=offset,
            length=16384,
            parent=parent
        )
    chr_size = header[5]
    for i in range(chr_size):
        offset = file_stream.tell()
        chr_bytes = file_stream.read(8192)
        chr_img = render_chr(chr_bytes)
        with BytesIO() as img_data:
            chr_img.save(img_data, "PNG")
            yield Submatch(
                name='CHRBank',
                display_name=f'CHRBank{i}',
                match_obj='',
                relative_offset=offset,
                length=8192,
                parent=parent,
                img_data=f"data:image/png;base64,{base64.b64encode(img_data.getvalue()).decode('utf-8')}"
            )


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


def render_chr(chr_bytes: bytes) -> Image:
    img = Image.new(mode='L', size=(8*16, 8*32))
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


@submatcher("application/x-nes-rom")
class INESMatcher(Match):
    def submatch(self, file_stream):
        yield from parse_ines(file_stream, parent=self)
