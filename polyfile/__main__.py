import argparse
import base64
import hashlib
import json
import logging
import os
import re
import signal
import sys
from typing import Optional

from . import html
from . import logger
from . import polyfile
from . import trid
from . import version
from .fileutils import PathOrStdin
from .magic import MagicMatcher


log = logger.getStatusLogger("polyfile")


class SIGTERMHandler:
    def __init__(self):
        self.terminated = False
        signal.signal(signal.SIGTERM, self.sigterm_handler)

    def sigterm_handler(self, signum, frame):
        sys.stderr.flush()
        sys.stderr.write('\n\nCaught SIGTERM. Exiting gracefully, and dumping partial results...\n')
        self.terminated = True


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.')
    parser.add_argument('FILE', nargs='?', default='-',
                        help='the file to analyze; pass \'-\' or omit to read from STDIN')
    parser.add_argument('--filetype', '-f', action='append',
                        help='explicitly match against the given filetype or filetype wildcard (default is to match'
                             'against all filetypes)')
    parser.add_argument('--list', '-l', action='store_true',
                        help='list the supported filetypes (for the `--filetype` argument) and exit')
    parser.add_argument('--html', '-t', type=argparse.FileType('wb'), required=False,
                        help='path to write an interactive HTML file for exploring the PDF')
    # parser.add_argument('--try-all-offsets', '-a', action='store_true',
    #                     help='Search for a file match at every possible offset; this can be very slow for larger '
    #                     'files')
    parser.add_argument('--only-match-mime', '-I', action='store_true',
                        help='just print out the matching MIME types for the file, one on each line')
    parser.add_argument('--only-match', '-m', action='store_true',
                        help='do not attempt to parse known filetypes; only match against file magic')
    parser.add_argument('--require-match', action='store_true', help='if no matches are found, exit with code 127')
    parser.add_argument('--max-matches', type=int, default=None,
                        help='stop scanning after having found this many matches')
    parser.add_argument('--debug', '-d', action='store_true', help='print debug information')
    parser.add_argument('--trace', '-dd', action='store_true', help='print extra verbose debug information')
    parser.add_argument('--quiet', '-q', action='store_true', help='suppress all log output (overrides --debug)')
    parser.add_argument('--version', '-v', action='store_true', help='print PolyFile\'s version information to STDERR')
    parser.add_argument('-dumpversion', action='store_true', help='print PolyFile\'s raw version information to STDOUT and exit')

    if argv is None:
        argv = sys.argv
    
    args = parser.parse_args(argv[1:])

    if args.dumpversion:
        print(' '.join(map(str, version.__version__)))
        exit(0)

    if args.list:
        for mimetype in sorted(MagicMatcher.DEFAULT_INSTANCE.mimetypes):
            print(mimetype)
        exit(0)

    if args.version:
        sys.stderr.write(f"PolyFile version {version.VERSION_STRING}\n")
        if args.FILE == '-' and sys.stdin.isatty():
            # No file argument was provided and it doesn't look like anything was piped into STDIN,
            # so instead of blocking on STDIN just exit
            exit(0)

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

    with PathOrStdin(args.FILE) as file_path:
        matches = []
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
                    for match in magic_matcher.match(f.read(), only_match_mime=True):
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
                matcher = polyfile.Matcher(submatch=not args.only_match, matcher=magic_matcher)
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
                'polyfile': version.VERSION_STRING
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
