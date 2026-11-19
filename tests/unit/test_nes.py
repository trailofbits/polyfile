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

    def test_legacy_header_metadata(self):
        header = VALID_HEADER[:8] + bytes(range(8, 16))
        fields = [m for m in parse_ines_header(header, self._root()) if m.relative_offset >= 8]
        self.assertEqual(
            [
                ("PRGRAMSize", "PRGRAMSize", 8, 1, 8),
                ("Flags", "Flags9", 9, 1, 9),
                ("Flags", "Flags10", 10, 1, 10),
                ("UnusedPadding", "UnusedPadding", 11, 5, bytes(range(11, 16))),
            ],
            [(m.name, m.display_name, m.offset, m.length, m.match) for m in fields],
        )

    def test_nes2_header_metadata(self):
        header = b"NES\x1a" + bytes((1, 0, 0xB2, 0xA9, 0x43, 0, 0x07, 0x86, 2, 0x53, 2, 31))
        matches = Matcher().match(header + bytes(16384))
        header_node = next(node for node in matches if node.name == "iNESHeader")
        list(matches)
        fields = [f for f in header_node.to_obj()["subEls"] if f["relative_offset"] >= 8]
        self.assertEqual(
            [
                ("MapperMSBAndSubmapper", 8, 1, "Mapper 939, submapper 4"),
                ("ROMSizeMSBs", 9, 1, "PRG-ROM 0, CHR-ROM 0"),
                ("PRGRAMAndNVRAMSize", 10, 1, "8192 bytes volatile, 0 bytes nonvolatile"),
                ("CHRRAMAndNVRAMSize", 11, 1, "4096 bytes volatile, 16384 bytes nonvolatile"),
                ("CPUPPUTiming", 12, 1, "2"),
                ("VsSystemType", 13, 1, "PPU type 3, hardware type 5"),
                ("MiscellaneousROMCount", 14, 1, "2"),
                ("DefaultExpansionDevice", 15, 1, "31"),
            ],
            [(f["name"], f["offset"], f["size"], f["value"]) for f in fields],
        )
        self.assertEqual([{"source": "file", "offset": 6, "size": 3}], fields[0]["dependencies"])

    def test_nes2_console_type_and_reserved_bits(self):
        for console, name, value in (
            (0, "Reserved", "187"),
            (2, "Reserved", "187"),
            (3, "ExtendedConsoleType", "11"),
        ):
            with self.subTest(console=console):
                header = b"NES\x1a" + bytes((1, 0, 0, 8 | console, 0, 0xDB, 0, 0))
                header += bytes((0xFF, 0xBB, 0xFE, 0xC1))
                nodes = parse_ines_header(header, self._root())
                fields = {node.offset: node.to_obj() for node in nodes}
                self.assertEqual("PRG-ROM 11, CHR-ROM 13", fields[9]["value"])
                self.assertEqual("3", fields[12]["value"])
                console_field = fields[13]
                self.assertEqual(
                    (name, 1, value),
                    (console_field["name"], console_field["size"], console_field["value"]),
                )
                self.assertEqual("2", fields[14]["value"])
                self.assertEqual("1", fields[15]["value"])

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
