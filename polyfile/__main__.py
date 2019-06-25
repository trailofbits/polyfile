import argparse
import sys

from . import polyfile


def main(argv=None):
    parser = argparse.ArgumentParser(description='A utility to recursively map the structure of a file.')

    if argv is None:
        argv = sys.argv
    
    #args = parser.parse_args(argv[1:])

    from . import trid

    for tdef in trid.match(argv[1], try_all_offsets=True):
        print(tdef)


if __name__ == '__main__':
    main()
