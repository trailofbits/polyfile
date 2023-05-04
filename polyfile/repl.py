import atexit
from abc import ABC, abstractmethod
from enum import Enum
from functools import partial, wraps
from io import StringIO
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from .fileutils import make_stream, Streamable
from .profiling import Unprofiled

if os.name == "posix":
    import readline
else:
    import pyreadline3 as readline

from .logger import getStatusLogger

log = getStatusLogger("polyfile")

HISTORY_PATH = Path.home() / ".polyfile_history"

T = TypeVar("T")


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


class ANSIWriter:
    def __init__(self, use_ansi: bool = True, escape_for_readline: bool = False):
        self.use_ansi: bool = use_ansi
        self.escape_for_readline: bool = escape_for_readline
        self.data = StringIO()

    @staticmethod
    def format(
            message: Any, bold: bool = False, dim: bool = False, color: Optional[ANSIColor] = None,
            escape_for_readline: bool = False
    ) -> str:
        prefixes: List[str] = []
        if bold and not dim:
            prefixes.append("\u001b[1m")
        elif dim and not bold:
            prefixes.append("\u001b[2m")
        if color is not None:
            prefixes.append(color.to_code())
        if prefixes:
            if escape_for_readline:
                message = f"\001{''.join(prefixes)}\002{message!s}\001\u001b[0m\002"
            else:
                message = f"{''.join(prefixes)}{message!s}\u001b[0m"
        else:
            message = str(message)
        return message

    def write(self, message: Any, bold: bool = False, dim: bool = False, color: Optional[ANSIColor] = None,
              escape_for_readline: Optional[bool] = None) -> str:
        if self.use_ansi:
            if escape_for_readline is None:
                escape_for_readline = self.escape_for_readline
            self.data.write(self.format(message=message, bold=bold, dim=dim, color=color,
                                        escape_for_readline=escape_for_readline))
        else:
            self.data.write(str(message))

    def write_context(self, file: Streamable, offset: int, context_bytes: int = 32, num_bytes: int = 1,
                      indent: str = "", max_num_bytes: Optional[int] = 80):
        ellipsis = ""
        if max_num_bytes is not None and num_bytes > max_num_bytes:
            ellipsis = "⋯"
            num_bytes = max_num_bytes - 1
        file = make_stream(file)
        bytes_before = min(offset, context_bytes)
        context_before = string_escape(file[offset - bytes_before:offset].content)
        current_byte = string_escape(file[offset:offset + num_bytes].content)
        context_after = string_escape(file[offset + num_bytes:offset + num_bytes + context_bytes].content)
        self.write(indent)
        self.write(context_before)
        self.write(f"{current_byte}", bold=True)
        self.write(ellipsis, dim=True)
        self.write(context_after)
        self.write("\n")
        self.write(indent)
        self.write(f"{' ' * len(context_before)}")
        self.write(f"{'^' * max(len(current_byte), 1)}", bold=True)
        if ellipsis:
            self.write("^", dim=True)
        self.write(f"{' ' * len(context_after)}\n")

    def __str__(self):
        return self.data.getvalue()


class CommandInfo:
    def __init__(self, name: str, help: str, aliases: Iterable[str], allows_abbreviation: bool = False,
                 completer: Optional[Callable[["Command", str, int, int], List[str]]] = None):
        self.name: str = name
        self.help: str = help
        self.aliases: List[str] = list(aliases)
        self.allows_abbreviation: bool = allows_abbreviation
        self.completer: Optional[Callable[["Command", str, int, int], List[str]]] = completer


class Command(ABC):
    def __init__(self, repl: "REPL", name: str, allows_abbreviation: bool = False, aliases: Iterable[str] = ()):
        self.repl: REPL = repl
        self.name: str = name
        self.allows_abbreviation: bool = allows_abbreviation
        self.aliases: Set[str] = set(aliases)

    @abstractmethod
    def usage(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def run(self, arguments: str):
        raise NotImplementedError()

    def complete(self, args: str, begin_idx: int, end_idx: int) -> List[str]:
        return []

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Command) and other.name == self.name

    @classmethod
    def wrap(cls: T, function: Callable[["REPL", str], Any], info: CommandInfo) -> T:
        class WrappedCommand(cls):
            def __init__(self, repl: "REPL"):
                super().__init__(
                    repl, name=info.name, allows_abbreviation=info.allows_abbreviation, aliases=info.aliases
                )

            def usage(self) -> str:
                return info.help

            def run(self, arguments: str):
                return function(self.repl, arguments)

            def complete(self, args: str, begin_idx: int, end_idx: int) -> List[str]:
                if info.completer is None:
                    return []
                else:
                    return info.completer(self, args, begin_idx, end_idx)

        return WrappedCommand


class ExitREPL(Exception):
    pass


