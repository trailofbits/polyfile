from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
import zipfile

from polyfile.kaitai.parser import KaitaiParser


class TestKaitai(TestCase):
    def test_parser_load(self):
        self.assertIsNotNone(KaitaiParser.load("image/jpeg.ksy"))

    def test_parse_zip(self):
        f = NamedTemporaryFile("wb", delete=False)
        try:
            f.close()
            with zipfile.ZipFile(f.name, "w") as test_zip:
                test_zip.write(__file__)
            _ = KaitaiParser.load("archive/zip.ksy").parse(f.name)
        finally:
            path = Path(f.name)
            if path.exists():
                path.unlink()
