"""Verify the exact bytes saved by standalone report download controls."""

import base64
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def downloaded_bytes(page: "Page", control: "Locator") -> bytes:
    """Activate a download control and return the saved payload."""
    with page.expect_download() as saved:
        control.click()
    path = saved.value.path()
    assert path is not None
    return Path(path).read_bytes()


@pytest.mark.parametrize(
    "mime",
    [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    ],
)
def test_vendor_mime_saves_binary_contents(
    viewer_page: "Page", report_factory: ReportFactory, mime: str
) -> None:
    contents = b"\x00Hello\xff\x80"
    node = match(0, len(contents), name="Vendor document", type=mime)
    open_report(viewer_page, report_factory(contents, [node]))
    viewer_page.locator(".tree_label").hover()
    control = viewer_page.locator('[data-action="download"]').first
    assert downloaded_bytes(viewer_page, control) == contents


@pytest.mark.parametrize("contents", [b"", bytes(range(256))])
def test_complete_file_download(
    viewer_page: "Page", report_factory: ReportFactory, contents: bytes
) -> None:
    open_report(viewer_page, report_factory(contents))
    control = viewer_page.locator('[data-action="download-file"]')
    assert downloaded_bytes(viewer_page, control) == contents


def test_range_download_slices_bytes(viewer_page: "Page", report_factory: ReportFactory) -> None:
    contents = b"before\x00\xffafter"
    node = match(6, 2, name="Binary range", type="application/vnd.ms-excel", extension="xls")
    open_report(viewer_page, report_factory(contents, [node]))
    viewer_page.locator(".tree_label").hover()
    control = viewer_page.locator('[data-action="download"]').first
    assert downloaded_bytes(viewer_page, control) == contents[6:8]


def test_decoded_source_download(viewer_page: "Page", report_factory: ReportFactory) -> None:
    contents = b"\x00decoded\xff"
    node = match(
        0,
        len(contents),
        name="Decoded bytes",
        source="decoded:0",
        decoded=base64.b64encode(contents).decode("ascii"),
    )
    open_report(viewer_page, report_factory(b"compressed", [node]))
    viewer_page.locator("#source").select_option("decoded:0")
    control = viewer_page.locator('[data-action="download-file"]')
    assert downloaded_bytes(viewer_page, control) == contents