def _write_history(repl: "REPL"):
    repl.store_history()


def command(help: str, name: str = "", aliases: Iterable[str] = (), allows_abbreviation: bool = False,
            completer: Optional[Callable[["Command", str, int, int], List[str]]] = None):
    def wrapper(func):
        if not name:
            func_name = func.__name__
        else:
            func_name = name
        setattr(func, "command_info", CommandInfo(
            name=func_name, help=help, aliases=aliases, allows_abbreviation=allows_abbreviation, completer=completer
        ))
        return func

    return wrapper


def completer(for_command: Union[str, "Command"]):
    def wrapper(func: Callable[["REPL", str, int, int], List[str]]):
        setattr(func, "completer_for", for_command)
        return func

    return wrapper


def arg_completer(for_command: Union[str, "Command"]):
    def transformer(func: Callable[["REPL", int, str, Tuple[str, ...]], List[str]]):
        @completer(for_command=for_command)
        @wraps(func)
        def wrapper(repl: "REPL", *args, **kwargs):
            if kwargs or args and isinstance(args[0], int):
                # chances are the caller is trying to call using the original function signature
                try:
                    return func(repl, *args, **kwargs)
                except TypeError:
                    # we were wrong! (probably)
                    pass
            if kwargs:
                raise TypeError(f"{func!r} cannot be called with keyword arguments")
            try:
                arguments, begin_idx, end_idx, *remainder = args
            except ValueError:
                raise TypeError(f"{func!r} was expected to have been called with exactly three arguments; got {args!r}")
            if remainder:
                raise TypeError(f"{func!r} received unexpected positional arguments {remainder!r}")
            num_arguments = 0
            last_token_start = 0
            arg_indexes: List[int] = []
            tokens: List[str] = []
            for i, (prev, c) in enumerate(zip(f"\0{arguments[:begin_idx+1]}", arguments[:begin_idx+1])):
                if prev == " " and c != " ":
                    tokens.append(arguments[last_token_start:i].rstrip())
                    num_arguments += 1
                    last_token_start = i
                arg_indexes.append(num_arguments)
            if len(arg_indexes) <= begin_idx:
                arg_indexes.extend([num_arguments] * (1 + begin_idx - len(arg_indexes)))
            return func(repl, arg_indexes[begin_idx], arguments[begin_idx:end_idx], tuple(tokens))

        return wrapper

    return transformer


class REPLMeta(type):
    _commands: Dict[str, Type[Command]]
    _completers: Dict[str, Callable[["REPL", str, int, int], List[str]]]

    def add_command(cls, name: str, command: Type[Command]):
        if name in cls._commands:
            raise ValueError(f"A command named {name} is already registered to {cls}")
        cls._commands[name] = command

    def add_completer(cls, for_command_name: str, completer: Callable[["REPL", str, int, int], List[str]]):
        if for_command_name in cls._completers:
            raise ValueError(f"A completer for command {for_command_name} is already registered to {cls}")
        cls._completers[for_command_name] = completer

    @property
    def command_types(self) -> Iterator[Tuple[str, Type[Command]]]:
        yielded_names = set()
        for cls in self.mro():
            if isinstance(cls, REPLMeta):
                for name, cmd in cls._commands.items():
                    if name not in yielded_names:
                        yield name, cmd
                        yielded_names.add(name)

    @property
    def completers(self) -> Iterator[Tuple[str, Callable[["REPL", str, int, int], List[str]]]]:
        yielded_names = set()
        for cls in self.mro():
            if isinstance(cls, REPLMeta):
                for name, cmd_completer in cls._completers.items():
                    if name not in yielded_names:
                        yield name, cmd_completer
                        yielded_names.add(name)

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._commands = {}
        cls._completers = {}
        for func_name, func in namespace.items():
            if hasattr(func, "command_info") and isinstance(func.command_info, CommandInfo):
                try:
                    cls.add_command(func.command_info.name, Command.wrap(func, func.command_info))
                except ValueError as e:
                    raise TypeError(str(e))
            elif hasattr(func, "completer_for"):
                if isinstance(func.completer_for, Command):
                    command_name = func.completer_for.name
                elif isinstance(func.completer_for, str):
                    command_name = func.completer_for
                else:
                    raise TypeError(f"Unknown command specifier {func.completer_for!r} on function {func.__qualname__}")
                cls.add_completer(command_name, func)
        return cls


class SetCompleter:
    def __init__(self, possibilities: Callable[[], Iterable[str]]):
        self.possibilities: Callable[[], Iterable[str]] = possibilities

    def __call__(self, args: str, begin_idx: Optional[int] = None, end_idx: Optional[int] = None) -> List[str]:
        if begin_idx is None:
            begin_idx = 0
        if end_idx is None:
            end_idx = len(args)
        to_complete = args[begin_idx:end_idx]
        possibilities = sorted(set(self.possibilities()))
        return [
            p for p in possibilities if p.startswith(to_complete)
        ]


