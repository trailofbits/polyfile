from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from pdb import Pdb
import sys
from typing import Any, Callable, ContextManager, Iterator, List, Optional, Type, TypeVar, Union

from .polyfile import __copyright__, __license__, __version__, CUSTOM_MATCHERS, Match, Submatch
from .logger import getStatusLogger
from .magic import (
    AbsoluteOffset, FailedTest, InvalidOffsetError, MagicMatcher, MagicTest, Offset, TestResult, TEST_TYPES
)
from .wildcards import Wildcard


log = getStatusLogger("polyfile")


class ANSIColor(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    def to_code(self) -> str:
        return f"\u001b[{self.value}m"


B = TypeVar("B", bound="Breakpoint")


BREAKPOINT_TYPES: List[Type["Breakpoint"]] = []


class Breakpoint(ABC):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ not in ("FailedBreakpoint", "MatchedBreakpoint"):
            BREAKPOINT_TYPES.append(cls)

    @abstractmethod
    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: Optional[TestResult]
    ) -> bool:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        raise NotImplementedError()

    @staticmethod
    def from_str(command: str) -> Optional["Breakpoint"]:
        if command.startswith("!"):
            return FailedBreakpoint.parse(command)
        elif command.startswith("="):
            return MatchedBreakpoint.parse(command)
        for b_type in BREAKPOINT_TYPES:
            parsed = b_type.parse(command)
            if parsed is not None:
                return parsed
        return None

    @classmethod
    @abstractmethod
    def print_usage(cls, debugger: "Debugger"):
        raise NotImplementedError()

    @abstractmethod
    def __str__(self):
        raise NotImplementedError()


class FailedBreakpoint(Breakpoint):
    def __init__(self, parent: Breakpoint):
        self.parent: Breakpoint = parent

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: Optional[TestResult]
    ) -> bool:
        return (result is None or isinstance(result, FailedTest)) and self.parent.should_break(
            test, data, absolute_offset, parent_match, result
        )

    @classmethod
    def parse(cls: B, command: str) -> Optional[B]:
        if not command.startswith("!"):
            return None
        parent = Breakpoint.from_str(command[1:])
        if parent is not None:
            return FailedBreakpoint(parent)
        else:
            return None

    @classmethod
    def print_usage(cls, debugger: "Debugger"):
        pass

    def __str__(self):
        return f"[FAILED] {self.parent!s}"


class MatchedBreakpoint(Breakpoint):
    def __init__(self, parent: Breakpoint):
        self.parent: Breakpoint = parent

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: Optional[TestResult]
    ) -> bool:
        return result is not None and not isinstance(result, FailedTest) and self.parent.should_break(
            test, data, absolute_offset, parent_match, result
        )

    @classmethod
    def parse(cls: B, command: str) -> Optional[B]:
        if not command.startswith("="):
            return None
        parent = Breakpoint.from_str(command[1:])
        if parent is not None:
            return MatchedBreakpoint(parent)
        else:
            return None

    @classmethod
    def print_usage(cls, debugger: "Debugger"):
        pass

    def __str__(self):
        return f"[MATCHED] {self.parent!s}"


class MimeBreakpoint(Breakpoint):
    def __init__(self, mimetype: str):
        self.mimetype: str = mimetype
        self.pattern: Wildcard = Wildcard.parse(mimetype)

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: Optional[TestResult]
    ) -> bool:
        return self.pattern.is_contained_in(test.mimetypes())

    @classmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        if command.lower().startswith("mime:"):
            return MimeBreakpoint(command[len("mime:"):])
        return None

    @classmethod
    def print_usage(cls, debugger: "Debugger"):
        debugger.write("b MIME:MIMETYPE", color=ANSIColor.MAGENTA)
        debugger.write(" to break when a test is capable of matching that mimetype.\nThe ")
        debugger.write("MIMETYPE", color=ANSIColor.MAGENTA)
        debugger.write(" can include the ")
        debugger.write("*", color=ANSIColor.MAGENTA)
        debugger.write(" and ")
        debugger.write("?", color=ANSIColor.MAGENTA)
        debugger.write(" wildcards.\nFor example:\n")
        debugger.write("    b MIME:application/pdf\n    b MIME:*pdf\n", color=ANSIColor.MAGENTA)

    def __str__(self):
        return f"Breakpoint: Matching for MIME {self.mimetype}"


