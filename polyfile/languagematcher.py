from typing import Optional

from .logger import StatusLogger
from .polyfile import Match, Submatch, register_parser
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult


log = StatusLogger("polyfile")

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


@register_parser("application/x-brainfuck")
def parse_bf(file_stream, match):
    commands = {
        ord('['): "LoopStart",
        ord(']'): "LoopEnd",
        ord('.'): "Print",
        ord('+'): "Increment",
        ord('-'): "Decrement",
        ord('>'): "MoveRight",
        ord('<'): "MoveLeft",
        ord(','): "Input",
    }
    relative_offset = 0
    loop_stack = []

    while True:
        b = file_stream.read(1)
        if len(b) < 1:
            break
        if b[0] in commands:
            if loop_stack:
                parent: Match = loop_stack[-1]
            else:
                parent = match
            if b == b"[":
                loop = Submatch(
                    "Loop",
                    match_obj="",
                    relative_offset=relative_offset,
                    parent=parent,
                    matcher=match.matcher
                )
                yield loop
                loop_stack.append(loop)
                parent = loop
            elif b == b"]":
                if not loop_stack:
                    log.warning(f"Unexpected closing bracket at offset {relative_offset + match.offset}")
                else:
                    loop_stack.pop()
            s = Submatch(
                commands[b[0]],
                match_obj=b,
                relative_offset=relative_offset - (parent.offset - match.offset),
                length=1,
                parent=parent,
                matcher=match.matcher
            )
            yield s
        relative_offset += 1
