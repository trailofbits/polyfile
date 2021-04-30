from unittest import TestCase

from polyfile.magic import MagicDefinition, MAGIC_DEFS


class MagicTest(TestCase):
    def test_parsing(self):
        for file in MAGIC_DEFS:
            print(file)
            MagicDefinition.parse(file)
