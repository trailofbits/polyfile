import argparse
import json
import logging
import shutil
import sys

from argparse import RawTextHelpFormatter
from functools import reduce

try:
    import cxxfilt
except ModuleNotFoundError:
    cxxfilt = None

from intervaltree import IntervalTree

from polyfile import logger, version

from .polymerge import merge, polyfile_type_graph
from . import polytracker

log = logger.getStatusLogger("PolyMerge")


def parse_dataflow_ranges(dataflow):
    dataflow_ranges = None

    dataflow_from_start = None
    dataflow_to_end = None

    if dataflow is None:
        return dataflow_from_start, dataflow_to_end, dataflow_ranges

    for dataflow_range in dataflow:
        parts = dataflow_range.split(':')
        if len(parts) > 2:
            raise ValueError(f"Error: Invalid dataflow range {dataflow_range!r}")
        elif len(parts) == 1:
            start = parts[0]
            end = None
        else:
            start, end = parts
        if start:
            try:
                start = int(start)
            except ValueError:
                raise ValueError(f"Error: Invalid dataflow range start {dataflow_range!r}")
        else:
            start = None
        had_end = False
        if end is not None:
            if end:
                try:
                    end = int(end)
                except ValueError:
                    raise ValueError(f"Error: Invalid dataflow range end {dataflow_range!r}")
            else:
                had_end = True
                end = None
        if start is not None and end is not None:
            # "start:end"
            if start >= end:
                raise ValueError(f"Error: Dataflow range start must be less than end in {dataflow_range}")
            if dataflow_ranges is None:
                dataflow_ranges = IntervalTree()
            dataflow_ranges[start:end] = True
        elif start is not None:
            if had_end:
                # "start:"
                if dataflow_to_end is None:
                    dataflow_to_end = start
                else:
                    dataflow_to_end = min(dataflow_to_end, start)
            else:
                # "offset"
                if dataflow_ranges is None:
                    dataflow_ranges = IntervalTree()
                dataflow_ranges[start:start+1] = True
        elif end is not None:
            # ":end"
            if dataflow_from_start is None:
                dataflow_from_start = end
            else:
                dataflow_from_start = max(dataflow_from_start, end)
        elif had_end:
            # ":"
            dataflow_to_end = 0

    return dataflow_from_start, dataflow_to_end, dataflow_ranges


