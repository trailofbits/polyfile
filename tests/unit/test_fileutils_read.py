"""Reads from physical member slices must not read or expose neighboring bytes."""

from io import BytesIO

import pytest

from polyfile.fileutils import FileStream

DATA = b"0123456789abcdefghijklmnopqrstuvwxyz"


class RecordingBytesIO(BytesIO):
    """Record actual source read requests at the filesystem boundary."""

    def __init__(self, data: bytes):
        super().__init__(data)
        self.name = "recording"
        self.requests: list[int | None] = []

    def read(self, size: int | None = -1, /) -> bytes:
        self.requests.append(size)
        return super().read(size)


@pytest.mark.parametrize("requested", [None, -1, -99])
@pytest.mark.parametrize("nested", [False, True])
def test_read_all_only_requests_remaining_region_bytes(
    requested: int | None,
    nested: bool,
) -> None:
    source = RecordingBytesIO(DATA)
    base = FileStream(source, start=3, length=8) if nested else source
    stream = FileStream(base, start=2 if nested else 5, length=3)
    assert stream.read(1) == b"5"
    assert stream.read(requested) == b"67"
    assert source.requests == [1, 2]
    assert stream.read(requested) == b""
    assert source.requests == [1, 2]


@pytest.mark.parametrize("requested", [None, -1, -99, 1000])
def test_bounded_read_does_not_leak_following_member_bytes(
    requested: int | None,
) -> None:
    source = RecordingBytesIO(DATA)
    stream = FileStream(source, start=5, length=3)
    assert stream.read(requested) == b"567"
    assert source.requests == [3]
    assert source.tell() == 8
