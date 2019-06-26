import argparse
import sys

from . import polyfile


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.')
    parser.add_argument('FILE', help='The file to analyze')

    if argv is None:
        argv = sys.argv
    
    args = parser.parse_args(argv[1:])

    for match in polyfile.match(args.FILE):
        print(repr(match))


if __name__ == '__main__':
    main()
