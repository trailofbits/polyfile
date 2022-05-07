from enum import Enum
from typing import Optional, Sequence

from .logger import StatusLogger
from .polyfile import Match, Submatch, register_parser
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult


log = StatusLogger("polyfile")


class BFCommandType(Enum):
    LOOP_START = "["
    LOOP_END = "]"
    INPUT = ","
    PRINT = "."
    SHIFT_RIGHT = ">"
    SHIFT_LEFT = "<"
    INCREMENT = "+"
    DECREMENT = "-"


class BFCommand:
    def __init__(self, command_type: BFCommandType, offset: int):
        self.command_type: BFCommandType = command_type
        self.offset: int = offset

    def __str__(self):
        return self.command_type.value

    def __repr__(self):
        return f"{self.__class__.__name__}(command_type={self.command_type!r}, offset={self.offset!r})"


class BFParseError(RuntimeError):
    def __init__(self, message: str, offset: int):
        super().__init__(message)
        self.offset: int = offset


class BFProgram:
    def __init__(self, commands: Sequence[BFCommand]):
        self.commands: Sequence[BFCommand] = commands
        self._num_loops: Optional[int] = None

    @property
    def num_loops(self) -> int:
        if self._num_loops is None:
            self._num_loops = sum(1 for c in self.commands if c.command_type == BFCommandType.LOOP_START)
        return self._num_loops

    def __bytes__(self):
        return bytes(bytearray(
            [ord(c.command_type.value) for c in self.commands]
        ))

    @classmethod
    def parse(cls, data: bytes) -> "BFProgram":
        opened = 0
        offset = 0
        commands: List[BFCommand] = []
        for offset, c in enumerate(data):
            try:
                command = BFCommand(BFCommandType(chr(c)), offset)
            except ValueError:
                continue
            commands.append(command)
            if command.command_type == BFCommandType.LOOP_START:
                opened += 1
            elif command.command_type == BFCommandType.LOOP_END:
                if opened == 0:
                    break
                opened -= 1
        if opened != 0:
            raise BFParseError("unbalanced square brackets", offset=offset)
        return BFProgram(tuple(commands))


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
        try:
            program = BFProgram.parse(data[absolute_offset:])
        except BFParseError as e:
            return FailedTest(self, offset=e.offset, message=str(e))
        important_commands = frozenset(BFCommandType) - {BFCommandType.INPUT}
        unique_commands = {c.command_type for c in program.commands}
        if program.commands:
            first_command = program.commands[0].offset
            last_command = program.commands[-1].offset
        else:
            first_command = 0
            last_command = 0
        if important_commands - unique_commands:
            return FailedTest(self, offset=first_command,
                              message=f"missing commands {', '.join(map(chr, important_commands - unique_commands))}")
        elif self.min_bf_loops > program.num_loops:
            return FailedTest(self, offset=first_command, message=f"expected at least {self.min_bf_loops} BrainFu loops "
                                                                  f"but only found {num_loops}")
        elif self.min_bf_commands > len(program.commands):
            return FailedTest(self, offset=first_command, message=f"expected at least {self.min_bf_commands} BrainFu "
                                                                  f"commands but only found {len(program.commands)}")
        else:
            assert 0 <= first_command <= last_command
            return MatchedTest(self, value=bytes(program), offset=first_command,
                               length=last_command - first_command)

            # if self.reject_arithmetical_noops and len(commands) > 1:
            #     if (c == ord('+') and commands[-2] == ord('-')) or \
            #             (c == ord('-') and commands[-2] == ord('+')):
            #         return FailedTest(self, offset=offset, message="BrainFu program contains arithmetic that cancels "
            #                                                        "itself out")

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
