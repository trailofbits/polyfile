from abc import ABC, abstractmethod
import atexit
from enum import Enum
from pathlib import Path
from pdb import Pdb
import sys
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional, Type, TypeVar, Union

from .polyfile import __copyright__, __license__, __version__, PARSERS, Match, Parser, ParserFunction, Submatch
from .magic import (
    AbsoluteOffset, FailedTest, InvalidOffsetError, MagicMatcher, MagicTest, Offset, TestResult, TEST_TYPES
)
from .profiling import Profiler, Unprofiled, unprofiled
from .repl import ANSIColor, ANSIWriter, arg_completer, command, ExitREPL, log, REPL, SetCompleter, string_escape
from .wildcards import Wildcard


B = TypeVar("B", bound="Breakpoint")
T = TypeVar("T")


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


class InstrumentedParser:
    def __init__(self, parser: Parser, debugger: "Debugger"):
        self.parser: Type[Parser] = parser
        self.debugger: Debugger = debugger
        self.original_parser: Optional[ParserFunction] = parser.parse

        def wrapper(parser_instance, *args, **kwargs) -> Iterator[Submatch]:
            yield from self.debugger.debug_parse(self, parser_instance, *args, **kwargs)

        parser.parse = wrapper

    @property
    def enalbed(self) -> bool:
        return self.original_parser is not None

    def uninstrument(self):
        if self.original_parser is not None:
            self.parser.parse = self.original_parser
        self.original_parser = None


class StepMode(Enum):
    RUNNING = 0
    SINGLE_STEPPING = 1
    NEXT = 2


T = TypeVar("T")


class Variable(Generic[T]):
    def __init__(self, possibilities: Iterable[T], value: T):
        self.possibilities: List[T] = list(possibilities)
        self._value: T = value
        self.value = value

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T):
        if new_value not in self.possibilities:
            raise ValueError(f"invalid value {new_value!r}; must be one of {self.possibilities!r}")
        self._value = new_value

    def parse(self, value: str) -> T:
        value = value.strip().lower()
        for p in self.possibilities:
            if str(p).lower() == value:
                return p
        raise ValueError(f"Invalid value {value!r}; must be one of {', '.join(map(str, self.possibilities))}")

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class BooleanVariable(Variable[bool]):
    def __init__(self, value: bool):
        super().__init__((True, False), value)

    def parse(self, value: str) -> T:
        try:
            return super().parse(value)
        except ValueError:
            pass
        value = value.strip().lower()
        if value == "0" or value == "f":
            return False
        return bool(value)

    def __bool__(self):
        return self.value


class BreakOnSubmatching(BooleanVariable):
    def __init__(self, value: bool, debugger: "Debugger"):
        self.debugger: Debugger = debugger
        super().__init__(value)

    @Variable.value.setter
    def value(self, new_value):
        Variable.value.fset(self, new_value)
        if self.debugger.enabled:
            # disable and re-enable the debugger to update the instrumentation
            self.debugger._uninstrument()
            self.debugger._instrument()


class Profile(BooleanVariable):
    def __init__(self, value: bool, debugger: "Debugger"):
        self.debugger: Debugger = debugger
        self._registered_callback = False
        super().__init__(value)

    @Variable.value.setter
    def value(self, new_value):
        Variable.value.fset(self, new_value)
        if new_value and not self._registered_callback:
            self._registered_callback = True
            atexit.register(Debugger.profile_command, self.debugger, "")


