"""Behavior regressions for bounded source-aware byte and text rendering."""

import base64
import re
from math import ceil
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


def scroll_rows(page: "Page", rows: int) -> None:
    """Scroll the virtual byte viewport by its measured row height."""
    bounds = page.locator("#hexdump .byteline").first.bounding_box()
    assert bounds is not None
    height = bounds["height"]
    page.locator("#scrollcontainer").evaluate(
        "(element, top) => { element.scrollTop = top; }", ceil(rows * height)
    )
    columns = page.locator("#hexdump .byteline").first.locator(".byte").count()
    expect(page.locator("#hexdump .byterow").first).to_have_text(
        re.compile(rf"^0*{rows * columns:x}:\s*$")
    )


def test_hover_finds_overlaps_in_only_the_active_source(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    decoded = match(0, 32, name="decoded", source="decoded:0",
                    decoded=base64.b64encode(bytes(32)).decode("ascii"))
    structure = [match(0, 256, name="root", children=[
        match(0, 32, name="first"), match(8, 24, name="second"),
        match(16, 16, name="third"), decoded,
    ])]
    open_report(viewer_page, report_factory(bytes(256), structure))
    viewer_page.locator("#byte18").hover()
    names = viewer_page.locator(".tree_label.highlighted > .node-name").all_text_contents()
    assert set(names) == {"root", "first", "second", "third"}
    viewer_page.locator("#source").select_option("decoded:0")
    viewer_page.locator("#byte2").hover()
    assert viewer_page.locator(".tree_label.highlighted > .node-name").all_text_contents() == [
        "decoded"
    ]


def test_padding_and_empty_files_have_no_hover_cursor(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    for contents in (b"", b"partial"):
        open_report(viewer_page, report_factory(contents))
        viewer_page.locator("#byte12").dispatch_event("pointerover")
        assert viewer_page.locator(".byte.cursor").count() == 0
        assert viewer_page.locator(".tree_label.highlighted").count() == 0


def test_selection_survives_scrolling_both_directions(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(8192), [match(0, 8192, name="entire file")]))
    viewer_page.locator(".node-name", has_text="entire file").click()
    for row in (40, 1, 80, 0):
        scroll_rows(viewer_page, row)
        present = viewer_page.locator("#hexdump .byte").evaluate_all(
            "cells => cells.filter(cell => cell.textContent).length"
        )
        assert viewer_page.locator("#hexdump .byte.manually-focused").count() == present


def test_hover_does_not_return_after_leaving_and_scrolling(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(8192)))
    viewer_page.locator(".tree_label").first.hover()
    assert viewer_page.locator("#hexdump .byte.highlighted").count() > 0
    viewer_page.locator("#search").hover()
    scroll_rows(viewer_page, 10)
    assert viewer_page.locator("#hexdump .byte.highlighted").count() == 0


def test_resize_reflows_columns_and_keeps_the_final_partial_row_reachable(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.set_viewport_size({"width": 1800, "height": 1000})
    open_report(viewer_page, report_factory(bytes(4096) + b"ENDING!"))
    expect(viewer_page.locator("#hexdump .byteline").first.locator(".byte")).to_have_count(16)
    viewer_page.set_viewport_size({"width": 600, "height": 380})
    expect(viewer_page.locator("#hexdump .byteline").first.locator(".byte")).to_have_count(8)
    viewer_page.locator("#scrollcontainer").evaluate(
        "element => { element.scrollTop = element.scrollHeight; }"
    )
    expect(viewer_page.locator("#hexdump .byte").filter(has_text="21")).to_have_count(1)
    cells = viewer_page.locator("#hexdump .byte").all_text_contents()
    assert [cell for cell in cells if cell][-7:] == ["45", "4e", "44", "49", "4e", "47", "21"]
    viewer_page.set_viewport_size({"width": 1800, "height": 1000})
    expect(viewer_page.locator("#hexdump .byteline").first.locator(".byte")).to_have_count(16)


def test_ascii_cells_use_fixed_width_printable_characters(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    contents = b"\x00\t\n\r\x1f A&<>\x7f\x80\xff"
    open_report(viewer_page, report_factory(contents))
    assert "".join(viewer_page.locator("#ascii .byte").all_text_contents()) == "····· A&<>···"
    assert viewer_page.locator('#readablebytes [data-offset="0"]').text_content() == "␀"


def test_utf8_preview_maps_codepoints_and_malformed_sequences_to_bytes(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    contents = b"A" * 15 + "€🙂".encode() + b"\xe1\x80Z\xed\xa0\x80" + b"A" * 8192
    open_report(viewer_page, report_factory(contents))
    euro = viewer_page.locator('#readablebytes [data-offset="15"]')
    assert euro.text_content() == "€"
    assert euro.get_attribute("data-length") == "3"
    assert viewer_page.locator('#readablebytes [data-offset="18"]').text_content() == "🙂"
    assert viewer_page.locator('#readablebytes [data-offset="22"]').text_content() == "�"
    malformed = viewer_page.locator('#readablebytes [data-offset="22"]')
    assert malformed.get_attribute("data-length") == "2"
    viewer_page.locator("#byte17").hover()
    assert "cursor" in (euro.get_attribute("class") or "")
    scroll_rows(viewer_page, 1)
    assert viewer_page.locator("#readablebytes .readable-byte").first.text_content() == "€"


def test_large_selection_keeps_only_viewport_cells(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    size = 8 * 1024 * 1024
    open_report(viewer_page, report_factory(bytes(size), [match(0, size, name="large source")]))
    before = viewer_page.locator("#hexdump .byte").count()
    viewer_page.locator(".node-name", has_text="large source").click()
    assert viewer_page.locator("#hexdump .byte.manually-focused").count() == before
    scroll_rows(viewer_page, 1000)
    assert viewer_page.locator("#hexdump .byte").count() == before
    assert before < 4096
