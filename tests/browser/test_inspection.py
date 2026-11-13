"""Keyboard, selection, navigation, and clipboard behavior in offline reports."""

import base64
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.browser.helpers import ReportFactory, match, open_report

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

expect = pytest.importorskip(
    "playwright.sync_api", reason="Install .[viewer-test] first"
).expect


def node_button(page: "Page", name: str) -> "Locator":
    """Find a selectable structure node by its visible name."""
    return page.locator(".tree_label").filter(has_text=name)


def navigate_to(page: "Page", offset: str) -> None:
    """Submit the visible offset control."""
    page.locator("#goto").fill(offset)
    page.locator("#goto").press("Enter")


def test_keyboard_selects_branches_and_leaves(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    branch = match(10, 20, name="branch", children=[match(12, 2, name="leaf")])
    open_report(
        viewer_page,
        report_factory(bytes(range(100)), [match(0, 100, children=[branch])]),
    )
    node_button(viewer_page, "branch").focus()
    viewer_page.keyboard.press("Enter")
    expect(node_button(viewer_page, "branch")).to_have_attribute("aria-pressed", "true")
    expect(viewer_page.locator("#selection-details")).to_contain_text("0xa (10)")
    expand = viewer_page.get_by_role("button", name="Expand branch", exact=True)
    expect(expand).to_have_attribute("aria-expanded", "false")
    expand.focus()
    viewer_page.keyboard.press("Space")
    expect(node_button(viewer_page, "leaf")).to_be_visible()
    node_button(viewer_page, "leaf").focus()
    viewer_page.keyboard.press("Space")
    expect(viewer_page.locator("#selection-details")).to_contain_text("0xc (12)")
    expect(viewer_page.locator("#selection-details")).to_contain_text("2 bytes")
    expect(node_button(viewer_page, "branch")).to_have_attribute(
        "aria-pressed", "false"
    )


@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_repeated_node_click_clears_selection_and_preserves_navigation(
    viewer_page: "Page", report_factory: ReportFactory, source: str
) -> None:
    payload = bytes(range(256)) * 32
    leaf = match(129, 1, name="leaf", source=source)
    selected = match(128, 16, name="selected node", source=source, children=[leaf])
    container = match(
        0, len(payload), name="source branch", source=source, children=[selected]
    )
    if source != "file":
        container["decoded"] = base64.b64encode(payload).decode("ascii")
        nodes = [match(0, 4, name="physical root", children=[container])]
    else:
        nodes = [container]
    open_report(viewer_page, report_factory(payload, nodes))
    viewer_page.get_by_role("button", name="Expand all", exact=True).click()
    label = node_button(viewer_page, "selected node")
    label.click()
    expect(label).to_have_attribute("aria-pressed", "true")
    viewer_page.locator("#scrollcontainer").evaluate(
        "element => { element.scrollTop = 0; }"
    )
    expect(viewer_page.locator("#byte-position")).to_contain_text("0x0–")
    position = viewer_page.locator("#byte-position").inner_text()
    label.dispatch_event("pointerover")
    expect(viewer_page.locator("#hexdump .highlighted")).to_have_count(16)
    label.click()
    expect(label).to_have_attribute("aria-pressed", "false")
    expect(
        viewer_page.locator(".manually-focused, .highlighted, .cursor")
    ).to_have_count(0)
    expect(viewer_page.locator("#selection-details")).to_have_text(
        "Select a structure node to inspect its byte range."
    )
    expect(viewer_page.locator("#source")).to_have_value(source)
    expect(viewer_page.locator("#byte-position")).to_have_text(position)
    expect(node_button(viewer_page, "leaf")).to_be_visible()
    expect(
        viewer_page.get_by_role("button", name="Collapse selected node", exact=True)
    ).to_have_attribute("aria-expanded", "true")
    viewer_page.locator("#search").hover()
    label.hover()
    expect(viewer_page.locator("#hexdump .highlighted")).to_have_count(16)


@pytest.mark.parametrize("key", ["Enter", "Space"])
def test_repeated_keyboard_activation_toggles_selection(
    viewer_page: "Page", report_factory: ReportFactory, key: str
) -> None:
    open_report(
        viewer_page, report_factory(b"data", [match(0, 4, name="selected node")])
    )
    label = node_button(viewer_page, "selected node")
    label.focus()
    for selected in (True, False, True):
        viewer_page.keyboard.press(key)
        expect(label).to_have_attribute("aria-pressed", str(selected).lower())
        expect(label).to_be_focused()
        expect(viewer_page.locator("#hexdump .manually-focused")).to_have_count(
            4 if selected else 0
        )
    viewer_page.keyboard.press("Escape")
    expect(label).to_have_attribute("aria-pressed", "false")
    expect(viewer_page.locator("#hexdump .manually-focused")).to_have_count(0)
    expect(viewer_page.locator("#selection-details")).to_have_text(
        "Select a structure node to inspect its byte range."
    )


def test_structure_search_reveals_collapsed_ancestors(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    nested = match(4, 8, name="branch", children=[match(6, 2, name="needle field")])
    open_report(
        viewer_page, report_factory(bytes(16), [match(0, 16, children=[nested])])
    )
    expect(node_button(viewer_page, "needle field")).not_to_be_visible()
    viewer_page.locator("#searchmode").select_option("structure")
    viewer_page.locator("#search").fill("needle field")
    expect(node_button(viewer_page, "needle field")).to_be_visible()
    expect(node_button(viewer_page, "needle field")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(viewer_page.locator("#selection-details")).to_contain_text("needle field")
    for direction in ("#searchdown", "#searchup", "#searchdown"):
        viewer_page.locator(direction).click()
        expect(node_button(viewer_page, "needle field")).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(viewer_page.locator("#hexdump .manually-focused")).to_have_count(2)


def test_hover_preserves_source_and_persistent_selection(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    decoded = match(0, 4, name="decoded node", source="decoded:0", decoded="ZGF0YQ==")
    nodes = [match(0, 4, name="physical node", children=[decoded])]
    open_report(viewer_page, report_factory(b"file", nodes))
    node_button(viewer_page, "physical node").click()
    node_button(viewer_page, "decoded node").hover()
    expect(viewer_page.locator("#source")).to_have_value("file")
    expect(node_button(viewer_page, "physical node")).to_have_attribute(
        "aria-pressed", "true"
    )
    node_button(viewer_page, "decoded node").click()
    node_button(viewer_page, "physical node").hover()
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    expect(node_button(viewer_page, "decoded node")).to_have_attribute(
        "aria-pressed", "true"
    )
    viewer_page.locator("#search").hover()
    expect(viewer_page.locator("#hexdump .manually-focused")).to_have_count(4)


def test_source_switch_removes_old_source_hover_labels(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    decoded = match(0, 4, name="decoded node", source="decoded:0", decoded="ZGF0YQ==")
    open_report(viewer_page, report_factory(b"file", [match(0, 4, children=[decoded])]))
    viewer_page.locator("#byte0").hover()
    expect(viewer_page.locator(".tree_label.highlighted")).to_have_count(1)
    viewer_page.locator("#source").select_option("decoded:0")
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    expect(viewer_page.locator("#byte0")).to_have_text("64")
    expect(
        viewer_page.locator('.tree_label.highlighted[data-source="file"]')
    ).to_have_count(0)
    viewer_page.locator("#byte0").dispatch_event("pointerover")
    expect(
        viewer_page.locator('.tree_label.highlighted[data-source="decoded:0"]')
    ).to_have_count(1)
    expect(
        viewer_page.locator('.tree_label.highlighted[data-source="file"]')
    ).to_have_count(0)


def test_source_switch_clears_synthetic_hover_without_retargeting(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    decoded = match(0, 4, name="decoded node", source="decoded:0", decoded="ZGF0YQ==")
    open_report(viewer_page, report_factory(b"file", [match(0, 4, children=[decoded])]))
    viewer_page.mouse.move(0, 0)
    viewer_page.locator("#byte0").dispatch_event("pointerover")
    expect(viewer_page.locator(".tree_label.highlighted")).to_have_count(1)
    viewer_page.locator("#source").select_option("decoded:0")
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    expect(viewer_page.locator("#byte0")).to_have_text("64")
    expect(viewer_page.locator(".tree_label.highlighted")).to_have_count(0)
    expect(viewer_page.locator("#hexdump .cursor")).to_have_count(0)


def test_cross_source_selection_refreshes_current_source_search(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    decoded = match(0, 4, name="decoded node", source="decoded:0", decoded="ZGF0YQ==")
    open_report(
        viewer_page, report_factory(b"needle", [match(0, 6, children=[decoded])])
    )
    viewer_page.locator("#searchmode").select_option("text")
    viewer_page.locator("#searchscope").select_option("current")
    viewer_page.locator("#search").fill("needle")
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1 · file")
    node_button(viewer_page, "decoded node").click()
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    expect(viewer_page.locator("#searchinfo")).to_have_text("0 results")
    expect(node_button(viewer_page, "decoded node")).to_have_attribute(
        "aria-pressed", "true"
    )


@pytest.mark.parametrize(
    "offset", ["", "xyz", "12junk", "-1", "+1", "0x", "8192", "9007199254740992"]
)
def test_invalid_offsets_preserve_view_and_selection(
    viewer_page: "Page", report_factory: ReportFactory, offset: str
) -> None:
    open_report(viewer_page, report_factory(bytes(range(256)) * 32))
    navigate_to(viewer_page, "0x80")
    before = viewer_page.locator("#byte-position").inner_text()
    navigate_to(viewer_page, offset)
    expect(viewer_page.locator("#goto")).to_have_attribute("aria-invalid", "true")
    expect(viewer_page.locator("#goto-error")).not_to_be_empty()
    expect(viewer_page.locator("#selection-details")).to_contain_text("0x80 (128)")
    expect(viewer_page.locator("#byte-position")).to_have_text(before)


def test_decimal_hex_and_final_byte_offsets(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(bytes(range(256)) * 32))
    for value, expected in [
        ("10", "0xa (10)"),
        ("0x10", "0x10 (16)"),
        ("8191", "0x1fff (8191)"),
    ]:
        navigate_to(viewer_page, value)
        expect(viewer_page.locator("#selection-details")).to_contain_text(expected)
        expect(viewer_page.locator("#goto-error")).to_be_empty()
    expect(viewer_page.locator("#hexdump .manually-focused")).to_have_text("ff")


def test_empty_source_offset_has_actionable_error(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    open_report(viewer_page, report_factory(b""))
    navigate_to(viewer_page, "0")
    expect(viewer_page.locator("#goto-error")).to_have_text(
        "This source has no bytes to navigate."
    )


def test_copy_fallback_contains_exact_bytes_and_restores_focus(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.add_init_script(
        "Object.defineProperty(navigator, 'clipboard', {value: undefined})"
    )
    child = match(1, 3, name="selected bytes")
    open_report(
        viewer_page, report_factory(b"\x00\xffA\x80", [match(0, 4, children=[child])])
    )
    node_button(viewer_page, "selected bytes").click()
    copy = viewer_page.get_by_role("button", name="Copy bytes as hex", exact=True)
    copy.click()
    dialog = viewer_page.locator("#clipboard-fallback")
    expect(dialog).to_be_visible()
    expect(dialog.locator("textarea")).to_have_value("ff 41 80")
    expect(dialog.locator("textarea")).to_be_focused()
    viewer_page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(copy).to_be_focused()
    expect(node_button(viewer_page, "selected bytes")).to_have_attribute(
        "aria-pressed", "true"
    )
    viewer_page.get_by_role("button", name="Copy offset", exact=True).click()
    expect(dialog.locator("textarea")).to_have_value("0x1")
    dialog.get_by_role("button", name="Close", exact=True).click()


def test_decoded_text_uses_unified_source_view(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    payload = "Decoded snowman ☃".encode()
    decoded = match(
        0,
        len(payload),
        name="decoded node",
        source="decoded:0",
        decoded=base64.b64encode(payload).decode("ascii"),
    )
    open_report(viewer_page, report_factory(b"file", [match(0, 4, children=[decoded])]))
    viewer_page.get_by_role(
        "button", name="View decoded text for decoded node", exact=True
    ).click()
    expect(viewer_page.locator("#source")).to_have_value("decoded:0")
    expect(viewer_page.locator("#text-view")).to_have_attribute("aria-pressed", "true")
    expect(viewer_page.locator("#readablebytes")).to_contain_text("Decoded snowman ☃")
    expect(viewer_page.locator("#decoded-preview")).to_have_count(0)


def test_tree_download_is_visible_and_keyboard_operable(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    child = match(1, 2, name="selected bytes")
    open_report(
        viewer_page, report_factory(b"\x00\xffA\x80", [match(0, 4, children=[child])])
    )
    download = viewer_page.get_by_role(
        "button", name="Download selected bytes", exact=True
    )
    expect(download).to_be_visible()
    download.focus()
    with viewer_page.expect_download() as result:
        viewer_page.keyboard.press("Enter")
    assert Path(result.value.path()).read_bytes() == b"\xffA"


def test_mobile_selection_opens_bytes_pane(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.set_viewport_size({"width": 390, "height": 844})
    open_report(viewer_page, report_factory(b"file", [match(0, 4, name="select me")]))
    viewer_page.locator("#structure-tab").click()
    node_button(viewer_page, "select me").click()
    expect(viewer_page.locator("#bytes-tab")).to_have_attribute("aria-selected", "true")
    expect(viewer_page.locator("#bytes-pane")).to_be_visible()


@pytest.mark.parametrize("mode", ["combined", "structure"])
def test_mobile_search_preserves_focus_while_typing(
    viewer_page: "Page", report_factory: ReportFactory, mode: str
) -> None:
    viewer_page.set_viewport_size({"width": 390, "height": 844})
    open_report(
        viewer_page, report_factory(b"data", [match(0, 4, name="alphabet field")])
    )
    viewer_page.locator("#searchmode").select_option(mode)
    search = viewer_page.locator("#search")
    search.focus()
    for index, letter in enumerate("alphabet", 1):
        viewer_page.keyboard.type(letter)
        expect(search).to_be_focused()
        expect(search).to_have_value("alphabet"[:index])
    expect(viewer_page.locator("#searchinfo")).to_contain_text("1 of 1")


def test_new_copy_request_cancels_pending_hex_preparation(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.add_init_script("""globalThis.copyWrites = [];
        Object.defineProperty(navigator, 'clipboard', {value: {
            writeText: async text => { globalThis.copyWrites.push(text); }
        }});""")
    viewer_page.clock.install()
    open_report(
        viewer_page, report_factory(bytes(1024 * 1024), [match(0, 1024 * 1024)])
    )
    viewer_page.locator(".tree_label").click()
    viewer_page.evaluate("""() => {
        const buttons = [...document.querySelectorAll('#selection-details button')];
        buttons.find(button => button.textContent === 'Copy bytes as hex').click();
        buttons.find(button => button.textContent === 'Copy offset').click();
    }""")
    viewer_page.clock.run_for(1000)
    assert viewer_page.evaluate("globalThis.copyWrites") == ["0x0"]


def test_mobile_details_leave_room_for_the_tree(
    viewer_page: "Page", report_factory: ReportFactory
) -> None:
    viewer_page.set_viewport_size({"width": 390, "height": 844})
    node = match(
        0,
        16,
        name="selected node",
        analysis_status="unsupported",
        analysis_message="Long analysis detail. " * 100,
    )
    open_report(viewer_page, report_factory(bytes(16), [node]))
    viewer_page.locator("#structure-tab").click()
    viewer_page.locator(".tree_label").click()
    viewer_page.locator("#structure-tab").click()
    tree = viewer_page.locator(".tree").bounding_box()
    details = viewer_page.locator("#selection-details").bounding_box()
    assert tree is not None and tree["height"] >= 80
    assert details is not None and details["height"] <= 140
