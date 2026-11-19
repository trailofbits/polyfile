"""Exercise PNG identification and Kaitai parsing through the installed CLI."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from PIL import Image


class TestWheelSmoke(TestCase):
    def test_png_mime_and_structure(self) -> None:
        with TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.png"
            with Image.new("RGB", (2, 3)) as image:
                image.save(sample)
            result = subprocess.run(
                [
                    sys.executable, "-I", "-m", "polyfile", "--quiet", sample.name,
                    "--format", "mime", "--output", "mime.txt",
                    "--format", "json", "--output", "report.json",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            mime_types = (sample.parent / "mime.txt").read_text(encoding="utf-8")
            self.assertIn("image/png", mime_types.splitlines())
            report = json.loads((sample.parent / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["length"], sample.stat().st_size)

        nodes = report["struc"]
        for name in ("image/png", "Png", "ihdr"):
            by_name = {node["name"]: node for node in nodes}
            self.assertIn(name, by_name)
            nodes = by_name[name]["subEls"]

        by_name = {node["name"]: node for node in nodes}
        for name, offset, dimension in (("width", 16, 2), ("height", 20, 3)):
            with self.subTest(field=name):
                self.assertIn(name, by_name)
                field = by_name[name]
                self.assertEqual((field["offset"], field["size"]), (offset, 4))
                self.assertEqual(field["value"], repr(dimension.to_bytes(4, "big")))


if __name__ == "__main__":
    main()