class ExtensionBreakpoint(Breakpoint):
    def __init__(self, ext: str):
        self.ext: str = ext

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: Optional[TestResult]
    ) -> bool:
        return self.ext in test.all_extensions()

    @classmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        if command.lower().startswith("ext:"):
            return ExtensionBreakpoint(command[len("ext:"):])
        return None

    @classmethod
    def print_usage(cls, debugger: "Debugger") -> str:
        debugger.write("b EXT:EXTENSION", color=ANSIColor.MAGENTA)
        debugger.write(" to break when a test is capable of matching that extension.\nFor example:\n")
        debugger.write("    b EXT:pdf\n", color=ANSIColor.MAGENTA)

    def __str__(self):
        return f"Breakpoint: Matching for extension {self.ext}"


class FileBreakpoint(Breakpoint):
    def __init__(self, filename: str, line: int):
        self.filename: str = filename
        self.line: int = line

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult],
            result: TestResult
    ) -> bool:
        if test.source_info is None or test.source_info.line != self.line:
            return False
        if "/" in self.filename:
            # it is a file path
            return str(test.source_info.path) == self.filename
        else:
            # treat it like a filename
            return test.source_info.path.name == self.filename

    @classmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        filename, *remainder = command.split(":")
        if not remainder:
            return None
        try:
            line = int("".join(remainder))
        except ValueError:
            return None
        if line <= 0:
            return None
        return FileBreakpoint(filename, line)

    @classmethod
    def print_usage(cls, debugger: "Debugger"):
        debugger.write("b FILENAME:LINE_NO", color=ANSIColor.MAGENTA)
        debugger.write(" to break when the line of the given magic file is reached.\nFor example:\n")
        debugger.write("    b archive:525\n", color=ANSIColor.MAGENTA)
        debugger.write("will break on the test at line 525 of the archive DSL file.\n")

    def __str__(self):
        return f"Breakpoint: {self.filename} line {self.line}"


class InstrumentedTest:
    def __init__(self, test: Type[MagicTest], debugger: "Debugger"):
        self.test: Type[MagicTest] = test
        self.debugger: Debugger = debugger
        if "test" in test.__dict__:
            self.original_test: Optional[Callable[[...], Optional[TestResult]]] = test.test

            def wrapper(test_instance, *args, **kwargs) -> Optional[TestResult]:
                # if self.original_test is None:
                #     # this is a NOOP
                #     return self.test.test(test_instance, *args, **kwargs)
                return self.debugger.debug(self, test_instance, *args, **kwargs)

            test.test = wrapper
        else:
            self.original_test = None

    @property
    def enabled(self) -> bool:
        return self.original_test is not None

    def uninstrument(self):
        if self.original_test is not None:
            # we are still assigned to the test function, so reset it
            self.test.test = self.original_test
        self.original_test = None


class InstrumentedMatch:
    def __init__(self, match: Type[Match], debugger: "Debugger"):
        self.match: Type[Match] = match
        self.debugger: Debugger = debugger
        if hasattr(match, "submatch"):
            self.original_submatch: Optional[Callable[..., Iterator[Submatch]]] = match.submatch

            def wrapper(match_instance, *args, **kwargs) -> Iterator[Submatch]:
                yield from self.debugger.debug_submatch(self, match_instance, *args, **kwargs)

            match.submatch = wrapper
        else:
            self.original_submatch = None

    @property
    def enalbed(self) -> bool:
        return self.original_submatch is not None

    def uninstrument(self):
        if self.original_submatch is not None:
            self.match.submatch = self.original_submatch
        self.original_submatch = None


