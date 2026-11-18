"""ICO identification follows validated image references independently of directory order."""

import gzip
from io import BytesIO
from itertools import permutations
import struct
import tarfile

from PIL import Image
import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.fileutils import FileStream
from polyfile.magic import MagicMatcher
from polyfile.polyfile import Match, Matcher, Submatch
from tests.test_zipmatcher import PNG

ICO = "image/vnd.microsoft.icon"


def dib(size: int = 40) -> bytes:
    """Build a 1-by-1, 32-bit icon bitmap with an XOR pixel and AND mask."""
    header = struct.pack("<IiiHHIIiiII", size, 1, 2, 1, 32, 0, 4, 0, 0, 0, 0)
    return header + bytes(size - 40) + b"\x00\x00\xff\xff" + bytes(4)


def icon(
    payloads: list[bytes],
    order: tuple[int, ...] | None = None,
    *,
    padding: int = 0,
    dimensions: tuple[int, int] = (1, 1),
) -> bytes:
    """Build a complete directory with independently ordered image references."""
    start = 6 + 16 * len(payloads) + padding
    entries = []
    for payload in payloads:
        entries.append(struct.pack("<BBBBHHII", *dimensions, 0, 0, 1, 32, len(payload), start))
        start += len(payload)
    if order is None:
        order = tuple(range(len(payloads)))
    return (
        struct.pack("<HHH", 0, 1, len(payloads))
        + b"".join(entries[index] for index in order)
        + bytes(padding)
        + b"".join(payloads)
    )


def classifications(data: bytes) -> list[Match]:
    return [node for node in Matcher(parse=False).match(data) if not isinstance(node, Submatch)]


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_png_directory_order_does_not_control_identification(order: tuple[int, ...]) -> None:
    data = icon([PNG] * 3, order)
    with Image.open(BytesIO(data)) as image:
        image.load()
        assert image.format == "ICO"
    assert [node.name for node in classifications(data)] == [ICO]


@pytest.mark.parametrize("payload", [PNG, dib()], ids=["png", "dib"])
@pytest.mark.parametrize("padding", range(8))
@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_valid_images_allow_every_first_offset_mask(
    payload: bytes, padding: int, order: tuple[int, ...]
) -> None:
    data = icon([payload, payload], order, padding=padding)
    with Image.open(BytesIO(data)) as image:
        image.load()
        assert image.size == (1, 1)
    assert [node.name for node in classifications(data)] == [ICO]


@pytest.mark.parametrize("size", [40, 52, 56, 108, 124])
def test_windows_dib_header_sizes_are_identified(size: int) -> None:
    assert [node.name for node in classifications(icon([dib(size)], padding=2))] == [ICO]


def test_png_and_dib_entries_can_be_reordered_together() -> None:
    data = icon([PNG, dib()], (1, 0))
    assert [node.name for node in classifications(data)] == [ICO]


@pytest.mark.parametrize("parse", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_identification_dispatches_each_png_once(parse: bool, reverse: bool) -> None:
    order = (1, 0) if reverse else (0, 1)
    data = icon([PNG, PNG], order)
    nodes = list(Matcher(parse=parse).match(data))
    assert len([node for node in nodes if node.name == ICO]) == 1
    images = [node for node in nodes if node.name == "image/png"]
    assert [(node.offset, node.length) for node in images] == (
        [(38 + index * len(PNG), len(PNG)) for index in order] if parse else []
    )
    if parse:
        assert all(node.parent is not None and node.parent.name == "img" for node in images)
        assert all(any(child.name == "Png" for child in node.children) for node in images)
        assert images[0].analysis_context.members == 2
        assert images[0].analysis_context.total_bytes == 2 * len(PNG)


def test_reordered_images_work_in_an_ico_only_matcher() -> None:
    matcher = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes=[ICO])
    nodes = list(Matcher(matcher=matcher, parse=False).match(icon([PNG, PNG], (1, 0))))
    assert [node.name for node in nodes] == [ICO]


@pytest.mark.parametrize("end", [0, 1, 4, 5, 6, 10, 21, 22, 30, 37])
def test_incomplete_headers_and_directories_are_not_added(end: int) -> None:
    assert ICO not in {node.name for node in classifications(icon([PNG, PNG], (1, 0))[:end])}


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (0, b"\x01"),
        (2, b"\x02"),
        (4, b"\x00\x00"),
        (4, b"\xff\xff"),
        (9, b"\x01"),
        (14, struct.pack("<I", 0)),
        (14, struct.pack("<I", 0xFFFFFFFF)),
        (18, struct.pack("<I", 0)),
        (18, struct.pack("<I", 8)),
        (18, struct.pack("<I", 0xFFFFFFF8)),
    ],
)
def test_invalid_header_entry_and_range_are_not_added(offset: int, value: bytes) -> None:
    data = bytearray(icon([PNG], padding=2))
    end = offset + len(value)
    data[offset:end] = value
    assert ICO not in {node.name for node in classifications(bytes(data))}


