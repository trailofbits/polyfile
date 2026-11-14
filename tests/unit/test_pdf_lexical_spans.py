"""Real PDF lexemes retain raw extents through decoding and dictionary construction."""

from typing import BinaryIO, cast

import pytest
from pdfminer.psparser import KWD

from polyfile.fileutils import FileStream
from polyfile.pdf import (
    PDFDict, PDFLiteral, PDFParser, PSBytes, PSStr, RawPDFStream,
    has_provenance, parse_object,
    pdf_parser,
)
from polyfile.polyfile import Match, Matcher
from pdf_fixtures import CATALOG, pdf_fixture

LEXEMES = [
    (b"(a\\nb)", b"a\nb", 1, 4),
    (b"(a\\101b)", b"aAb", 1, 6),
    (b"(a\\\nb)", b"ab", 1, 4),
    (b"(a(b)c)", b"a(b)c", 1, 5),
    (b"()", b"", 1, 0),
    (b"<616263>", b"abc", 1, 6),
    (b"<61 62>", b"ab", 1, 5),
    (b"/AB#43", "ABC", 0, 6),
    (b"/\xff", b"\xff", 0, 2),
    (b"/A#ff", b"A\xff", 0, 5),
    (b"/\xc3\xa9", "é", 0, 3),
]


def parse_value(data: bytes, composite: bool = False) -> object:
    with (
        FileStream(b"prefix!" + data + b"outside", start=7) as backing,
        FileStream(backing, length=len(data)) as stream,
    ):
        parser = PDFParser(cast(BinaryIO, RawPDFStream(stream)))
        parser.auto_flush = True
        return parser.nextobject()[1] if composite else parser.nexttoken()[1]


@pytest.mark.parametrize("case", LEXEMES)
@pytest.mark.parametrize("position", [0, PDFParser.BUFSIZ - 1, PDFParser.BUFSIZ])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("source_base", [0, 117])
def test_raw_lexeme_extents_reach_serialized_matches(
    case: tuple[bytes, str | bytes, int, int], position: int, source: str, source_base: int,
) -> None:
    lexeme, expected, relative, size = case
    value = parse_value(b" " * position + lexeme + b" ")
    assert has_provenance(value)
    assert (value.pdf_offset, value.pdf_bytes) == (position + relative, size)
    if isinstance(value, PDFLiteral):
        assert value.name == expected
        assert has_provenance(value.name)
        assert (value.name.pdf_offset, value.name.pdf_bytes) == (position + 1, len(lexeme) - 1)
        assert value.raw_name == lexeme[1:]
    else:
        assert value == expected
    matcher = Matcher(parse=False)
    parent = Match(
        "PDF", None, relative_offset=source_base, length=position + len(lexeme),
        matcher=matcher, source=source,
    )
    list(parse_object(value, matcher, parent, pdf_header_offset=source_base))
    output = parent.children[0].to_obj()
    assert (output["offset"], output["size"], output["source"]) == (
        source_base + position + relative, size, source,
    )


@pytest.mark.parametrize("data", [b"(a\\nb)", b"<616263>", b"/AB#43"])
def test_decoded_lexemes_do_not_invent_precise_slice_offsets(data: bytes) -> None:
    value = parse_value(data + b" ")
    if isinstance(value, PDFLiteral):
        value = value.name
    assert isinstance(value, (PSStr, PSBytes))
    part = value[1:2]
    assert has_provenance(part)
    assert (part.pdf_offset, part.pdf_bytes) == (value.pdf_offset, value.pdf_bytes)


@pytest.mark.parametrize("name", [b"A", b"AB#43", b"\xff", b"A#ff", b"\xc3\xa9"])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("source_base", [0, 117])
def test_dictionary_pairs_preserve_names_and_measure_from_actual_parent(
    name: bytes, source: str, source_base: int,
) -> None:
    data = b"<< /" + name + b" 42 >> "
    dictionary = parse_value(data, composite=True)
    assert isinstance(dictionary, PDFDict)
    key = next(iter(dictionary))
    assert isinstance(key, PSStr)
    assert key.pdf_raw_name == name
    expected_name = name.replace(b"#43", b"C").replace(b"#ff", b"\xff")
    try:
        expected_key = expected_name.decode("utf-8")
    except UnicodeDecodeError:
        expected_key = str(expected_name)
    assert key == expected_key
    assert dictionary[expected_key] == 42
    matcher = Matcher(parse=False)
    parent = Match(
        "PDF", None, relative_offset=source_base, length=len(data), matcher=matcher, source=source,
    )
    nodes = list(parse_object(dictionary, matcher, parent, pdf_header_offset=source_base))
    pair = next(node for node in nodes if node.name == "KeyValuePair")
    key_node = next(node for node in nodes if node.name == "Key")
    value_node = next(node for node in nodes if node.name == "Value")
    number = next(node for node in nodes if node.name == "PSInt")
    number_start = data.index(b"42")
    assert (dictionary.pdf_offset, dictionary.pdf_bytes) == (0, len(data) - 1)
    assert (pair.offset, pair.length) == (source_base + 3, number_start + 2 - 3)
    assert (key_node.offset, key_node.length) == (source_base + 3, len(name) + 1)
    for node in (value_node, number):
        output = node.to_obj()
        assert (output["offset"], output["size"], output["source"]) == (
            source_base + number_start, 2, source,
        )


@pytest.mark.parametrize("data", [b"42", b"3.125", b"/Name"])
def test_tokens_ending_at_eof_use_the_real_source_end(data: bytes) -> None:
    value = parse_value(data)
    assert has_provenance(value)
    assert (value.pdf_offset, value.pdf_bytes) == (0, len(data))


def test_physical_objects_cover_their_complete_dictionary_and_endobj() -> None:
    data = pdf_fixture(CATALOG)
    parent = Match("PDF", None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    objects = [node for node in nodes if node.name == "PDFObject"]
    assert len(objects) == 2
    for number, node in enumerate(objects, 1):
        start = data.index(f"{number} 0 obj".encode())
        end = data.index(b"endobj", start) + len(b"endobj\n")
        assert (node.offset, node.length) == (start, end - start)
        assert all(child.offset + child.length <= end for child in node.children)


def test_parsing_does_not_attach_positions_to_shared_keyword_singletons() -> None:
    keywords = [KWD(value) for value in (b"R", b"<<", b">>", b"[", b"]")]
    before = [dict(vars(keyword)) for keyword in keywords]
    parse_value(b"<< /A [3 0 R] >> ", composite=True)
    assert [vars(keyword) for keyword in keywords] == before
