# PolyFile
<p align="center">
  <img src="logo/polyfile_name.png?raw=true" width="256" title="PolyFile">
</p>
<br />

[![PyPI version](https://badge.fury.io/py/polyfile.svg)](https://badge.fury.io/py/polyfile)
[![Tests](https://github.com/trailofbits/polyfile/workflows/Tests/badge.svg)](https://github.com/trailofbits/polyfile/actions)
[![Slack Status](https://slack.empirehacking.nyc/badge.svg)](https://slack.empirehacking.nyc)

A utility to identify and map the semantic and syntactic structure of files,
including polyglots, chimeras, and schizophrenic files. It has [a pure-Python implementation of libmagic](#file-support) and can act as a drop-in replacement for the [`file` command](https://github.com/file/file). However, unlike `file`, PolyFile can recursively identify embedded files, like [binwalk](https://github.com/ReFirmLabs/binwalk).

PolyFile can be used in conjunction with its sister tool
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
pip3 install .
```

Important: Before installing from source, make sure Java is installed. Java is used to
run the Kaitai Struct compiler, which compiles the file format definitions.

This will automatically install the `polyfile` and `polymerge` executables in your path.

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
Found a file of type application/pdf at byte offset 0
Found a file of type application/x-brainfuck at byte offset 0
Found a file of type image/png at byte offset 0
Found a file of type application/zip at byte offset 0
Found a file of type application/java-archive at byte offset 0
Saved HTML output to output.html
```

Run `polyfile --help` for full usage instructions.

### Interactive Debugger

PolyFile has an interactive debugger both for its file matching and parsing. It can be used to debug a libmagic pattern 
definition, determine why a specific file fails to be classified as the expected MIME type, or step through a parser.
You can run PolyFile with the debugger enabled using the `-db` option.

### File Support

PolyFile has a cleanroom, [pure Python implementation of the libmagic file classifier](#libmagic-implementation), and supports all 263 MIME types that it can identify.

It currently has support for parsing and semantically mapping the following formats:
* PDF, using an instrumented version of [Didier Stevens' public domain, permissive, forensic parser](https://blog.didierstevens.com/programs/pdf-tools/)
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

PolyFile has several options for outputting its results, specified by its `--format` option. For computer-readable output, PolyFile has an extension of the [SBuD](https://github.com/corkami/sbud) JSON format described [in the documentation](docs/json_format.md). Prior to version 0.5.0 this was the default output format of PolyFile. However, now the default output format is to mimic the behavior of the `file` command. To maintain the original behavior, use the `--format sbud` option.

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

Instructions on extending PolyFile to support more file formats with new matchers and parsers is described [in the documentation]([in the documentation](docs/extending_polyfile.md)).

## License and Acknowledgements

This research was developed by [Trail of
Bits](https://www.trailofbits.com/) with funding from the Defense
Advanced Research Projects Agency (DARPA) under the SafeDocs program
as a subcontractor to [Galois](https://galois.com). It is licensed under the [Apache 2.0 license](LICENSE).
© 2019, Trail of Bits.