def string_escape(data: Union[bytes, int]) -> str:
    if not isinstance(data, int):
        return "".join(string_escape(d) for d in data)
    elif data == ord('\n'):
        return "\\n"
    elif data == ord('\t'):
        return "\\t"
    elif data == ord('\r'):
        return "\\r"
    elif data == 0:
        return "\\0"
    elif data == ord('\\'):
        return "\\\\"
    elif 32 <= data <= 126:
        return chr(data)
    else:
        return f"\\x{data:02X}"


class StepMode(Enum):
    RUNNING = 0
    SINGLE_STEPPING = 1
    NEXT = 2


class Debugger(ContextManager["Debugger"]):
    def __init__(self, break_on_submatching: bool = True):
        self.instrumented_tests: List[InstrumentedTest] = []
        self.breakpoints: List[Breakpoint] = []
        self._entries: int = 0
        self.step_mode: StepMode = StepMode.RUNNING
        self.last_command: Optional[str] = None
        self.last_test: Optional[MagicTest] = None
        self.last_parent_match: Optional[MagicTest] = None
        self.data: bytes = b""
        self.last_offset: int = 0
        self.last_result: Optional[TestResult] = None
        self.repl_test: Optional[MagicTest] = None
        self.instrumented_matches: List[InstrumentedMatch] = []
        self.break_on_submatching: bool = break_on_submatching
        self._pdb: Optional[Pdb] = None

    def save_context(self):
        class DebugContext:
            def __init__(self, debugger: Debugger):
                self.debugger: Debugger = debugger
                self.__saved_state = {}

            def __enter__(self) -> Debugger:
                self.__saved_state = dict(self.debugger.__dict__)
                return self.debugger

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.debugger.__dict__ = self.__saved_state

        return DebugContext(self)

    @property
    def enabled(self) -> bool:
        return any(t.enabled for t in self.instrumented_tests)

    @enabled.setter
    def enabled(self, is_enabled: bool):
        # Uninstrument any existing instrumentation:
        for t in self.instrumented_tests:
            t.uninstrument()
        self.instrumented_tests = []
        for m in self.instrumented_matches:
            m.uninstrument()
        self.instrumented_matches = []
        if is_enabled:
            # Instrument all of the MagicTest.test functions:
            for test in TEST_TYPES:
                if "test" in test.__dict__:
                    # this class actually implements the test() function
                    self.instrumented_tests.append(InstrumentedTest(test, self))
            if self.break_on_submatching:
                for match in CUSTOM_MATCHERS.values():
                    if hasattr(match, "submatch"):
                        self.instrumented_matches.append(InstrumentedMatch(match, self))
            self.write(f"PolyFile {__version__}\n", color=ANSIColor.MAGENTA, bold=True)
            self.write(f"{__copyright__}\n{__license__}\n\nFor help, type \"help\".\n")
            self.repl()

    def __enter__(self) -> "Debugger":
        self._entries += 1
        if self._entries == 1:
            self.enabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._entries -= 1
        if self._entries == 0:
            self.enabled = False

    def should_break(self) -> bool:
        return self.step_mode == StepMode.SINGLE_STEPPING or (
            self.step_mode == StepMode.NEXT and self.last_result
        ) or any(
            b.should_break(self.last_test, self.data, self.last_offset, self.last_parent_match, self.last_result)
            for b in self.breakpoints
        )

    def write_test(self, test: MagicTest, is_current_test: bool = False):
        for comment in test.comments:
            if comment.source_info is not None and comment.source_info.original_line is not None:
                self.write(f"  {comment.source_info.path.name}", dim=True, color=ANSIColor.CYAN)
                self.write(":", dim=True)
                self.write(f"{comment.source_info.line}\t", dim=True, color=ANSIColor.CYAN)
                self.write(comment.source_info.original_line.strip(), dim=True)
                self.write("\n")
            else:
                self.write(f"  # {comment!s}\n", dim=True)
        if is_current_test:
            self.write("→ ", bold=True)
        else:
            self.write("  ")
        if test.source_info is not None and test.source_info.original_line is not None:
            source_prefix = f"{test.source_info.path.name}:{test.source_info.line}"
            indent = f"{' ' * len(source_prefix)}\t"
            self.write(test.source_info.path.name, dim=True, color=ANSIColor.CYAN)
            self.write(":", dim=True)
            self.write(test.source_info.line, dim=True, color=ANSIColor.CYAN)
            self.write("\t")
            self.write(test.source_info.original_line.strip(), color=ANSIColor.BLUE, bold=True)
        else:
            indent = ""
            self.write(f"{'>' * test.level}{test.offset!s}\t")
            self.write(test.message, color=ANSIColor.BLUE, bold=True)
        if test.mime is not None:
            self.write(f"\n  {indent}!:mime ", dim=True)
            self.write(test.mime, color=ANSIColor.BLUE)
        for e in test.extensions:
            self.write(f"\n  {indent}!:ext  ", dim=True)
            self.write(str(e), color=ANSIColor.BLUE)
        self.write("\n")

    def write(self, message: Any, bold: bool = False, dim: bool = False, color: Optional[ANSIColor] = None):
        if sys.stdout.isatty():
            if isinstance(message, MagicTest):
                self.write_test(message)
                return
            prefixes: List[str] = []
            if bold and not dim:
                prefixes.append("\u001b[1m")
            elif dim and not bold:
                prefixes.append("\u001b[2m")
            if color is not None:
                prefixes.append(color.to_code())
            if prefixes:
                sys.stdout.write(f"{''.join(prefixes)}{message!s}\u001b[0m")
                return
        sys.stdout.write(str(message))

    def prompt(self, message: str, default: bool = True) -> bool:
        while True:
            self.write(f"{message} ", bold=True)
            self.write("[", dim=True)
            if default:
                self.write("Y", bold=True, color=ANSIColor.GREEN)
                self.write("n", dim=True, color=ANSIColor.RED)
            else:
                self.write("y", dim=True, color=ANSIColor.GREEN)
                self.write("N", bold=True, color=ANSIColor.RED)
            self.write("] ", dim=True)
            answer = input().strip().lower()
            if not answer:
                return default
            elif answer == "n":
                return False
            elif answer == "y":
                return True

    def print_context(self, data: bytes, offset: int, context_bytes: int = 32, num_bytes: int = 1):
        bytes_before = min(offset, context_bytes)
        context_before = string_escape(data[offset - bytes_before:offset])
        current_byte = string_escape(data[offset:offset+num_bytes])
        context_after = string_escape(data[offset + num_bytes:offset + num_bytes + context_bytes])
        self.write(context_before)
        self.write(current_byte, bold=True)
        self.write(context_after)
        self.write("\n")
        self.write(f"{' ' * len(context_before)}")
        self.write(f"{'^' * len(current_byte)}", bold=True)
        self.write(f"{' ' * len(context_after)}\n")

    def debug(
            self,
            instrumented_test: InstrumentedTest,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ) -> Optional[TestResult]:
        if instrumented_test.original_test is None:
            result = instrumented_test.test.test(test, data, absolute_offset, parent_match)
        else:
            result = instrumented_test.original_test(test, data, absolute_offset, parent_match)
        if self.repl_test is test:
            # this is a one-off test run from the REPL, so do not save its results
            return result
        self.last_result = result
        self.last_test = test
        self.data = data
        self.last_offset = absolute_offset
        self.last_parent_match = parent_match
        if self.should_break():
            self.repl()
        return self.last_result

    def print_where(
            self,
            test: Optional[MagicTest] = None,
            offset: Optional[int] = None,
            parent_match: Optional[TestResult] = None,
            result: Optional[TestResult] = None
    ):
        if test is None:
            test = self.last_test
        if test is None:
            self.write("The first test has not yet been run.\n", color=ANSIColor.RED)
            self.write("Use `step`, `next`, or `run` to start testing.\n")
            return
        if offset is None:
            offset = self.last_offset
        if parent_match is None:
            parent_match = self.last_parent_match
        if result is None:
            result = self.last_result
        wrote_breakpoints = False
        for b in self.breakpoints:
            if b.should_break(test, self.data, offset, parent_match, result):
                self.write(b, color=ANSIColor.MAGENTA)
                self.write("\n")
                wrote_breakpoints = True
        if wrote_breakpoints:
            self.write("\n")
        test_stack = [test]
        while test_stack[-1].parent is not None:
            test_stack.append(test_stack[-1].parent)
        for i, t in enumerate(reversed(test_stack)):
            if i == len(test_stack) - 1:
                self.write_test(t, is_current_test=True)
            else:
                self.write_test(t)
        test_stack = list(reversed(test.children))
        descendants = []
        while test_stack:
            descendant = test_stack.pop()
            if descendant.can_match_mime:
                descendants.append(descendant)
                test_stack.extend(reversed(descendant.children))
        for t in descendants:
            self.write_test(t)
        self.write("\n")
        data_offset = offset
        if not isinstance(test.offset, AbsoluteOffset):
            try:
                data_offset = test.offset.to_absolute(self.data, parent_match)
                self.write(str(test.offset), color=ANSIColor.BLUE)
                self.write(" = byte offset ", dim=True)
                self.write(f"{data_offset!s}\n", bold=True)
            except InvalidOffsetError as e:
                self.write(f"{e!s}\n", color=ANSIColor.RED)
        if result is not None and hasattr(result, "length"):
            context_bytes = result.length
        else:
            context_bytes = 1
        self.print_context(self.data, data_offset, num_bytes=context_bytes)
        if result is not None:
            if not result:
                self.write("Test failed.\n", color=ANSIColor.RED)
                if isinstance(result, FailedTest):
                    self.write(result.message)
                    self.write("\n")
            else:
                self.write("Test succeeded.\n", color=ANSIColor.GREEN)

    def print_match(self, match: Match):
        obj = match.to_obj()
        self.write("{\n", bold=True)
        for key, value in obj.items():
            if isinstance(value, list):
                # TODO: Maybe implement list printing later.
                #       I don't think there will be lists here currently, thouh.
                continue
            self.write(f"  {key!r}", color=ANSIColor.BLUE)
            self.write(": ", bold=True)
            if isinstance(value, int) or isinstance(value, float):
                self.write(str(value))
            else:
                self.write(repr(value), color=ANSIColor.GREEN)
            self.write(",\n", bold=True)
        self.write("}\n", bold=True)

    def debug_submatch(self, instrumented_match: InstrumentedMatch, match: Match, file_stream) -> Iterator[Submatch]:
        log.clear_status()

        if instrumented_match.original_submatch is None:
            submatch = instrumented_match.match.submatch
        else:
            submatch = instrumented_match.original_submatch

        def print_location():
            self.write(f"{file_stream.name}", dim=True, color=ANSIColor.CYAN)
            self.write(":", dim=True)
            self.write(f"{file_stream.tell()} ", dim=True, color=ANSIColor.CYAN)

        if self._pdb is not None:
            # We are already debugging!
            print_location()
            self.write(f"Parsing for submatches using {instrumented_match.match.__name__}.\n")
            yield from submatch(match, file_stream)
            return
        self.print_match(match)
        print_location()
        self.write(f"About to parse for submatches using {instrumented_match.match.__name__}.\n")
        if not self.prompt("Debug using PDB?", default=False):
            yield from submatch(match, file_stream)
            return
        try:
            self._pdb = Pdb(skip=["polyfile.magic_debugger", "polyfile.magic"])
            self._pdb.prompt = "\u001b[1m(polyfile-Pdb)\u001b[0m "
            generator = submatch(match, file_stream)
            while True:
                try:
                    result = self._pdb.runcall(next, generator)
                    self.write(f"Got a submatch:\n", dim=True)
                    self.print_match(result)
                    yield result
                except StopIteration:
                    self.write(f"Yielded all submatches from {match.__class__.__name__} at offset {match.offset}.\n")
                    break
                print_location()
                if not self.prompt("Continue debugging the next submatch?", default=True):
                    if self.prompt("Print the remaining submatches?", default=False):
                        for result in generator:
                            self.print_match(result)
                            yield result
                    else:
                        yield from generator
                    break
        finally:
            self._pdb = None

    def repl(self):
        log.clear_status()
        if self.last_test is not None:
            self.print_where()
        while True:
            try:
                self.write("(polyfile) ", bold=True)
                sys.stdout.flush()
                command = input()
            except EOFError:
                # the user pressed ^D to quit
                exit(0)
            if not command:
                if self.last_command is None:
                    continue
                command = self.last_command
            command = command.lstrip()
            space_index = command.find(" ")
            if space_index > 0:
                command, args = command[:space_index], command[space_index+1:].strip()
            else:
                args = ""
            if "help".startswith(command):
                usage = [
                    ("help", "print this message"),
                    ("continue", "continue execution until the next breakpoint is hit"),
                    ("step", "step through a single magic test"),
                    ("next", "continue execution until the next test that matches"),
                    ("where", "print the context of the current magic test"),
                    ("test", "test the following libmagic DSL test at the current position"),
                    ("print", "print the computed absolute offset of the following libmagic DSL offset"),
                    ("breakpoint", "list the current breakpoints or add a new one"),
                    ("delete", "delete a breakpoint"),
                    ("quit", "exit the debugger"),
                ]
                aliases = {
                    "where": ("info stack", "backtrace")
                }
                left_col_width = max(len(u[0]) for u in usage)
                left_col_width = max(left_col_width, max(len(c) for a in aliases.values() for c in a))
                left_col_width += 3
                for command, msg in usage:
                    self.write(command, bold=True, color=ANSIColor.BLUE)
                    self.write(f" {'.' * (left_col_width - len(command) - 2)} ")
                    self.write(msg)
                    if command in aliases:
                        self.write(" (aliases: ", dim=True)
                        alternatives = aliases[command]
                        for i, alt in enumerate(alternatives):
                            if i > 0 and len(alternatives) > 2:
                                self.write(", ", dim=True)
                            if i == len(alternatives) - 1 and len(alternatives) > 1:
                                self.write(" and ", dim=True)
                            self.write(alt, bold=True, color=ANSIColor.BLUE)
                        self.write(")", dim=True)
                    self.write("\n")

            elif "continue".startswith(command) or "run".startswith(command):
                self.step_mode = StepMode.RUNNING
                self.last_command = command
                return
            elif "step".startswith(command):
                self.step_mode = StepMode.SINGLE_STEPPING
                self.last_command = command
                return
            elif "next".startswith(command):
                self.step_mode = StepMode.NEXT
                self.last_command = command
                return
            elif "quit".startswith(command):
                exit(0)
            elif "delete".startswith(command):
                if args:
                    try:
                        breakpoint_num = int(args)
                    except ValueError:
                        breakpoint_num = -1
                    if not (0 <= breakpoint_num < len(self.breakpoints)):
                        print(f"Error: Invalid breakpoint \"{args}\"")
                        continue
                    b = self.breakpoints[breakpoint_num]
                    self.breakpoints = self.breakpoints[:breakpoint_num] + self.breakpoints[breakpoint_num + 1:]
                    self.write(f"Deleted {b!s}\n")
            elif "test".startswith(command):
                if args:
                    if self.last_test is None:
                        self.write("The first test has not yet been run.\n", color=ANSIColor.RED)
                        self.write("Use `step`, `next`, or `run` to start testing.\n")
                        continue
                    try:
                        test = MagicMatcher.parse_test(args, Path("STDIN"), 1, parent=self.last_test)
                        if test is None:
                            self.write("Error parsing test\n", color=ANSIColor.RED)
                            continue
                        try:
                            with self.save_context():
                                self.repl_test = test
                                if test.parent is None:
                                    self.last_result = None
                                    self.last_offset = 0
                                result = test.test(self.data, self.last_offset, parent_match=self.last_result)
                        finally:
                            if test.parent is not None:
                                test.parent.children.remove(test)
                        self.print_where(
                           test=test, offset=self.last_offset, parent_match=self.last_result, result=result
                        )
                    except ValueError as e:
                        self.write(f"{e!s}\n", color=ANSIColor.RED)
                else:
                    self.write("Usage: ", dim=True)
                    self.write("test", bold=True, color=ANSIColor.BLUE)
                    self.write(" LIBMAGIC DSL TEST\n", bold=True)
                    self.write("Attempt to run the given test.\n\nExample:\n")
                    self.write("test", bold=True, color=ANSIColor.BLUE)
                    self.write(" 0 search \\x50\\x4b\\x05\\x06 ZIP EOCD record\n", bold=True)
            elif "breakpoint".startswith(command):
                if args:
                    parsed = Breakpoint.from_str(args)
                    if parsed is None:
                        self.write("Error: Invalid breakpoint pattern\n", color=ANSIColor.RED)
                    else:
                        self.write(parsed, color=ANSIColor.MAGENTA)
                        self.write("\n")
                        self.breakpoints.append(parsed)
                else:
                    if self.breakpoints:
                        for i, b in enumerate(self.breakpoints):
                            self.write(f"{i}:\t", dim=True)
                            self.write(b, color=ANSIColor.MAGENTA)
                            self.write("\n")
                    else:
                        self.write("No breakpoints set.\n", color=ANSIColor.RED)
                        for b_type in BREAKPOINT_TYPES:
                            b_type.print_usage(self)
                            self.write("\n")
                        self.write("\nBy default, breakpoints will trigger whenever a matching test is run.\n\n"
                                   "Prepend a breakpoint with ")
                        self.write("!", bold=True)
                        self.write(" to only trigger the breakpoint when the test fails.\nFor Example:\n")
                        self.write("    b !MIME:application/zip\n", color=ANSIColor.MAGENTA)
                        self.write("will only trigger if a test that could match a ZIP file failed.\n\n"
                                   "Prepend a breakpoint with ")
                        self.write("=", bold=True)
                        self.write(" to only trigger the breakpoint when the test passes.\n For example:\n")
                        self.write("    b =archive:1337\n", color=ANSIColor.MAGENTA)
                        self.write("will only trigger if the test on line 1337 of the archive DSL matched.\n\n")

            elif "print".startswith(command):
                if args:
                    if self.last_test is None:
                        self.write("The first test has not yet been run.\n", color=ANSIColor.RED)
                        self.write("Use `step`, `next`, or `run` to start testing.\n")
                        continue
                    try:
                        dsl_offset = Offset.parse(args)
                    except ValueError as e:
                        self.write(f"{e!s}\n", color=ANSIColor.RED)
                        continue
                    try:
                        absolute = dsl_offset.to_absolute(self.data, self.last_result)
                        self.write(f"{absolute}\n", bold=True)
                        self.print_context(self.data, absolute)
                    except InvalidOffsetError as e:
                        self.write(f"{e!s}\n", color=ANSIColor.RED)
                        continue
                else:
                    self.write("Usage: ", dim=True)
                    self.write("print", bold=True, color=ANSIColor.BLUE)
                    self.write(" LIBMAGIC DSL OFFSET\n", bold=True)
                    self.write("Calculate the absolute offset for the given DSL offset.\n\nExample:\n")
                    self.write("print", bold=True, color=ANSIColor.BLUE)
                    self.write(" (&0x7c.l+0x26)\n", bold=True)
            elif "where".startswith(command) or "info stack".startswith(command) or "backtrace".startswith(command):
                self.print_where()
            else:
                self.write(f"Undefined command: {command!r}. Try \"help\".\n", color=ANSIColor.RED)
                self.last_command = None
                continue
            self.last_command = command
