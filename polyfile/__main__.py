import argparse
from contextlib import ExitStack
import json
import logging
import re
import signal
import sys
from textwrap import dedent
from typing import ContextManager, Optional, TextIO

from . import html
from . import logger
from .fileutils import PathOrStdin, PathOrStdout
from .magic import MagicMatcher
from .debugger import Debugger
from .polyfile import __version__, Analyzer
from .repl import ExitREPL


log = logger.getStatusLogger("polyfile")


class SIGTERMHandler:
    def __init__(self):
        self.terminated = False
        signal.signal(signal.SIGTERM, self.sigterm_handler)

    def sigterm_handler(self, signum, frame):
        sys.stderr.flush()
        sys.stderr.write('\n\nCaught SIGTERM. Exiting gracefully, and dumping partial results...\n')
        self.terminated = True


class KeyboardInterruptHandler:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, KeyboardInterrupt):
            try:
                sys.stdout.flush()
                sys.stderr.flush()
                sys.stderr.write("\n\nCaught keyboard interrupt.\n")
                if not sys.stderr.isatty() or not sys.stdin.isatty():
                    sys.exit(128 + 15)
                while True:
                    sys.stderr.write("Would you like PolyFile to output its current progress? [Yn] ")
                    result = input()
                    if not result or result.lower() == 'y':
                        return True
                    elif result and result.lower() == 'n':
                        sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(128 + signal.SIGINT)
        else:
            return exc_type is None


class FormatOutput:
    valid_formats = ("mime", "html", "json", "sbud", "explain")
    default_format = "file"

    def __init__(self, output_format: Optional[str] = None, output_path: Optional[str] = None):
        if output_format is None:
            output_format = self.default_format
        self.output_format: str = output_format
        self.output_path: Optional[str] = output_path

    @property
    def output_to_stdout(self) -> bool:
        return self.output_path is None or self.output_path == "-"

    @property
    def output_stream(self) -> ContextManager[TextIO]:
        if self.output_path is None:
            return PathOrStdout("-")
        else:
            return PathOrStdout(self.output_path)

    def __hash__(self):
        return hash((self.output_format, self.output_path))

    def __eq__(self, other):
        return isinstance(other, FormatOutput) and other.output_format == self.output_format and other.output_path == self.output_path

    def __str__(self):
        return self.output_format

    __repr__ = __str__


