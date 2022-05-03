import argparse
from contextlib import ExitStack
import base64
import hashlib
import json
import logging
import os
import re
import signal
import sys
from textwrap import dedent
from typing import Optional

from . import html
from . import logger
from . import polyfile
from .fileutils import PathOrStdin, PathOrStdout
from .magic import MagicMatcher, MatchContext
from .debugger import Debugger
from .polyfile import __version__, Analyzer


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


class ValidateOutput(argparse.Action):
    valid_outputs = ("mime", "html", "json", "sbud")

    def __call__(self, parser, args, values, option_string=None):
        output, path = values
        if output not in self.valid_outputs:
            raise ValueError(f"invalid output format: {output!r}, expected one of {self.valid_outputs!r}")
        if not hasattr(args, self.dest) or getattr(args, self.dest) is None:
            setattr(args, self.dest, [])
        if path != "-":
            # make sure this path isn't reused in any of the existing outputs:
            for other_output, other_path in getattr(args, self.dest):
                if other_path == path:
                    raise ValueError(f"output path {path!r} cannot be used for both --output {other_output} and "
                                     f"--output {output}")
        getattr(args, self.dest).append((output, path))


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('FILE', nargs='?', default='-',
                        help='the file to analyze; pass \'-\' or omit to read from STDIN')

    parser.add_argument('--output', '-o', action=ValidateOutput, nargs=2,
                        metavar=(f"{{{','.join(ValidateOutput.valid_outputs)}}}", "PATH"),
                        help=dedent("""the output format and a path to save the output

Output formats are:
mime ... the detected MIME types associated with the file, like the output of the `file` command
html ... an interactive HTML-based hex viewer
json ... a modified version of the SBUD format in JSON syntax
sbud ... equivalent to 'json'

The path can be '-' for STDOUT

If no output is specified, PolyFile defaults to `--output json -`,
but this will change to `--output mime -` in v0.5.0"""))

    parser.add_argument('--filetype', '-f', action='append',
                        help='explicitly match against the given filetype or filetype wildcard (default is to match '
                             'against all filetypes)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--list', '-l', action='store_true',
                       help='list the supported filetypes for the `--filetype` argument and exit')
    group.add_argument('--html', '-t', type=argparse.FileType('wb'), required=False,
                       help='path to write an interactive HTML file for exploring the PDF')
    # parser.add_argument('--try-all-offsets', '-a', action='store_true',
    #                     help='Search for a file match at every possible offset; this can be very slow for larger '
    #                     'files')
    group.add_argument('--only-match-mime', '-I', action='store_true',
                       help='just print out the matching MIME types for the file, one on each line')
    parser.add_argument('--only-match', '-m', action='store_true',
                        help='do not attempt to parse known filetypes; only match against file magic')
    parser.add_argument('--require-match', action='store_true', help='if no matches are found, exit with code 127')
    parser.add_argument('--max-matches', type=int, default=None,
                        help='stop scanning after having found this many matches')
    parser.add_argument('--debugger', '-db', action='store_true', help='drop into an interactive debugger for libmagic '
                                                                       'file definition matching and PolyFile parsing')
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

    if not hasattr(args, "output") or args.output is None or len(args.output) == 0:
        # TODO: Change this from "json" to "mime" in v0.5.0:
        setattr(args, "output", [("json", "-")])

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
    except KeyboardInterrupt:
        # this will happen if the user presses ^C wile reading from STDIN
        exit(1)
        return  # this is here because linters are dumb and will complain about the next line without it

    with path_or_stdin as file_path, ExitStack() as stack:
        if args.debugger:
            stack.enter_context(Debugger(break_on_parsing=not args.no_debug_python))
        elif args.no_debug_python:
            log.warning("Ignoring `--no-debug-python`; it can only be used with the --debugger option.")
        if sys.stderr.isatty() and not sys.stdout.isatty():
            log.warning("""The default output format for PolyFile will be changing in forthcoming release v0.5.0!
Currently, the default output format is SBUD/JSON.
In release v0.5.0, it will switch to the equivalent of the current `--only-match-mime` option.
To preserve the original behavior, add the `- ` command line option.
Please update your scripts!

""")
        analyzer = Analyzer(file_path, parse=not args.only_match, magic_matcher=magic_matcher)

        needs_sbud = any(output_format in {"html", "json", "sbud"} for output_format, _ in args.output)
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

        for output_format, path in args.output:
            with PathOrStdout(path) as output:
                if output_format == "mime":
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
                    if args.require_match and not found_match and not needs_sbud:
                        log.info("No matches found, exiting")
                        exit(127)
                    if omm:
                        log.clear_status()
                    else:
                        log.info(f"Saved MIME output to {path}")
                elif output_format == "json" or output_format == "sbud":
                    assert needs_sbud
                    json.dump(sbud, output)
                    if path != "-":
                        log.info(f"Saved {output_format.upper()} output to {path}")
                elif output_format == "html":
                    assert needs_sbud
                    output.write(html.generate(file_path, sbud))
                    if path != "-":
                        log.info(f"Saved HTML output to {path}")
                else:
                    raise NotImplementedError(f"TODO: Add support for output format {output_format!r}")
        exit(0)

        try:
            if args.only_match_mime:
                with open(file_path, "rb") as f:
                    if magic_matcher is None:
                        magic_matcher = MagicMatcher.DEFAULT_INSTANCE
                    omm = sys.stderr.isatty() and sys.stdout.isatty() and logging.root.level <= logging.INFO
                    if omm:
                        # figure out the longest MIME type so we can make sure the columns are aligned
                        longest_mimetype = max(len(mimetype) for mimetype in magic_matcher.mimetypes)
                    mimetypes = set()
                    for match in magic_matcher.match(MatchContext.load(f, only_match_mime=True)):
                        new_mimetypes = match.mimetypes - mimetypes
                        mimetypes |= new_mimetypes
                        matches.extend(new_mimetypes)
                        for mimetype in new_mimetypes:
                            if omm:
                                log.clear_status()
                                sys.stdout.write(mimetype)
                                sys.stdout.flush()
                                sys.stderr.write("." * (longest_mimetype - len(mimetype) + 1))
                                sys.stderr.write(str(match))
                                sys.stderr.flush()
                                sys.stdout.write("\n")
                                sys.stdout.flush()
                            else:
                                print(mimetype)
                    if omm:
                        log.clear_status()
            elif args.max_matches is None or args.max_matches > 0:
                matcher = polyfile.Matcher(parse=not args.only_match, matcher=magic_matcher)
                for match in matcher.match(file_path):
                    if sigterm_handler.terminated:
                        break
                    if hasattr(match.match, 'filetype'):
                        filetype = match.match.filetype
                    else:
                        filetype = match.name
                    if match.parent is None:
                        log.info(f"Found a file of type {filetype} at byte offset {match.offset}")
                        matches.append(match)
                        if args.max_matches is not None and len(matches) >= args.max_matches:
                            log.info(f"Found { args.max_matches } matches; stopping early")
                            break
                    elif isinstance(match, polyfile.Submatch):
                        log.debug(f"Found a subregion of type {filetype} at byte offset {match.offset}")
                    else:
                        log.info(f"Found an embedded file of type {filetype} at byte offset {match.offset}")
            sys.stderr.flush()
        except KeyboardInterrupt:
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
                        break
                    elif result and result.lower() == 'n':
                        sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(128 + signal.SIGINT)
        if args.require_match and not matches:
            log.info("No matches found, exiting")
            exit(127)
        elif args.only_match_mime:
            exit(0)
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as hash_file:
            data = hash_file.read()
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
            b64contents = base64.b64encode(data)
            file_length = len(data)
            data = None
        if args.FILE == '-':
            filename = 'STDIN',
        else:
            filename = os.path.split(args.FILE)[-1]
        sbud = {
            'MD5': md5.hexdigest(),
            'SHA1': sha1.hexdigest(),
            'SHA256': sha256.hexdigest(),
            'b64contents': b64contents.decode('utf-8'),
            'fileName': filename,
            'length': file_length,
            'versions': {
                'polyfile': __version__
            },
            'struc': [
                match.to_obj() for match in matches
            ]
        }
        print(json.dumps(sbud))
        if args.html:
            args.html.write(html.generate(file_path, sbud).encode('utf-8'))
            args.html.close()
            log.info(f"Saved HTML output to {args.html.name}")
        if sigterm_handler.terminated:
            sys.exit(128 + signal.SIGTERM)


if __name__ == '__main__':
    main()