class Debugger(REPL):
    def __init__(self, break_on_parsing: bool = True):
        super().__init__(name="the debugger")
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
        self.instrumented_parsers: List[InstrumentedParser] = []
        self.break_on_submatching: BreakOnSubmatching = BreakOnSubmatching(break_on_parsing, self)
        self.profile: Profile = Profile(False, self)
        self.variables_by_name: Dict[str, Variable] = {
            "break_on_parsing": self.break_on_submatching,
            "profile": self.profile
        }
        self.variable_descriptions: Dict[str, str] = {
            "break_on_parsing": "Break when a PolyFile parser is about to be invoked and debug using PDB (default=True;"
                                " disable from the command line with `--no-debug-python`)",
            "profile": "Profile the performance of each magic test that is run (default=False)"
        }
        self.profile_results: Dict[Union[MagicTest, Type[Parser]], float] = {}
        self._pdb: Optional[Pdb] = None
        self._debug_next: bool = False

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

    def _uninstrument(self):
        # Uninstrument any existing instrumentation:
        for t in self.instrumented_tests:
            t.uninstrument()
        self.instrumented_tests = []
        for m in self.instrumented_parsers:
            m.uninstrument()
        self.instrumented_parsers = []

    def _instrument(self):
        # Instrument all of the MagicTest.test functions:
        for test in TEST_TYPES:
            if "test" in test.__dict__:
                # this class actually implements the test() function
                self.instrumented_tests.append(InstrumentedTest(test, self))
        if self.break_on_submatching.value:
            for parsers in PARSERS.values():
                for parser in parsers:
                    self.instrumented_parsers.append(InstrumentedParser(parser, self))

    @enabled.setter
    def enabled(self, is_enabled: bool):
        was_enabled = self.enabled
        self._uninstrument()
        if is_enabled:
            self._instrument()
            self.load_history()
            self.write(f"PolyFile {__version__}\n", color=ANSIColor.MAGENTA, bold=True)
            self.write(f"{__copyright__}\n{__license__}\n\nFor help, type \"help\".\n")
            self.repl()
        elif was_enabled:
            # we are now disabled, so store our history
            self.store_history()

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
        writer = ANSIWriter(use_ansi=sys.stdout.isatty())
        if self.profile.value and test in self.profile_results:
            pre_mime_text = f"\t⏱  {int(self.profile_results[test] + 0.5)}ms"
        else:
            pre_mime_text = ""
        test.write(writer, is_current_test=is_current_test, pre_mime_text=pre_mime_text)
        super().write(str(writer))

    def write(self, message: Any, bold: bool = False, dim: bool = False, color: Optional[ANSIColor] = None):
        if sys.stdout.isatty() and isinstance(message, MagicTest):
            self.write_test(message)
        else:
            super().write(message=message, bold=bold, dim=dim, color=color)

    def print_context(self, data: bytes, offset: int, context_bytes: int = 32, num_bytes: int = 1):
        writer = ANSIWriter(use_ansi=sys.stdout.isatty())
        writer.write_context(data, offset, context_bytes, num_bytes)
        super().write(message=str(writer))

    def _debug(self, func: Callable[[Any], T], *args, **kwargs) -> T:
        if self.profile.value:
            self.write("Warning:", bold=True, color=ANSIColor.RED)
            self.write(" Profiling will be disabled for this test while debugging!\n")
        with Unprofiled():
            # check if there is already a debugger attached, most likely an IDE like PyCharm;
            # if so, use that debugger instead of creating our own instance of pdb
            external_debugger = sys.gettrace() is not None or self._pdb is not None
            if not external_debugger:
                self._pdb = Pdb(skip=["polyfile.magic_debugger", "polyfile.magic"])
                if sys.stderr.isatty():
                    self._pdb.prompt = "\001\u001b[1m\002(polyfile-Pdb)\001\u001b[0m\002 "
                else:
                    self._pdb.prompt = "(polyfile-Pdb) "
                try:
                    result = self._pdb.runcall(func, *args, **kwargs)
                finally:
                    self._pdb = None
            else:
                breakpoint()
                # This next line will invoke the test:
                result = func(*args, **kwargs)
            return result

    def debug(
            self,
            instrumented_test: InstrumentedTest,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ) -> Optional[TestResult]:
        profiler = Profiler()
        if instrumented_test.original_test is None:
            test_func = instrumented_test.test.test
        else:
            test_func = instrumented_test.original_test
        if self._debug_next:
            self._debug_next = False
            result: TestResult = self._debug(test_func, test, data, absolute_offset, parent_match)
        else:
            with profiler:
                result = test_func(test, data, absolute_offset, parent_match)
        if self.profile.value:
            self.profile_results[test] = profiler.elapsed_ms
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

    @unprofiled
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

    def debug_parse(self, instrumented_parser: InstrumentedParser, file_stream, match: Match) -> Iterator[Submatch]:
        log.clear_status()

        if instrumented_parser.original_parser is None:
            parse = instrumented_parser.parser.parse
        else:
            parse = instrumented_parser.original_parser

        def print_location():
            self.write(f"{file_stream.name}", dim=True, color=ANSIColor.CYAN)
            self.write(":", dim=True)
            self.write(f"{file_stream.tell()} ", dim=True, color=ANSIColor.CYAN)

        if self._pdb is not None:
            # We are already debugging!
            print_location()
            self.write(f"Parsing for submatches using {instrumented_parser.parser!s}.\n")
            profiler = Profiler()
            with profiler:
                yield from parse(file_stream, match)
            if self.profile.value:
                self.profile_results[instrumented_parser.parser] = profiler.elapsed_ms
            return
        with Unprofiled():
            self.print_match(match)
            print_location()
            self.write(f"About to parse for submatches using {instrumented_parser.parser!s}.\n")
            buffer = ANSIWriter(use_ansi=sys.stderr.isatty(), escape_for_readline=True)
            buffer.write("Debug using PDB? ")
            buffer.write("(disable this prompt with `", dim=True)
            buffer.write("set ", color=ANSIColor.BLUE)
            buffer.write("break_on_parsing ", color=ANSIColor.GREEN)
            buffer.write("False", color=ANSIColor.CYAN)
            buffer.write("`)", dim=True)
        if not self.prompt(str(buffer), default=False):
            with Profiler() as p:
                yield from parse(file_stream, match)
                if self.profile.value:
                    self.profile_results[instrumented_parser.parser] = p.elapsed_ms
            return
        try:
            if self.profile.value:
                self.write("Warning:", bold=True, color=ANSIColor.RED)
                self.write(" Profiling will be disabled for this parser while debugging!\n")
            with Unprofiled():
                # check if there is already a debugger attached, most likely an IDE like PyCharm;
                # if so, use that debugger instead of creating our own instance of pdb
                external_debugger = sys.gettrace() is not None
                if not external_debugger:
                    self._pdb = Pdb(skip=["polyfile.magic_debugger", "polyfile.magic"])
                    if sys.stderr.isatty():
                        self._pdb.prompt = "\001\u001b[1m\002(polyfile-Pdb)\001\u001b[0m\002 "
                    else:
                        self._pdb.prompt = "(polyfile-Pdb) "
                generator = parse(file_stream, match)
                while True:
                    try:
                        if external_debugger:
                            breakpoint()
                            # This next line will invoke the parser:
                            result = next(generator)
                        else:
                            result = self._pdb.runcall(next, generator)
                        self.write(f"Got a submatch:\n", dim=True)
                        self.print_match(result)
                        yield result
                    except StopIteration:
                        self.write(f"Yielded all submatches from {match.__class__.__name__} at offset {match.offset}."
                                   f"\n")
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

    def before_prompt(self):
        if self.last_test is not None:
            self.print_where()

    @command(name="continue", allows_abbreviation=True, help="continue execution until the next breakpoint is hit",
             aliases=("run",))
    def cont(self, arguments: str):
        self.step_mode = StepMode.RUNNING
        self.last_command = command
        raise ExitREPL()

    @command(allows_abbreviation=True, help="step through a single magic test")
    def step(self, arguments: str):
        self.step_mode = StepMode.SINGLE_STEPPING
        self.last_command = command
        raise ExitREPL()

    @command(allows_abbreviation=False, name="debug_and_rerun", help="re-run the last test and debug in PDB")
    def debug_and_rerun(self, arguments: str):
        self.last_command = command
        if self.last_test is None:
            self.write("Error: A test has not yet been run\n", color=ANSIColor.RED)
            return
        test = self.last_test.__class__.test
        # Is the test instrumented? If so, find the original version!
        for instrumented in self.instrumented_tests:
            if instrumented.test.test is test:
                test = instrumented.original_test
                break
        self._debug(test, self.last_test, self.data, self.last_offset, self.last_parent_match)

    @command(allows_abbreviation=False, name="debug_and_continue", aliases=("debug", "debug_and_cont"),
             help="continue while debugging in PDB")
    def debug_and_continue(self, arguments: str):
        if sys.gettrace() is None and self._pdb is None:
            self.write("Error: ", color=ANSIColor.RED)
            self.write("`", dim=True)
            self.write("debug_and_continue", color=ANSIColor.BLUE)
            self.write("`", dim=True)
            self.write(" can only be called when running from an external debugger like PDB or PyCharm",
                       color=ANSIColor.RED)
            return
        self.step_mode = StepMode.RUNNING
        self.last_command = command
        try:
            raise ExitREPL()
        finally:
            breakpoint()

    @command(allows_abbreviation=False, help="step into the next magic test and debug in PDB")
    def debug_and_step(self, arguments: str):
        self.step_mode = StepMode.SINGLE_STEPPING
        self.last_command = command
        self._debug_next = True
        raise ExitREPL()

    @command(allows_abbreviation=True, help="continue execution until the next test that matches")
    def next(self, arguments: str):
        self.step_mode = StepMode.NEXT
        self.last_command = command
        raise ExitREPL()

    @command(allows_abbreviation=True,
             help="print the context of the current magic test",
             aliases=("info stack", "backtrace"))
    def where(self, arguments: str):
        self.print_where()

    @command(allows_abbreviation=False, name="profile", help="print current profiling results (to enable profiling, "
                                                             "use `set profile True`)", )
    def profile_command(self, arguments: str):
        if not self.profile_results:
            if not self.profile.value:
                self.write("Profiling is disabled.\n", color=ANSIColor.RED)
                self.write("Enable it by running `set profile True`.\n")
            else:
                self.write("No profiling data yet.\n")
            return
        self.write("Profile Results:\n", bold=True)
        tests = sorted([(runtime, test) for test, runtime in self.profile_results.items()], reverse=True,
                       key=lambda x: x[0])
        max_text_width = 0
        for runtime, test in tests:
            if isinstance(test, MagicTest):
                if test.source_info is not None and test.source_info.original_line is not None:
                    max_text_width = max(max_text_width,
                                         len(test.source_info.path.name) + 1 + len(str(test.source_info.line)))
                else:
                    max_text_width = max(max_text_width, test.level + len(str(test.offset)))
            else:
                max_text_width = max(max_text_width, len(str(test)))
        for runtime, test in tests:
            if isinstance(test, MagicTest):
                self.write("🪄 ")
                if test.source_info is not None and test.source_info.original_line is not None:
                    self.write(test.source_info.path.name, dim=True, color=ANSIColor.CYAN)
                    self.write(":", dim=True)
                    self.write(test.source_info.line, dim=True, color=ANSIColor.CYAN)
                    padding = max_text_width - (len(test.source_info.path.name) + 1 + len(str(test.source_info.line)))
                else:
                    self.write(f"{'>' * test.level}{test.offset!s}", color=ANSIColor.BLUE)
                    padding = max_text_width - test.level - len(str(test.offset))
            else:
                self.write("🖥 ")
                self.write(str(test), color=ANSIColor.BLUE)
                padding = max_text_width - len(str(test))
            self.write(" " * padding)
            if runtime >= 1.0:
                self.write(f" ⏱  {int(runtime + 0.5)}ms\n")
            else:
                self.write(f" ⏱  {runtime:.2f}ms\n")

    @command(allows_abbreviation=True, help="test the following libmagic DSL test at the current position")
    def test(self, args: str):
        if args:
            if self.last_test is None:
                self.write("The first test has not yet been run.\n", color=ANSIColor.RED)
                self.write("Use `step`, `next`, or `run` to start testing.\n")
                return
            try:
                test = MagicMatcher.parse_test(args, Path("STDIN"), 1, parent=self.last_test)
                if test is None:
                    self.write("Error parsing test\n", color=ANSIColor.RED)
                    return
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

    @command(allows_abbreviation=True, help="print the computed absolute offset of the following libmagic DSL offset")
    def print(self, args: str):
        if args:
            if self.last_test is None:
                self.write("The first test has not yet been run.\n", color=ANSIColor.RED)
                self.write("Use `step`, `next`, or `run` to start testing.\n")
                return
            try:
                dsl_offset = Offset.parse(args)
            except ValueError as e:
                self.write(f"{e!s}\n", color=ANSIColor.RED)
                return
            try:
                absolute = dsl_offset.to_absolute(self.data, self.last_result)
                self.write(f"{absolute}\n", bold=True)
                self.print_context(self.data, absolute)
            except InvalidOffsetError as e:
                self.write(f"{e!s}\n", color=ANSIColor.RED)
                return
        else:
            self.write("Usage: ", dim=True)
            self.write("print", bold=True, color=ANSIColor.BLUE)
            self.write(" LIBMAGIC DSL OFFSET\n", bold=True)
            self.write("Calculate the absolute offset for the given DSL offset.\n\nExample:\n")
            self.write("print", bold=True, color=ANSIColor.BLUE)
            self.write(" (&0x7c.l+0x26)\n", bold=True)

    @command(allows_abbreviation=True, help="list the current breakpoints or add a new one")
    def breakpoint(self, args: str):
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

    @arg_completer(for_command="delete")
    def delete_completer(self, index: int, arg: str, prev_arguments: Iterable[str]):
        if index == 0:
            return SetCompleter(lambda: map(str, range(len(self.breakpoints))))(arg)
        else:
            return []

    @command(allows_abbreviation=True, help="delete a breakpoint")
    def delete(self, args: str):
        if args:
            try:
                breakpoint_num = int(args)
            except ValueError:
                breakpoint_num = -1
            if not (0 <= breakpoint_num < len(self.breakpoints)):
                print(f"Error: Invalid breakpoint \"{args}\"")
            else:
                b = self.breakpoints[breakpoint_num]
                self.breakpoints = self.breakpoints[:breakpoint_num] + self.breakpoints[breakpoint_num + 1:]
                self.write(f"Deleted {b!s}\n")

    @arg_completer(for_command="set")
    def set_completer(self, index: int, arg: str, prev_arguments: Iterable[str]):
        if index == 0:
            return SetCompleter(lambda: self.variables_by_name.keys())(arg)
        elif index == 1:
            if prev_arguments[-1] in self.variables_by_name:
                var = self.variables_by_name[prev_arguments[-1]]
                return SetCompleter(lambda: map(str, var.possibilities))(arg)
        return []

    @command(help="modifies part of the debugger environment")
    def set(self, arguments: str):
        parsed = arguments.strip().split()
        if len(parsed) == 3 and parsed[1].strip() == "=":
            parsed = [parsed[0], parsed[1]]
        if len(parsed) != 2:
            self.write("Usage: ", dim=True)
            self.write("set", bold=True, color=ANSIColor.BLUE)
            self.write(" VARIABLE ", bold=True, color=ANSIColor.GREEN)
            self.write("VALUE\n\n", bold=True, color=ANSIColor.CYAN)
            self.write("Options:\n\n", bold=True)
            for name, var in self.variables_by_name.items():
                self.write(f"    {name} ", bold=True, color=ANSIColor.GREEN)
                self.write("[", dim=True)
                for i, value in enumerate(var.possibilities):
                    if i > 0:
                        self.write("|", dim=True)
                    self.write(str(value), bold=True, color=ANSIColor.CYAN)
                self.write("]\n    ", dim=True)
                self.write(self.variable_descriptions[name])
                self.write("\n\n")
        elif parsed[0] not in self.variables_by_name:
            self.write("Error: Unknown variable ", bold=True, color=ANSIColor.RED)
            self.write(parsed[0], bold=True)
            self.write("\n")
        else:
            try:
                var = self.variables_by_name[parsed[0]]
                var.value = var.parse(parsed[1])
            except ValueError as e:
                self.write(f"{e!s}\n", bold=True, color=ANSIColor.RED)

    @arg_completer(for_command="show")
    def show_completer(self, index: int, arg: str, prev_arguments: Iterable[str]):
        if index == 0:
            return SetCompleter(lambda: self.variables_by_name.keys())(arg)
        else:
            return []

    @command(help="prints part of the debugger environment")
    def show(self, arguments: str):
        parsed = arguments.strip().split()
        if len(parsed) > 2:
            self.write("Usage: ", dim=True)
            self.write("show", bold=True, color=ANSIColor.BLUE)
            self.write(" VARIABLE\n\n", bold=True, color=ANSIColor.GREEN)
            self.write("Options:\n", bold=True)
            for name, var in self.variables_by_name.items():
                self.write(f"\n    {name}\n    ", bold=True, color=ANSIColor.GREEN)
                self.write(self.variable_descriptions[name])
                self.write("\n")
        elif not parsed:
            for i, (name, var) in enumerate(self.variables_by_name.items()):
                if i > 0:
                    self.write("\n")
                self.write(name, bold=True, color=ANSIColor.GREEN)
                self.write(" = ", dim=True)
                self.write(str(var.value), bold=True, color=ANSIColor.CYAN)
                self.write("\n")
                self.write(self.variable_descriptions[name])
                self.write("\n")
        elif parsed[0] not in self.variables_by_name:
            self.write("Error: Unknown variable ", bold=True, color=ANSIColor.RED)
            self.write(parsed[0], bold=True)
            self.write("\n")
        else:
            self.write(parsed[0], bold=True, color=ANSIColor.GREEN)
            self.write(" = ", dim=True)
            self.write(str(self.variables_by_name[parsed[0]].value), bold=True, color=ANSIColor.CYAN)
            self.write("\n")
            self.write(self.variable_descriptions[parsed[0]])
