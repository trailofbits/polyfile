# PolyFile
<p align="center">
  <img src="logo/polyfile_name.png?raw=true" width="256" title="PolyFile">
</p>
<br />

[![PyPI version](https://badge.fury.io/py/polyfile.svg)](https://badge.fury.io/py/polyfile)
[![Tests](https://github.com/trailofbits/polyfile/workflows/Tests/badge.svg)](https://github.com/trailofbits/polyfile/actions)
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

Important: Before installing from source, make sure Java is installed. Java is used to
run the Kaitai Struct compiler, which compiles the file format definitions.

This will automatically install the `polyfile` and `polymerge` executables in your path.

## Usage

```
usage: polyfile [-h] [--format {mime,html,json,sbud}] [--output OUTPUT]
                [--filetype FILETYPE] [--list] [--html HTML]
                [--only-match-mime] [--only-match] [--require-match]
                [--max-matches MAX_MATCHES] [--debugger] [--no-debug-python]
                [--quiet | --debug | --trace] [--version] [-dumpversion]
                [FILE]

A utility to recursively map the structure of a file.

positional arguments:
  FILE                  the file to analyze; pass '-' or omit to read from STDIN

optional arguments:
  -h, --help            show this help message and exit
  --format {mime,html,json,sbud}, -r {mime,html,json,sbud}
                        PolyFile's output format

                        Output formats are:
                        mime ... the detected MIME types associated with the file,
                                 like the output of the `file` command
                        html ... an interactive HTML-based hex viewer
                        json ... a modified version of the SBUD format in JSON syntax
                        sbud ... equivalent to 'json'

                        Multiple formats can be output at once:

                            polyfile INPUT_FILE -f mime -f json

                        Their output will be concatenated to STDOUT in the order that
                        they occur in the arguments.

                        To save each format to a separate file, see the `--output` argument.

                        If no format is specified, PolyFile defaults to `--format sbud`,
                        but this will change to `--format mime` in v0.5.0
  --output OUTPUT, -o OUTPUT
                        an optional output path for `--format`

                        Each instance of `--output` applies to the previous instance
                        of the `--format` option.

                        For example:

                            polyfile INPUT_FILE --format html --output output.html \
                                                --format sbud --output output.json

                        will save HTML to to `output.html` and SBUD to `output.json`.
                        No two outputs can be directed at the same file path.

                        The path can be '-' for STDOUT.
                        If an `--output` is omitted for a format,
                        then it will implicitly be printed to STDOUT.
  --filetype FILETYPE, -f FILETYPE
                        explicitly match against the given filetype or filetype wildcard (default is to match against all filetypes)
  --list, -l            list the supported filetypes for the `--filetype` argument and exit
  --html HTML, -t HTML  path to write an interactive HTML file for exploring the PDF;
                        equivalent to `--format html --output HTML`
  --only-match-mime, -I
                        "just print out the matching MIME types for the file, one on each line;
                        equivalent to `--format mime`
  --only-match, -m      do not attempt to parse known filetypes; only match against file magic
  --require-match       if no matches are found, exit with code 127
  --max-matches MAX_MATCHES
                        stop scanning after having found this many matches
  --debugger, -db       drop into an interactive debugger for libmagic file definition matching and PolyFile parsing
  --no-debug-python     by default, the `--debugger` option will break on custom matchers and prompt to debug using PDB. This option will suppress those prompts.
  --quiet, -q           suppress all log output
  --debug, -d           print debug information
  --trace, -dd          print extra verbose debug information
  --version, -v         print PolyFile's version information to STDERR
  -dumpversion          print PolyFile's raw version information to STDOUT and exit
```

To generate a JSON mapping of a file, run:

```
polyfile INPUT_FILE > output.json
```

You can optionally have PolyFile output an interactive HTML page containing a labeled, interactive hexdump of the file:
```
polyfile INPUT_FILE --html output.html > output.json
```

### Interactive Debugger

PolyFile has an interactive debugger both for its file matching and parsing. It can be used to debug a libmagic pattern 
definition, determine why a specific file fails to be classified as the expected MIME type, or step through a parser.
You can run PolyFile with the debugger enabled using the `-db` option.

### File Support

PolyFile has a cleanroom, [pure Python implementation of the libmagic file classifier](#libmagic-implementation), and
supports all 263 MIME types that it can identify.

It currently has support for parsing and semantically mapping the following formats:
* PDF, using an instrumented version of [Didier Stevens' public domain, permissive, forensic parser](https://blog.didierstevens.com/programs/pdf-tools/)
* ZIP, including recursive identification of all ZIP contents
* JPEG/JFIF, using its [Kaitai Struct grammar](https://formats.kaitai.io/jpeg/index.html)
* [iNES](https://wiki.nesdev.com/w/index.php/INES)
* [Any other format](https://formats.kaitai.io/index.html) specified in a [KSY grammar](https://doc.kaitai.io/user_guide.html)

For an example that exercises all of these file formats, run:
```bash
curl -v --silent https://www.sultanik.com/files/ESultanikResume.pdf | polyfile --html ESultanikResume.html - > ESultanikResume.json
```

Prior to PolyFile version 0.3.0, it used the [TrID database](http://mark0.net/soft-trid-deflist.html) for file
identification rather than the libmagic file definitions. This proved to be very slow (since TrID has many duplicate
entries) and prone to false positives (since TrID's file definitions are much simpler than libmagic's). The original
TrID matching code is still shipped with PolyFile and can be invoked programmatically, but it is not used by default.

### Output Format

PolyFile outputs its mapping in an extension of the [SBuD](https://github.com/corkami/sbud) JSON format described [in the documentation](docs/json_format.md).

PolyFile can also emit a standalone HTML document that contains an interactive hex viewer as well as syntax trees for
the discovered file formats. Simply pass the `--html` argument to PolyFile with an output path:
```console
$ polyfile input_file --html output.html
```

### libMagic Implementation

PolyFile has a cleanroom implementation of [libmagic (used in the `file` command)](https://github.com/file/file).
It can be invoked programmatically by running:
```python
from polyfile.magic import MagicMatcher

with open("file_to_test", "rb") as f:
    # the default instance automatically loads all file definitions
    for match in MagicMatcher.DEFAULT_INSTANCE.match(f.read()):
        for mimetype in match.mimetypes:
            print(f"Matched MIME: {mimetype}")
        print(f"Match string: {match!s}")
```
To load a specific or custom file definition:
```python
list_of_paths_to_definitions = ["def1", "def2"]
matcher = MagicMatcher.parse(*list_of_paths_to_definitions)
with open("file_to_test", "rb") as f:
    for match in matcher.match(f.read()):
        ...
```

### Debugging the libmagic DSL
`libmagic` has an esoteric, poorly documented doman-specific language (DSL) for specifying its matching signatures.
You can read the minimal and—as we have discovered in our cleanroom implementation—_incomplete_ documentation by running
`man 5 magic`. PolyFile implements an interactive debugger for stepping through the DSL specifications, modeled after
GDB. You can enter this debugger by passing the `--debugger` or `-db` argument to PolyFile. It is useful for both
implementing new `libmagic` DSLs, as well as figuring out why an existing DSL fails to match against a given file.
```console
$ polyfile -db input_file
PolyFile 0.3.5
Copyright ©2021 Trail of Bits
Apache License Version 2.0 https://www.apache.org/licenses/

For help, type "help".
(polyfile) help
help ....... print this message
continue ... continue execution until the next breakpoint is hit
step ....... step through a single magic test
next ....... continue execution until the next test that matches
where ...... print the context of the current magic test (aliases: info stack and backtrace)
test ....... test the following libmagic DSL test at the current position
print ...... print the computed absolute offset of the following libmagic DSL offset
breakpoint . list the current breakpoints or add a new one
delete ..... delete a breakpoint
quit ....... exit the debugger
```

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
                 [--dataflow [DATAFLOW ...]] [--no-intermediate-functions]
                 [--demangle] [--type-hierarchy TYPE_HIERARCHY]
                 [--type-hierarchy-pdf TYPE_HIERARCHY_PDF] [--diff [DIFF ...]]
                 [--debug] [--quiet] [--version] [-dumpversion]
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
  --dataflow [DATAFLOW ...]
                        For the CFG generation options, only render functions that participated in dataflow. `--dataflow 10` means that only functions in the dataflow related to byte 10 should be included. `--dataflow 10:30` means that only functions operating on bytes 10 through 29 should be included. The beginning or end of a range can be omitted and will default to the beginning and end of the file, respectively. Multiple `--dataflow` ranges can be specified. `--dataflow :` will render the CFG only with functions that operated on tainted bytes. Omitting `--dataflow` will produce a CFG containing all functions.
  --no-intermediate-functions
                        To be used in conjunction with `--dataflow`. If enabled, only functions in the dataflow graph if they operated on the tainted bytes. This can result in a disjoint dataflow graph.
  --demangle            Demangle C++ function names in the CFG (requires that PolyFile was installed with the `demangle` option, or that the `cxxfilt` Python module is installed.)
  --type-hierarchy TYPE_HIERARCHY, -t TYPE_HIERARCHY
                        Optional path to output a Graphviz .dot file representing the type hierarchy extracted from PolyFile
  --type-hierarchy-pdf TYPE_HIERARCHY_PDF, -y TYPE_HIERARCHY_PDF
                        Similar to --type-hierarchy, but renders the graph to a PDF instead of outputting the .dot source
  --diff [DIFF ...]     Diff an arbitrary number of input polytracker.json files, all treated as the same class, against one or more polytracker.json provided after `--diff` arguments
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

## License and Acknowledgements

This research was developed by [Trail of
Bits](https://www.trailofbits.com/) with funding from the Defense
Advanced Research Projects Agency (DARPA) under the SafeDocs program
as a subcontractor to [Galois](https://galois.com). It is licensed under the [Apache 2.0 license](LICENSE).
© 2019, Trail of Bits.
