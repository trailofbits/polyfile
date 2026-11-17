"""Render byte windows while retaining exact UTF-8 source spans."""

from dataclasses import dataclass

from rich.cells import cell_len

from polyfile.explorer.model import ByteRange, ByteSource


@dataclass(frozen=True)
class TextUnit:
    """One visible glyph and the bytes that produced it."""

    text: str
    range: ByteRange


def _utf8_length(data: bytes, index: int) -> int:
    lead = data[index]
    expected = 1
    if 0xC2 <= lead <= 0xDF:
        expected = 2
    elif 0xE0 <= lead <= 0xEF:
        expected = 3
    elif 0xF0 <= lead <= 0xF4:
        expected = 4
    length = 1
    bounds = {0xE0: (0xA0, 0xBF), 0xED: (0x80, 0x9F), 0xF0: (0x90, 0xBF), 0xF4: (0x80, 0x8F)}
    while length < expected and index + length < len(data):
        lower, upper = bounds.get(lead, (0x80, 0xBF)) if length == 1 else (0x80, 0xBF)
        if not lower <= data[index + length] <= upper:
            break
        length += 1
    return length


def _visible_text(data: bytes) -> str:
    if len(data) == 1 and data[0] < 32:
        return chr(0x2400 + data[0])
    if data == b"\x7f":
        return "␡"
    text = data.decode("utf-8", errors="replace")
    text = "".join(char if char.isprintable() else "�" for char in text)
    if cell_len(text) == 0:
        return "◌" + text
    return text


def text_units(source: ByteSource, start: int, length: int) -> tuple[TextUnit, ...]:
    """Decode a bounded window, preserving byte spans at malformed boundaries.

    A glyph belongs to the byte row containing its first byte. Up to three bytes
    on either side of the window establish the boundaries of UTF-8 characters.
    Terminal control characters are rendered as visible glyphs.

    Args:
        source: Physical or decoded byte source.
        start: First byte of the row.
        length: Number of source bytes assigned to the row.

    Returns:
        Visible glyphs with source-qualified byte spans.
    """
    if length == 0:
        return ()
    before = max(0, start - 3)
    end = min(source.length, start + length)
    data = source.read(before, min(source.length, end + 3) - before)
    result = []
    index = 0
    while before + index < end:
        size = _utf8_length(data, index)
        offset = before + index
        if offset >= start:
            end_index = index + size
            result.append(
                TextUnit(
                    _visible_text(data[index:end_index]),
                    ByteRange(source.identifier, offset, size),
                )
            )
        index += size
    return tuple(result)
