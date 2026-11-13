"""Parser positions belong to analysis sources independently of backing stream views."""

import pytest

from polyfile.fileutils import FileStream
from polyfile.kaitaimatcher import LazyKaitaiParser
from polyfile.polyfile import Match, Matcher, Submatch
from tests.test_zipmatcher import PNG


def parser_stream(data: bytes, backing_base: int, nested: bool) -> FileStream:
    """Present the same bytes through direct and nested views of a backing buffer."""
    stream = FileStream(
        b"!" * backing_base + data + b"outside", start=backing_base, length=len(data)
    )
    return FileStream(stream) if nested else stream


def parser_parent(data: bytes, source_base: int, decoded: bool) -> Match:
    """Create a parser parent in either the physical or an independent decoded source."""
    matcher = Matcher(parse=False)
    if decoded:
        encoded = Match("encoded", None, relative_offset=601, length=10, matcher=matcher)
        source = Submatch(
            "decoded_content",
            None,
            parent=encoded,
            source="decoded:0",
            length=source_base + len(data),
        )
        return Submatch("input", None, relative_offset=source_base, length=len(data), parent=source)
    return Match("input", None, relative_offset=source_base, length=len(data), matcher=matcher)


@pytest.mark.parametrize("backing_base", [0, 37])
@pytest.mark.parametrize("source_base", [0, 117])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("decoded", [False, True])
def test_kaitai_positions_use_the_parser_parent_source(
    backing_base: int,
    source_base: int,
    nested: bool,
    decoded: bool,
) -> None:
    parser = LazyKaitaiParser("image/png.ksy", "image/png")
    baseline = list(parser(FileStream(PNG), parser_parent(PNG, 0, False)))
    parent = parser_parent(PNG, source_base, decoded)
    matches = list(parser(parser_stream(PNG, backing_base, nested), parent))
    assert matches[0].offset == source_base
    assert [
        (m.name, m.offset - source_base, m.relative_offset, m.length, m.match) for m in matches
    ] == [(m.name, m.offset, m.relative_offset, m.length, m.match) for m in baseline]
    for match in matches:
        assert match.source == parent.source
        start = match.offset - source_base
        assert PNG[start : start + match.length] == match.match


def test_selected_backing_view_is_a_zero_based_analysis_input() -> None:
    matches = list(Matcher().match(parser_stream(PNG, 37, True)))
    image = next(m for m in matches if m.name == "image/png" and m.parent is None)
    assert image.offset == 0
    assert next(m for m in image.children if m.name == "Png").offset == 0
