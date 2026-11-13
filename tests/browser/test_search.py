"""Source-aware searches over the bytes embedded in standalone reports."""

import base64
import gzip
import re
import zlib
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip(
    "playwright.sync_api", reason="Install .[viewer-test] first"
).expect


def submit_search(page: "Page", query: str, mode: str = "text") -> None:
    """Set the mode and wait for a byte search to complete."""
    page.locator("#searchmode").select_option(mode)
    page.locator("#search").fill(query)
    expect(page.locator("#searchinfo")).to_have_text(
        re.compile(r"^(\d+ of \d+|0 results)")
    )


def decoded_node(source: str, contents: bytes) -> dict[str, object]:
    """Build a decoded source whose label does not affect byte search counts."""
    return match(
        0,
        len(contents),
        name="decoded content",
        source=source,
        decoded=base64.b64encode(contents).decode("ascii"),
    )


def test_combined_default_merges_identical_ranges(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    nodes = [match(0, 10, name="root", children=[match(0, 2, name="4142")])]
    open_report(viewer_page, report_factory(b"AB ab 4142", nodes))
    expect(viewer_page.locator("#searchmode")).to_have_value("combined")
    expect(viewer_page.locator("#searchscope")).to_have_value("all")
    viewer_page.locator("#search").fill("4142")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 2")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("file @ 0x0")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("hex, structure")
    viewer_page.locator("#searchdown").click()
    expect(viewer_page.locator("#searchinfo")).to_contain_text("2 of 2 · file @ 0x6")


def test_structure_mode_marks_nodes_without_searching_raw_bytes(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    nodes = [match(0, 16, name="root", children=[match(10, 6, name="Symbol table")])]
    open_report(viewer_page, report_factory(b"symbol....symbol", nodes))
    submit_search(viewer_page, "symbol", "structure")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1 · file @ 0xa")
    expect(viewer_page.locator(".tree_label.searchresult")).to_contain_text(
        "Symbol table"
    )
    viewer_page.locator("#search").fill("")
    expect(viewer_page.locator(".tree_label.searchresult")).to_have_count(0)


def test_numeric_order_overlaps_and_chunk_boundaries(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    contents = bytearray(b"." * 40000)
    for offset, payload in [
        (2, b"aba"),
        (10, b"aba"),
        (16383, b"ababa"),
        (32767, b"aba"),
    ]:
        end = offset + len(payload)
        contents[offset:end] = payload
    open_report(viewer_page, report_factory(bytes(contents)))
    submit_search(viewer_page, "aba")
    for index, offset in enumerate([2, 10, 16383, 16385, 32767], 1):
        status = f"{index} of 5 · file @ 0x{offset:x}"
        expect(viewer_page.locator("#searchinfo")).to_contain_text(status)
        viewer_page.locator("#searchdown").click()
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 5 · file @ 0x2")
    viewer_page.locator("#searchup").click()
    expect(viewer_page.locator("#searchinfo")).to_contain_text("5 of 5 · file @ 0x7fff")


def test_results_switch_sources_and_current_scope(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    children = [
        decoded_node("decoded:0", b"needle"),
        decoded_node("decoded:1", b"_needle"),
    ]
    nodes = [match(0, 9, name="root", children=children)]
    open_report(viewer_page, report_factory(b"___needle", nodes))
    submit_search(viewer_page, "needle")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 3 · file @ 0x3")
    for index, source in [(2, "decoded:0"), (3, "decoded:1")]:
        viewer_page.locator("#searchdown").click()
        expect(viewer_page.locator("#source")).to_have_value(source)
        expect(viewer_page.locator("#searchinfo")).to_contain_text(
            f"{index} of 3 · {source}"
        )
    viewer_page.locator("#searchscope").select_option("current")
    expect(viewer_page.locator("#searchinfo")).to_contain_text(
        "1 of 1 · decoded:1 @ 0x1"
    )


def test_default_search_finds_embedded_bytes(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    payload = b"stream-only-needle"
    nodes = [match(0, 4, children=[decoded_node("decoded:0", payload)])]
    open_report(viewer_page, report_factory(b"file", nodes))
    viewer_page.locator("#search").fill(payload.decode())
    viewer_page.locator("#search").press("Enter")
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")


@pytest.mark.parametrize("query", ["0x", "abc", "gg", "-1", "ab,cd"])
def test_explicit_hex_rejects_malformed_input(
    viewer_page: "Page", report_factory: ReportFactory, query: str
) -> None:
    open_report(viewer_page, report_factory(bytes(range(256))))
    viewer_page.locator("#searchmode").select_option("hex")
    viewer_page.locator("#search").fill(query)
    expect(viewer_page.locator("#searchinfo")).to_contain_text(
        "Enter hexadecimal byte pairs"
    )
    expect(viewer_page.locator("#searchdown")).to_be_disabled()
    viewer_page.keyboard.press("Control+g")


def test_utf8_ascii_case_and_exact_binary_hex(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory("Aé aÉ aé".encode()))
    submit_search(viewer_page, "aé")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 2 · file @ 0x0")
    viewer_page.locator("#matchcase").check()
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1 · file @ 0x8")
    submit_search(viewer_page, "0x61 c3 a9", "hex")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1 · file @ 0x8")
    submit_search(viewer_page, "aÉ")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1 · file @ 0x4")


def test_slash_input_and_empty_navigation_are_safe(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(b"font/key"))
    viewer_page.keyboard.press("Control+g")
    submit_search(viewer_page, "font")
    viewer_page.locator("#search").press("/")
    expect(viewer_page.locator("#search")).to_have_value("font/")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1")
    submit_search(viewer_page, "missing")
    viewer_page.keyboard.press("Control+g")
    viewer_page.keyboard.press("Control+Shift+g")
    expect(viewer_page.locator("#searchinfo")).to_have_text("0 results")
    viewer_page.locator("#search").fill("")
    expect(viewer_page.locator("#searchinfo")).to_have_text("")


def test_new_query_cancels_old_search(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    contents = b"." * (2 * 1024 * 1024) + b"needle"
    open_report(viewer_page, report_factory(contents))
    viewer_page.locator("#searchmode").select_option("text")
    viewer_page.locator("#search").fill("missing")
    viewer_page.locator("#search").fill("needle")
    expect(viewer_page.locator("#searchinfo")).to_contain_text(
        "1 of 1 · file @ 0x200000"
    )
    viewer_page.locator("#searchdown").click()
    expect(viewer_page.locator("#searchinfo")).to_contain_text(
        "1 of 1 · file @ 0x200000"
    )


def pdf_stream(contents: bytes) -> bytes:
    """Build a valid PDF containing one Flate-compressed stream."""
    compressed = zlib.compress(contents)
    stream_header = f"<< /Length {len(compressed)} /Filter /FlateDecode >>\n".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /Payload 3 0 R >>",
        b"<< /Type /Pages /Kids [] /Count 0 >>",
        stream_header + b"stream\n" + compressed + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(document)
    document.extend(b"xref\n0 4\n0000000000 65535 f \n")
    for offset in offsets:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n")
    document.extend(f"{xref}\n%%EOF\n".encode())
    return bytes(document)


def gzip_zip(contents: bytes) -> bytes:
    """Return a gzip stream containing a deflated ZIP member."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("payload.json", contents)
    return gzip.compress(buffer.getvalue(), mtime=0)


@pytest.mark.parametrize(
    "container", [pdf_stream, gzip_zip], ids=["pdf-stream", "gzip-zip"]
)
def test_real_decoded_streams_are_searchable(
    viewer_page: "Page",
    report_factory: ReportFactory,
    tmp_path: Path,
    container: Callable[[bytes], bytes],
) -> None:
    from polyfile.html import source_buffers
    from polyfile.polyfile import Analyzer

    needle = b"ViewerNeedle_9c5f1702"
    contents = container(b'{"font": "' + needle + b'"}')
    assert needle not in contents
    path = tmp_path / "compressed.bin"
    path.write_bytes(contents)
    sbud = Analyzer(path).sbud()
    buffers = source_buffers(sbud)
    matches = [
        source
        for source, data in buffers.items()
        if needle in base64.b64decode(data["encoded"])
    ]
    assert matches and "file" not in matches
    open_report(viewer_page, report_factory(contents, sbud["struc"]))
    submit_search(viewer_page, needle.decode())
    expect(viewer_page.locator("#searchinfo")).to_contain_text(
        f"1 of {len(matches)} · decoded:"
    )
    expect(viewer_page.locator("#source")).to_have_value(matches[0])
    for source in matches[1:]:
        viewer_page.locator("#searchdown").click()
        expect(viewer_page.locator("#source")).to_have_value(source)
