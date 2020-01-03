import argparse
import json
import logging
import sys

from argparse import RawTextHelpFormatter

from polyfile import logger, version

from .polymerge import merge


def main(argv=None):
    parser = argparse.ArgumentParser(description='''A utility to merge the JSON output of `polyfile`
with a polytracker.json file from PolyTracker.

https://github.com/trailofbits/polyfile/
https://github.com/trailofbits/polytracker/
''', formatter_class=RawTextHelpFormatter)
    parser.add_argument('POLYFILE_JSON', type=argparse.FileType('r'), help='')
    parser.add_argument('POLYTRACKER_JSON', type=argparse.FileType('r'), help='')
    parser.add_argument('--simplify', '-s', action='store_true', help='Simplify the function mapping by only labeling PolyFile elements that have the fewest number of functions.')
    parser.add_argument('--debug', '-d', action='store_true', help='Print debug information')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress all log output (overrides --debug)')
    parser.add_argument('--version', '-v',
                        action='version',
                        version=f"PolyMerge version {version.VERSION_STRING}\n",
                        help='Print PolyMerge\'s version information and exit'
    )
    parser.add_argument('-dumpversion',
                        action='version',
                        version=' '.join(map(str, version.__version__)),
                        help='Print PolyMerge\'s raw version information and exit'
    )

    if argv is None:
        argv = sys.argv

    args = parser.parse_args(argv[1:])

    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logger.STATUS)

    polyfile_json = json.load(args.POLYFILE_JSON)
    args.POLYFILE_JSON.close()
    polytracker_json = json.load(args.POLYTRACKER_JSON)
    args.POLYTRACKER_JSON.close()
    print(json.dumps(merge(polyfile_json, polytracker_json, simplify=args.simplify)))


if __name__ == '__main__':
    main()
