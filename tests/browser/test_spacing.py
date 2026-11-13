"""Check byte-column spacing and embedded branding across viewer layouts."""

from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


@pytest.mark.parametrize("width", [390, 900, 920, 1440])
def test_byte_columns_have_space_and_fit_the_pane(
    viewer_page: "Page", report_factory: ReportFactory, width: int
) -> None:
    viewer_page.set_viewport_size({"width": width, "height": 900})
    open_report(viewer_page, report_factory(bytes(8192)))
    expect(viewer_page.locator("#ascii .byte").first).to_be_visible()
    geometry = viewer_page.locator("#scrollcapture").evaluate(
        """capture => {
            const hex = document.getElementById('hexdump').getBoundingClientRect();
            const ascii = document.getElementById('ascii').getBoundingClientRect();
            return {gap: ascii.left - hex.right, aligned: ascii.top === hex.top,
                    fits: capture.scrollWidth <= capture.clientWidth + 1};
        }"""
    )
    assert geometry["gap"] >= 8
    assert geometry["aligned"]
    assert geometry["fits"]
