"""Behavioral regressions for native SIMH detection and tape record structure."""

import struct
from io import BytesIO

import pytest

from polyfile.magic import MagicMatcher
from polyfile.simh import END_OF_MEDIUM, MIME_TYPE, SIMHTest


def record(payload: bytes, *, flags: int = 0) -> bytes:
    word = len(payload) | flags
    return (
        struct.pack("<I", word)
        + payload
        + b"\0" * (len(payload) & 1)
        + struct.pack("<I", word)
    )


def detected(data: bytes) -> bool:
    return any(
        MIME_TYPE in match.mimetypes
        for match in MagicMatcher.DEFAULT_INSTANCE.match(data)
    )


@pytest.mark.parametrize("payload", [b"DATA", b"odd", b"x", b"a" * 512])
def test_native_record_lengths(payload: bytes) -> None:
    assert detected(record(payload) + struct.pack("<II", 0, END_OF_MEDIUM))


@pytest.mark.parametrize("flags", [0, 0x80000000, 0x10000000, 0xF0000000])
def test_native_record_flags(flags: int) -> None:
    assert detected(record(b"DATA", flags=flags))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\0" * 64,
        struct.pack("<I", END_OF_MEDIUM),
        struct.pack("<II", 0, END_OF_MEDIUM),
        struct.pack("<I", 4) + b"DATA",
        struct.pack("<I", 4) + b"DATA" + struct.pack("<I", 6),
        record(b"DATA", flags=0x01000000),
    ],
)
def test_non_images(data: bytes) -> None:
    assert not detected(data)


def test_native_probe_reads_raw_bytes_and_paths(tmp_path) -> None:
    data = record(b"DATA") + struct.pack("<II", 0, END_OF_MEDIUM)
    path = tmp_path / "sample.tap"
    path.write_bytes(data)
    matcher = MagicMatcher([SIMHTest()])
    for value in (data, BytesIO(data), path):
        assert [str(match) for match in matcher.match(value)] == ["SIMH tape data"]


def test_native_detector_retains_other_classifications() -> None:
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(record(b'{"tape": true}')))
    assert any(MIME_TYPE in match.mimetypes for match in matches)


def test_later_truncation_retains_native_identification() -> None:
    assert detected(record(b"DATA") + struct.pack("<I", 128) + b"partial")


def test_invalid_later_trailer_rejects_native_identification() -> None:
    assert not detected(record(b"DATA") + struct.pack("<III", 4, 0, 8))
