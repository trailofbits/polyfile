import tempfile
from pathlib import Path
from typing import Any, Iterator, List, Set, Tuple
from unittest import TestCase

from polyfile.magic import MagicMatcher, MagicTest, printf_to_python

RENDER_VALUES: Tuple[Any, ...] = (0, 1234, -1, 2 ** 40, b"abc", "abc")
"""One value of every shape a test can hand its message: an integer, a byte string, a string.

A conversion only has to accept one of them. `%d` rejecting `b"abc"` says nothing, because a test
whose message holds `%d` never yields bytes; a message no value at all can render is the defect.
"""


def every_test(matcher: MagicMatcher) -> Iterator[MagicTest]:
    """Walks a matcher's tests, including the subtests nested under them.

    Args:
        matcher: the matcher to walk.

    Yields:
        Each test once, in no particular order.
    """
    seen: Set[int] = set()
    stack: List[MagicTest] = list(matcher)
    while stack:
        test = stack.pop()
        if id(test) in seen:
            continue
        seen.add(id(test))
        yield test
        stack.extend(test.children)


def renders(message: str, value: Any) -> bool:
    """Reports whether `message` formats `value` without raising."""
    try:
        message % (value,)
    except (ValueError, TypeError):
        return False
    return True


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


class TestEveryBundledMessageRenders(TestCase):
    """Guards against a bundled message whose conversion nothing can format.

    `Match._soft_magic_message` formats a matched test's message with the value the test read, and
    catches the `ValueError` that a conversion Python does not understand raises, logs it, and
    keeps the message as it stands. So a definition PolyFile cannot render does not fail, or warn
    anyone who is not reading the log: it prints its own format string where the value belongs, and
    only a reader who knows what the output should say will notice.

    That is how `%#16.16llx` survived in seven bundled definitions. This walks all of them so the
    next one cannot.
    """

    maxDiff = None
    """Every offending definition is named, rather than the first few and an ellipsis."""

    def unrenderable(self) -> List[Tuple[str, str]]:
        """Every bundled message spelling that no representative value formats.

        Returns:
            Pairs of source location and message, one per spelling that nothing renders.
        """
        failures: List[Tuple[str, str]] = []
        for test in every_test(MagicMatcher.DEFAULT_INSTANCE):
            message = getattr(test, "message", None)
            if message is None:
                continue
            # `possibilities` yields both arms of a ternary, so neither hides behind the other
            for spelling in message.possibilities():
                candidate = spelling.lstrip()
                # `_soft_magic_message` strips a leading backspace and skips a message with no
                # conversion, and `%%` is an escaped percent rather than one
                candidate = candidate[1:] if candidate.startswith("\b") else candidate
                if "%" not in candidate.replace("%%", ""):
                    continue
                rendered = printf_to_python(candidate)
                if not any(renders(rendered, value) for value in RENDER_VALUES):
                    failures.append((str(test.source_info), candidate))
        return failures

    def test_every_message_with_a_conversion_renders_some_value(self):
        failures = self.unrenderable()
        self.assertEqual([], failures, (
            f"{len(failures)} bundled message(s) carry a conversion that no value formats, so each "
            f"one prints its own format string where the value belongs. Either the conversion needs "
            f"handling in `printf_to_python`, or the definition is wrong."
        ))

    def test_the_walk_reaches_the_messages_it_is_meant_to_check(self):
        """A walk that silently reached nothing would pass the gate above forever."""
        with_conversion = [
            spelling
            for test in every_test(MagicMatcher.DEFAULT_INSTANCE)
            if getattr(test, "message", None) is not None
            for spelling in test.message.possibilities()
            if "%" in spelling.replace("%%", "")
        ]
        self.assertGreater(len(with_conversion), 3000)
