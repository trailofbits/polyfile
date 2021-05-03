from unittest import TestCase

from polyfile.magic import MagicMatcher, MAGIC_DEFS


class MagicTest(TestCase):
    def test_parsing(self):
        MagicMatcher.parse(*MAGIC_DEFS)
