from unittest import TestCase

from polyfile.kaitai import parser


class TestKaitai(TestCase):
    def test_get_parser(self):
        self.assertIsNotNone(parser.get_parser("image/jpeg.ksy"))
