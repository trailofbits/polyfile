import argparse
import json
import logging
import sys

from . import logger
from . import polyfile


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.')
    parser.add_argument('FILE', help='The file to analyze')
    parser.add_argument('--debug', '-d', action='store_true', help='Print debug information')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress all log output (overrides --debug)')

    if argv is None:
        argv = sys.argv
    
    args = parser.parse_args(argv[1:])

    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logger.STATUS)

    matches = []
    for match in polyfile.match(args.FILE):
        if match.parent is None:
            sys.stderr.write(f"Found a file of type {match.match.filetype} at byte offset {match.offset}\n")
            matches.append(match.to_obj())
        else:
            sys.stderr.write(f"Found an embedded file of type {match.match.filetype} at byte offset {match.offset}\n")
        sys.stderr.flush()
    print(json.dumps(matches))


if __name__ == '__main__':
    main()
