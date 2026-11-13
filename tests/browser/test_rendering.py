"""Behavior regressions for bounded source-aware byte and text rendering."""

import base64
from typing import TYPE_CHECKING

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page


def scroll_rows(page: "Page", rows: int) -> None:
    """Scroll the virtual byte viewport by its measured row height."""
    height = page.locator("#hexdump .byteline").first.bounding_box()["height"]
    page.locator("#scrollcontainer").evaluate(
        "(element, top) => { element.scrollTop = top; }", rows * height
    )
    page.wait_for_timeout(50)


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
        viewer_page.locator("#byte12").hover()
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
    assert viewer_page.locator("#hexdump .byteline").first.locator(".byte").count() == 16
    viewer_page.set_viewport_size({"width": 600, "height": 380})
    viewer_page.wait_for_timeout(100)
    assert viewer_page.locator("#hexdump .byteline").first.locator(".byte").count() == 8
    viewer_page.locator("#scrollcontainer").evaluate(
        "element => { element.scrollTop = element.scrollHeight; }"
    )
    viewer_page.wait_for_timeout(100)
    cells = viewer_page.locator("#hexdump .byte").all_text_contents()
    assert [cell for cell in cells if cell][-7:] == ["45", "4e", "44", "49", "4e", "47", "21"]
    viewer_page.set_viewport_size({"width": 1800, "height": 1000})
    viewer_page.wait_for_timeout(100)
    assert viewer_page.locator("#hexdump .byteline").first.locator(".byte").count() == 16


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
    assert viewer_page.locator('#readablebytes [data-offset="22"]').get_attribute("data-length") == "2"
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
