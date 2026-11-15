"""Identify HWP 5.0 through its compound-document FileHeader stream.

Sector layouts follow Microsoft's MS-CFB specification. This reader only validates
the allocation paths needed to identify FileHeader; it does not decode documents.
"""

from collections.abc import Iterator
from dataclasses import dataclass
import struct
from typing import cast

from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)


_FREE = 0xFFFFFFFF
_END = 0xFFFFFFFE
_FAT = 0xFFFFFFFD
_DIFAT = 0xFFFFFFFC
_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_HWP_SIGNATURE = b"HWP Document File"


def _u32(data: memoryview, offset: int) -> int:
    return cast(int, struct.unpack_from("<I", data, offset)[0])


@dataclass(frozen=True)
class _DirectoryEntry:
    data: memoryview
    version: int

    @property
    def name(self) -> str:
        length = struct.unpack_from("<H", self.data, 64)[0]
        end = length - 2
        if not 2 <= length <= 64 or length % 2 or self.data[end:length] != b"\0\0":
            raise ValueError("CFB directory entry has an invalid name length or terminator")
        name = bytes(self.data[:end]).decode("utf-16le")
        if "\0" in name:
            raise ValueError("CFB directory entry name contains an embedded terminator")
        return name

    @property
    def kind(self) -> int:
        return self.data[66]

    @property
    def start(self) -> int:
        return _u32(self.data, 116)

    @property
    def size(self) -> int:
        if self.version == 3:
            return _u32(self.data, 120)
        return cast(int, struct.unpack_from("<Q", self.data, 120)[0])


