"""Encoding classification validates complete inputs with bounded temporary storage."""

import tracemalloc

import pytest

from polyfile.magic import UTF8_BYTE_ORDER_MARK, detect_text_encoding

CHUNK_BYTES = 64 * 1024


def traced_encoding(data: bytes) -> tuple[str | None, int]:
    """Measures temporary allocations after the input already exists."""
    tracemalloc.start()
    try:
        encoding = detect_text_encoding(data)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return encoding, peak


@pytest.mark.parametrize(
    "prefix,unit,expected",
    [
        (b"", b"\x00\xff", None),
        (UTF8_BYTE_ORDER_MARK, b"\x00\xff", None),
        (b"\xff\xfe", b"\x00\x00", None),
        (b"\x00\x00\xfe\xff", b"\x00\x00\x00\x00", None),
        (b"", b"a", "ascii"),
        (b"", b"caf\xe9", "iso-8859-1"),
        (b"", b"caf\x8b", "unknown-8bit"),
        (b"", "café".encode(), "utf-8"),
        (UTF8_BYTE_ORDER_MARK, "café".encode(), "utf-8-sig"),
        (b"\xff\xfe", "a🙂".encode("utf-16le"), "utf-16le"),
        (b"\x00\x00\xfe\xff", "a🙂".encode("utf-32be"), "utf-32be"),
        (b"", b"\x05\xc1", "ebcdic"),
        (b"", b"\x05\x41", "ebcdic-international"),
    ],
)
def test_classification_allocations_do_not_grow_with_input(
    prefix: bytes, unit: bytes, expected: str | None
) -> None:
    peaks = []
    for size in (1024 * 1024, 8 * 1024 * 1024):
        data = prefix + unit * (size // len(unit))
        encoding, peak = traced_encoding(data)
        assert encoding == expected
        peaks.append(peak)
    assert peaks[1] < peaks[0] + 256 * 1024
    assert peaks[1] < 1024 * 1024


@pytest.mark.parametrize("before", [CHUNK_BYTES - 3, CHUNK_BYTES - 2, CHUNK_BYTES - 1])
@pytest.mark.parametrize("prefix", [b"", UTF8_BYTE_ORDER_MARK])
def test_utf8_characters_can_cross_a_chunk_boundary(before: int, prefix: bytes) -> None:
    data = prefix + b"a" * before + "🙂tail".encode()
    assert detect_text_encoding(data) == ("utf-8-sig" if prefix else "utf-8")


@pytest.mark.parametrize(
    "ending,expected",
    [
        (b"\xc2", "iso-8859-1"),
        (b"\xe2\x82", "unknown-8bit"),
        (b"\xf0\x9f\x99", "unknown-8bit"),
        (b"\xed\xa0\x80", "unknown-8bit"),
        (b"\xc0\xaf", "iso-8859-1"),
    ],
)
def test_malformed_utf8_keeps_its_eight_bit_fallback(
    ending: bytes, expected: str
) -> None:
    assert detect_text_encoding(b"a" * (CHUNK_BYTES - 1) + ending) == expected


@pytest.mark.parametrize("position", [CHUNK_BYTES - 1, CHUNK_BYTES, CHUNK_BYTES + 1])
@pytest.mark.parametrize("unit", [b"a", b"\x05"])
def test_invalid_bytes_after_a_valid_prefix_are_rejected(
    position: int, unit: bytes
) -> None:
    assert detect_text_encoding(unit * position + b"\x00") is None


@pytest.mark.parametrize(
    "bom,encoding,unit",
    [
        (b"\xff\xfe", "utf-16le", 2),
        (b"\xfe\xff", "utf-16be", 2),
        (b"\xff\xfe\x00\x00", "utf-32le", 4),
        (b"\x00\x00\xfe\xff", "utf-32be", 4),
    ],
)
def test_ucs_validation_keeps_surrogates_and_incomplete_tail_units(
    bom: bytes, encoding: str, unit: int
) -> None:
    text = "a" * (CHUNK_BYTES // unit - 1) + "🙂tail"
    data = bom + text.encode(encoding)
    for tail in range(unit):
        assert detect_text_encoding(data + b"\xff" * tail) == encoding


def test_a_utf8_bom_without_a_body_remains_plain_utf8() -> None:
    assert detect_text_encoding(UTF8_BYTE_ORDER_MARK) == "utf-8"


@pytest.mark.parametrize(
    "bom,encoding,unit",
    [
        (b"\xff\xfe", "utf-16le", 2),
        (b"\xfe\xff", "utf-16be", 2),
        (b"\xff\xfe\x00\x00", "utf-32le", 4),
        (b"\x00\x00\xfe\xff", "utf-32be", 4),
    ],
)
@pytest.mark.parametrize("ending", ["\x01", "\ud800", "\ud800tail"])
def test_invalid_ucs_text_across_chunks_is_rejected(
    bom: bytes, encoding: str, unit: int, ending: str
) -> None:
    text = "a" * (CHUNK_BYTES // unit - 1) + ending
    assert detect_text_encoding(bom + text.encode(encoding, "surrogatepass")) is None


@pytest.mark.parametrize(
    "ending,expected", [(b"\xe9", "iso-8859-1"), (b"\x8b", "unknown-8bit")]
)
def test_late_high_bytes_change_the_encoding(ending: bytes, expected: str) -> None:
    assert detect_text_encoding(b"a" * (CHUNK_BYTES + 1) + ending) == expected


def test_international_ebcdic_after_a_valid_chunk_changes_the_encoding() -> None:
    data = b"\x05" * CHUNK_BYTES + b"\x41" + b"\x05" * CHUNK_BYTES
    assert detect_text_encoding(data) == "ebcdic-international"
