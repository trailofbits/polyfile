"""Text soft magic reads libmagic's UTF-8 rendering of every text encoding."""

from pathlib import Path

import pytest

from polyfile.magic import (
    EBCDIC_TO_ASCII,
    TEXT_ENCODING_MAX_BYTES,
    UTF8_BYTE_ORDER_MARK,
    MagicMatcher,
    MatchContext,
    MatchedTest,
    detect_text_encoding,
)

SVG = (
    '<?xml version="1.0"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>\n'
)


def ebcdic_bytes(value: bytes) -> bytes:
    """Encodes using the inverse of libmagic's identification table."""
    return bytes(EBCDIC_TO_ASCII.index(byte) for byte in value)


def text_matcher(tmp_path: Path, value: str) -> MagicMatcher:
    """Builds a text-only search with a MIME type and a fixed description."""
    definition = tmp_path / "text.magic"
    definition.write_text(
        f"0\tsearch/128/t\t{value}\tfound\n!:mime text/x-buffer-test\n",
        encoding="utf-8",
    )
    return MagicMatcher.parse(definition)


def test_bom_utf8_svg_matches_without_the_mark() -> None:
    data = UTF8_BYTE_ORDER_MARK + SVG.encode()
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(data))
    assert {str(match) for match in matches} == {
        "SVG Scalable Vector Graphics image, Unicode text, UTF-8 (with BOM) text",
        "XML 1.0 document, Unicode text, UTF-8 (with BOM) text",
        "XML document, Unicode text, UTF-8 (with BOM) text",
    }
    for match in matches:
        assert match.context.data == SVG.encode()
        assert match.context.decoded_from == "utf-8-sig"


@pytest.mark.parametrize(
    "data,encoding,text",
    [
        (b"caf\xe9 TARGET\n", "iso-8859-1", "café TARGET\n"),
        (b"caf\x8b TARGET\n", "unknown-8bit", "caf\x8b TARGET\n"),
        (ebcdic_bytes(b"hello\tTARGET\n"), "ebcdic", "hello\tTARGET\n"),
        (ebcdic_bytes(b"caf\xe9\tTARGET\n"), "ebcdic-international", "café\tTARGET\n"),
    ],
)
def test_search_offsets_are_in_the_identified_decoded_buffer(
    tmp_path: Path, data: bytes, encoding: str, text: str
) -> None:
    assert detect_text_encoding(data) == encoding
    context = MatchContext(data, path=tmp_path / "input", only_match_mime=True)
    match = next(text_matcher(tmp_path, "TARGET").match(context))
    assert match.context.data == text.encode()
    assert match.context.decoded_from == encoding
    assert match.context.path == context.path
    assert match.context.only_match_mime
    result = match[0]
    assert isinstance(result, MatchedTest)
    assert result.offset == text.encode().index(b"TARGET")
    assert result.length == len(b"TARGET")
    assert (
        f"decoded from this file as {encoding}, not into the file itself"
        in match.explain(file=data, ansi_color=False)
    )


@pytest.mark.parametrize(
    "data,value",
    [(b"caf\xe9\n", "café"), (b"caf\x8b\n", "caf\x8b")],
)
def test_text_values_can_match_transcoded_high_bytes(
    tmp_path: Path, data: bytes, value: str
) -> None:
    match = next(text_matcher(tmp_path, value).match(data))
    assert str(match).startswith("found")
    result = match[0]
    assert isinstance(result, MatchedTest)
    length = len(value.encode())
    assert result.length == length
    assert match.context.data[:length] == value.encode()


@pytest.mark.parametrize(
    "data,encoding",
    [(b"plain ASCII\n", "ascii"), ("café\n".encode(), "utf-8"), (b"\x00\x01", None)],
)
def test_unchanged_or_binary_inputs_keep_their_context(
    data: bytes, encoding: str | None
) -> None:
    context = MatchContext(data)
    assert context.text_test_context(encoding) is context
    assert context.decoded_from is None


def test_an_unknown_encoding_keeps_the_existing_context() -> None:
    context = MatchContext(b"text\n")
    assert context.text_test_context("not-a-text-encoding") is context


@pytest.mark.parametrize(
    "source,encoding,expected",
    [
        (b"\xe9", "iso-8859-1", "é".encode()),
        (b"\x8b", "unknown-8bit", "\x8b".encode()),
        (ebcdic_bytes(b"a"), "ebcdic", b"a"),
        (ebcdic_bytes(b"\xe9"), "ebcdic-international", "é".encode()),
    ],
)
def test_transcoding_stops_at_the_source_byte_limit(
    source: bytes, encoding: str, expected: bytes
) -> None:
    context = MatchContext(source * TEXT_ENCODING_MAX_BYTES + b"TAIL")
    assert (
        context.text_test_context(encoding).data == expected * TEXT_ENCODING_MAX_BYTES
    )


def test_a_utf8_bom_buffer_drops_a_character_cut_by_the_byte_limit() -> None:
    text = b"a" * (TEXT_ENCODING_MAX_BYTES - 4)
    data = UTF8_BYTE_ORDER_MARK + text + "éTAIL".encode()
    assert MatchContext(data).text_test_context("utf-8-sig").data == text


@pytest.mark.parametrize(
    "document,mime", [(b'{"a":1}\n', "application/json"), (b"a,b\n1,2\n", "text/csv")]
)
def test_preliminary_checks_keep_the_original_bom_bytes(
    document: bytes, mime: str
) -> None:
    context = MatchContext(UTF8_BYTE_ORDER_MARK + document)
    match = next(
        match
        for match in MagicMatcher.DEFAULT_INSTANCE.match(context)
        if mime in match.mimetypes
    )
    assert match.context is context
    assert match.context.decoded_from is None


@pytest.mark.parametrize("document", [b'{"a":1}\t\n', b"a,b\n1,2\t\n"])
def test_preliminary_checks_do_not_parse_translated_ebcdic(document: bytes) -> None:
    data = ebcdic_bytes(document)
    assert detect_text_encoding(data) == "ebcdic"
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(data))
    assert not any(
        {"application/json", "text/csv"}.intersection(match.mimetypes)
        for match in matches
    )
