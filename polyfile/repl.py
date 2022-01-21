import atexit
from abc import ABC, abstractmethod
from enum import Enum
from io import StringIO
from pathlib import Path
import readline
import sys
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar

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

    def __str__(self):
        return self.data.getvalue()


class CommandInfo:
    def __init__(self, name: str, help: str, aliases: Iterable[str], allows_abbreviation: bool = False):
        self.name: str = name
        self.help: str = help
        self.aliases: List[str] = list(aliases)
        self.allows_abbreviation: bool = allows_abbreviation


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

        return WrappedCommand


class ExitREPL(Exception):
    pass


def _write_history(repl: "REPL"):
    repl.store_history()


def command(help: str, name: str = "", aliases: Iterable[str] = (), allows_abbreviation: bool = False):
    def wrapper(func):
        if not name:
            func_name = func.__name__
        else:
            func_name = name
        setattr(func, "command_info", CommandInfo(
            name=func_name, help=help, aliases=aliases, allows_abbreviation=allows_abbreviation
        ))
        return func

    return wrapper


class REPLMeta(type):
    _commands: Dict[str, Type[Command]]

    def add_command(cls, name: str, command: Type[Command]):
        if name in cls._commands:
            raise ValueError(f"A command named {name} is already registered to {cls}")
        cls._commands[name] = command

    @property
    def command_types(mcls) -> Iterator[Tuple[str, Type[Command]]]:
        yielded_names = set()
        for cls in mcls.mro():
            if isinstance(cls, REPLMeta):
                for name, cmd in cls._commands.items():
                    if name not in yielded_names:
                        yield name, cmd
                        yielded_names.add(name)

    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        cls._commands = {}
        for func_name, func in namespace.items():
            if hasattr(func, "command_info") and isinstance(func.command_info, CommandInfo):
                try:
                    cls.add_command(func.command_info.name, Command.wrap(func, func.command_info))
                except ValueError as e:
                    raise TypeError(str(e))
        return cls


class REPL(metaclass=REPLMeta):
    def __init__(self, name: str, prompt: Optional[str] = None):
        self.name: str = name
        self._prev_history_length: int = 0
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

    def _complete(self, text, state):
        print(f"text={text!r}, state={state!r}")
        return []

    def load_history(self):
        try:
            readline.read_history_file(HISTORY_PATH)
            self._prev_history_length = readline.get_current_history_length()
        except FileNotFoundError:
            open(HISTORY_PATH, 'wb').close()
            self._prev_history_length = 0
        # default history len is -1 (infinite), which may grow unruly
        readline.set_history_length(2048)

    def store_history(self):
        new_length = readline.get_current_history_length()
        try:
            readline.append_history_file(max(new_length - self._prev_history_length, 0), HISTORY_PATH)
            self._prev_history_length = readline.get_current_history_length()
        except IOError as e:
            log.warning(f"Unable to save history to {HISTORY_PATH!s}: {e!s}")

    def input(self, prompt: str = "") -> str:
        prev_completer = readline.get_completer()
        if not self._bound_tab_completion:
            self._bound_tab_completion = True
            readline.parse_and_bind("tab: complete")
            self.load_history()
            atexit.register(_write_history, self)
        readline.set_completer(self._complete)
        try:
            return input(self.repl_prompt)
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

    def before_prompt(self):
        pass

    def repl(self):
        log.clear_status()
        self.before_prompt()
        while True:
            command_name = self.input(self.repl_prompt)
            if not command_name:
                if self.last_command is None:
                    continue
                command_name = self.last_command
            command_name = command_name.lstrip()
            original_command = command_name
            space_index = command_name.find(" ")
            if space_index > 0:
                command_name, args = command_name[:space_index], command_name[space_index+1:].strip()
            else:
                args = ""
            if command_name in self.commands:
                command = self.commands[command_name]
            else:
                for command in self.commands.values():
                    if command.allows_abbreviation and command.name.startswith(command_name):
                        break
                else:
                    # is it an alias?
                    for command in self.commands.values():
                        if not command.allows_abbreviation:
                            if command_name in command.aliases:
                                break
                            else:
                                continue
                        for alias in command.aliases:
                            if alias.startswith(command_name):
                                break
                        else:
                            continue
                        break
                    else:
                        self.write(f"Undefined command: {command_name!r}. Try \"help\".\n", color=ANSIColor.RED)
                        self.last_command = None
                        continue
            try:
                command.run(args)
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


class ARLCompleter:
    def __init__(self,logic):
        self.logic = logic

    def traverse(self,tokens,tree):
        if tree is None:
            return []
        elif len(tokens) == 0:
            return []
        if len(tokens) == 1:
            return [x+' ' for x in tree if x.startswith(tokens[0])]
        else:
            if tokens[0] in tree.keys():
                return self.traverse(tokens[1:],tree[tokens[0]])
            else:
                return []
        return []

    def complete(self,text,state):
        try:
            tokens = readline.get_line_buffer().split()
            if not tokens or readline.get_line_buffer()[-1] == ' ':
                tokens.append()
            results = self.traverse(tokens,self.logic) + [None]
            return results[state]
        except Exception as e:
            print(e)

logic = {
    'build':
            {
            'barracks':None,
            'bar':None,
            'generator':None,
            'lab':None
            },
    'train':
            {
            'riflemen':None,
            'rpg':None,
            'mortar':None
            },
    'research':
            {
            'armor':None,
            'weapons':None,
            'food':None
            }
    }