"""Baseline behaviors that every standalone HTML viewer must preserve."""

import base64
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


def test_report_opens_offline(viewer_page: "Page", report_factory: ReportFactory) -> None:
    contents = b"PolyFile offline report\x00\xff"
    report = report_factory(contents, [match(0, len(contents), name="offline fixture")])
    open_report(viewer_page, report)
    expect(viewer_page.locator("#byte0")).to_have_text("50")
    expect(viewer_page.locator(".tree_label")).to_contain_text("offline fixture")
    assert viewer_page.locator("script[src], link[rel=stylesheet][href]").count() == 0


def test_empty_report_renders(viewer_page: "Page", report_factory: ReportFactory) -> None:
    open_report(viewer_page, report_factory(b""))
    expect(viewer_page.locator("#byte0")).to_have_text("")
    expect(viewer_page.locator(".coverage")).to_contain_text("0 bytes")


def test_decoded_sources_render(viewer_page: "Page", report_factory: ReportFactory) -> None:
    payload = b"decoded bytes"
    decoded = match(
        0,
        len(payload),
        name="decoded fixture",
        source="decoded:0",
        decoded=base64.b64encode(payload).decode("ascii"),
    )
    report = report_factory(b"file", [match(0, 4, children=[decoded])])
    open_report(viewer_page, report)
    viewer_page.locator("#source").select_option("decoded:0")
    expect(viewer_page.locator("#byte0")).to_have_text("64")
    expect(viewer_page.locator(".coverage")).to_contain_text("decoded:0")


def test_original_download_matches_input(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    contents = bytes(range(256))
    open_report(viewer_page, report_factory(contents))
    with viewer_page.expect_download() as result:
        viewer_page.get_by_role("button", name="Download File", exact=True).click()
    assert Path(result.value.path()).read_bytes() == contents
