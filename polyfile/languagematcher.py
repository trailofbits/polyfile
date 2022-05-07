from typing import Optional

from .logger import StatusLogger
from .polyfile import Match, Submatch, register_parser
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult


log = StatusLogger("polyfile")


class BFMatcher(MagicTest):
    min_bf_commands: int = 24
    """The minimum number of BF commands that must appear for the file to be classified as a BF program

    This is an arbitrary value; the default is high enough to eliminate most false-positives, at the expense of missing
    the detection of shorter BrainFu programs.
    """

    min_bf_loops: int = 2
    """The minimum number of BF loops that must appear for the file to be classified as a BF program

    This is an arbitrary value that we have set high enough to eliminate most false-positives, at the expense of missing
    the detection of simpler BrainFu programs.
    """

    reject_infinite_loops: bool = False
    """If True, then reject any BF program that contains an infinite loop"""

    reject_arithmetical_noops: bool = True
    """If True, then reject any BF program that contains arithmetic that cancels itself

    For example: `-+` or `+-`
    """

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
        commands = bytearray()
        num_loops = 0
        important_commands = frozenset((ord('['), ord(']'), ord('.'), ord('+'), ord('-'), ord('>'), ord('<')))
        first_command = -1
        last_command = -1
        has_infinite_loop = False
        for offset, c in enumerate(data):
            if c in important_commands:
                commands.append(c)
                if first_command < 0:
                    first_command = offset
                last_command = offset
            # if self.reject_arithmetical_noops and len(commands) > 1:
            #     if (c == ord('+') and commands[-2] == ord('-')) or \
            #             (c == ord('-') and commands[-2] == ord('+')):
            #         return FailedTest(self, offset=offset, message="BrainFu program contains arithmetic that cancels "
            #                                                        "itself out")
            if c == ord('['):
                opened += 1
                num_loops += 1
            elif c == ord(']'):
                opened -= 1
                if opened < 0:
                    break
                # TODO: Complete inifnite loop detection
                # elif len(commands) >= 2 and commands[-2] == ord('['):
                #     # there is an infinite loop
                #     if self.reject_infinite_loops:
                #         return FailedTest(self, offset=offset, message="BrainFu program contains an infinite loop, "
                #                                                        "which is not permitted")
                #     else:
                #         # no sense in analyzing any code after an infinite loop
                #         # break
                #         pass
        if opened != 0:
            return FailedTest(self, offset=offset, message="unbalanced square brackets")
        unique_commands = frozenset(commands)
        if len(unique_commands) != len(important_commands):
            return FailedTest(self, offset=offset,
                              message=f"missing commands {', '.join(map(chr, important_commands - unique_commands))}")
        elif self.min_bf_loops > num_loops:
            return FailedTest(self, offset=offset, message=f"expected at least {self.min_bf_loops} BrainFu loops but "
                                                           f"only found {num_loops}")
        elif self.min_bf_commands > len(commands):
            return FailedTest(self, offset=offset, message=f"expected at least {self.min_bf_commands} BrainFu "
                                                           f"commands but only found {len(commands)}")
        else:
            assert 0 <= first_command <= last_command
            return MatchedTest(self, value=bytes(commands), offset=first_command, length=last_command - first_command)


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
