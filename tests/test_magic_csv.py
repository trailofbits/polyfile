"""CSV classification follows libmagic's raw-byte detector and encoding descriptions."""

from pathlib import Path

import pytest

from polyfile.magic import (
    EBCDIC_TO_ASCII,
    MAGIC_DEFS,
    AbsoluteOffset,
    CSVTest,
    FailedTest,
    MagicMatcher,
    Match,
    MatchContext,
    MatchedTest,
)

DOCUMENT = "a,b,café\n1,2,3\n4,5,6\n"


def csv_match(data: bytes) -> Match | None:
    """Return the owned CSV definition's match without unrelated format descriptions."""
    definition = next(path for path in MAGIC_DEFS if path.name == "csv")
    return next(iter(MagicMatcher.parse(definition).match(data)), None)


def csv_result(data: bytes) -> MatchedTest | FailedTest:
    """Run the CSV test directly so rejected inputs cannot fall back to plain text."""
    result = CSVTest(offset=AbsoluteOffset(0)).test(data, 0, None)
    assert isinstance(result, (MatchedTest, FailedTest))
    return result


@pytest.mark.parametrize(
    "data,description",
    [
        (b"a,b,c\n1,2,3\n4,5,6\n", "CSV ASCII text"),
        (DOCUMENT.encode(), "CSV Unicode text, UTF-8 text"),
        (b"\xef\xbb\xbf" + DOCUMENT.encode(), "CSV Unicode text, UTF-8 (with BOM) text"),
        (DOCUMENT.encode("latin-1"), "CSV ISO-8859 text"),
        (b"a,b,caf\x8b\n1,2,3\n4,5,6\n", "CSV Non-ISO extended-ASCII text"),
        (b"\xff\xfe" + DOCUMENT.encode("utf-16le"),
         "CSV Unicode text, UTF-16, little-endian text"),
        (b"\xfe\xff" + DOCUMENT.encode("utf-16be"),
         "CSV Unicode text, UTF-16, big-endian text"),
        (b"\xff\xfe\x00\x00" + DOCUMENT.encode("utf-32le"),
         "CSV Unicode text, UTF-32, little-endian text"),
        (b"\x00\x00\xfe\xff" + DOCUMENT.encode("utf-32be"),
         "CSV Unicode text, UTF-32, big-endian text"),
    ],
)
def test_csv_names_its_encoding_and_preserves_file_extents(
    data: bytes, description: str
) -> None:
    match = csv_match(data)
    assert match is not None
    assert str(match) == description
    assert set(match.mimetypes) == {"text/csv"}
    assert match.text_encoding is None
    assert match.context.data == data
    assert match.context.decoded_from is None
    result = match[0]
    assert isinstance(result, MatchedTest)
    assert result.offset == 0
    assert result.length == len(data)


@pytest.mark.parametrize(
    "data",
    [
        b"a,b\n1,2\n",
        b'"a,b",c\n"d,e",f\n',
        b'"a""b",c\n"d""e",f\n',
        b'"a\nb",c\n"d\ne",f\n',
        b'ab"c,d"e,f\n1,2\n',
        b"a,b\r\n1,2\r\n",
        b"a,b\n1,2\ninvalid incomplete row",
        b'a,b\n1,2\n"unterminated',
    ],
)
def test_csv_accepts_reference_quote_and_completed_row_shapes(data: bytes) -> None:
    assert csv_result(data)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"a,b",
        b"a,b\n",
        b"a,b\n1,2",
        b"a\n1\n",
        b"a,b\n1,2,3\n",
        b"a,b,c\n1,2\n",
        b"a,b\n\n",
        b"a\tb\n1\t2\n",
        b"a,b\r1,2\r",
        b'"a,b\n1,2\n',
        b"a,b\n1,2\n\x00\x01",
    ],
)
def test_csv_rejects_incomplete_inconsistent_or_nontext_inputs(data: bytes) -> None:
    assert not csv_result(data)


def test_csv_applies_the_stricter_tenth_row_boundary() -> None:
    assert csv_result(b"a,b\n" * 9)
    assert not csv_result(b"a,b\n" * 10)
    assert csv_result(b"a,b,c\n" * 10)
    assert not csv_result(b"a,b,c\n" * 9 + b"a,b\n")
    assert csv_result(b"a,b,c\n" * 10 + b"inconsistent,row\n")


def test_ebcdic_csv_is_not_translated_before_delimiter_detection() -> None:
    document = b"a,b\n1,2\t\n"
    data = bytes(EBCDIC_TO_ASCII.index(byte) for byte in document)
    assert not csv_result(data)


def test_csv_keeps_the_original_context_when_matching(tmp_path: Path) -> None:
    definition = next(path for path in MAGIC_DEFS if path.name == "csv")
    data = b"\xef\xbb\xbfa,b\n1,2\n"
    context = MatchContext(data, path=tmp_path / "input.csv", only_match_mime=True)
    match = next(MagicMatcher.parse(definition).match(context))
    assert match.context is context
    assert str(match) == "CSV Unicode text, UTF-8 (with BOM) text"


def test_csv_at_a_nonzero_offset_keeps_the_physical_extent() -> None:
    data = b"HEADa,b\n1,2\n"
    result = CSVTest(offset=AbsoluteOffset(4)).test(data, 4, None)
    assert isinstance(result, MatchedTest)
    assert result.offset == 4
    assert result.length == len(data) - 4
    assert result.value == "ASCII"
