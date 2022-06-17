from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
import zipfile

from polyfile.kaitai.parser import KaitaiParser, RootNode, Segment


class TestKaitai(TestCase):
    def test_parser_load(self):
        self.assertIsNotNone(KaitaiParser.load("image/jpeg.ksy"))

    def test_parse_zip(self):
        f = NamedTemporaryFile("wb", delete=False)
        try:
            f.close()
            with zipfile.ZipFile(f.name, "w") as test_zip:
                test_zip.write(__file__)
            for node in KaitaiParser.load("archive/zip.ksy").parse(f.name).ast.dfs():
                with self.subTest(kaitai_node=node.name):
                    if node.parent is None:
                        self.assertIsInstance(node, RootNode)
                    else:
                        self.assertGreaterEqual(node.start, node.parent.start)
                        self.assertLessEqual(node.end, node.parent.end)
                        self.assertLessEqual(len(node.segment), len(node.parent.segment))
        finally:
            path = Path(f.name)
            if path.exists():
                try:
                    path.unlink()
                except PermissionError:
                    # This can sometimes happen on Windows due to a race condition
                    pass

    def test_segments(self):
        s = Segment(0, 10)
        self.assertTrue(s)
        self.assertEqual(s[:5], Segment(0, 5))
        self.assertEqual(s[-1], Segment(9, 10))
        self.assertEqual(s[1:3], Segment(1, 3))
        self.assertRaises(IndexError, s.__getitem__, -len(s) - 1)
        self.assertRaises(IndexError, s.__getitem__, len(s))
        self.assertRaises(ValueError, s.__getitem__, slice(0, 1, 5))
        self.assertFalse(s[20:30])
