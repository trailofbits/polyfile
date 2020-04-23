# PolyFile
<p align="center">
  <img src="logo/polyfile_name.png?raw=true" width="256" title="PolyFile">
</p>
<br />

[![Build Status](https://travis-ci.com/trailofbits/polyfile.svg?branch=master)](https://travis-ci.com/trailofbits/polyfile)
[![PyPI version](https://badge.fury.io/py/polyfile.svg)](https://badge.fury.io/py/polyfile)
[![Slack Status](https://empireslacking.herokuapp.com/badge.svg)](https://empireslacking.herokuapp.com)

A utility to identify and map the semantic structure of files,
including polyglots, chimeras, and schizophrenic files. It can be used
in conjunction with its sister tool
[PolyTracker](https://github.com/trailofbits/polytracker) for
_Automated Lexical Annotation and Navigation of Parsers_, a backronym
devised solely for the purpose of collectively referring to the tools
as _The ALAN Parsers Project_.

## Quickstart

You can install the latest stable version of PolyFile from PyPI:
```
pip3 install polyfile
```

To install PolyFile from source, in the same directory as this README, run:
```
pip3 install -e .
```

This will automatically install the `polyfile` and `polymerge` executables in your path.

## Usage

```
usage: polyfile [-h] [--filetype FILETYPE] [--list] [--html HTML]
                [--try-all-offsets] [--only-match] [--debug] [--quiet]
                [--version] [-dumpversion]
                [FILE]

A utility to recursively map the structure of a file.

positional arguments:
  FILE                  The file to analyze; pass '-' or omit to read from
                        STDIN

optional arguments:
  -h, --help            show this help message and exit
  --filetype FILETYPE, -f FILETYPE
                        Explicitly match against the given filetype (default
                        is to match against all filetypes)
  --list, -l            list the supported filetypes (for the `--filetype`
                        argument) and exit
  --html HTML, -t HTML  Path to write an interactive HTML file for exploring
                        the PDF
  --try-all-offsets, -a
                        Search for a file match at every possible offset; this
                        can be very slow for larger files
  --only-match, -m      Do not attempt to parse known filetypes; only match
                        against file magic
  --debug, -d           Print debug information
  --quiet, -q           Suppress all log output (overrides --debug)
  --version, -v         Print PolyFile's version information to STDERR
  -dumpversion          Print PolyFile's raw version information to STDOUT and
                        exit
```

To generate a JSON mapping of a file, run:

```
polyfile INPUT_FILE > output.json
```

You can optionally have PolyFile output an interactive HTML page containing a labeled, interactive hexdump of the file:
```
polyfile INPUT_FILE --html output.html > output.json
```

## File Support

PolyFile can identify all 10,000+ file formats in the [TrID database](http://mark0.net/soft-trid-deflist.html).
It currently has support for parsing and semantically mapping the following formats:
* PDF, using an instrumented version of [Didier Stevens' public domain, permissive, forensic parser](https://blog.didierstevens.com/programs/pdf-tools/)
* ZIP, including reursive identification of all ZIP contents
* JPEG/JFIF, using its [Kaitai Struct grammar](https://formats.kaitai.io/jpeg/index.html)
* [iNES](https://wiki.nesdev.com/w/index.php/INES)
* [Any other format](https://formats.kaitai.io/index.html) specified in a [KSY grammar](https://doc.kaitai.io/user_guide.html)

For an example that exercises all of these file formats, run:
```bash
curl -v --silent https://www.sultanik.com/files/ESultanikResume.pdf | polyfile --html ESultanikResume.html - > ESultanikResume.json
```

## Output Format

PolyFile outputs its mapping in an extension of the [SBuD](https://github.com/corkami/sbud) JSON format described [in the documentation](docs/json_format.md).

## Merging Output From PolyTracker

[PolyTracker](https://github.com/trailofbits/polytracker) is PolyFile’s sister utility for automatically instrumenting
a parser to track the input byte offsets operated on by each function. The output of both tools can be merged to
automatically label the semantic purpose of the functions in a parser. For example, given an instrumented black-box
binary, we can quickly determine which functions in the program are responsible for parsing which parts of the input
file format’s grammar. This is an area of active research intended to achieve fully automated grammar extraction from a
parser.

A separate utility called `polymerge` is installed with PolyFile specifically designed to merge the output of both
tools.

```
usage: polymerge [-h] [--cfg CFG] [--cfg-pdf CFG_PDF]
                 [--dataflow [DATAFLOW [DATAFLOW ...]]]
                 [--no-intermediate-functions] [--demangle]
                 [--type-hierarchy TYPE_HIERARCHY]
                 [--type-hierarchy-pdf TYPE_HIERARCHY_PDF]
                 [--diff [DIFF [DIFF ...]]] [--debug] [--quiet] [--version]
                 [-dumpversion]
                 FILES [FILES ...]

A utility to merge the JSON output of `polyfile`
with a polytracker.json file from PolyTracker.

https://github.com/trailofbits/polyfile/
https://github.com/trailofbits/polytracker/

positional arguments:
  FILES                 Path to the PolyFile JSON output and/or the PolyTracker JSON output. Merging will only occur if both files are provided. The `--cfg` and `--type-hierarchy` options can be used if only a single file is provided, but no merging will occur.

optional arguments:
  -h, --help            show this help message and exit
  --cfg CFG, -c CFG     Optional path to output a Graphviz .dot file representing the control flow graph of the program trace
  --cfg-pdf CFG_PDF, -p CFG_PDF
                        Similar to --cfg, but renders the graph to a PDF instead of outputting the .dot source
  --dataflow [DATAFLOW [DATAFLOW ...]]
                        For the CFG generation options, only render functions that participated in dataflow. `--dataflow 10` means that only functions in the dataflow related to byte 10 should be included. `--dataflow 10:30` means that only functions operating on bytes 10 through 29 should be included. The beginning or end of a range can be omitted and will default to the beginning and end of the file, respectively. Multiple `--dataflow` ranges can be specified. `--dataflow :` will render the CFG only with functions that operated on tainted bytes. Omitting `--dataflow` will produce a CFG containing all functions.
  --no-intermediate-functions
                        To be used in conjunction with `--dataflow`. If enabled, only functions in the dataflow graph if they operated on the tainted bytes. This can result in a disjoint dataflow graph.
  --demangle            Demangle C++ function names in the CFG (requires that PolyFile was installed with the `demangle` option, or that the `cxxfilt` Python module is installed.)
  --type-hierarchy TYPE_HIERARCHY, -t TYPE_HIERARCHY
                        Optional path to output a Graphviz .dot file representing the type hierarchy extracted from PolyFile
  --type-hierarchy-pdf TYPE_HIERARCHY_PDF, -y TYPE_HIERARCHY_PDF
                        Similar to --type-hierarchy, but renders the graph to a PDF instead of outputting the .dot source
  --diff [DIFF [DIFF ...]]
                        Diff an arbitrary number of input polytracker.json files, all treated as the same class, against one or more polytracker.json provided after `--diff` arguments
  --debug, -d           Print debug information
  --quiet, -q           Suppress all log output (overrides --debug)
  --version, -v         Print PolyMerge's version information and exit
  -dumpversion          Print PolyMerge's raw version information and exit
```

The output of `polymerge` is the same as [PolyFile’s output format](docs/json_format.md), augmented with the following:
1. For each semantic label in the hierarchy, a list of…
    1. …functions that operated on bytes tainted with that label; and
    2. …functions whose control flow was influenced by bytes tainted with that label.
2. For each type within the semantic hierarchy, a list of functions that are “most specialized” in processing that type.
   This process is described in the next section.

`polymerge` can also optionally emit a Graphviz `.dot` file or rendered PDF of the runtime control-flow graph recorded
by PolyTracker. 

### Identifying Function Specializations 

As mentioned above, `polymerge` attempts to match each semantic type of the input file to a set of functions that are
“most specialized” in operating on that type. This is an active area of academic research  and is likely to change in
the future, but here is the current method employed by `polymerge`:
1. For each semantic type in the input file, collect the functions that operated on bytes from that type;
2. For each function, calculate the Shannon entropy of the different types on which that function operated;
3. Sort the functions by entropy, and select the functions in the smallest standard deviation; and
4. Keep the functions that are shallowest in the dominator tree of the runtime control-flow graph.

## Current Status and Known Deficiencies
* The instrumented Kaitai Struct parser generator implementation has only been tested on the JPEG/JFIF grammar;
  other KSY definitions may exercise portions of the KSY specification that have not yet been implemented

## License and Acknowledgements

This research was developed by [Trail of
Bits](https://www.trailofbits.com/) with funding from the Defense
Advanced Research Projects Agency (DARPA) under the SafeDocs program
as a subcontractor to [Galois](https://galois.com). It is licensed under the [Apache 2.0 lisense](LICENSE).
The [PDF parser](polyfile/pdfparser.py) is modified from the parser developed by Didier Stevens and released into the
 public domain. © 2019, Trail of Bits.
