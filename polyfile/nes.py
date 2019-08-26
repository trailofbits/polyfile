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
        file_stream.read(8192)
        yield Submatch(
            name='CHRBank',
            display_name=f'CHRBank{i}',
            match_obj='',
            relative_offset=offset,
            length=8192,
            parent=parent
        )


@submatcher('rom-nes.trid.xml')
class INESMatcher(Match):
    def submatch(self, file_stream):
        yield from parse_ines(file_stream, parent=self)
