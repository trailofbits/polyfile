"""Structure filtering and expansion preserve byte inspection state."""

import re
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

expect = pytest.importorskip(
    "playwright.sync_api", reason="Install .[viewer-test] first"
).expect


def tree_nodes() -> list[dict[str, object]]:
    """Build a nested tree with independent name, type, and message matches."""
    needle = match(20, 4, name="Needle field", type="application/x-secret",
                   analysis_message="Parser limit reached")
    branch = match(16, 64, name="Payload group", children=[needle])
    return [match(0, 128, name="Root", children=[
        branch, match(100, 8, name="Trailer"), match(112, 8, name="Unrelated")
    ])]


def node_label(page: "Page", name: str) -> "Locator":
    """Find one selection control by its exact visible node name."""
    return page.locator(".tree_label").filter(has=page.get_by_text(name, exact=True))


def node_toggle(page: "Page", name: str) -> "Locator":
    """Find the independent expansion control for a named parent."""
    uid = node_label(page, name).get_attribute("data-uid")
    return page.locator(f'[data-action="toggle-node"][data-node-uid="{uid}"]')


@pytest.mark.parametrize("query", ["nEeDlE", "APPLICATION/X-SECRET", "LIMIT REACHED"])
def test_filter_keeps_matching_nodes_and_their_ancestors(
    viewer_page: "Page", report_factory: ReportFactory, query: str
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    expect(node_label(viewer_page, "Needle field")).not_to_be_visible()
    viewer_page.locator("#tree-filter").fill(query)
    expect(viewer_page.locator("#tree-filter-info")).to_have_text("1 of 5 nodes matches.")
    visible = viewer_page.locator(".tree_label:visible .node-name").all_text_contents()
    assert visible == ["Root", "Payload group", "Needle field"]
    expect(node_toggle(viewer_page, "Payload group")).to_have_attribute("aria-expanded", "true")


def test_clearing_filter_restores_the_first_expansion_snapshot(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    expect(node_toggle(viewer_page, "Root")).to_have_attribute("aria-expanded", "true")
    expect(node_toggle(viewer_page, "Payload group")).to_have_attribute("aria-expanded", "false")
    viewer_page.locator("#tree-filter").fill("Needle")
    expect(node_label(viewer_page, "Needle field")).to_be_visible()
    viewer_page.locator("#tree-filter").fill("Trailer")
    viewer_page.locator("#tree-filter").fill("")
    expect(node_toggle(viewer_page, "Root")).to_have_attribute("aria-expanded", "true")
    expect(node_toggle(viewer_page, "Payload group")).to_have_attribute("aria-expanded", "false")
    expect(node_label(viewer_page, "Needle field")).not_to_be_visible()
    expect(node_label(viewer_page, "Trailer")).to_be_visible()
    expect(viewer_page.locator("#tree-filter-info")).to_have_text("5 nodes")


def test_expand_and_collapse_preserve_selection_source_and_byte_range(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    viewer_page.locator("#expand-all").click()
    node_label(viewer_page, "Needle field").click()
    selected_uid = node_label(viewer_page, "Needle field").get_attribute("data-uid")
    details = viewer_page.locator("#selection-details").text_content()
    highlights = viewer_page.locator("#hexdump .byte.manually-focused").all_text_contents()
    viewer_page.locator("#collapse-all").click()
    expect(node_label(viewer_page, "Needle field")).not_to_be_visible()
    expect(viewer_page.locator(".tree_label.manually-focused")).to_have_attribute(
        "data-uid", selected_uid
    )
    expect(viewer_page.locator("#source")).to_have_value("file")
    assert viewer_page.locator("#selection-details").text_content() == details
    assert viewer_page.locator("#hexdump .byte.manually-focused").all_text_contents() == highlights
    viewer_page.locator("#expand-all").click()
    expect(node_label(viewer_page, "Needle field")).to_be_visible()


def test_structure_search_reveals_a_filtered_and_collapsed_node(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    viewer_page.locator("#collapse-all").click()
    viewer_page.locator("#tree-filter").fill("Trailer")
    expect(node_label(viewer_page, "Needle field")).not_to_be_visible()
    viewer_page.locator("#searchmode").select_option("structure")
    viewer_page.locator("#search").fill("Needle field")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1")
    expect(viewer_page.locator("#tree-filter")).to_have_value("")
    expect(node_label(viewer_page, "Needle field")).to_be_visible()
    expect(node_label(viewer_page, "Needle field")).to_have_class(re.compile("manually-focused"))


def test_selecting_a_visible_match_retains_the_filter(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    viewer_page.locator("#tree-filter").fill("Needle")
    node_label(viewer_page, "Needle field").click()
    expect(viewer_page.locator("#tree-filter")).to_have_value("Needle")
    expect(node_label(viewer_page, "Trailer")).not_to_be_visible()


def test_empty_and_unmatched_filters_report_their_counts(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    viewer_page.locator("#tree-filter").fill("nothing matches")
    expect(viewer_page.locator("#tree-filter-info")).to_have_text("0 of 5 nodes match.")
    expect(viewer_page.locator(".tree_label:visible")).to_have_count(0)
    open_report(viewer_page, report_factory(b"", []))
    expect(viewer_page.locator("#tree-filter-info")).to_have_text("No structure nodes.")
    expect(viewer_page.locator("#expand-all")).to_be_disabled()
    expect(viewer_page.locator("#collapse-all")).to_be_disabled()
    viewer_page.locator("#tree-filter").fill("anything")
    expect(viewer_page.locator("#tree-filter-info")).to_have_text("0 of 0 nodes match.")


def test_filter_and_expansion_controls_work_from_the_keyboard(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(128), tree_nodes()))
    node_label(viewer_page, "Trailer").click()
    viewer_page.locator("#tree-filter").fill("Needle")
    viewer_page.locator("#tree-filter").press("Escape")
    expect(viewer_page.locator("#tree-filter")).to_have_value("")
    expect(node_label(viewer_page, "Trailer")).to_have_class(re.compile("manually-focused"))
    viewer_page.locator("#expand-all").focus()
    viewer_page.keyboard.press("Enter")
    expect(node_label(viewer_page, "Needle field")).to_be_visible()
    viewer_page.locator("#collapse-all").focus()
    viewer_page.keyboard.press("Space")
    expect(node_label(viewer_page, "Trailer")).not_to_be_visible()
