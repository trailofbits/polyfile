"""Build report data and load generated viewers without a web server."""

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from playwright.sync_api import Page

MatchData: TypeAlias = dict[str, object]


class ReportFactory(Protocol):
    """Render independent reports from arbitrary bytes and match trees."""

    def __call__(
        self,
        contents: bytes,
        nodes: list[MatchData] | None = None,
        *,
        filename: str = "sample.bin",
    ) -> Path:
        """Return the path to a generated standalone report."""
        ...


def match(
    offset: int,
    size: int,
    *,
    name: str = "field",
    source: str = "file",
    children: Sequence[MatchData] = (),
    **extra: object,
) -> MatchData:
    """Build a match with the fields needed by the HTML generator.

    Args:
        offset: Byte offset within the selected source.
        size: Match length in bytes.
        name: Visible label in the syntax tree.
        source: Physical or decoded source identifier.
        children: Nested matches.
        **extra: Additional SBuD fields, such as decoded bytes or MIME type.

    Returns:
        A match dictionary suitable for a generated report.
    """
    return {
        "offset": offset,
        "relative_offset": offset,
        "size": size,
        "type": "application/octet-stream",
        "name": name,
        "source": source,
        "value": "",
        "subEls": list(children),
        **extra,
    }


def open_report(page: "Page", report: Path) -> None:
    """Open a report through file:// and wait for byte cells to initialize.

    Args:
        page: An isolated browser test page.
        report: The generated HTML file to open.
    """
    page.goto(report.as_uri())
    page.locator("#loading").wait_for(state="detached")
    page.locator(".hexdump .byteline").first.wait_for(state="visible")
