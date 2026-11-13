# PolyFile
<p align="center">
  <img src="logo/polyfile_name.png?raw=true" width="256" title="PolyFile">
</p>
<br />

[![PyPI version](https://badge.fury.io/py/polyfile.svg)](https://badge.fury.io/py/polyfile)
[![Tests](https://github.com/trailofbits/polyfile/workflows/Tests/badge.svg)](https://github.com/trailofbits/polyfile/actions)
[![Slack Status](https://slack.empirehacking.nyc/badge.svg)](https://slack.empirehacking.nyc)

A utility to identify and map the semantic and syntactic structure of files,
including polyglots, chimeras, and schizophrenic files. It has [a Python implementation of libmagic](#file-support) and can act as a drop-in replacement for the [`file` command](https://github.com/file/file). However, unlike `file`, PolyFile recurses into the files it identifies: the ZIP parser matches every decompressed member, the PDF parser matches every decoded stream, and every non-constant byte field of a parsed structure is matched again on its own. A few matchers also search for their magic anywhere in the input, so a ZIP archive that does not start at byte offset zero is still found. PolyFile does not scan every offset the way [binwalk](https://github.com/ReFirmLabs/binwalk) does; [issue #3532](https://github.com/trailofbits/polyfile/issues/3532) tracks that.

PolyFile can be used in conjunction with its sister tool
[PolyTracker](https://github.com/trailofbits/polytracker) for
_Automated Lexical Annotation and Navigation of Parsers_, a backronym
devised solely for the purpose of collectively referring to the tools
as _The ALAN Parsers Project_.

## Quickstart

PolyFile requires Python 3.11 or later.

You can install the latest stable version of PolyFile from PyPI with
[uv](https://docs.astral.sh/uv/):
```
uv tool install polyfile
```

Regex matching uses the native [`google-re2`](https://pypi.org/project/google-re2/) dependency,
which the installer installs automatically. If your platform has no compatible wheel, building
that dependency requires a C++ compiler, RE2 headers and libraries, and pybind11.

To run PolyFile once without installing it:
```
uvx polyfile <file>
```

To install PolyFile from source, clone the repository with its submodules and run uv in the
same directory as this README:
```
git submodule update --init --recursive
uv pip install .
```

Installing from source builds in an isolated environment, so it needs network access to fetch
the build backend. To build offline, install `setuptools>=83.0.0` yourself and run
`uv pip install --no-build-isolation .`.

Installing from PyPI reuses the parsers that the published distribution already carries.
Installing from a source checkout regenerates them, and only that path needs Java, which runs
the Kaitai Struct compiler that compiles the file format definitions.

This installs the `polyfile` executable in your path. The companion merge tool runs as
`python -m polymerge`.

## Usage

Running `polyfile` on a file with no arguments will mimic the behavior of `file --keep-going`:
```console
$ polyfile png-polyglot.png
PNG image data, 256 x 144, 8-bit/color RGB, non-interlaced
Brainfu** Program
Malformed PDF
PDF document, version 1.3,  1 pages
ZIP end of central directory record Java JAR archive 
```
To generate an interactive hex viewer for the file, use the `--html` option:
```console
$ polyfile --html output.html png-polyglot.png
```
The viewer renders any byte that no match describes in gray on a diagonal hatch, and reports how many
such bytes the file has above the hex dump.

Run `polyfile --help` for full usage instructions.

### Large files and recursive analysis

The default `file` output and `--format mime` identify the input without running format parsers.
Identification continues after finding a format so that secondary formats and polyglots remain
visible. Some matching rules search the entire input, so identification time can still grow with
the file size.

JSON, SBuD, and HTML output also parse recognized formats and recursively analyze supported
embedded or decoded content. Use `--max-depth 0` to prevent recursive content analysis while
retaining the input's identification and top-level structure:

```console
$ polyfile archive.zip --format json --no-contents --max-depth 0
```

The input has depth zero; higher limits allow more levels of content analysis. Depth limits do
not bound the input's identification work or speed up the default `file` and MIME output paths.
They help with formats that have recursive parsers. PolyFile currently identifies 7z archives
but does not parse their members; [issue #3685](https://github.com/trailofbits/polyfile/issues/3685)
tracks that capability.

Use `--only-match` with structured output to disable format parsing entirely. It does not reduce
the matching work for the default `file` or MIME outputs. For JSON and SBuD output,
`--no-contents` omits the input's base64 copy and reduces serialization work; it does not skip
identification or recursive analysis. HTML output requires that copy and cannot use
`--no-contents`.

### Terminal status

When stderr is a terminal, PolyFile displays the discovered file types, elapsed time, and
progress through the current matcher pass. Recursive analysis can discover additional work,
so the progress bar measures tests in that pass rather than a percentage of the entire scan.
The live tree shows recent matches and their ancestors; the complete file-type tree remains
in your terminal when analysis finishes. Parser fields are omitted from this view.

For example, the final stderr view for `--format mime` on a 67-byte PNG resembles:

```text
PolyFile  sample.png
Matches
└── image/png  @ 0x0 | 67 bytes | file
Complete | 1 matches | 0.02s
```

Each offset belongs to the indicated source: `file` is the original input, and `decoded:0`,
`decoded:1`, and subsequent identifiers refer to decoded buffers. Embedded classifications
include member names when available. Limitations and interrupted scans retain their partial
results and identify why analysis stopped.

The display uses the analysis your output format already performs. The `file`, `mime`, and
`explain` formats identify the input; JSON, SBuD, and HTML also expose recursively discovered
files. The default `file` view uses identification descriptions; MIME and recursive views use
MIME labels. To watch recursive analysis while saving JSON, run:

```console
$ polyfile --format json --no-contents sample.zip > sample.json
```

Result data goes to stdout or the selected `--output` path. All logging and status go to
stderr. When stderr is redirected, live status and ordinary informational messages are
suppressed; warnings and errors remain as plain text. Explicit `--debug` and `--trace`
diagnostics also remain available. Use `--quiet` to suppress all logging and status.

PolyFile respects `NO_COLOR`, prints a static final summary with `TERM=dumb`, and disables
live status in the interactive debugger.

### Interactive Debugger

PolyFile has an interactive debugger both for its file matching and parsing. It can be used to debug a libmagic pattern 
definition, determine why a specific file fails to be classified as the expected MIME type, or step through a parser.
You can run PolyFile with the debugger enabled using the `-db` option.

### File Support

PolyFile has a cleanroom, [Python implementation of the libmagic file classifier](#libmagic-implementation), and supports all 896 MIME types that it can identify.

It currently has support for parsing and semantically mapping the following formats:
* PDF, using [pdfminer.six](https://github.com/pdfminer/pdfminer.six) to decode objects and streams
* ZIP, including recursive identification of all ZIP contents
* JPEG/JFIF, using its [Kaitai Struct grammar](https://formats.kaitai.io/jpeg/index.html)
* [iNES](https://wiki.nesdev.com/w/index.php/INES)
* [Any other format](https://formats.kaitai.io/index.html) specified in a [KSY grammar](https://doc.kaitai.io/user_guide.html)

For an example that exercises all of these file formats, run:
```bash
curl -v --silent https://www.sultanik.com/files/ESultanikResume.pdf | polyfile --html ESultanikResume.html -
```

Prior to PolyFile version 0.3.0, it used the [TrID database](http://mark0.net/soft-trid-deflist.html) for file
identification rather than the libmagic file definitions. This proved to be very slow (since TrID has many duplicate
entries) and prone to false positives (since TrID's file definitions are much simpler than libmagic's). The original
TrID matching code is still shipped with PolyFile and can be invoked programmatically, but it is not used by default.

### Output Format

PolyFile has several options for outputting its results, specified by its `--format` option. For computer-readable output, PolyFile has an extension of the [SBuD](https://github.com/corkami/sbud) JSON format described [in the documentation](https://github.com/trailofbits/polyfile/blob/master/docs/json_format.md). Prior to version 0.5.0 this was the default output format of PolyFile. However, now the default output format is to mimic the behavior of the `file` command. To maintain the original behavior, use the `--format sbud` option.

The `json` and `sbud` formats include a `b64contents` key holding a base64 encoding of the entire input, so their output grows with the size of the file you analyze. Pass `--no-contents` to leave that key out; PolyFile then skips the encoding instead of computing it and throwing the result away. The key is omitted rather than emptied, so a consumer that needs the contents fails instead of reading the input as empty. The HTML hex viewer is built from the contents, so you cannot combine `--no-contents` with `--format html` or `--html`.

### libmagic Implementation

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

## Extending PolyFile

Instructions on extending PolyFile to support more file formats with new matchers and parsers is described [in the documentation](https://github.com/trailofbits/polyfile/blob/master/docs/extending_polyfile.md).

## License and Acknowledgements

This research was developed by [Trail of
Bits](https://www.trailofbits.com/) with funding from the Defense
Advanced Research Projects Agency (DARPA) under the SafeDocs program
as a subcontractor to [Galois](https://galois.com). It is licensed under the [Apache 2.0 license](https://github.com/trailofbits/polyfile/blob/master/LICENSE).
© 2019, Trail of Bits.

PolyFile generates most of its parsers from the [Kaitai Struct format gallery](https://formats.kaitai.io/),
where each format specification carries its own license. A generated parser is a derivative work of
its specification, so PolyFile builds parsers only from specifications under a permissive license.
The distributed package therefore contains no copyleft code, and the specifications PolyFile cannot
redistribute are excluded from the source distribution. For the details, see
[Licensing of generated parsers](https://github.com/trailofbits/polyfile/blob/master/docs/extending_polyfile.md#licensing-of-generated-parsers).
