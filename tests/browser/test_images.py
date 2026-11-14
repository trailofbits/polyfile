"""Embedded images follow source-qualified byte ranges without expanding the tree."""

import base64
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from tests.browser.helpers import MatchData, ReportFactory, match, open_report
from tests.browser.test_rendering import scroll_rows

if TYPE_CHECKING:
    from playwright.sync_api import Page

expect = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first").expect


def image_node(
    offset: int, size: int, *, name: str = "Landscape", source: str = "file",
    children: Sequence[MatchData] = (),
) -> MatchData:
    """Create a real image preview independently of its enclosing byte extent."""
    output = BytesIO()
    image = Image.new("RGB", (320, 160), "#007a80")
    image.paste("#6cddd0", (24, 24, 140, 136))
    image.paste("#e1ebf2", (164, 24, 296, 72))
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return match(offset, size, name=name, source=source, children=children,
                 img_data=f"data:image/png;base64,{encoded}")


def nested_images() -> list[MatchData]:
    """Model images in two nested decoded sources and their encoded containers."""
    image = image_node(32, 512, source="decoded:1")
    inner = match(0, 1024, source="decoded:1", children=[image],
                  decoded=base64.b64encode(bytes(1024)).decode("ascii"))
    encoded = match(128, 256, name="inner container", source="decoded:0", children=[inner])
    outer = match(0, 2048, source="decoded:0", children=[encoded],
                  decoded=base64.b64encode(bytes(2048)).decode("ascii"))
    return [match(0, 8192, children=[match(160, 1024, children=[outer])])]


