import tempfile
from pathlib import Path
from typing import Set
from unittest import TestCase

from polyfile.magic import MagicMatcher, printf_to_python


class TestPrintfToPython(TestCase):
    """Guards the rewrite of libmagic's C conversion specifications into Python's.

    libmagic writes its messages in C's printf language, where an integer conversion may declare
    how wide its argument is. Python infers that from the value and raises
    ``ValueError: unsupported format character 'l'`` when it is spelled out, so the modifier has to
    come off before the message is formatted.
    """

    def test_a_length_modifier_is_removed(self):
        self.assertEqual("%x", printf_to_python("%llx"))
        self.assertEqual("%d", printf_to_python("%lld"))
        self.assertEqual("%u", printf_to_python("%llu"))
        self.assertEqual("%d", printf_to_python("%ld"))

    def test_flags_width_and_precision_survive_it(self):
        """The defect: these were the spellings the old prefix match could not see.

        `%ll` and `%#ll` were removed with `str.replace`, which only matches when the modifier
        follows the `%` immediately, so anything carrying a flag, a field width or a precision fell
        through to Python's `%` operator and raised.
        """
        self.assertEqual("%#16.16x", printf_to_python("%#16.16llx"))
        self.assertEqual("%016x", printf_to_python("%016llx"))
        self.assertEqual("%0x", printf_to_python("%0llx"))
        self.assertEqual("%#016x", printf_to_python("%#016llx"))
        self.assertEqual("%-16x", printf_to_python("%-16llx"))
        self.assertEqual("%+d", printf_to_python("%+lld"))
        self.assertEqual("% d", printf_to_python("% lld"))

    def test_a_conversion_without_a_length_modifier_is_untouched(self):
        for conversion in ("%d", "%u", "%s", "%c", "%x", "%#x", "%#8.8x", "%.3s", "%-.8s", "%%"):
            with self.subTest(conversion=conversion):
                self.assertEqual(conversion, printf_to_python(conversion))

    def test_surrounding_text_is_untouched(self):
        self.assertEqual("uuid %0x,", printf_to_python("uuid %0llx,"))
        self.assertEqual("at %#16.16x offset", printf_to_python("at %#16.16llx offset"))


class TestMessagesRenderTheValue(TestCase):
    """Checks end to end that a message carrying a length modifier reports its value.

    Each expectation was taken from `file` 5.48 built from the `file` submodule, run as
    ``TZ=UTC LC_ALL=C ./file/src/file -b -m <definition> <file>`` over the same eight bytes.
    """

    DATA: bytes = bytes(range(8))

    def messages(self, definition: str) -> Set[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "definition"
            path.write_bytes(definition.encode("utf-8"))
            return {str(match) for match in MagicMatcher.parse(path).match(self.DATA)}

    def test_a_length_modifier_reports_its_value(self):
        for conversion, expected in (
            ("%llx", "n 706050403020100,"),
            ("%0llx", "n 706050403020100,"),
            ("%016llx", "n 0706050403020100,"),
            ("%16.16llx", "n 0706050403020100,"),
            ("%#16.16llx", "n 0x0706050403020100,"),
            ("%#016llx", "n 0x706050403020100,"),
            ("%-16llx", "n 706050403020100 ,"),
            ("%lld", "n 506097522914230528,"),
            ("%llu", "n 506097522914230528,"),
            ("%+lld", "n +506097522914230528,"),
        ):
            with self.subTest(conversion=conversion):
                self.assertEqual({expected}, self.messages(f"0\tlequad\tx\tn {conversion},\n"))

    def test_an_uppercase_conversion_keeps_its_case_in_the_prefix(self):
        """`%#llX` prints `0X`, not `0x`.

        The rewrite this replaced substituted the literal `0x%` for `%#ll`, so the `#` flag's
        prefix was lower case whatever the conversion was.
        """
        self.assertEqual({"n 0X706050403020100,"}, self.messages("0\tlequad\tx\tn %#llX,\n"))
        self.assertEqual({"n 0x706050403020100,"}, self.messages("0\tlequad\tx\tn %#llx,\n"))
