"""Isolated browsers and generated report fixtures for offline viewer tests."""

import base64
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import pytest

from tests.browser.helpers import MatchData, ReportFactory, match

if TYPE_CHECKING:
    from playwright.sync_api import Browser, ConsoleMessage, Page, Route

_CALL_REPORT = pytest.StashKey[pytest.TestReport]()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the browser engine option to the browser test directory."""
    parser.addoption(
        "--browser",
        action="append",
        choices=("chromium", "firefox", "webkit"),
        help="Browser engine to test; repeat to run multiple engines (default: chromium).",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Run browser fixtures once for each requested engine."""
    if "browser_name" in metafunc.fixturenames:
        engines = metafunc.config.getoption("--browser") or ["chromium"]
        metafunc.parametrize("browser_name", engines, scope="session")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    """Remember test failures so fixture teardown can save a screenshot."""
    report = yield
    if report.when == "call":
        item.stash[_CALL_REPORT] = report
    return report


@pytest.fixture(scope="session")
def viewer_browser(browser_name: str) -> Iterator["Browser"]:
    """Launch one browser engine for the requested test session."""
    playwright = pytest.importorskip("playwright.sync_api", reason="Install .[viewer-test] first")
    with playwright.sync_playwright() as driver:
        browser = getattr(driver, browser_name).launch()
        yield browser
        browser.close()


@pytest.fixture
def viewer_page(viewer_browser: "Browser", request: pytest.FixtureRequest) -> Iterator["Page"]:
    """Provide an offline page and fail on JavaScript or network errors."""
    failures: list[str] = []
    context = viewer_browser.new_context(
        viewport={"width": 1440, "height": 900}, service_workers="block", offline=True
    )

    def route_request(route: "Route") -> None:
        if urlsplit(route.request.url).scheme in {"file", "data", "blob", "about"}:
            route.continue_()
        else:
            failures.append(f"External request: {route.request.url}")
            route.abort()

    def console_message(message: "ConsoleMessage") -> None:
        if message.type == "error":
            failures.append(f"Console error: {message.text}")

    def observe_page(page: "Page") -> None:
        page.on("pageerror", lambda error: failures.append(f"JavaScript error: {error}"))
        page.on("console", console_message)

    context.route("**/*", route_request)
    context.on("page", observe_page)
    page = context.new_page()
    yield page
    report = request.node.stash.get(_CALL_REPORT, None)
    if failures or (report is not None and report.failed):
        directory = Path("test-results") / request.node.name
        directory.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(directory / "failure.png"), full_page=True)
    context.close()
    assert not failures, "\n".join(failures)


@pytest.fixture
def report_factory(tmp_path: Path) -> ReportFactory:
    """Render each report from fresh input data in a separate temporary directory."""
    from polyfile.html import generate

    report_number = 0

    def render(
        contents: bytes,
        nodes: list[MatchData] | None = None,
        *,
        filename: str = "sample.bin",
    ) -> Path:
        nonlocal report_number
        directory = tmp_path / str(report_number)
        directory.mkdir()
        report_number += 1
        input_path = directory / filename
        input_path.write_bytes(contents)
        sbud = {
            "fileName": filename,
            "length": len(contents),
            "b64contents": base64.b64encode(contents).decode("ascii"),
            "struc": deepcopy(nodes if nodes is not None else [match(0, len(contents))]),
        }
        report = directory / "report.html"
        report.write_text(generate(str(input_path), sbud), encoding="utf-8")
        return report

    return render
