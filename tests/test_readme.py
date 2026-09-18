import re
from pathlib import Path
from typing import List, Tuple
from unittest import TestCase

REPO_ROOT: Path = Path(__file__).absolute().parent.parent
README_PATH: Path = REPO_ROOT / "README.md"

MARKDOWN_LINK: re.Pattern = re.compile(r"\[(?P<text>[^]]*)]\((?P<target>[^)\s]+)\)")
"""Matches an inline markdown link, capturing its text and its target."""

ABSOLUTE_SCHEMES: Tuple[str, ...] = ("https://", "http://", "mailto:")


def readme_link_targets() -> List[str]:
    """The target of every inline markdown link in README.md.

    Returns:
        The targets, in the order they appear.
    """
    return [match.group("target") for match in MARKDOWN_LINK.finditer(README_PATH.read_text())]


class TestReadmeLinks(TestCase):
    """Guards the links in the README that PyPI serves as the project description.

    PyPI renders README.md verbatim and resolves a relative target against pypi.org, where nothing
    of this repository exists, so a link that works on GitHub 404s for anyone arriving from
    ``pip show`` or the project page. Every target therefore has to be absolute or a fragment.
    """

    def test_every_link_is_absolute_or_a_fragment(self):
        relative = [
            target for target in readme_link_targets()
            if not target.startswith(ABSOLUTE_SCHEMES) and not target.startswith("#")
        ]
        self.assertEqual([], relative, (
            "PyPI serves README.md as the project description and resolves a relative link against "
            "pypi.org, so these targets are broken there. Write them as "
            "https://github.com/trailofbits/polyfile/blob/master/<path>."
        ))

    def test_no_link_target_is_itself_a_link(self):
        """A nested ``[text]([text](target))`` renders as literal text around a broken link.

        `test_every_link_is_absolute_or_a_fragment` catches the spelling of this that README.md
        actually carried, because the inner target was relative. It would not catch one whose inner
        target is absolute, so this looks for the shape rather than the symptom: a link target that
        opens with the ``[`` of another link.
        """
        text = README_PATH.read_text()
        nested = [
            text[match.start():match.start() + 60]
            for match in re.finditer(r"]\(\s*\[", text)
        ]
        self.assertEqual([], nested, (
            "these link targets open with another markdown link, which renders as literal text "
            "wrapped around a broken link"
        ))