def main(argv=None):
    parser = argparse.ArgumentParser(description='''A utility to merge the JSON output of `polyfile`
with a polytracker.json file from PolyTracker.

https://github.com/trailofbits/polyfile/
https://github.com/trailofbits/polytracker/
''', formatter_class=RawTextHelpFormatter)
    parser.add_argument('FILES', type=argparse.FileType('r'), nargs='+', help='Path to the PolyFile JSON output and/or the PolyTracker JSON output. Merging will only occur if both files are provided. The `--cfg` and `--type-hierarchy` options can be used if only a single file is provided, but no merging will occur.')
    parser.add_argument('--cfg', '-c', type=str, default=None, help='Optional path to output a Graphviz .dot file representing the control flow graph of the program trace')
    parser.add_argument('--cfg-pdf', '-p', type=str, default=None, help='Similar to --cfg, but renders the graph to a PDF instead of outputting the .dot source')
    parser.add_argument('--dataflow', type=str, nargs='*', help='For the CFG generation options, only render functions that participated in dataflow. `--dataflow 10` means that only functions in the dataflow related to byte 10 should be included. `--dataflow 10:30` means that only functions operating on bytes 10 through 29 should be included. The beginning or end of a range can be omitted and will default to the beginning and end of the file, respectively. Multiple `--dataflow` ranges can be specified. `--dataflow :` will render the CFG only with functions that operated on tainted bytes. Omitting `--dataflow` will produce a CFG containing all functions.')
    parser.add_argument('--no-intermediate-functions', action='store_true', help='To be used in conjunction with `--dataflow`. If enabled, only functions in the dataflow graph if they operated on the tainted bytes. This can result in a disjoint dataflow graph.')
    parser.add_argument('--demangle', action='store_true', help='Demangle C++ function names in the CFG (requires that PolyFile was installed with the `demangle` option, or that the `cxxfilt` Python module is installed.)')
    parser.add_argument('--type-hierarchy', '-t', type=str, default=None, help='Optional path to output a Graphviz .dot file representing the type hierarchy extracted from PolyFile')
    parser.add_argument('--type-hierarchy-pdf', '-y', type=str, default=None, help='Similar to --type-hierarchy, but renders the graph to a PDF instead of outputting the .dot source')
    parser.add_argument('--diff', type=argparse.FileType('r'), nargs='*', help='Diff an arbitrary number of input polytracker.json files, all treated as the same class, against one or more polytracker.json provided after `--diff` arguments')
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

    build_cfg = args.cfg is not None or args.cfg_pdf is not None
    built_type_hierarchy = args.type_hierarchy is not None or args.type_hierarchy_pdf is not None

    if len(args.diff) > 0:
        input_program_traces = [polytracker.parse(json.load(diff_file)) for diff_file in args.FILES]
        program_traces_to_diff = [polytracker.parse(json.load(diff_file)) for diff_file in args.diff]

        def labeler(funcname):
            if args.demangle:
                if funcname.startswith('dfs$'):
                    funcname = funcname[4:]
                return cxxfilt.demangle(funcname)
            else:
                return funcname

        first_funcs = None
        for f in input_program_traces:
            fnames = set(labeler(fname) for fname in f.functions.keys())
            if first_funcs is None:
                first_funcs = fnames
            else:
                first_funcs &= fnames

        second_funcs = None
        for f in input_program_traces:
            fnames = set(labeler(fname) for fname in f.functions.keys())
            if second_funcs is None:
                second_funcs = fnames
            else:
                second_funcs &= fnames

        print('\n'.join(second_funcs ^ first_funcs))
        exit(0)

    if len(args.FILES) == 1:
        if build_cfg and built_type_hierarchy:
            parser.print_help()
            sys.stderr.write('\n')
            log.critical("Error: Two input files (PolyFile, PolyTracker) are required when both `--cfg` and `--type-hierarchy` options are enabled.")
            parser.exit()
        elif build_cfg:
            polyfile_json_file = None
            polytracker_json_file = args.FILES[0]
        elif built_type_hierarchy:
            polyfile_json_file = args.FILES[0]
            polytracker_json_file = None
        else:
            return 0
    elif len(args.FILES) != 2:
        parser.print_help()
        sys.stderr.write('\n')
        log.critical("Error: Expected at most two input files")
        parser.exit()
    else:
        polyfile_json_file = args.FILES[0]
        polytracker_json_file = args.FILES[1]

    if build_cfg and args.demangle and cxxfilt is None:
        log.critical("Error: The `cxxfilt` package is not installed. Either reinstall PolyFile with the `demangle` option enabled, or run `pip3 install cxxfilt`.")
        parser.exit()

    try:
        dataflow_from_start, dataflow_to_end, dataflow_ranges = parse_dataflow_ranges(args.dataflow)
    except ValueError as e:
        parser.print_help()
        sys.stderr.write('\n')
        log.critical(f"Error: {e!s}")
        parser.exit()

    if polyfile_json_file is not None:
        polyfile_json = json.load(polyfile_json_file)
        polyfile_json_file.close()
    else:
        polyfile_json = None
    if polytracker_json_file is not None:
        program_trace = polytracker.parse(json.load(polytracker_json_file))
        polytracker_json_file.close()
    else:
        program_trace = None

    if polyfile_json is not None and program_trace is not None:
        merged = merge(polyfile_json, program_trace)
        print(json.dumps(merged))

    if build_cfg:
        log.status("Reconstructing the runtime control flow graph...")
        cfg = program_trace.cfg

        def labeler(f):
            if args.demangle:
                funcname = f.name
                if funcname.startswith('dfs$'):
                    funcname = funcname[4:]
                return cxxfilt.demangle(funcname)
            else:
                return f.name

        if dataflow_from_start is not None or dataflow_to_end is not None or dataflow_ranges is not None:
            dataflow_functions = set()
            for f in program_trace.functions.values():
                check_more = False
                for offsets in f.input_bytes.values():
                    for offset in offsets:
                        if (dataflow_to_end is not None and offset >= dataflow_to_end) \
                                or (dataflow_from_start is not None and offset < dataflow_from_start) \
                                or (dataflow_ranges is not None and dataflow_ranges[offset]):
                            dataflow_functions.add(f)
                            break
                    else:
                        check_more = True
                    if not check_more:
                        break
                else:
                    log.debug(f"Function {f!r} did not operate on any tainted bytes")
            if not args.no_intermediate_functions:
                # add all functions that have both an ancestor and descendant
                # in the dominator tree that's also in in dataflow_functions
                doms = program_trace.cfg.dominator_forest
                orig_functions = frozenset(dataflow_functions)
                for f in program_trace.functions.values():
                    if f in orig_functions:
                        continue
                    if doms.ancestors(f).intersection(orig_functions) \
                            and doms.descendants(f).intersection(orig_functions):
                        log.debug(f"Adding intermediate function {f.name} to the dataflow graph")
                        dataflow_functions.add(f)

            node_filter = lambda func: func in dataflow_functions
        else:
            node_filter = None

        dot = cfg.to_dot(labeler=labeler, node_filter=node_filter)#(merged_json_obj=merged)
        log.clear_status()
        if args.cfg is not None:
            with open(args.cfg, 'w') as cfg_file:
                cfg_file.write(dot.source)
            log.info(f"Saved CFG .dot graph to {args.cfg}")
        if args.cfg_pdf is not None:
            log.status("Rendering the runtime CFG to a PDF...")
            rendered_path = dot.render(args.cfg_pdf, cleanup=True)
            log.clear_status()
            if rendered_path != args.cfg_pdf:
                shutil.move(rendered_path, args.cfg_pdf)
            log.info(f"Saved CFG graph PDF to {args.cfg_pdf}")

    if built_type_hierarchy:
        log.status("Building the input file type hierarchy...")
        type_dominators: cfg.DAG = polyfile_type_graph(polyfile_json).dominator_forest
        dot = type_dominators.to_dot()
        if args.type_hierarchy:
            with open(args.type_hierarchy, 'w') as dot_file:
                dot_file.write(dot.source)
            log.info(f"Saved type hierarchy .dot graph to {args.type_hierarchy}")
        if args.type_hierarchy_pdf is not None:
            log.status("Rendering the type hierarchy to a PDF...")
            rendered_path = dot.render(args.type_hierarchy_pdf, cleanup=True)
            log.clear_status()
            if rendered_path != args.type_hierarchy_pdf:
                shutil.move(rendered_path, args.type_hierarchy_pdf)
            log.info(f"Saved type hierarchy PDF to {args.type_hierarchy_pdf}")


if __name__ == '__main__':
    main()