@pytest.mark.parametrize("field", [3, 8, 12])
def test_every_directory_entry_is_validated(field: int) -> None:
    data = bytearray(icon([PNG, PNG], (1, 0)))
    data[22 + field] = 0xFF
    assert ICO not in {node.name for node in classifications(bytes(data))}


@pytest.mark.parametrize("length", [0, 1, 7, 8, 16, 32])
def test_incomplete_png_header_is_not_added(length: int) -> None:
    assert ICO not in {node.name for node in classifications(icon([PNG[:length]], padding=2))}


@pytest.mark.parametrize("offset", [0, 4, 8, 12, 16, 20])
def test_png_signature_and_dimensions_are_checked(offset: int) -> None:
    payload = bytearray(PNG)
    payload[offset] ^= 0xFF
    assert ICO not in {node.name for node in classifications(icon([bytes(payload)], padding=2))}


@pytest.mark.parametrize("length", [0, 1, 7, 16, 39])
def test_incomplete_dib_header_is_not_added(length: int) -> None:
    assert ICO not in {node.name for node in classifications(icon([dib()[:length]], padding=2))}


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (0, struct.pack("<I", 0)),
        (0, struct.pack("<I", 124)),
        (4, struct.pack("<i", -1)),
        (4, struct.pack("<i", 2)),
        (8, struct.pack("<i", 1)),
        (8, struct.pack("<i", -2)),
        (12, struct.pack("<H", 0)),
        (14, struct.pack("<H", 7)),
    ],
)
def test_dib_header_fields_are_checked(offset: int, value: bytes) -> None:
    payload = bytearray(dib())
    end = offset + len(value)
    payload[offset:end] = value
    assert ICO not in {node.name for node in classifications(icon([bytes(payload)], padding=2))}


def test_zero_directory_dimensions_represent_256_pixels() -> None:
    stream = BytesIO()
    Image.new("RGBA", (256, 256)).save(stream, format="PNG")
    data = icon([stream.getvalue()], padding=2, dimensions=(0, 0))
    assert [node.name for node in classifications(data)] == [ICO]


@pytest.mark.parametrize("decoded", [False, True])
def test_reordered_ico_is_dispatched_inside_a_tar_member(decoded: bool) -> None:
    data = icon([PNG, PNG], (1, 0))
    stream = BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        member = tarfile.TarInfo("icon.ico")
        member.size = len(data)
        archive.addfile(member, BytesIO(data))
    archive_data = gzip.compress(stream.getvalue()) if decoded else stream.getvalue()
    nodes = list(Matcher().match(archive_data))
    assert len([node for node in nodes if node.name == ICO]) == 1
    images = [node for node in nodes if node.name == "image/png"]
    assert len(images) == 2
    assert [(node.offset, node.length) for node in images] == [(617, len(PNG)), (550, len(PNG))]
    assert all(node.source == ("decoded:0" if decoded else "file") for node in images)


def test_reordered_ico_keeps_bounded_view_coordinates() -> None:
    data = icon([PNG, PNG], (1, 0))
    with FileStream(b"prefix" + data + b"suffix", start=6, length=len(data)) as stream:
        nodes = list(Matcher().match(stream))
    images = [node for node in nodes if node.name == "image/png"]
    assert [(node.offset, node.length) for node in images] == [(105, len(PNG)), (38, len(PNG))]


@pytest.mark.parametrize(
    "limits",
    [AnalysisLimits(max_depth=0), AnalysisLimits(max_members=0), AnalysisLimits(max_total_bytes=0)],
)
def test_identification_preserves_member_limit_enforcement(limits: AnalysisLimits) -> None:
    nodes = list(Matcher(limits=limits).match(icon([PNG, PNG], (1, 0))))
    assert len([node for node in nodes if node.name == ICO]) == 1
    assert not any(node.name == "image/png" for node in nodes)
    assert any(node.analysis_status == "limited" for node in nodes)


def test_reordered_ico_is_identified_in_decoded_content() -> None:
    nodes = list(Matcher().match(gzip.compress(icon([PNG, PNG], (1, 0)))))
    assert len([node for node in nodes if node.name == ICO]) == 1
    assert len([node for node in nodes if node.name == "image/png"]) == 2


@pytest.mark.parametrize("overlap", [False, True])
def test_duplicate_or_overlapping_references_keep_parser_protections(overlap: bool) -> None:
    data = bytearray(icon([PNG, PNG], (1, 0)))
    if overlap:
        data[30:34] = struct.pack("<I", 2 * len(PNG))
    else:
        data[34:38] = struct.pack("<I", 105)
    nodes = list(Matcher().match(bytes(data)))
    assert len([node for node in nodes if node.name == ICO]) == 1
    assert len([node for node in nodes if node.name == "image/png"]) == 1
    assert any(node.analysis_status == "unsupported" for node in nodes)