class _CompoundFile:
    def __init__(self, data: bytes) -> None:
        self.data = memoryview(data)
        self.version, self.sector_size = self._header()
        self.sector_count = len(data) // self.sector_size - 1
        self._difat_sectors: set[int] = set()
        self._fat_sectors = self._load_fat()
        self._reserved = set(self._fat_sectors) | self._difat_sectors
        for sector in self._fat_sectors:
            if self._table_next(self._fat_sectors, sector) != _FAT:
                raise ValueError("CFB FAT sector is not marked as allocated to the FAT")
        for sector in self._difat_sectors:
            if self._table_next(self._fat_sectors, sector) != _DIFAT:
                raise ValueError("CFB DIFAT sector is not marked as allocated to the DIFAT")
        self._directory = self._allocated_chain(_u32(self.data, 48))
        expected = 0 if self.version == 3 else len(self._directory)
        if _u32(self.data, 40) != expected:
            raise ValueError("CFB directory sector count disagrees with its allocation chain")

    def _header(self) -> tuple[int, int]:
        if len(self.data) < 512 or self.data[:8] != _SIGNATURE:
            raise ValueError("CFB header is truncated or has an invalid signature")
        version, order, shift, mini_shift = cast(
            tuple[int, int, int, int], struct.unpack_from("<4H", self.data, 26)
        )
        if (version, shift) not in ((3, 9), (4, 12)) or order != 0xFFFE or mini_shift != 6:
            raise ValueError("CFB header has an unsupported version or sector layout")
        size = 1 << shift
        if len(self.data) < size or _u32(self.data, 56) != 4096:
            raise ValueError("CFB header is truncated or has an invalid mini-stream cutoff")
        return version, size

    def _sector(self, sector: int) -> memoryview:
        if not 0 <= sector < self.sector_count:
            raise ValueError("CFB allocation refers to a sector outside the file")
        offset = (sector + 1) * self.sector_size
        end = offset + self.sector_size
        return self.data[offset:end]

    def _difat_entries(self) -> Iterator[int]:
        yield from struct.unpack_from("<109I", self.data, 76)
        sector, count = _u32(self.data, 68), _u32(self.data, 72)
        if count > self.sector_count:
            raise ValueError("CFB DIFAT sector count exceeds the file")
        for _ in range(count):
            if sector in self._difat_sectors:
                raise ValueError("CFB DIFAT chain contains a cycle")
            data = self._sector(sector)
            self._difat_sectors.add(sector)
            for offset in range(0, self.sector_size - 4, 4):
                yield _u32(data, offset)
            sector = _u32(data, self.sector_size - 4)
        if sector != _END:
            raise ValueError("CFB DIFAT chain does not end at its declared length")

    def _load_fat(self) -> tuple[int, ...]:
        count = _u32(self.data, 44)
        if not 0 < count <= self.sector_count:
            raise ValueError("CFB FAT sector count exceeds the file or is zero")
        sectors: list[int] = []
        seen: set[int] = set()
        for sector in self._difat_entries():
            if sector == _FREE:
                continue
            self._sector(sector)
            if sector in seen or len(sectors) >= count:
                raise ValueError("CFB DIFAT repeats a FAT sector or exceeds its declared count")
            sectors.append(sector)
            seen.add(sector)
        if len(sectors) != count or seen & self._difat_sectors:
            raise ValueError("CFB FAT count is inconsistent or overlaps the DIFAT")
        return tuple(sectors)

    def _table_next(self, table: tuple[int, ...], sector: int) -> int:
        page, index = divmod(sector, self.sector_size // 4)
        if page >= len(table):
            raise ValueError("CFB allocation table does not cover the requested sector")
        return _u32(self._sector(table[page]), index * 4)

    def _chain(self, start: int, table: tuple[int, ...], bound: int) -> tuple[int, ...]:
        sectors: list[int] = []
        visited: set[int] = set()
        sector = start
        while sector != _END:
            if not 0 <= sector < bound or sector in visited:
                raise ValueError("CFB allocation chain is out of bounds or contains a cycle")
            visited.add(sector)
            sectors.append(sector)
            sector = self._table_next(table, sector)
        return tuple(sectors)

    def _allocated_chain(self, start: int) -> tuple[int, ...]:
        sectors = self._chain(start, self._fat_sectors, self.sector_count)
        if self._reserved.intersection(sectors):
            raise ValueError("CFB allocation chains overlap")
        self._reserved.update(sectors)
        return sectors

    def _stream_chain(self, start: int, size: int) -> tuple[int, ...]:
        if size > self.sector_count * self.sector_size:
            raise ValueError("CFB declared stream size exceeds the file")
        sectors = self._allocated_chain(start)
        if len(sectors) != (size + self.sector_size - 1) // self.sector_size:
            raise ValueError("CFB stream size disagrees with its allocation chain")
        return sectors

    def _entry(self, index: int) -> _DirectoryEntry:
        page, entry = divmod(index, self.sector_size // 128)
        if page >= len(self._directory):
            raise ValueError("CFB directory refers to an entry outside its allocation chain")
        data = self._sector(self._directory[page])
        start, end = entry * 128, (entry + 1) * 128
        return _DirectoryEntry(data[start:end], self.version)

    def _file_header(self, root: _DirectoryEntry) -> _DirectoryEntry:
        stack = [_u32(root.data, 76)]
        visited = {0}
        found: _DirectoryEntry | None = None
        while stack:
            index = stack.pop()
            if index == _FREE:
                continue
            if index in visited:
                raise ValueError("CFB directory sibling links contain a cycle or repeated entry")
            visited.add(index)
            entry = self._entry(index)
            if entry.kind not in (1, 2):
                raise ValueError("CFB root directory references an invalid object type")
            stack.extend((_u32(entry.data, 68), _u32(entry.data, 72)))
            if entry.name == "FileHeader" and entry.kind == 2:
                if found is not None:
                    raise ValueError("CFB root directory repeats the FileHeader stream")
                found = entry
        if found is None:
            raise ValueError("CFB root directory has no FileHeader stream")
        return found

    def _mini_prefix(self, entry: _DirectoryEntry, root: _DirectoryEntry) -> memoryview:
        minifat = self._allocated_chain(_u32(self.data, 60))
        if not minifat or len(minifat) != _u32(self.data, 64):
            raise ValueError("CFB mini FAT chain disagrees with its declared sector count")
        root_chain = self._stream_chain(root.start, root.size)
        chain = self._chain(entry.start, minifat, (root.size + 63) // 64)
        if len(chain) != (entry.size + 63) // 64:
            raise ValueError("CFB mini-stream size disagrees with its allocation chain")
        for index, sector in enumerate(chain):
            if sector * 64 + min(64, entry.size - index * 64) > root.size:
                raise ValueError("CFB mini stream extends past the root mini-stream data")
        page, offset = divmod(chain[0] * 64, self.sector_size)
        end = offset + len(_HWP_SIGNATURE)
        return self._sector(root_chain[page])[offset:end]

    def has_hwp_header(self) -> bool:
        root = self._entry(0)
        if root.kind != 5 or root.name != "Root Entry":
            raise ValueError("CFB directory does not start with a root storage entry")
        entry = self._file_header(root)
        if entry.size < len(_HWP_SIGNATURE):
            raise ValueError("CFB FileHeader is too short for the HWP signature")
        if entry.size < 4096:
            prefix = self._mini_prefix(entry, root)
        else:
            chain = self._stream_chain(entry.start, entry.size)
            prefix = self._sector(chain[0])[: len(_HWP_SIGNATURE)]
        return prefix == _HWP_SIGNATURE


class HWP5Matcher(MagicTest):
    """Recognize HWP 5.0 using a validated compound-document FileHeader stream."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-hwp",
            extensions=("hwp",),
            message="Hancom HWP (Hangul Word Processor) file, version 5.0",
        )

    @property
    def precedes_soft_magic(self) -> bool:
        return True

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self,
        data: bytes,
        absolute_offset: int,
        parent_match: TestResult | None,
    ) -> TestResult:
        try:
            if _CompoundFile(data).has_hwp_header():
                return MatchedTest(self, value=data, offset=0, length=len(data))
        except ValueError as error:
            return FailedTest(self, offset=0, message=str(error))
        return FailedTest(
            self, offset=0, message="CFB FileHeader does not contain the HWP signature"
        )


MagicMatcher.DEFAULT_INSTANCE.add(HWP5Matcher())
