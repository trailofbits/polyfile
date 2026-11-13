"""Check embedded artwork and theme-aware wordmark colors."""

from typing import TYPE_CHECKING, Literal

import pytest

from tests.browser.helpers import ReportFactory, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


@pytest.mark.parametrize(
    ("theme", "system_scheme", "file_color"),
    [
        ("light", "dark", "rgb(24, 23, 23)"),
        ("dark", "light", "rgb(255, 255, 255)"),
        ("system", "light", "rgb(24, 23, 23)"),
        ("system", "dark", "rgb(255, 255, 255)"),
    ],
)
def test_brand_logo_and_wordmark_work_offline(
    viewer_page: "Page",
    report_factory: ReportFactory,
    theme: str,
    system_scheme: Literal["light", "dark"],
    file_color: str,
) -> None:
    viewer_page.emulate_media(color_scheme=system_scheme)
    open_report(viewer_page, report_factory(b"branding"))
    viewer_page.locator("#theme").select_option(theme)
    image = viewer_page.locator(".brand-mark img")
    expect(image).to_be_visible()
    source = image.get_attribute("src")
    assert source is not None
    assert source.startswith("data:image/svg+xml;base64,")
    expect(image).to_have_js_property("complete", True)
    assert image.evaluate("image => image.naturalWidth") > 0
    expect(viewer_page.locator(".brand-poly")).to_have_css("color", "rgb(162, 0, 0)")
    expect(viewer_page.locator(".brand-file")).to_have_css("color", file_color)