def test_image_is_visible_with_collapsed_ancestors_and_tracks_its_range(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    node = image_node(64, 2048)
    root = match(0, 8192, children=[match(32, 4096, name="container", children=[node])])
    open_report(viewer_page, report_factory(bytes(8192), [root]))
    expect(viewer_page.locator("#byte-pane")).to_have_attribute("data-images", "gutter")
    expect(viewer_page.locator(".tree_custom img")).to_be_hidden()
    preview = viewer_page.get_by_role("button", name="Enlarge Landscape")
    expect(preview).to_be_visible()
    card = viewer_page.locator(".image-card").bounding_box()
    row = viewer_page.locator("#hexdump .byteline").nth(4).bounding_box()
    ascii_bounds = viewer_page.locator("#ascii").bounding_box()
    assert card and row and ascii_bounds
    assert abs(card["y"] - row["y"]) <= 1
    assert card["x"] > ascii_bounds["x"] + ascii_bounds["width"]
    scroll_rows(viewer_page, 20)
    expect(preview).to_be_visible()
    marker = viewer_page.locator(".image-range-marker").bounding_box()
    ascii_bounds = viewer_page.locator("#ascii").bounding_box()
    assert marker and ascii_bounds
    assert abs(marker["y"] - ascii_bounds["y"]) <= 1
    scroll_rows(viewer_page, 140)
    expect(preview).to_have_count(0)
    scroll_rows(viewer_page, 0)
    expect(preview).to_be_visible()


def test_crowded_images_are_browsable_and_preserve_choice(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    nodes = [image_node(32 + index * 16, 2048, name=f"Image {index}") for index in range(3)]
    open_report(viewer_page, report_factory(bytes(8192), [match(0, 8192, children=nodes)]))
    expect(viewer_page.locator(".image-card")).to_have_count(1)
    expect(viewer_page.locator(".image-controls span")).to_have_text("Image 1 of 3")
    viewer_page.get_by_role("button", name="Next image in group").click()
    chosen = viewer_page.locator(".image-open").get_attribute("aria-label")
    assert chosen is not None
    expect(viewer_page.locator(".image-controls span")).to_have_text("Image 2 of 3")
    scroll_rows(viewer_page, 1)
    expect(viewer_page.locator(".image-open")).to_have_attribute("aria-label", chosen)
    viewer_page.get_by_role("button", name="Previous image in group").click()
    expect(viewer_page.locator(".image-controls span")).to_have_text("Image 1 of 3")


def test_dialog_enlarges_and_restores_keyboard_focus_without_changing_selection(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    nodes = [match(0, 8192, name="root", children=[image_node(0, 2048)])]
    open_report(viewer_page, report_factory(bytes(8192), nodes))
    viewer_page.locator(".tree_label").first.click()
    preview = viewer_page.get_by_role("button", name="Enlarge Landscape")
    preview.focus()
    preview.press("Enter")
    dialog = viewer_page.get_by_role("dialog", name="Landscape")
    expect(dialog).to_be_visible()
    image = dialog.locator("img")
    expect(image).to_be_visible()
    bounds = image.bounding_box()
    thumbnail = preview.bounding_box()
    assert bounds and thumbnail and bounds["width"] > thumbnail["width"]
    expect(dialog.get_by_role("button", name="Close", exact=True)).to_be_focused()
    viewer_page.keyboard.press("/")
    expect(viewer_page.locator("#search")).not_to_be_focused()
    viewer_page.keyboard.press("Tab")
    expect(dialog.get_by_role("button", name="Reveal structure")).to_be_focused()
    viewer_page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(preview).to_be_focused()
    expect(viewer_page.locator(".tree_label[aria-pressed=true] > .node-name")).to_have_text("root")


def test_nested_images_use_container_anchors_and_reveal_the_actual_source(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    open_report(viewer_page, report_factory(bytes(8192), nested_images()))
    caption = viewer_page.locator(".image-caption")
    expect(caption).to_contain_text("From decoded:1 · container file @ 0xa0 · 1024 bytes")
    viewer_page.locator(".image-open").hover()
    expect(viewer_page.locator("#byte160")).to_have_class("byte highlighted")
    viewer_page.locator("#source").select_option("decoded:0")
    expect(caption).to_contain_text("container decoded:0 @ 0x80 · 256 bytes")
    viewer_page.locator("#source").select_option("decoded:1")
    expect(caption).to_contain_text("decoded:1 @ 0x20 · 512 bytes")
    expect(caption).not_to_contain_text("container")
    viewer_page.locator("#source").select_option("file")
    viewer_page.locator(".image-open").click()
    viewer_page.get_by_role("button", name="Reveal structure").click()
    expect(viewer_page.locator("#source")).to_have_value("decoded:1")
    selected = viewer_page.locator(".tree_label[aria-pressed=true]")
    expect(selected).to_contain_text("Landscape")
    expect(selected).to_be_focused()
    expect(viewer_page.locator(".tree_custom img")).to_be_visible()


@pytest.mark.parametrize("width", [390, 720, 1024, 1440])
def test_images_fit_responsive_layouts_and_text_mode(
    viewer_page: "Page", report_factory: ReportFactory, width: int,
) -> None:
    viewer_page.set_viewport_size({"width": width, "height": 900})
    open_report(viewer_page, report_factory(bytes(8192), [image_node(0, 8192)]))
    preview = viewer_page.get_by_role("button", name="Enlarge Landscape")
    expect(preview).to_be_visible()
    assert viewer_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    geometry = viewer_page.locator("#scrollcapture").evaluate(
        "element => ({fits: element.scrollWidth <= element.clientWidth + 1})"
    )
    assert geometry["fits"]
    if width == 390:
        expect(viewer_page.locator("#byte-pane")).to_have_attribute("data-images", "strip")
        rail = viewer_page.locator("#image-previews").bounding_box()
        byte = viewer_page.locator("#ascii .byteline").last.bounding_box()
        assert rail and byte and rail["y"] >= byte["y"] + byte["height"]
    viewer_page.get_by_role("button", name="Text", exact=True).click()
    expect(viewer_page.locator("#image-previews")).to_be_hidden()
    viewer_page.get_by_role("button", name="Bytes", exact=True).click()
    expect(preview).to_be_visible()
    viewer_page.set_viewport_size({"width": 1800, "height": 1000})
    expect(viewer_page.locator("#byte-pane")).to_have_attribute("data-images", "gutter")
    viewer_page.set_viewport_size({"width": 390, "height": 400})
    expect(viewer_page.locator("#byte-pane")).to_have_attribute("data-images", "strip")
    expect(preview).to_be_visible()
    viewer_page.locator("#scrollcontainer").evaluate("el => { el.scrollTop = el.scrollHeight; }")
    expect(viewer_page.locator("#hexdump .byte").last).not_to_have_text("")


def test_sources_without_images_and_rejected_urls_do_not_reserve_space(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    for contents in (b"", bytes(32)):
        for url in ("https://example.com/image.png", "data:image/svg+xml;base64,PHN2Zy8+"):
            node = match(0, len(contents), img_data=url)
            open_report(viewer_page, report_factory(contents, [node]))
            expect(viewer_page.locator("#image-previews")).to_be_hidden()
            expect(viewer_page.locator(".tree_custom img")).to_have_count(0)
    decoded = match(0, 32, source="decoded:0", decoded=base64.b64encode(bytes(32)).decode())
    open_report(viewer_page, report_factory(bytes(128), [image_node(0, 128, children=[decoded])]))
    viewer_page.locator("#source").select_option("decoded:0")
    expect(viewer_page.locator("#image-previews")).to_be_hidden()
    viewer_page.locator("#source").select_option("file")
    expect(viewer_page.locator(".image-open")).to_be_visible()


def test_preview_failure_and_out_of_bounds_ranges_leave_viewer_usable(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    invalid = image_node(5000, 10)
    broken = match(0, 4096, name="broken image", img_data="data:image/png;base64,AA==")
    open_report(viewer_page, report_factory(bytes(4096), [invalid, broken]))
    expect(viewer_page.locator(".image-open")).to_contain_text("Image preview unavailable")
    expect(viewer_page.locator(".image-card")).to_have_count(1)
    viewer_page.locator("#goto").fill("0x100")
    viewer_page.locator("#goto").press("Enter")
    expect(viewer_page.locator("#byte0")).to_have_text("00")
    open_report(viewer_page, report_factory(bytes(32), [image_node(100, 20)]))
    expect(viewer_page.locator("#image-previews")).to_be_hidden()


@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_image_layout_preview(
    viewer_page: "Page", report_factory: ReportFactory, browser_name: str, width: int, theme: str,
) -> None:
    viewer_page.set_viewport_size({"width": width, "height": 900})
    nodes = [image_node(64, 4096), image_node(80, 4096, name="Second image")]
    open_report(viewer_page, report_factory(bytes(8192), [match(0, 8192, children=nodes)]))
    viewer_page.locator("#theme").select_option(theme)
    directory = Path("test-results")
    directory.mkdir(exist_ok=True)
    viewer_page.screenshot(path=str(directory / f"images-{browser_name}-{width}-{theme}.png"))


def test_group_choice_keeps_keyboard_focus_when_an_earlier_image_leaves(
    viewer_page: "Page", report_factory: ReportFactory,
) -> None:
    nodes = [image_node(32, 16, name="short"), image_node(48, 4096, name="long")]
    open_report(viewer_page, report_factory(bytes(8192), [match(0, 8192, children=nodes)]))
    next_image = viewer_page.get_by_role("button", name="Next image in group")
    next_image.focus()
    next_image.press("Enter")
    expect(viewer_page.locator(".image-open")).to_have_attribute("aria-label", "Enlarge long")
    scroll_rows(viewer_page, 8)
    expect(viewer_page.locator(".image-open")).to_have_attribute("aria-label", "Enlarge long")
    expect(viewer_page.locator(".image-open")).to_be_focused()
    expect(viewer_page.locator(".image-controls span")).to_have_text("Image 1 of 1")


@pytest.mark.parametrize("source", ["file", "missing"])
def test_invalid_child_range_does_not_fall_back_to_its_parent(
    viewer_page: "Page", report_factory: ReportFactory, source: str,
) -> None:
    root = match(0, 128, children=[image_node(512, 32, source=source)])
    open_report(viewer_page, report_factory(bytes(128), [root]))
    expect(viewer_page.locator("#image-previews")).to_be_hidden()
