# Extending PolyFile

Matchers classify byte sequences. Parsers map a classified sequence into a best-effort tree.

## Public Python API

Starting with PolyFile 1.0, the interfaces below and the documented import paths, call
signatures, type annotations, and behavior of their operations form the public contract.
Patch and minor releases preserve compatibility for callers of these APIs. PolyFile gives
at least one minor release of notice before removing a deprecated API in a major release.
The release notes identify the deprecated API and its replacement when one exists, and calls
emit `DeprecationWarning` where practical. Type checkers can use the installed package's
annotations because it includes the [`py.typed` marker](https://typing.python.org/en/latest/spec/distributing.html#packaging-type-information).

| Import from | Supported interface |
| --- | --- |
| `polyfile` | `Matcher`, `Match`, `Submatch`, `AnalysisLimits`, and `SourceSpan` for analysis and its results. `Parser`, `PARSERS`, `register_parser`, and `InvalidMatch` for parser extensions. |
| `polyfile` | `__version__` gives the installed version. `main(argv=None)` runs the CLI. Explicit arguments include the executable name. |
| `polyfile.polyfile` | `Analyzer` for analyzing a named file and producing an SBuD report. |
| `polyfile.magic` | `MagicMatcher` and `MatchContext` for classification. The [matcher extension hooks](#implement-a-python-matcher) describe `MagicTest`, `AbsoluteOffset`, `TestType`, `TestResult`, `MatchedTest`, and `FailedTest`. |
| `polyfile.fileutils` | `FileStream` for [bounded binary reads](#read-from-a-parser-stream). |
| `polyfile.expressions`, `polyfile.structs` | The [expression evaluator](#standalone-expression-evaluator) and [binary struct helpers](#struct-parsing) documented in this guide. |
| `polyfile.search`, `polyfile.serialization` | The [standalone search and serialization APIs](search_serialization.md). |

Treat other operations as implementation details. Built-in magic definitions and parser
coverage can evolve as file-format support changes. Treat the ordering of separate matches
and of parsers registered for the same MIME type as unspecified.

### Analyze input

- `Matcher(parse=True, matcher=None, *, limits=None)` uses the built-in `MagicMatcher` unless you
  supply one. `match(file_stream, parent=None)` yields structural `Match` objects, including
  descendants as parsers produce them. `parse=False` yields MIME match nodes and skips parser
  dispatch. `identify(file_stream)` skips parsing and yields `polyfile.magic.Match`
  classifications. Both methods accept bytes, a path as a string or `Path`, or a seekable binary
  stream. Analysis starts at the beginning of the supplied input or bounded view. A stream you
  supply stays open by default, and its position may change.
- `Analyzer(path, parse=True, magic_matcher=None, *, limits=None)` accepts a string or `Path`.
  `matches()` yields root structural matches and populates their children as you advance the
  iterator. Exhaust it before inspecting a complete tree. `magic_matches()` yields
  classifications, including those with no MIME type, and `mime_types()` yields
  `(mime_type, classification)` pairs. `close()` ends active scans and releases their resources.
- `Analyzer.sbud(matches=None, include_contents=True)` returns a JSON-serializable dictionary
  following the [SBuD format](json_format.md). It consumes the analysis or the supplied iterable
  before serializing the trees. Set `include_contents=False` to omit `b64contents`.

```python
from polyfile import Matcher

matches = list(Matcher().match(b'{"example": true}'))
assert any(match.name == "application/json" for match in matches)
```

Recursive matching is parser-directed. Parsers inspect meaningful regions such as archive
members and decoded streams and can pass them to `Matcher.match()` with a parent node. Individual
magic definitions can also search beyond offset zero. PolyFile does not run its classifier at
every offset. See the [decision on exhaustive scanning](https://github.com/trailofbits/polyfile/issues/3532)
and [recursive analysis limits](#limit-recursive-analysis).

### Read a match tree

`Match` and `Submatch` provide `name` (the MIME type or structural field type), `display_name`,
`match` (the stored value), `parent`, `children`, `source`, `offset`, and `length`.
Iterating or indexing a node accesses its immediate children. Offsets count bytes in the source
identified by `source`. `relative_offset` counts from the parent when it uses the same source
and from the start of the node's source otherwise. Use `to_obj()` or `json()` to serialize
the node and its descendants.

`SourceSpan(source, offset, size)` describes a byte interval contributing to a value. When you
pass spans as a node's `dependencies`, supply the source identifier for each interval. A
dependency describes contributing input, while `offset` and `length` locate the node itself.
See [physical and decoded sources](json_format.md#physical-and-decoded-sources).

## Standalone expression evaluator

Use `polyfile.expressions.parse` in Python to evaluate an expression over field values you supply.
Parse the text once, then pass a mapping of names to values each time you call `interpret`.
This example calculates the payload size of an optional record.

```python
from polyfile.expressions import parse

size = parse("record.present ? record.count * record.width : 0")
assert size.interpret({"record": {"present": True, "count": 3, "width": 4}}) == 12
assert size.interpret({"record": {"present": False}}) == 0
```

Write integer literals in decimal or with a `0x`, `0o`, or `0b` prefix. Identifiers start with an
ASCII letter or underscore and can also contain digits. Whitespace is optional around symbolic
operators. Parentheses group expressions. The following rows list operators from highest to lowest
precedence.

| Operators | Behavior |
| --- | --- |
| `.`, `::` | Read a literal name. Use `record.field` for a mapping key, or `enum::name` for a named enum member or mapping entry. Access chains run left to right. |
| Unary `+`, `-`, `not`, `~` | Identity, numeric negation, logical negation, and bitwise complement. |
| `*`, `/`, `%` | Multiplication, floor division, and remainder. |
| Binary `+`, `-` | Addition and subtraction. |
| `<<`, `>>` | Bit shifts. |
| `<`, `<=`, `>`, `>=` | Ordering. |
| `==`, `!=` | Equality. |
| `&` | Bitwise AND. |
| `^` | Bitwise XOR. |
| `\|` | Bitwise OR. |
| `and` | Return the first falsy operand or the last operand. |
| `or` | Return the first truthy operand or the last operand. |
| `condition ? yes : no` | Evaluate the selected branch. Nested conditionals associate to the right. |

Addition and comparisons use the operands' Python behavior. For example, adding two strings
concatenates them. Operators that require integers accept integers, decimal text, and unsigned
big-endian `bytes` or `bytearray` values. Empty text and byte sequences convert to zero.

`parse` raises `ValueError` for invalid syntax. During evaluation, an unknown identifier or
missing mapping key raises `KeyError`. Applying `.` to a non-mapping raises `TypeError`.
Conversion and arithmetic errors propagate from the selected operands. The `and`, `or`, and
conditional operators skip lookups and calculations in branches they do not take.

## Matchers

### Use a magic definition

`MagicMatcher.DEFAULT_INSTANCE` contains the bundled definitions. Use
`MagicMatcher.parse(*def_files)` for a separate classifier loaded from string or `Path` filenames.
`MagicMatcher(tests=())` accepts an iterable of Python tests. Use
`add(test, test_type=TestType.UNKNOWN)` to register a test instance or load definitions from a
`Path`. It returns the registered tests.

`MagicMatcher.match(to_match)` yields `polyfile.magic.Match` classifications with iterable
`mimetypes` and `extensions` and a human-readable description through `str(match)`. Pass bytes,
a path, a binary stream, or a `MatchContext(data, path=None, only_match_mime=False,
decoded_from=None)`. Use `only_match_mime=True` to filter out results with no MIME type.
`MatchContext.load(stream_or_path, only_match_mime=False)` loads a path or reads a stream from
its current cursor. The `data` attribute holds the matched bytes. When `decoded_from` names
an encoding, classification offsets refer to that decoded buffer.

The bundled magic library mirrors the `file` submodule. See
[how to update it](updating_libmagic_defs.md). For custom definitions, see `man 5 magic` and
the [libmagic DSL overview](https://blog.trailofbits.com/2022/07/01/libmagic-the-blathering/).
The example below loads a test for the NITF signature. The
[NITF matcher](../polyfile/nitf.py) shows the project's full definition.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from polyfile.magic import MagicMatcher

with TemporaryDirectory() as directory:
    definition = Path(directory) / "nitf"
    definition.write_bytes(b"0 string NITF02.10 NITF\n!:mime application/vnd.nitf\n")
    nitf_matcher = MagicMatcher.parse(definition)

assert any(
    "application/vnd.nitf" in result.mimetypes
    for result in nitf_matcher.match(b"NITF02.10\x00")
)
```

Regex tests use [RE2 syntax](https://github.com/google/re2/wiki/Syntax) and select the
leftmost, longest byte match. Matching is independent of the caller's locale; case-insensitive
flags fold ASCII letters. Lookaround assertions and backreferences are unsupported. A custom
definition containing unsupported syntax fails with its filename and line number. Rewrite it
using supported expressions or a Python matcher. Regex tests never fall back to a backtracking
engine.

See [custom magic compatibility](libmagic_compatibility.md) for supported modifier spellings,
value boundaries, and deliberate differences from libmagic.

### Implement a Python matcher

Subclass `MagicTest` and pass an offset such as `AbsoluteOffset(0)` to its constructor. Supply
a MIME type through `mime`, a description through `message`, and any filename suffixes through
`extensions`. Implement both methods below.

- `subtest_type() -> TestType` selects the pass. Use `TestType.BINARY` to match against input
  bytes or `TestType.TEXT` for recognized text.
- `test(data, absolute_offset, parent_match) -> TestResult` receives the matching buffer, the
  computed byte offset into that buffer, and the optional parent test result. Return
  `MatchedTest` with the value, offset, and length when the signature matches. Return
  `FailedTest` with the offset and failure message otherwise. Pass the supplied parent result
  through to either result.

```python
from polyfile.magic import (
    AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType,
)

class ExampleMatcher(MagicTest):
    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-example",
            extensions=("example",),
            message="Example file",
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None,
    ) -> TestResult:
        signature = b"EXAMPLE\x00"
        if data.startswith(signature, absolute_offset):
            return MatchedTest(self, signature, absolute_offset, len(signature), parent_match)
        return FailedTest(self, absolute_offset, "Missing example signature", parent_match)


example_matcher = MagicMatcher([ExampleMatcher()])
assert any(
    "application/x-example" in result.mimetypes
    for result in example_matcher.match(b"EXAMPLE\x00payload")
)
```

Pass `example_matcher` to `Matcher` to use that classifier in structural analysis. Use
`MagicMatcher.DEFAULT_INSTANCE.add(ExampleMatcher())` to register it on the process-wide
default instead.

## Parsing

### Implement and register a parser

`PARSERS` is a dictionary from exact MIME types to sets of parser instances. Each parser
receives a bounded `FileStream` and the matched `Match`. If your parser rejects the
classification or input, raise `InvalidMatch` before constructing any nodes. The MIME
classification remains available to the caller.

Create each structural node with `Submatch(name, match_obj, relative_offset=0, length=None,
parent=match)` and yield ancestors before their descendants. Pass an explicit `length` for
fields with a fixed size. A node with no explicit length derives its extent from its children
in the same source. Set `display_name` for a human-readable label and `description` to
control its displayed value. Use `source` and `dependencies` for source-qualified mapping.

Implement `Parser.parse(self, stream: FileStream, match: Match) -> Iterator[Match]` in a
subclass and register an instance with `PARSERS[mime_type].add(parser)`. You can pass the
instance to `register_parser(*filetypes)(parser)` to register it for several MIME types.
To register a function instead, decorate a callable that takes `(stream, match)` and yields
matches. The decorated name refers to the registered `Parser` instance, which you can call
with the same two arguments. The example uses the classifier from the preceding section.

```python
from collections.abc import Iterator

from polyfile import InvalidMatch, Match, Matcher, Submatch, register_parser
from polyfile.fileutils import FileStream


@register_parser("application/x-example")
def parse_example(stream: FileStream, match: Match) -> Iterator[Match]:
    signature = b"EXAMPLE\x00"
    header = stream.read(len(signature))
    if header != signature:
        raise InvalidMatch("Missing example signature")

    yield Submatch("Header", header, length=len(header), parent=match)
    offset = stream.tell()
    payload = stream.read()
    yield Submatch("Payload", payload, relative_offset=offset, length=len(payload), parent=match)


matches = list(Matcher(matcher=example_matcher).match(b"EXAMPLE\x00payload"))
assert [(node.name, node.offset, node.length) for node in matches[0].children] == [
    ("Header", 0, 8),
    ("Payload", 8, 7),
]
```

### Read from a parser stream

`FileStream(path_or_stream, start=0, length=None, mode="rb", close_on_exit=None)` creates a
read-only view of bytes, a path, or a seekable binary stream. `start` is relative to the
immediate input. `length` counts bytes from `start`, clamps at the end of the input, and
defaults to all remaining bytes. `read(n=None)`, `tell()`, `seek(offset, from_what=0)`, and
`len(stream)` use the view's bounds and coordinates. Related views share a cursor. A
context-managed view closes a path it opened and leaves caller-supplied streams open by
default. Use `close_on_exit` to override this.

The parser's stream starts at its match's first byte. Use a view-relative position for a
direct child's `relative_offset` in the same source. `stream.offset()` gives the view's start
in the backing buffer. Use `match.offset` and `match.source` to locate bytes in the analysis.

### Kaitai Struct Parsers

The majority of PolyFile’s parsers are automatically generated from the [Kaitai Struct format gallery](https://formats.kaitai.io/). They are compiled at build time by PolyFile's in-tree build backend, [`build_backend.py`](../build_backend.py), which calls [`compile_kaitai_parsers.py`](../compile_kaitai_parsers.py) to produce the pure-Python parsers in [`polyfile/kaitai/parsers/*.py`](../polyfile/kaitai/parsers/). These parsers should not be edited since they are automatically generated and will be overwritten the next time PolyFile is rebuilt. Building from a source distribution reuses the parsers that the distribution already carries, so it needs neither Java nor the compiler download.

Unfortunately, the Kaitai Struct parsers are not currently tagged based upon the MIME type of the files they parse. Therefore, PolyFile maintains a manual mapping from MIME types to Kaitai parsers. This mapping lives in [`polyfile.kaitaimatcher.KAITAI_MIME_MAPPING`](../polyfile/kaitaimatcher.py):
```python
KAITAI_MIME_MAPPING: dict[str, str] = {
    "image/gif": "image/gif.ksy",
    "image/png": "image/png.ksy",
    "image/jpeg": "image/jpeg.ksy",
    "image/vnd.microsoft.icon": "image/ico.ksy",
    # Other mappings.
}
```

Several MIME types may share one specification. Repeat the specification as the value of each key,
as `font/ttf`, `font/otf`, and `application/vnd.ms-opentype` all do for `font/ttf.ksy`. To register
a second parser for a MIME type that already has one, add it to `EXTRA_PARSERS` instead; both
parsers are tried, and one that cannot handle the data raises `InvalidMatch` and is skipped.

#### Adding a mapping

Three things have to hold, and `tests/test_kaitai.py` checks all of them:

1. **PolyFile must be able to emit the MIME type.** Dispatch is an exact lookup on the MIME type
   the magic matcher resolved, so a key that no matcher emits is dead code: the parser never runs
   and nothing reports an error. Check the key against `polyfile --list`.
2. **The generated parser must be importable.** kaitai-struct-compiler 0.11 does not escape Python
   reserved words used as identifiers, nor backslashes in the docstrings it copies from a
   specification's `doc:` key, so `polyfile.kaitai.compiler._fix_reserved_keywords()` rewrites both
   at generation time. `TestGeneratedParsers` fails if a parser reaches the package that Python
   still cannot read.
3. **Parsing a real file must yield more than a root node.** `StructNode.explore` walks only a
   specification's `seq:` fields, never its `instances:`, so a specification that keeps its content
   in `instances:` produces an empty tree. Add a sample to `TestKaitaiParsing` to prove otherwise.

Watch for specifications that can loop forever. `archive/rar.ksy` is deliberately unmapped because
its `blocks` field is `repeat: eos` over a switch whose RAR5 case consumes no bytes, so a 76-byte
RAR5 file makes it allocate until memory runs out. `TestKaitaiParsing.test_truncated_input_does_not_hang`
guards the mapped specifications against the same shape of bug.

#### When libmagic detects a format but assigns no MIME type

Some bundled definitions identify a format without an `!:mime` line, which leaves PolyFile with no
key to dispatch on. Do not add the `!:mime` line to `polyfile/magic_defs/`: those files are a
hand-maintained copy of upstream Magdir, and a local edit there is easy to lose the next time they
are refreshed. Define the test in Python instead, the way [`polyfile/nitf.py`](../polyfile/nitf.py)
and the Doom WAD and Creative Voice File tests in
[`polyfile/kaitaimatcher.py`](../polyfile/kaitaimatcher.py) do:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from polyfile.magic import MagicMatcher, TestType

with TemporaryDirectory() as directory:
    definition = Path(directory) / "doom"
    definition.write_bytes(b"""0\tstring\t=IWAD\t\tDoom main IWAD data
!:mime application/x-doom
!:ext wad
""")
    MagicMatcher.DEFAULT_INSTANCE.add(definition, test_type=TestType.BINARY)
```

#### Licensing of generated parsers

A parser produced by the Kaitai Struct compiler is a derivative work of the `.ksy` specification it
was generated from. PolyFile is distributed under the Apache 2.0 license, so it can only ship
parsers generated from specifications under a compatible permissive license.

Each specification in the format gallery carries its own license, chosen by whoever contributed it,
and a few are copyleft. To keep the distributed package Apache 2.0 throughout,
[`compile_kaitai_parsers.py`](../compile_kaitai_parsers.py) compiles a specification only when its
`license` key appears in `PERMISSIVE_LICENSES`. Everything else is skipped, and
[`MANIFEST.in`](../MANIFEST.in) keeps those specifications out of the source distribution as well.

The rule is an allowlist rather than a list of licenses to reject, for two reasons. A rejection list
has to name every copyleft family, and it matches by substring, so `GPL` does not catch
`GFDL-1.3-or-later`. An allowlist also excludes specifications that declare no license at all, which
grant no redistribution rights whatsoever.

To see what is excluded and why:

```console
$ python compile_kaitai_parsers.py --audit
Excluding 6 format specification(s) without a permissive license:
  GFDL-1.3-or-later        filesystem/lvm2.ksy
  GPL-3.0-or-later         filesystem/vdi.ksy
  GPL-2.0-or-later         firmware/broadcom_trx.ksy
  no license               game/renderware_binary_stream.ksy
  LGPL-2.1                 image/pif.ksy
  GPL-3.0-or-later         scientific/nt_mdt/nt_mdt.ksy
```

After you update the `kaitai_struct_formats` submodule, run the audit again. If maintainers
approve a new license for redistribution, add its license identifier to `PERMISSIVE_LICENSES`
and rerun the audit. In `MANIFEST.in`, add an `exclude kaitai_struct_formats/<path>` line for
each newly excluded specification and remove lines for specifications the audit now permits or
that upstream removed. Run `uv run pytest tests/test_licensing.py` to verify that the exclusion
paths match the audit and that the package contains only eligible parsers.

## Struct Parsing

PolyFile has a convenience utility defined in [`structs.py`](../polyfile/structs.py) for defining and loading binary structures:

```python
from io import BytesIO

from polyfile.structs import ByteField, Int32LE, Struct, UInt8LE

class Test(Struct):
    foo: UInt8LE
    bar: Int32LE
    data: ByteField["foo"]

test = Test.read(BytesIO(b"\x03234567890"))
print(test.foo, test.bar, test.data)
```

This can be used for both matching and parsing, as is demonstrated in the [ZIP matcher](../polyfile/zipmatcher.py).
`Struct.read()` preserves the subclass, so `Test.read()` returns a `Test`. Use `typing.Self` for
this kind of return annotation in your own methods. Use a `TypeVar` for independent value types,
such as the element type of a generic container.

## Debugging Matchers and Parsers

PolyFile implements an interactive debugger for stepping through the DSL specifications and parsers, modeled after
GDB. You can enter this debugger by passing the `--debugger` or `-db` argument to PolyFile. It is useful for both
implementing new `libmagic` DSLs, as well as figuring out why an existing DSL fails to match against a given file.
```console
$ polyfile -db input_file
PolyFile 0.5.6
Copyright ©2023–2026 Trail of Bits
Apache License Version 2.0 https://www.apache.org/licenses/

For help, type "help".
(polyfile) help
breakpoint ......... list the current breakpoints or add a new one
continue ........... continue execution until the next breakpoint is hit (aliases: run)
debug_and_continue . continue while debugging in PDB (aliases: debug and debug_and_cont)
debug_and_rerun .... re-run the last test and debug in PDB
debug_and_step ..... step into the next magic test and debug in PDB
delete ............. delete a breakpoint
help ............... print this message
next ............... continue execution until the next test that matches
print .............. print the computed absolute offset of the following libmagic DSL offset
profile ............ print current profiling results (to enable profiling, use `set profile True`)
quit ............... exit the debugger
set ................ modifies part of the debugger environment
show ............... prints part of the debugger environment
step ............... step through a single magic test
test ............... test the following libmagic DSL test at the current position
where .............. print the context of the current magic test (aliases: backtrace and info stack)
```

## Limit recursive analysis

Pass an `AnalysisLimits` instance through the keyword-only `limits` argument of `Matcher` or
`Analyzer` to limit recursive content analysis. All fields default to `None`, meaning unlimited.
A configured codec memory limit must be positive; zero remains valid for the integer recursion controls.
The command line exposes the same controls as `--max-depth`, `--max-member-bytes`,
`--max-total-bytes`, `--max-members`, and `--max-codec-memory`. Values are nonnegative integers;
zero prevents the corresponding recursive work except for codec memory, which must be positive.
`--helper-timeout` accepts positive finite seconds, including fractions, and limits each external
decoder invocation. Its Python API field is `AnalysisLimits.helper_timeout`. Codec memory limits
apply where a decoder supports them; they do not limit the Python process's total memory.

UNIX compress (`.Z`) decoding automatically uses `ggzip` or `gzip` from `PATH` when its version
banner identifies GNU gzip 1.15 or newer. Other gzip implementations and older releases report
`unsupported`, with an installation message. PolyFile invokes fixed arguments with standard input
and output, without a shell, inherited codec options, or extraction into the filesystem. See
[external decoder behavior](external_decoders.md) for setup, resource controls, and integrity limits.

LRZIP decoding automatically uses `lrzip` 0.7.3 or newer from `PATH` for unencrypted archive
versions 0.6 and 0.7. It preserves encoded framing and recursively analyzes validated output with
a separate source. Encrypted archives, unsupported versions, and missing helpers report explicit
status. See [LRZIP decoder behavior](external_decoders.md#lrzip) for compatibility and limits.

ZIP DEFLATE requires a 64 KiB codec-memory allowance when that control is configured. ZIP
bzip2/LZMA members report unsupported analysis when byte or memory limits are configured,
because the standard-library ZIP backend cannot bound their incremental decoder output.
Without configured limits, those backends retain their normal decoding behavior. ZIP entry
counts exclude structural field probes and count each archive member once.

7z archives use the pinned `py7zr==1.1.4` backend in isolated Python helpers. Member metadata,
solid/non-solid streams, compressed headers, integrity checks, recursive coordinates, and all
analysis controls are described in [7z archive analysis](sevenzip.md).

The original input has depth zero and does not consume the recursive member or byte budgets.
Depth counts transitions into content, including archive members and decoded streams, rather
than structural nodes. Byte counts are cumulative across an analysis, including siblings. Member
counts include container entries without payloads, such as directories and links, and codec
members. Parsers admit entries with `AnalysisContext.claim_entry()` and mark their content region
with `analysis_member_counted = True` before recursive matching to avoid counting it twice. A skipped region remains in the output with `analysis_status: "limited"` and an
`analysis_message` naming the limit. A new top-level analysis starts a new budget even when you
reuse a `Matcher`.

## TAR member analysis

The native TAR matcher validates the first header checksum and recognizes V7, POSIX, and GNU
headers. A valid native checksum verdict replaces generic soft-magic TAR aliases with
`application/x-tar`, preventing repeated traversal of nested archives. Specialized soft-magic
matches remain available, including Gentoo GPKG. The parser handles
all emitted TAR MIME variants and GPKG containers. An all-zero empty archive is not classified
as TAR because it has no checksum-bearing header, but the TAR parser can map its end markers
when invoked explicitly.

Regular members are analyzed recursively in physical `FileStream` slices. TAR headers, data,
padding, end markers, and trailing data retain offsets in their containing buffer. Header field
names follow their variant: USTAR prefixes, old GNU timestamps and sparse descriptors, and V7
reserved padding remain distinct. PAX local and
global names and sizes, USTAR prefixes, and GNU long names and link names are applied while the
original extension records remain visible. Effective archive paths and link targets are escaped
metadata; no path is extracted or followed. Directories, links, devices, and FIFOs have no nested
file analysis. A non-file entry that declares a payload is invalid.

Invalid checksums, truncated records, malformed extensions, missing end markers, and incomplete
payloads report an invalid region while preserving preceding valid structure. Two consecutive
zero blocks end the archive; remaining bytes are retained as trailing data. Old GNU and PAX
sparse members stop structural traversal with an unsupported status. Their logical contents are
never reconstructed or allocated. Compressed TAR wrappers require a decoder for the wrapper;
plain TAR parsing does not automatically run an external decompressor.

## Bzip2 decoded content

Bzip2 uses Python's standard-library `bz2.BZ2Decompressor`; no helper executable or additional
package is required. If Python lacks its optional `bz2` module, classification remains available
and decoding reports unsupported status. Each complete concatenated stream contributes to one
decoded buffer, so a JSON document or archive can span streams. Block and combined checksums are
validated before the decoded buffer is published. Truncation, invalid headers, corrupted data,
and trailing bytes, including zero bytes, report invalid status instead of publishing partial
content.

The physical tree maps each stream's signature, declared block size, and first block checksum.
An empty stream's aligned end marker and combined checksum are mapped directly. Later blocks
and the nonempty stream footer can be bit-aligned, so their encoded bytes remain in the
`compressed_data` region rather than receiving invented byte offsets.

Optional output and stream-count limits are checked incrementally. Before constructing each
codec instance, its header is checked against the configured codec-memory allowance using
libbz2's ordinary workspace estimate of `100000 + 4 * block_size` bytes. Python does not expose
libbz2's alternative small-memory mode. This allowance governs libbz2 workspace, separately
from Python's input/output buffers and report storage. See the [bzip2 memory-management
manual](https://sourceware.org/bzip2/manual/manual.html) for the workspace model. Limits are
unlimited when omitted.

## XZ decoded content

XZ uses Python's standard-library `lzma.LZMADecompressor` with explicit `FORMAT_XZ` framing.
No helper executable or additional dependency is required. Missing `lzma` support and integrity
check IDs unavailable in the installed liblzma report unsupported status. Header CRC32, stream
flags, block checks, index, and footer integrity are validated before publishing decoded content.
Check types supported by the backend include no check, CRC32, CRC64, and SHA-256.

Complete concatenated streams contribute to one decoded buffer, including documents split
between streams. Zero padding between or after streams must have a length divisible by four;
leading padding and other trailing bytes are invalid. The physical tree retains each stream's
header, encoded blocks, index, footer, and padding with exact byte offsets. Invalid or truncated
input keeps its wrapper and available raw structure without publishing partial decoded children.

Decoded output is requested from liblzma in bounded chunks. A configured codec-memory allowance
is passed to native `memlimit` before dictionary allocation; an omitted allowance passes `None`
and sets no application limit. Memory-limit failures report limited status. The output, total
byte, depth, and stream-count controls share the containing analysis's budget. Padding does not
consume a stream entry. See the [Python lzma incremental-decoding
reference](https://docs.python.org/3/library/lzma.html#lzma.LZMADecompressor) for backend semantics.

## LZMA-alone decoded content

Legacy LZMA-alone uses the standard-library `lzma` backend and explicit `FORMAT_ALONE` framing.
Its 13-byte header retains the properties byte, unsigned 32-bit dictionary size, and unsigned
64-bit decoded size. An all-ones decoded size means unknown length and requires an end marker.
Known-size streams can omit the marker; a marker with a known size requires liblzma 5.2.6 or
newer. The decoder follows the installed backend's ending support and checks declared sizes.
LZMA-alone has no checksum.

Property bytes above 224 are invalid. Valid properties with `lc + lp > 4` report unsupported
status because liblzma cannot decode them. Other valid properties and unsigned dictionary
values, including noncanonical dictionary sizes, use native validation and memory admission.
No auto-detection dictionary or 256 GiB size heuristic is applied by the explicit decoder.
Automatic classification continues to follow bundled libmagic rules, which can miss valid
small-dictionary or nondefault-property headers.

LZMA-alone does not define concatenated files. Trailing bytes, including another stream or zero
padding, are rejected using XZ Utils' strict policy. Complete decoded bytes receive their own
source and recursive JSON/archive analysis; malformed input never publishes partial children.
Known sizes are checked against an optional output allowance before codec construction, and
unknown-size output requests are bounded incrementally. Native memory, depth, and member
controls use the shared optional analysis limits; omitted limits remain unlimited.

See the [XZ project's LZMA file-format specification](https://github.com/tukaani-project/xz/blob/master/doc/lzma-file-format.txt)
for legacy properties and ending rules.
