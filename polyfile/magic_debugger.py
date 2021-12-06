from abc import ABC, abstractmethod
from enum import Enum
import sys
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from .logger import getStatusLogger
from .magic import MagicTest, TestResult, TEST_TYPES


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
        BREAKPOINT_TYPES.append(cls)

    @abstractmethod
    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ) -> bool:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def usage(cls) -> str:
        raise NotImplementedError()

    @abstractmethod
    def __str__(self):
        raise NotImplementedError()


class MimeBreakpoint(Breakpoint):
    def __init__(self, mimetype: str):
        self.mimetype: str = mimetype

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ) -> bool:
        return self.mimetype in test.mimetypes()

    @classmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        if command.lower().startswith("mime:"):
            return MimeBreakpoint(command[len("mime:"):])
        return None

    @classmethod
    def usage(cls) -> str:
        return "`b MIME:MIMETYPE` to break when a test is capable of matching that mimetype. For example, " \
               "\"b MIME:application/pdf\"."

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
            parent_match: Optional[TestResult]
    ) -> bool:
        return self.ext in test.all_extensions()

    @classmethod
    def parse(cls: Type[B], command: str) -> Optional[B]:
        if command.lower().startswith("ext:"):
            return ExtensionBreakpoint(command[len("ext:"):])
        return None

    @classmethod
    def usage(cls) -> str:
        return "`b EXT:EXTENSION` to break when a test is capable of matching that extension. For example, " \
               "\"b EXT:pdf\"."

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
            parent_match: Optional[TestResult]
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
    def usage(cls) -> str:
        return "`b FILENAME:LINE_NO` to break when the line of the given magic file is reached. For example, " \
               "\"b archive:525\"."

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
        if self.original_test is not None and self.test.test is self:
            # we are still assigned to the test function, so reset it
            self.test.test = self.original_test
        self.original_test = None


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


class Debugger:
    def __init__(self):
        self.instrumented_tests: List[InstrumentedTest] = []
        self.breakpoints: List[Breakpoint] = []
        self._entries: int = 0
        self.single_stepping: bool = True
        self.last_command: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return any(t.enabled for t in self.instrumented_tests)

    @enabled.setter
    def enabled(self, is_enabled: bool):
        # Uninstrument any existing instrumentation:
        for t in self.instrumented_tests:
            t.uninstrument()
        self.instrumented_tests = []
        if is_enabled:
            # Instrument all of the MagicTest.test functions:
            for test in TEST_TYPES:
                if "test" in test.__dict__:
                    # this class actually implements the test() function
                    self.instrumented_tests.append(InstrumentedTest(test, self))

    def __enter__(self) -> "Debugger":
        self._entries += 1
        if self._entries == 1:
            self.enabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._entries -= 1
        if self._entries == 0:
            self.enabled = False

    def should_break(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ) -> bool:
        return self.single_stepping or any(
            b.should_break(test, data, absolute_offset, parent_match) for b in self.breakpoints
        )

    def write_test(self, test: MagicTest):
        if test.source_info is not None and test.source_info.original_line is not None:
            self.write(f"{test.source_info.path.name}:{test.source_info.line} ", dim=True)
            self.write(test.source_info.original_line.strip(), color=ANSIColor.BLUE)
        else:
            self.write(f"{'>' * test.level}{test.offset!s}\t")
            self.write(test.message, color=ANSIColor.BLUE)
        if test.mime is not None:
            self.write("\n!:mime\t", dim=True)
            self.write(test.mime, color=ANSIColor.BLUE)
        for e in test.extensions:
            self.write("\n!:ext\t", dim=True)
            self.write(str(e), color=ANSIColor.BLUE)

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

    def print_context(self, data: bytes, offset: int, context_bytes: int = 32):
        bytes_before = min(offset, context_bytes)
        context_before = string_escape(data[:bytes_before])
        if 0 <= offset < len(data):
            current_byte = string_escape(data[offset])
        else:
            current_byte = ""
        context_after = string_escape(data[offset + 1:offset + context_bytes])
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
        if self.should_break(test, data, absolute_offset, parent_match):
            self.repl(test, data, absolute_offset, parent_match)
        if instrumented_test.original_test is None:
            result = instrumented_test.test.test(test, data, absolute_offset, parent_match)
        else:
            result = instrumented_test.original_test(test, data, absolute_offset, parent_match)
        if self.single_stepping:
            if result is None:
                self.write("Test failed.\n\n", color=ANSIColor.RED)
            else:
                self.write("Test succeeded.\n\n", color=ANSIColor.GREEN)
        return result

    def repl(
            self,
            test: MagicTest,
            data: bytes,
            absolute_offset: int,
            parent_match: Optional[TestResult]
    ):
        log.clear_status()
        for b in self.breakpoints:
            if b.should_break(test, data, absolute_offset, parent_match):
                self.write(b, color=ANSIColor.MAGENTA)
                self.write("\n")
        self.write(test)
        self.write("\n\n")
        self.print_context(data, absolute_offset)
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
                print("TODO: Usage")
            elif "continue".startswith(command) or "run".startswith(command):
                self.single_stepping = False
                self.last_command = command
                return
            elif "step".startswith(command) or "next".startswith(command):
                self.single_stepping = True
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
            elif "breakpoint".startswith(command):
                if args:
                    for b_type in BREAKPOINT_TYPES:
                        parsed = b_type.parse(args)
                        if parsed is not None:
                            self.write(parsed, color=ANSIColor.MAGENTA)
                            self.write("\n")
                            self.breakpoints.append(parsed)
                            break
                    else:
                        self.write("Error: Invalid breakpoint pattern\n", color=ANSIColor.RED)
                else:
                    if self.breakpoints:
                        for i, b in enumerate(self.breakpoints):
                            self.write(f"{i}:\t", dim=True)
                            self.write(b, color=ANSIColor.MAGENTA)
                            self.write("\n")
                    else:
                        self.write("No breakpoints set.\n", color=ANSIColor.RED)
                        for b_type in BREAKPOINT_TYPES:
                            self.write(b_type.usage())
                            self.write("\n")
            elif "where".startswith(command) or "info stack".startswith(command) or "backtrace".startswith(command):
                test_stack = [test]
                while test_stack[-1].parent is not None:
                    test_stack.append(test_stack[-1].parent)
                for i, t in enumerate(reversed(test_stack)):
                    cmd = str(t).replace("\n", "\n  ")
                    if i == len(test_stack) - 1:
                        print(f"> {cmd}")
                    else:
                        print(f"  {cmd}")
                test_stack = list(reversed(test.children))
                descendants = []
                while test_stack:
                    descendant = test_stack.pop()
                    if descendant.can_match_mime:
                        descendants.append(descendant)
                        test_stack.extend(reversed(descendant.children))
                for t in descendants:
                    cmd = str(t).replace("\n", "\n  ")
                    print(f"  {cmd}")
                print("")
                self.print_context(data, absolute_offset)
            else:
                self.write(f"Undefined command: {command!r}. Try \"help\".\n", color=ANSIColor.RED)
                self.last_command = None
                continue
            self.last_command = command