class REPL(metaclass=REPLMeta):
    def __init__(self, name: str, prompt: Optional[str] = None,
                 completer: Optional[Callable[[str, int], Optional[str]]] = None):
        self.name: str = name
        self._prev_history_length: int = 0
        if completer is None:
            self.completer: Callable[[str, int], Optional[str]] = REPLCompleter(self).complete
        else:
            self.completer = completer
        self.commands: Dict[str, Command] = {
            name: command_type(self) for name, command_type in self.__class__.command_types
        }
        self.last_command: Optional[str] = None
        if prompt is None:
            if sys.stderr.isatty():
                self.repl_prompt: str = ANSIWriter.format("(polyfile) ", bold=True, escape_for_readline=True)
            else:
                self.repl_prompt = "(polyfile) "
        else:
            self.repl_prompt = prompt
        self._bound_tab_completion: bool = False

    def command_names(self) -> Iterator[str]:
        yield from self.commands.keys()
        for cmd in self.commands.values():
            yield from cmd.aliases

    def get_completer(self, for_command: Command) -> Callable[[str, int, int], List[str]]:
        for cmd_name, cmd_completer in self.__class__.completers:
            if cmd_name == for_command.name:
                return partial(cmd_completer, self)  # type: ignore
        return for_command.complete

    @arg_completer(for_command="help")
    def help_completer(self, index: int, arg: str, prev_arguments: Iterable[str]):
        if index == 0:
            return SetCompleter(self.command_names)(arg)
        else:
            return []

    @command(help="print this message", allows_abbreviation=True)
    def help(self, arguments: str):
        arguments = arguments.strip()
        if arguments:
            if arguments not in self.commands:
                self.write(f"Undefined command: {arguments!r}. Try \"help\".\n", color=ANSIColor.RED)
            else:
                cmd = self.commands[arguments]
                self.write(cmd.usage())
                if cmd.aliases:
                    self.write(" (aliases: ", dim=True)
                    for i, alt in enumerate(sorted(cmd.aliases)):
                        if i > 0 and len(cmd.aliases) > 2:
                            self.write(", ", dim=True)
                        if i == len(cmd.aliases) - 1 and len(cmd.aliases) > 1:
                            self.write(" and ", dim=True)
                        self.write(alt, bold=True, color=ANSIColor.BLUE)
                    self.write(")", dim=True)
                self.write("\n")
        else:
            usages = {
                cmd.name: cmd.usage() for cmd in self.commands.values()
            }
            usage = [
                (name, usages[name]) for name in sorted(usages.keys())
            ]
            aliases = {
                cmd.name: sorted(cmd.aliases) for cmd in self.commands.values() if cmd.aliases
            }
            left_col_width = max(len(u[0]) for u in usage)
            if any(bool(v) for v in aliases.values()):
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

    def prompt(self, message: str, default: bool = True) -> bool:
        with Unprofiled():
            while True:
                buffer = ANSIWriter(use_ansi=sys.stderr.isatty(), escape_for_readline=True)
                buffer.write(f"{message} ", bold=True)
                buffer.write("[", dim=True)
                if default:
                    buffer.write("Y", bold=True, color=ANSIColor.GREEN)
                    buffer.write("n", dim=True, color=ANSIColor.RED)
                else:
                    buffer.write("y", dim=True, color=ANSIColor.GREEN)
                    buffer.write("N", bold=True, color=ANSIColor.RED)
                buffer.write("] ", dim=True)
                try:
                    answer = input(str(buffer)).strip().lower()
                except EOFError:
                    raise KeyboardInterrupt()
                if not answer:
                    return default
                elif answer == "n":
                    return False
                elif answer == "y":
                    return True

    def load_history(self):
        try:
            readline.read_history_file(str(HISTORY_PATH))
            self._prev_history_length = readline.get_current_history_length()
        except (FileNotFoundError, OSError):
            open(HISTORY_PATH, 'wb').close()
            self._prev_history_length = 0
        # default history len is -1 (infinite), which may grow unruly
        readline.set_history_length(2048)

    def store_history(self):
        new_length = readline.get_current_history_length()
        try:
            if hasattr(readline, "append_history_file"):
                readline.append_history_file(max(new_length - self._prev_history_length, 0), HISTORY_PATH)
            self._prev_history_length = readline.get_current_history_length()
        except IOError as e:
            log.warning(f"Unable to save history to {HISTORY_PATH!s}: {e!s}")

    def input(self, prompt: str = "") -> str:
        if not self._bound_tab_completion:
            self._bound_tab_completion = True
            readline.parse_and_bind("tab: complete")
            self.load_history()
            atexit.register(_write_history, self)
        prev_completer = readline.get_completer()
        readline.set_completer(self.completer)
        try:
            return input(prompt)
        except EOFError:
            # the user pressed ^D to quit
            return self.handle_eof()
        finally:
            readline.set_completer(prev_completer)

    def write(self, message: Any, bold: bool = False, dim: bool = False, color: Optional[ANSIColor] = None):
        if sys.stdout.isatty():
            message = ANSIWriter.format(message=message, bold=bold, dim=dim, color=color)
        sys.stdout.write(str(message))

    def handle_eof(self) -> str:
        # called when the user presses ^D on input()
        exit(0)
        return ""

    def before_prompt(self):
        pass

    def get_command(self, command_name: str) -> Command:
        if command_name in self.commands:
            return self.commands[command_name]
        for command in self.commands.values():
            if command.allows_abbreviation and command.name.startswith(command_name):
                return command
        # is it an alias?
        for command in self.commands.values():
            if not command.allows_abbreviation:
                if command_name in command.aliases:
                    return command
                else:
                    continue
            for alias in command.aliases:
                if alias.startswith(command_name):
                    return command
        raise KeyError(command_name)

    def run_command(self, command_str: str):
        command_name = command_str.lstrip()
        space_index = command_name.find(" ")
        if space_index > 0:
            command_name, args = command_name[:space_index], command_name[space_index + 1:].strip()
        else:
            args = ""

        try:
            return self.get_command(command_name).run(args)
        except KeyError:
            self.write(f"Undefined command: {command_name!r}. Try \"help\".\n", color=ANSIColor.RED)
            raise

    def repl(self):
        log.clear_status()
        self.before_prompt()
        while True:
            try:
                command_name = self.input(self.repl_prompt)
            except KeyboardInterrupt:
                continue
            if not command_name:
                if self.last_command is None:
                    continue
                command_name = self.last_command
            command_name = command_name.lstrip()
            original_command = command_name

            try:
                self.run_command(command_name)
            except KeyError:
                self.last_command = None
                continue
            except ExitREPL:
                break
            finally:
                self.last_command = original_command


