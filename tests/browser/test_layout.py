"""Responsive workspace, theme, and navigation regression tests."""

import base64
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


def first_address(page: "Page") -> int:
    """Read the first visible byte address from the report."""
    return int(page.locator("#hexdump .byterow").first.inner_text().rstrip(": "), 16)


@pytest.mark.parametrize(
    ("width", "height"), [(1440, 900), (1024, 768), (768, 1024), (390, 844), (720, 450)]
)
def test_workspace_fits_viewport(
    viewer_page: "Page", report_factory: ReportFactory, width: int, height: int
) -> None:
    viewer_page.set_viewport_size({"width": width, "height": height})
    children = [match(index * 8, 8, name=f"field {index}") for index in range(100)]
    report = report_factory(bytes(800), [match(0, 800, children=children)])
    open_report(viewer_page, report)
    assert viewer_page.evaluate(
        "document.documentElement.scrollWidth <= innerWidth && "
        "document.documentElement.scrollHeight <= innerHeight"
    )
    if width >= 900:
        structure = viewer_page.locator("#structure-pane").bounding_box()
        byte_pane = viewer_page.locator("#bytes-pane").bounding_box()
        assert structure is not None and byte_pane is not None
        assert structure["y"] == byte_pane["y"]
        assert structure["x"] + structure["width"] < byte_pane["x"]
    else:
        expect(viewer_page.get_by_role("tab", name="Bytes", exact=True)).to_be_visible()
        expect(viewer_page.locator("#structure-pane")).to_be_hidden()
        viewer_page.get_by_role("tab", name="Structure", exact=True).click()
        expect(viewer_page.locator("#structure-pane")).to_be_visible()
        expect(viewer_page.locator("#bytes-pane")).to_be_hidden()
    expect(viewer_page.get_by_role("link", name="PolyFile", exact=True)).to_have_attribute(
        "href", "https://github.com/trailofbits/polyfile"
    )


def test_tabs_and_display_preserve_source(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.set_viewport_size({"width": 390, "height": 844})
    contents = b"Decoded text\n" * 200
    node = match(
        0, len(contents), source="decoded:0", decoded=base64.b64encode(contents).decode("ascii")
    )
    open_report(viewer_page, report_factory(b"file", [match(0, 4, children=[node])]))
    viewer_page.locator("#source").select_option("decoded:0")
    address = viewer_page.locator("#hexdump .byterow").first
    initial = address.inner_text()
    viewer_page.locator("#scrollcontainer").evaluate("element => { element.scrollTop = 240; }")
    expect(address).not_to_have_text(initial)
    position = first_address(viewer_page)
    viewer_page.get_by_role("button", name="Text", exact=True).click()
    expect(viewer_page.locator("#text-pane")).to_be_visible()
    expect(viewer_page.locator("#scrollcapture")).to_be_hidden()
    viewer_page.get_by_role("button", name="Bytes", exact=True).click()
    viewer_page.get_by_role("tab", name="Structure", exact=True).click()
    viewer_page.get_by_role("tab", name="Structure", exact=True).press("ArrowRight")
    expect(viewer_page.get_by_role("tab", name="Bytes", exact=True)).to_be_focused()
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    assert first_address(viewer_page) == position


def test_separator_supports_keyboard_and_pointer(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(4096)))
    separator = viewer_page.get_by_role("separator", name="Resize structure pane")
    initial = viewer_page.locator("#structure-pane").bounding_box()
    assert initial is not None
    separator.focus()
    separator.press("ArrowRight")
    resized = viewer_page.locator("#structure-pane").bounding_box()
    assert resized is not None and resized["width"] > initial["width"]
    bounds = separator.bounding_box()
    assert bounds is not None
    viewer_page.mouse.move(bounds["x"] + 6, bounds["y"] + bounds["height"] / 2)
    viewer_page.mouse.down()
    viewer_page.mouse.move(850, bounds["y"] + bounds["height"] / 2)
    viewer_page.mouse.up()
    dragged = viewer_page.locator("#structure-pane").bounding_box()
    assert dragged is not None and dragged["width"] > resized["width"]
    separator.press("Home")
    assert int(separator.get_attribute("aria-valuenow") or "0") >= 20


def test_theme_choices_follow_system_and_override_it(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.emulate_media(color_scheme="dark")
    open_report(viewer_page, report_factory(b"theme"))
    background = "getComputedStyle(document.body).backgroundColor"
    assert viewer_page.evaluate(background) == "rgb(14, 22, 30)"
    viewer_page.locator("#theme").select_option("light")
    assert viewer_page.evaluate(background) == "rgb(243, 246, 248)"
    viewer_page.locator("#theme").select_option("dark")
    assert viewer_page.evaluate(background) == "rgb(14, 22, 30)"
    viewer_page.emulate_media(color_scheme="light")
    viewer_page.locator("#theme").select_option("system")
    assert viewer_page.evaluate(background) == "rgb(243, 246, 248)"


def test_wheel_respects_line_units_and_horizontal_input(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(8192)))
    capture = viewer_page.locator("#scrollcapture")
    columns = viewer_page.locator("#hexdump .byteline").first.locator(".byte").count()
    capture.dispatch_event("wheel", {"deltaY": 2, "deltaMode": 1, "cancelable": True})
    assert first_address(viewer_page) == columns * 2
    allowed = capture.evaluate(
        "element => element.dispatchEvent(new WheelEvent('wheel', "
        "{deltaX: 100, deltaY: 0, bubbles: true, cancelable: true}))"
    )
    assert allowed
    assert first_address(viewer_page) == columns * 2


def test_last_byte_remains_reachable_after_height_changes(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(8192) + b"\xfe"))
    for height in (1000, 500, 1100):
        viewer_page.set_viewport_size({"width": 1024, "height": height})
        viewer_page.evaluate(
            "() => new Promise(resolve => "
            "requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        scroll = viewer_page.locator("#scrollcontainer")
        scroll.evaluate("element => { element.scrollTop = element.scrollHeight; }")
        expect(viewer_page.locator("#hexdump .byte").filter(has_text="fe")).to_have_count(1)
        values = viewer_page.locator("#hexdump .byte").all_text_contents()
        assert [value for value in values if value][-1] == "fe"


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_layout_preview(
    viewer_page: "Page", report_factory: ReportFactory, browser_name: str, width: int, theme: str
) -> None:
    viewer_page.set_viewport_size({"width": width, "height": 900 if width == 1440 else 844})
    contents = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 16
    children = [match(0, 8, name="PNG signature"), match(8, 25, name="IHDR · image header")]
    children += [
        match(33 + index * 64, 64, name=f"IDAT · image data [{index}]") for index in range(8)
    ]
    report = report_factory(
        contents, [match(0, len(contents), name="PNG image data", children=children)],
        filename="sample-polyglot.png",
    )
    open_report(viewer_page, report)
    viewer_page.locator("#theme").select_option(theme)
    directory = Path("test-results")
    directory.mkdir(exist_ok=True)
    viewer_page.screenshot(path=str(directory / f"layout-{browser_name}-{width}-{theme}.png"))