class ValidateOutput(argparse.Action):
    @staticmethod
    def add_output(args: argparse.Namespace, path: str):
        if not hasattr(args, "format") or args.format is None:
            setattr(args, "format", [])
        if len(args.format) == 0:
            args.format.append(FormatOutput(output_path=path))
            return
        existing_format: FormatOutput = args.format[-1]
        if path != "-":
            # make sure this path isn't already used
            for output_format in args.format[:-1]:
                if output_format.output_path == path:
                    raise ValueError(f"output path {path!r} cannot be used for both --format "
                                     f"{output_format.output_format} and --format {existing_format.output_format}")
        if existing_format.output_path is not None and existing_format.output_path != path:
            args.format.append(FormatOutput(output_format=existing_format.output_format, output_path=path))
        else:
            existing_format.output_path = path

    def __call__(self, parser, args, values, option_string=None):
        ValidateOutput.add_output(args, values)


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('FILE', nargs='?', default='-',
                        help='the file to analyze; pass \'-\' or omit to read from STDIN')

    parser.add_argument('--format', '-r', type=FormatOutput, action="append", choices=[
        FormatOutput(f) for f in FormatOutput.valid_formats + ("json",)
    ], help=dedent("""PolyFile's output format

Output formats are:
file ...... the detected formats associated with the file,
            like the output of the `file` command
mime ...... the detected MIME types associated with the file,
            like the output of the `file --mime-type` command
explain ... like 'mime', but adds a human-readable explanation
            for why each MIME type matched
html ...... an interactive HTML-based hex viewer
json ...... a modified version of the SBUD format in JSON syntax
sbud ...... equivalent to 'json'

Multiple formats can be output at once:

    polyfile INPUT_FILE -f mime -f json

Their output will be concatenated to STDOUT in the order that
they occur in the arguments.

To save each format to a separate file, see the `--output` argument.

If no format is specified, PolyFile defaults to `--format file`"""))

    parser.add_argument('--output', '-o', action=ValidateOutput, type=str, # nargs=2,
                        # metavar=(f"{{{','.join(ValidateOutput.valid_outputs)}}}", "PATH"),
                        help=dedent("""an optional output path for `--format`

Each instance of `--output` applies to the previous instance
of the `--format` option.

For example:

    polyfile INPUT_FILE --format html --output output.html \\
                        --format sbud --output output.json

will save HTML to to `output.html` and SBUD to `output.json`.
No two outputs can be directed at the same file path.

The path can be '-' for STDOUT.
If an `--output` is omitted for a format,
then it will implicitly be printed to STDOUT.
"""))

    parser.add_argument('--filetype', '-f', action='append',
                        help='explicitly match against the given filetype or filetype wildcard (default is to match '
                             'against all filetypes)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--list', '-l', action='store_true',
                       help='list the supported filetypes for the `--filetype` argument and exit')
    group.add_argument('--html', '-t', action="append",
                       help=dedent("""path to write an interactive HTML file for exploring the PDF;
equivalent to `--format html --output HTML`"""))
    group.add_argument("--explain", action="store_true", help="equivalent to `--format explain")
    # parser.add_argument('--try-all-offsets', '-a', action='store_true',
    #                     help='Search for a file match at every possible offset; this can be very slow for larger '
    #                     'files')
    group.add_argument('--only-match-mime', '-I', action='store_true',
                       help=dedent(""""just print out the matching MIME types for the file, one on each line;
equivalent to `--format mime`"""))
    parser.add_argument('--only-match', '-m', action='store_true',
                        help='do not attempt to parse known filetypes; only match against file magic')
    parser.add_argument('--require-match', action='store_true', help='if no matches are found, exit with code 127')
    parser.add_argument('--max-matches', type=int, default=None,
                        help='stop scanning after having found this many matches')
    parser.add_argument('--debugger', '-db', action='store_true', help='drop into an interactive debugger for libmagic '
                                                                       'file definition matching and PolyFile parsing')
    parser.add_argument('--eval-command', '-ex', type=str, action='append', help='execute the given debugger command')
    parser.add_argument('--no-debug-python', action='store_true', help='by default, the `--debugger` option will break '
                                                                       'on custom matchers and prompt to debug using '
                                                                       'PDB. This option will suppress those prompts.')
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument('--quiet', '-q', action='store_true', help='suppress all log output')
    verbosity_group.add_argument('--debug', '-d', action='store_true', help='print debug information')
    verbosity_group.add_argument('--trace', '-dd', action='store_true', help='print extra verbose debug information')

    parser.add_argument('--version', '-v', action='store_true', help='print PolyFile\'s version information to STDERR')

    group.add_argument('-dumpversion', action='store_true',
                       help='print PolyFile\'s raw version information to STDOUT and exit')

    if argv is None:
        argv = sys.argv

    try:
        args = parser.parse_args(argv[1:])
    except ValueError as e:
        parser.print_usage()
        sys.stderr.write(f"polyfile: error: {e!s}\n")
        exit(1)

    if args.dumpversion:
        print(__version__)
        exit(0)

    if args.eval_command and not args.debugger:
        parser.print_usage()
        sys.stderr.write("polyfile: error: the `--eval-command` argument can only be used in conjunction with "
                         "`--debugger`\n")
        exit(1)

    if args.list:
        for mimetype in sorted(MagicMatcher.DEFAULT_INSTANCE.mimetypes):
            print(mimetype)
        exit(0)

    if args.version:
        sys.stderr.write(f"PolyFile version {__version__}\n")
        if args.FILE == '-' and sys.stdin.isatty():
            # No file argument was provided and it doesn't look like anything was piped into STDIN,
            # so instead of blocking on STDIN just exit
            exit(0)

    if not hasattr(args, "format") or args.format is None or len(args.format) == 0:
        setattr(args, "format", [])

    if hasattr(args, "html") and args.html is not None:
        for html_path in args.html:
            args.format.append(FormatOutput(output_format="html"))
            ValidateOutput.add_output(args, html_path)

    if hasattr(args, "explain") and args.explain:
        args.format.append(FormatOutput(output_format="explain"))

    if args.only_match_mime:
        args.format.append(FormatOutput(output_format="mime"))

    if not args.format:
        args.format.append(FormatOutput())

    if args.quiet:
        logger.setLevel(logging.CRITICAL)
    elif args.trace:
        logger.setLevel(logger.TRACE)
    elif args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logger.STATUS)

    if args.filetype:
        regex = r'|'.join(fr"({ f.replace('*', '.*').replace('?', '.?') })" for f in args.filetype)
        matcher = re.compile(regex)
        mimetypes = [mimetype for mimetype in MagicMatcher.DEFAULT_INSTANCE.mimetypes if matcher.fullmatch(mimetype)]
        if not mimetypes:
            log.error(f"Filetype argument(s) { args.filetype } did not match any known definitions!")
            exit(1)
        log.info(f"Only matching against these types: {', '.join(mimetypes)}")
        magic_matcher: Optional[MagicMatcher] = MagicMatcher.DEFAULT_INSTANCE.only_match(mimetypes=mimetypes)
    else:
        magic_matcher = None

    sigterm_handler = SIGTERMHandler()

    try:
        path_or_stdin = PathOrStdin(args.FILE)
    except FileNotFoundError:
        log.error(f"Cannot open {args.FILE!r} (No such file or directory)")
        exit(1)
    except KeyboardInterrupt:
        # this will happen if the user presses ^C wile reading from STDIN
        exit(1)
        return  # this is here because linters are dumb and will complain about the next line without it

    with path_or_stdin as file_path, ExitStack() as stack:
        if args.debugger:
            debugger = Debugger(break_on_parsing=not args.no_debug_python)
            if args.eval_command:
                for ex in args.eval_command:
                    try:
                        debugger.before_prompt()
                        debugger.write(f"{debugger.repl_prompt}{ex}\n")
                        debugger.run_command(ex)
                    except KeyError:
                        exit(1)
                    except ExitREPL:
                        exit(0)
                debugger.write("\n")
            stack.enter_context(debugger)
        elif args.no_debug_python:
            log.warning("Ignoring `--no-debug-python`; it can only be used with the --debugger option.")

        analyzer = Analyzer(file_path, parse=not args.only_match, magic_matcher=magic_matcher)

        needs_sbud = any(output_format.output_format in {"html", "json", "sbud"} for output_format in args.format)
        with KeyboardInterruptHandler():
            # do we need to do a full match? if so, do that up front:
            if needs_sbud:
                if args.max_matches is None or args.max_matches > 0:
                    for match in analyzer.matches():
                        if sigterm_handler.terminated:
                            break
                        if match.parent is None:
                            if args.max_matches is not None and len(analyzer.matches_so_far) >= args.max_matches:
                                log.info(f"Found {args.max_matches} matches; stopping early")
                                break
        if needs_sbud:
            sbud = analyzer.sbud(matches=analyzer.matches_so_far)

            if args.require_match and not analyzer.matches_so_far:
                log.info("No matches found, exiting")
                exit(127)

        for output_format in args.format:
            with output_format.output_stream as output:
                if output_format.output_format == "file":
                    istty = sys.stderr.isatty() and output.isatty() and logging.root.level <= logging.INFO
                    lines = set()
                    with KeyboardInterruptHandler():
                        for match in analyzer.magic_matches():
                            line = str(match)
                            if line not in lines:
                                lines.add(line)
                                if istty:
                                    log.clear_status()
                                    output.write(f"{line}\n")
                                    output.flush()
                                else:
                                    output.write(f"{line}\n")
                    if istty:
                        log.clear_status()
                elif output_format.output_format in ("mime", "explain"):
                    omm = sys.stderr.isatty() and output.isatty() and logging.root.level <= logging.INFO
                    if omm:
                        # figure out the longest MIME type so we can make sure the columns are aligned
                        longest_mimetype = max(len(mimetype) for mimetype in analyzer.magic_matcher.mimetypes)
                    found_match = False
                    with KeyboardInterruptHandler():
                        for mimetype, match in analyzer.mime_types():
                            found_match = True
                            if omm:
                                log.clear_status()
                                output.write(mimetype)
                                output.flush()
                                sys.stderr.write("." * (longest_mimetype - len(mimetype) + 1))
                                sys.stderr.write(str(match))
                                sys.stderr.flush()
                                output.write("\n")
                                output.flush()
                            else:
                                output.write(mimetype)
                                output.write("\n")
                            if output_format.output_format == "explain":
                                output.write(match.explain(ansi_color=output.isatty(), file=file_path))
                    if args.require_match and not found_match and not needs_sbud:
                        log.info("No matches found, exiting")
                        exit(127)
                    if omm:
                        log.clear_status()
                    elif not output_format.output_to_stdout:
                        log.info(f"Saved MIME output to {output_format.output_path}")
                elif output_format.output_format == "json" or output_format.output_format == "sbud":
                    assert needs_sbud
                    json.dump(sbud, output)
                    if not output_format.output_to_stdout:
                        log.info(f"Saved {output_format.output_format.upper()} output to {output_format.output_path}")
                elif output_format.output_format == "html":
                    assert needs_sbud
                    output.write(html.generate(file_path, sbud))
                    if not output_format.output_to_stdout:
                        log.info(f"Saved HTML output to {output_format.output_path}")
                else:
                    # This should never happen because the output formats are constrained by argparse
                    raise NotImplementedError(f"TODO: Add support for output format {output_format!r}")

        if sigterm_handler.terminated:
            sys.exit(128 + signal.SIGTERM)


if __name__ == '__main__':
    main()
