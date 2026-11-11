from unittest import TestCase

from polyfile.nes import parse_ines_header
from polyfile.polyfile import InvalidMatch, Match, Matcher


VALID_HEADER = b"NES\x1a" + bytes([1, 0, 0, 0]) + bytes(8)


class INESHeaderTest(TestCase):
    def _root(self) -> Match:
        return Match(name="root", match_obj=b"", relative_offset=0, matcher=Matcher())

    def test_rejects_bad_magic(self):
        with self.assertRaises(InvalidMatch):
            list(parse_ines_header(b"NOPE" + bytes(12), self._root()))

    def test_rejects_truncated_header(self):
        """A header shorter than 16 bytes is not a usable iNES header.

        Lengths 4 to 10 used to raise IndexError, which the parser dispatcher
        catches as an unexpected error, logs, and then drops the rest of the
        submatches. Lengths 11 to 15 raised nothing at all and produced an
        iNESHeader claiming to be 16 bytes with a short UnusedPadding.
        """
        for length in range(4, 16):
            with self.subTest(length=length):
                with self.assertRaises(InvalidMatch):
                    list(parse_ines_header(VALID_HEADER[:length], self._root()))

    def test_accepts_full_header(self):
        names = [m.name for m in parse_ines_header(VALID_HEADER, self._root())]

        self.assertEqual(names[0], "iNESHeader")
        for expected in ("iNESMagic", "PRGSize", "CHRSize", "UnusedPadding"):
            self.assertIn(expected, names)
