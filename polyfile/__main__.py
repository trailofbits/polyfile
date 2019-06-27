import argparse
import sys

from . import logger
from . import polyfile


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.')
    parser.add_argument('FILE', help='The file to analyze')

    if argv is None:
        argv = sys.argv
    
    args = parser.parse_args(argv[1:])

    logger.setLevel(logger.STATUS)

    for match in polyfile.match(args.FILE):
        if match.parent is None:
            sys.stderr.write(f"Found a file of type {match.filetype.filetype} at byte offset {match.offset}\n")
        else:
            sys.stderr.write(f"Found an embedded file of type {match.filetype.filetype} at byte offset {match.offset}\n")
        sys.stderr.flush()


if __name__ == '__main__':
    main()
