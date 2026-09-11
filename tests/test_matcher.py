from pathlib import Path
from typing import Iterable, Iterator, List, Tuple
from unittest import TestCase

from polyfile.fileutils import FileStream
from polyfile.magic import Match as MagicMatch
from polyfile.polyfile import Match, Matcher

from .test_zipmatcher import build_zip, temporary_file

Structure = List[Tuple[int, str, int, int]]


def structure(matches: Iterable[Match]) -> Structure:
    """Flattens a match tree into a value that two matcher runs can be compared on.

    Args:
        matches: The matches one :meth:`polyfile.polyfile.Matcher.match` call produced.

    Returns:
        The depth, name, absolute offset, and length of every match, in the order the matcher
        produced them.
    """
    flattened: Structure = []
    for match in matches:
        depth = 0
        parent = match.parent
        while parent is not None:
            depth += 1
            parent = parent.parent
        flattened.append((depth, match.name, match.offset, match.length))
    return flattened


def mime_types(matches: Iterator[MagicMatch]) -> List[str]:
    """Returns every MIME type a :meth:`polyfile.polyfile.Matcher.identify` call reported."""
    return sorted(mimetype for match in matches for mimetype in match.mimetypes)


class TestMatcherInputForms(TestCase):
    """Regression tests for #3463.

    `Matcher.match` accepts a path, a `Path`, an open binary stream, or a `FileStream`, and
    `MatchContext.load` reads whichever it is to EOF before any parser runs. Only the first two
    survived that: a path is reopened, while an already-open stream was handed to the parsers
    still sitting at EOF, so every parser read `b""` and mapped nothing.
    """

    def assertArchiveMapped(self, mapped: Structure):
        """Asserts that a match tree covers the records of a ZIP, not only its file type."""
        names = [name for _, name, _, _ in mapped]
        self.assertIn("application/zip", names)
        self.assertIn("LocalFileHeader", names)
        self.assertIn("CentralDirectory", names)
        self.assertIn("EndOfCentralDirectory", names)

    def matched(self, source) -> Structure:
        return structure(Matcher(parse=True).match(source))

    def test_every_input_form_produces_the_same_structure(self):
        with temporary_file(build_zip()) as path:
            from_path = self.matched(str(path))
            self.assertArchiveMapped(from_path)
            self.assertEqual(from_path, self.matched(Path(path)))
            with open(path, "rb") as stream:
                self.assertEqual(from_path, self.matched(stream))
            with FileStream(str(path)) as stream:
                self.assertEqual(from_path, self.matched(stream))


class TestMatcherStreamReuse(TestCase):
    """Regression tests for #3463 on the other entry points that read a caller's stream.

    `Matcher.identify` never re-wraps its stream, so it did not lose structure the way `match`
    did, but it left the caller's handle at EOF. A second call on the same handle saw an empty
    file and reported `application/octet-stream`.
    """

    def test_identify_is_repeatable_on_one_handle(self):
        with temporary_file(build_zip()) as path, open(path, "rb") as stream:
            matcher = Matcher(parse=False)
            first = mime_types(matcher.identify(stream))
            self.assertIn("application/zip", first)
            self.assertEqual(first, mime_types(matcher.identify(stream)))

    def test_match_is_repeatable_on_one_handle(self):
        with temporary_file(build_zip()) as path, open(path, "rb") as stream:
            matcher = Matcher(parse=True)
            first = structure(matcher.match(stream))
            self.assertEqual(first, structure(matcher.match(stream)))