class Quit(Command):
    def __init__(self, repl: REPL):
        super().__init__(repl, name="quit", allows_abbreviation=True)

    def usage(self) -> str:
        return f"exit {self.repl.name}"

    def run(self, arguments: str):
        exit(0)


REPL.add_command("quit", Quit)


class REPLCompleter:
    def __init__(self, repl: REPL):
        self.repl: REPL = repl

    def traverse(self, tokens, tree):
        if tree is None:
            return []
        elif len(tokens) == 0:
            return []
        if len(tokens) == 1:
            return [x+' ' for x in tree if x.startswith(tokens[0])]
        elif tokens[0] in tree.keys():
            return self.traverse(tokens[1:],tree[tokens[0]])
        return []

    def complete(self, text: str, state: int) -> Optional[str]:
        commandline = readline.get_line_buffer()
        space_index = commandline.find(" ")
        if space_index < 0 or (space_index > 0 and readline.get_endidx() < space_index):
            # we are completing the command name
            possible_names = sorted({
                cmd_name for cmd_name in self.repl.commands.keys()
                if cmd_name.startswith(text)
            } | {
                alias
                for cmd in self.repl.commands.values()
                for alias in cmd.aliases
                if alias.startswith(text)
            }) + [None]
            if state < len(possible_names):
                if state == 0 and len(possible_names) == 2:
                    # there is only one possibility, so append it with a space since it is the only choice
                    return f"{possible_names[0]} "
                return possible_names[state]
            else:
                return None
        if space_index > 0:
            command_name, args = commandline[:space_index], commandline[space_index + 1:]
        else:
            command_name = ""
            args = ""
        try:
            command = self.repl.get_command(command_name)
        except KeyError:
            return None
        completer = self.repl.get_completer(for_command=command)
        try:
            possibilities = completer(
                args, readline.get_begidx() - space_index - 1, readline.get_endidx() - space_index - 1
            ) + [None]  # type: ignore
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            log.warning(f"Command {completer!r}({args!r}, "
                        f"{readline.get_begidx() - space_index - 1}, {readline.get_endidx() - space_index - 1}) "
                        f"raised an exception: {e!r}")
            return None

        if state < len(possibilities):
            if state == 0 and len(possibilities) == 2:
                # there is only one possibility, so append it with a space since it is the only choice
                return f"{possibilities[0]} "
            return possibilities[state]
        else:
            log.warning(f"Command {command.__class__.__name__}.complete({args!r}, "
                        f"{readline.get_begidx() - space_index - 1}, {readline.get_endidx() - space_index - 1}) "
                        f"returned an invalid result: {possibilities[:-1]!r}")
            return None
