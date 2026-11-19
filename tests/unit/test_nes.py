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

    def test_short_trainer_and_rom_banks(self):
        cases = (("Trainer", (0, 0, 4)), ("PRGBank", (1, 0, 0)), ("CHRBank", (0, 1, 0)))
        for field, flags in cases:
            for payload in (b"", b"abc"):
                with self.subTest(field=field, size=len(payload)):
                    data = b"NES\x1a" + bytes(flags) + bytes(9) + payload
                    matches = list(Matcher().match(data))
                    root = next(m for m in matches if m.name == "application/x-nes-rom")
                    self.assertEqual("invalid", root.analysis_status)
                    self.assertIn(field, root.analysis_message or "")
                    self.assertTrue(all(m.offset + m.length <= len(data) for m in matches))
                    actual = sum(m.length for m in matches if m.name == field)
                    self.assertEqual(len(payload), actual)

    def test_nes2_exponent_sizes(self):
        header = b"NES\x1a" + bytes((56, 41, 0, 8, 0, 0xff)) + bytes(6)
        data = header + bytes(16384) + bytes(3072)
        matches = list(Matcher().match(data))
        spans = [(m.name, m.offset, m.length) for m in matches if m.name in {"PRGBank", "CHRBank"}]
        self.assertEqual([("PRGBank", 16, 16384), ("CHRBank", 16400, 3072)], spans)

    def test_nes2_extended_count_and_legacy_padding(self):
        for flags, expected in ((8, "invalid"), (0, None)):
            with self.subTest(flags=flags):
                header = b"NES\x1a" + bytes((1, 0, 0, flags, 0, 1)) + bytes(6)
                matches = list(Matcher().match(header + bytes(16384)))
                root = next(m for m in matches if m.name == "application/x-nes-rom")
                self.assertEqual(expected, root.analysis_status)
                self.assertEqual([16384], [m.length for m in matches if m.name == "PRGBank"])
