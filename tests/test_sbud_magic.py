"""Structured magic output uses the matched values and stable extension preferences."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

from PIL import Image

from polyfile.fileutils import Tempfile
from polyfile.magic import MagicMatcher
from polyfile.polyfile import Analyzer


class StructuredMagicTests(TestCase):
    def test_each_mime_uses_its_own_rule_value(self):
        rules = (
            b"0 byte x first:%u\n!:mime application/x-first\n"
            b">1 byte x second:%u\n!:mime application/x-second\n"
            b">2 byte x\n!:mime application/x-empty-message\n"
            b">3 byte x ${x?executable:ordinary}:%u\n!:mime application/x-mode\n"
        )
        with Tempfile(rules) as path, Tempfile(b"ABCD") as source:
            analyzer = Analyzer(source, parse=False, magic_matcher=MagicMatcher.parse(path))
            nodes = {node["type"]: node["value"] for node in analyzer.sbud()["struc"]}
        self.assertEqual(nodes["application/x-first"], "first:65")
        self.assertEqual(nodes["application/x-second"], "second:66")
        self.assertEqual(nodes["application/x-empty-message"], "")
        self.assertEqual(nodes["application/x-mode"], "ordinary:68")

    def test_structured_magic_values_render_substitutions(self):
        with Tempfile(b"0 byte x value:%u\n!:mime application/x-value\n") as rules:
            custom = MagicMatcher.parse(rules)
            cases = ((custom, b"AxyzZ", "value:65"),
                     (None, b"UNIF\x07\x00\x00\x00", "NES ROM image (UNIF v7 format)"))
            for matcher, data, expected in cases:
                with Tempfile(data) as path:
                    analyzer = Analyzer(path, parse=False, magic_matcher=matcher)
                    self.assertIn(expected, [str(match) for match in analyzer.magic_matches()])
                    values = [node["value"] for node in analyzer.sbud()["struc"]]
                    self.assertIn(expected, values)

    def test_jpeg_extension_is_stable_across_hash_seeds(self):
        with Tempfile(b"") as path:
            Image.new("RGB", (1, 1)).save(Path(path), format="JPEG")
            script = (
                "import sys; from polyfile.polyfile import Analyzer; "
                "nodes = Analyzer(sys.argv[1], parse=False).sbud()['struc']; "
                "print(next(n['extension'] for n in nodes if n['type'] == 'image/jpeg'))"
            )
            extensions = {
                subprocess.check_output(
                    [sys.executable, "-c", script, str(path)],
                    env={**os.environ, "PYTHONHASHSEED": seed}, text=True,
                ).strip()
                for seed in ("0", "1", "2", "3")
            }
            self.assertEqual(len(extensions), 1, extensions)
