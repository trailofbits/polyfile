"""HWP 5.0 identification reads bounded compound-document stream chains."""

from dataclasses import dataclass, field
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from polyfile.magic import MagicMatcher, MatchContext
from tests.test_zipmatcher import build_zip


FREE = 0xFFFFFFFF
END = 0xFFFFFFFE
FAT = 0xFFFFFFFD
DIFAT = 0xFFFFFFFC
SIGNATURE = b"HWP Document File"
DESCRIPTION = "Hancom HWP (Hangul Word Processor) file, version 5.0"
MIME = "application/x-hwp"


@dataclass
class CompoundFixture:
    sector_size: int
    data: bytearray
    sectors: dict[str, tuple[int, ...]] = field(default_factory=dict)
    positions: dict[str, int] = field(default_factory=dict)

    def allocate(self, name: str, count: int) -> tuple[int, ...]:
        first = len(self.data) // self.sector_size - 1
        self.sectors[name] = tuple(range(first, first + count))
        self.data.extend(bytes(self.sector_size * count))
        return self.sectors[name]

    def position(self, sector: int) -> int:
        return (sector + 1) * self.sector_size

    def write(self, offset: int, content: bytes) -> None:
        end = offset + len(content)
        self.data[offset:end] = content

    def set_fat(self, sector: int, next_sector: int) -> None:
        page, index = divmod(sector, self.sector_size // 4)
        offset = self.position(self.sectors["fat"][page]) + index * 4
        struct.pack_into("<I", self.data, offset, next_sector)

    def chain(self, sectors: tuple[int, ...]) -> None:
        for index, sector in enumerate(sectors):
            self.set_fat(sector, sectors[index + 1] if index + 1 < len(sectors) else END)


def directory_entry(name: str, kind: int, start: int, size: int, *, child: int = FREE) -> bytes:
    entry = bytearray(128)
    encoded = name.encode("utf-16le") + b"\0\0"
    entry[: len(encoded)] = encoded
    struct.pack_into("<HBBIII", entry, 64, len(encoded), kind, 1, FREE, FREE, child)
    struct.pack_into("<IQ", entry, 116, start, size)
    return bytes(entry)


def compound_header(fixture: CompoundFixture, *, extended_difat: bool) -> None:
    data, size = fixture.data, fixture.sector_size
    data[:8] = bytes.fromhex("d0cf11e0a1b11ae1")
    struct.pack_into(
        "<HHHHH", data, 24, 62, 3 if size == 512 else 4, 0xFFFE, 9 if size == 512 else 12, 6
    )
    directory_count = len(fixture.sectors["directory"]) if size == 4096 else 0
    struct.pack_into(
        "<IIIIIIIII",
        data,
        40,
        directory_count,
        len(fixture.sectors["fat"]),
        fixture.sectors["directory"][0],
        0,
        4096,
        fixture.sectors.get("minifat", (END,))[0],
        len(fixture.sectors.get("minifat", ())),
        fixture.sectors.get("difat", (END,))[0],
        int(extended_difat),
    )
    for index in range(109):
        value = fixture.sectors["fat"][index] if index < len(fixture.sectors["fat"]) else FREE
        struct.pack_into("<I", data, 76 + index * 4, value)


def allocate_tables(fixture: CompoundFixture, *, extended_difat: bool) -> None:
    fixture.allocate("directory", 1)
    fat_sectors = fixture.allocate("fat", 110 if extended_difat else 1)
    for sector in fat_sectors:
        offset = fixture.position(sector)
        fixture.write(offset, b"\xff" * fixture.sector_size)
    for sector in fat_sectors:
        fixture.set_fat(sector, FAT)
    if extended_difat:
        sector = fixture.allocate("difat", 1)[0]
        fixture.set_fat(sector, DIFAT)
        offset = fixture.position(sector)
        fixture.write(offset, b"\xff" * fixture.sector_size)
        struct.pack_into("<I", fixture.data, offset, fat_sectors[-1])
        struct.pack_into("<I", fixture.data, offset + fixture.sector_size - 4, END)


def store_payload(fixture: CompoundFixture, size: int) -> tuple[int, int]:
    if size >= 4096:
        sectors = fixture.allocate(
            "payload", (size + fixture.sector_size - 1) // fixture.sector_size
        )
        fixture.chain(sectors)
        fixture.positions["payload"] = fixture.position(sectors[0])
        return sectors[0], 0
    minifat = fixture.allocate("minifat", 1)[0]
    fixture.chain((minifat,))
    offset = fixture.position(minifat)
    fixture.write(offset, b"\xff" * fixture.sector_size)
    mini_count = (size + 63) // 64
    for index in range(9, 9 + mini_count):
        following = index + 1 if index + 1 < 9 + mini_count else END
        struct.pack_into("<I", fixture.data, offset + index * 4, following)
    root_size = (9 + mini_count) * 64
    root = fixture.allocate("root", (root_size + fixture.sector_size - 1) // fixture.sector_size)
    fixture.chain(root)
    fixture.positions["payload"] = fixture.position(root[576 // fixture.sector_size])
    fixture.positions["payload"] += 576 % fixture.sector_size
    return 9, root_size


def build_compound(
    *,
    sector_size: int = 512,
    stream_size: int = 128,
    extended_difat: bool = False,
    split_directory: bool = False,
) -> CompoundFixture:
    fixture = CompoundFixture(sector_size, bytearray(sector_size))
    allocate_tables(fixture, extended_difat=extended_difat)
    first, root_size = store_payload(fixture, stream_size)
    entry_index = 1
    if split_directory:
        fixture.allocate("padding", 1)
        original = fixture.sectors["directory"]
        second = fixture.allocate("directory_tail", 1)
        fixture.sectors["directory"] = original + second
        entry_index = sector_size // 128
    fixture.chain(fixture.sectors["directory"])
    root_start = fixture.sectors.get("root", (END,))[0]
    root_offset = fixture.position(fixture.sectors["directory"][0])
    header_offset = fixture.position(fixture.sectors["directory"][-1]) + (
        0 if split_directory else 128
    )
    fixture.positions.update(root_entry=root_offset, header_entry=header_offset)
    fixture.write(
        root_offset, directory_entry("Root Entry", 5, root_start, root_size, child=entry_index)
    )
    fixture.write(header_offset, directory_entry("FileHeader", 2, first, stream_size))
    offset = fixture.positions["payload"]
    fixture.write(offset, SIGNATURE)
    compound_header(fixture, extended_difat=extended_difat)
    return fixture


def native_matches(data: bytes) -> list[str]:
    matcher = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes=[MIME])
    return [str(match) for match in matcher.match(data) if MIME in match.mimetypes]


def assert_bounded_rejection(data: bytes) -> None:
    script = """
import sys
from polyfile.magic import MagicMatcher
matcher = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes=["application/x-hwp"])
assert not any("application/x-hwp" in match.mimetypes
               for match in matcher.match(sys.stdin.buffer.read()))
"""
    subprocess.run(
        [sys.executable, "-c", script],
        input=data,
        capture_output=True,
        check=True,
        timeout=5,
    )


@pytest.mark.parametrize("sector_size", [512, 4096])
@pytest.mark.parametrize("stream_size", [128, 4096])
@pytest.mark.parametrize("split_directory", [False, True])
def test_identifies_standard_and_mini_stream_layouts(
    sector_size: int,
    stream_size: int,
    split_directory: bool,
) -> None:
    fixture = build_compound(
        sector_size=sector_size, stream_size=stream_size, split_directory=split_directory
    )
    assert native_matches(bytes(fixture.data)) == [DESCRIPTION]


def test_original_hwp5_corpus_has_exact_description_and_mime() -> None:
    path = Path(__file__).parents[1] / "file/tests/HWP2016.hwp.testfile"
    data = path.read_bytes()
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(data))
    assert DESCRIPTION in {str(match) for match in matches}
    assert MIME in {mime for match in matches for mime in match.mimetypes}
    assert "application/hwp+zip" not in {mime for match in matches for mime in match.mimetypes}


@pytest.mark.parametrize("selection", ["mime", "extension"])
def test_selected_identification_retains_the_correct_type(selection: str) -> None:
    matcher = MagicMatcher.DEFAULT_INSTANCE
    if selection == "mime":
        matcher = matcher.only_match(mimetypes=[MIME])
    else:
        matcher = matcher.only_match(extensions=["hwp"])
    data = bytes(build_compound().data)
    matches = list(matcher.match(MatchContext(data, only_match_mime=True)))
    assert {mime for match in matches for mime in match.mimetypes} == {MIME}


@pytest.mark.parametrize("sector_size", [512, 4096])
def test_reads_fat_locations_from_extended_difat(sector_size: int) -> None:
    fixture = build_compound(sector_size=sector_size, extended_difat=True)
    assert native_matches(bytes(fixture.data)) == [DESCRIPTION]


@pytest.mark.parametrize("length", [0, 7, 511, 512, 1023, 1535])
def test_rejects_truncated_compound_structures(length: int) -> None:
    assert native_matches(bytes(build_compound().data[:length])) == []


@pytest.mark.parametrize(
    ("offset", "format_string", "value"),
    [
        (0, "<Q", 0),
        (26, "<H", 2),
        (28, "<H", 0),
        (30, "<H", 31),
        (32, "<H", 5),
        (40, "<I", 1),
        (44, "<I", 0),
        (44, "<I", FREE),
        (48, "<I", FREE),
        (56, "<I", 64),
        (60, "<I", FREE),
        (64, "<I", 2),
        (68, "<I", 0),
        (72, "<I", FREE),
        (76, "<I", FREE),
        (76, "<I", 1000),
    ],
)
def test_rejects_invalid_header_fields(offset: int, format_string: str, value: int) -> None:
    fixture = build_compound()
    struct.pack_into(format_string, fixture.data, offset, value)
    assert native_matches(bytes(fixture.data)) == []


@pytest.mark.parametrize(
    ("entry", "offset", "format_string", "value"),
    [
        ("root_entry", 0, "<H", ord("X")),
        ("root_entry", 66, "<B", 2),
        ("root_entry", 76, "<I", FREE),
        ("root_entry", 116, "<I", 0),
        ("root_entry", 120, "<I", FREE),
        ("root_entry", 120, "<I", 693),
        ("header_entry", 64, "<H", 0),
        ("header_entry", 64, "<H", 3),
        ("header_entry", 64, "<H", 66),
        ("header_entry", 20, "<H", 1),
        ("header_entry", 66, "<B", 0),
        ("header_entry", 66, "<B", 1),
        ("header_entry", 68, "<I", 1),
        ("header_entry", 72, "<I", 1000),
        ("header_entry", 116, "<I", 1000),
        ("header_entry", 120, "<I", 16),
        ("header_entry", 120, "<I", 64),
    ],
)
def test_rejects_invalid_directory_fields(
    entry: str,
    offset: int,
    format_string: str,
    value: int,
) -> None:
    fixture = build_compound()
    struct.pack_into(format_string, fixture.data, fixture.positions[entry] + offset, value)
    assert_bounded_rejection(bytes(fixture.data))


@pytest.mark.parametrize("name", [b"F\0\0\0", b"\0\xd8", b"N\0o\0t\0H\0W\0P\0"])
def test_rejects_missing_or_invalid_file_header_names(name: bytes) -> None:
    fixture = build_compound()
    offset = fixture.positions["header_entry"]
    fixture.write(offset, name)
    assert native_matches(bytes(fixture.data)) == []


@pytest.mark.parametrize("table", ["directory", "root", "minifat", "payload"])
@pytest.mark.parametrize("next_sector", [None, FREE])
def test_rejects_cyclic_or_invalid_fat_chains(table: str, next_sector: int | None) -> None:
    fixture = build_compound(stream_size=4096 if table == "payload" else 128)
    sector = fixture.sectors[table][-1]
    fixture.set_fat(sector, sector if next_sector is None else next_sector)
    assert_bounded_rejection(bytes(fixture.data))


@pytest.mark.parametrize("next_sector", [9, 1000, END])
def test_rejects_invalid_mini_stream_chains(next_sector: int) -> None:
    fixture = build_compound()
    offset = fixture.position(fixture.sectors["minifat"][0]) + 9 * 4
    struct.pack_into("<I", fixture.data, offset, next_sector)
    assert_bounded_rejection(bytes(fixture.data))


def test_rejects_duplicate_fat_sectors() -> None:
    fixture = build_compound()
    struct.pack_into("<I", fixture.data, 44, 2)
    struct.pack_into("<I", fixture.data, 80, fixture.sectors["fat"][0])
    assert_bounded_rejection(bytes(fixture.data))


def test_rejects_invalid_fat_sector_marker() -> None:
    fixture = build_compound()
    fixture.set_fat(fixture.sectors["fat"][0], END)
    assert native_matches(bytes(fixture.data)) == []


@pytest.mark.parametrize("cycle", [False, True])
def test_rejects_invalid_difat_chains(cycle: bool) -> None:
    fixture = build_compound(extended_difat=True)
    sector = fixture.sectors["difat"][0]
    if cycle:
        struct.pack_into("<I", fixture.data, 72, 2)
        struct.pack_into(
            "<I", fixture.data, fixture.position(sector) + fixture.sector_size - 4, sector
        )
    else:
        fixture.set_fat(sector, END)
    assert_bounded_rejection(bytes(fixture.data))


def test_rejects_duplicate_file_header_entries() -> None:
    fixture = build_compound()
    offset = fixture.positions["header_entry"]
    end = offset + 128
    fixture.write(end, bytes(fixture.data[offset:end]))
    struct.pack_into("<I", fixture.data, offset + 72, 2)
    assert native_matches(bytes(fixture.data)) == []


def test_checks_the_stream_signature_before_suppressing_the_soft_magic_alias() -> None:
    fixture = build_compound()
    fixture.data[fixture.positions["payload"]] = ord("X")
    assert native_matches(bytes(fixture.data)) == []
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(bytes(fixture.data)))
    assert "application/hwp+zip" in {mime for match in matches for mime in match.mimetypes}


def test_version3_ignores_legacy_uninitialized_high_stream_size_bits() -> None:
    fixture = build_compound()
    struct.pack_into("<I", fixture.data, fixture.positions["header_entry"] + 124, FREE)
    assert native_matches(bytes(fixture.data)) == [DESCRIPTION]


def test_preserves_other_types_in_hwp_zip_polyglots() -> None:
    data = build_zip(prefix=bytes(build_compound().data))
    matches = list(MagicMatcher.DEFAULT_INSTANCE.match(data))
    assert {MIME, "application/zip"} <= {mime for match in matches for mime in match.mimetypes}


def test_cli_reports_the_correct_hwp_mime(tmp_path: Path) -> None:
    path = tmp_path / "document.hwp"
    path.write_bytes(bytes(build_compound().data))
    result = subprocess.run(
        [sys.executable, "-m", "polyfile", "--only-match-mime", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert MIME in result.stdout.splitlines()
    assert "application/hwp+zip" not in result.stdout
