from typing import Optional

from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult


class BFMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-brainfuck",
            extensions=("bf",),
            message="Brainfu** Program"
        )

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        # It is a valid brain-fu program if all of the [ and ] are balanced
        opened = 0
        offset = 0
        commands = set()
        important_commands = frozenset((ord('['), ord(']'), ord('.'), ord('+'), ord('-'), ord('>'), ord('<')))
        first_command = -1
        last_command = -1
        for offset, c in enumerate(data):
            if c in important_commands:
                commands.add(c)
                if first_command < 0:
                    first_command = offset
                last_command = offset
            if c == ord('['):
                opened += 1
            elif c == ord(']'):
                opened -= 1
                if opened < 0:
                    break
        if opened != 0:
            return FailedTest(self, offset=offset, message="unbalanced square brackets")
        elif len(commands) != len(important_commands):
            return FailedTest(self, offset=offset, message="missing commands "
                                                           f"{', '.join(map(chr, important_commands - commands))}")
        else:
            assert 0 <= first_command <= last_command
            return MatchedTest(self, value=data, offset=first_command, length=last_command - first_command)


MagicMatcher.DEFAULT_INSTANCE.add(BFMatcher())
