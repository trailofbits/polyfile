# Extending PolyFile

PolyFile has two primary components:
1. **Matchers**: classify the MIME types of input byte sequences; and
2. **Parsers**: produce a best-effort syntax tree for input byte sequences that have been classified.

## Matchers

### Libmagic Pattern Matching DSL

The majority of PolyFile’s matchers are automatically generated from [`libmagic`’s pattern definition library](../polyfile/magic_defs).

`libmagic` has an esoteric, poorly documented domain-specific language (DSL) for specifying its matching signatures.
You can read the minimal and—as we have discovered in our cleanroom implementation—_incomplete_ documentation by running
`man 5 magic`, or read [our blog post enumerating the DSL's idiosyncracies](https://blog.trailofbits.com/2022/07/01/libmagic-the-blathering/).

PolyFile’s matcher for the [NITF image format](../polyfile/nitf.py) provides a good example of how to programmatically define a new matcher using the `libmagic` DSL:
```python
from pathlib import Path

from polyfile.fileutils import ExactNamedTempfile
from polyfile.magic import MagicMatcher, TestType

with ExactNamedTempfile(b"""# The default libmagic test for NITF does not associate a MIME type,
# and does not support NITF 02.10
0       string  NITF       NITF
>4      string  02.10      \ version 2.10 (ISO/IEC IS 12087-5)
>25     string  >\0     dated %.14s
!:mime application/vnd.nitf
!:ext ntf
""", name="NITFMatcher") as t:
    nitf_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t), test_type=TestType.BINARY)[0]
```

### Pure Python Matchers

The `libmagic` DSL can be eschewed by programmatically defining a matcher using PolyFile’s `MagicTest` API.

```python
from typing import Optional

from polyfile.magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType

class ExampleMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),           # the file offset at which this test starts matching
            mime="application-x/example-mime",  # the MIME type associated with this type
            extensions=("example",),            # file extensions associated with this type, if any
            message="A message that will be printed when this test matches an input"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY  # use TestType.TEXT if this test only works on non-binary input

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if data.startswith(b"example"):
            return MatchedTest(self, value=data, offset=0, length=len(data))
        else:
            return FailedTest(self, offset=0, message="This is not an example file!")

# Register the matcher so it always runs:
MagicMatcher.DEFAULT_INSTANCE.add(RelaxedJarMatcher())
```

## Parsing

### Implementing a Parser

Once a Matcher detects a Match, PolyFile checks to see if a Parser exists for the matche’s MIME type. This MIME-to-parser mapping is stored in the `polyfile.PARSERS` dict:
```python
PARSERS: Dict[str, Set[polyfile.Parser]] = defaultdict(set)
```

All PolyFile parsers extend off of the [`polyfile.Parser`](../polyfile/polyfile.py) abstract class.
It contains one function that subclasses must implement:

```python
def parse(self, stream: polyfile.fileutils.FileStream, match: polyfile.Match) -> Iterator[
    polyfile.Submatch]
```
This function is passed a readable byte stream and the `match` object returned by the Matcher and is expected to yield a sequence of `Submatch` objects. If the parse fails and/or if the parser determines that the Matcher’s `match` classification was incorrect, the parser may `raise` a `polyfile.InvalidMatch` exception.

Each Submatch object is effectively an abstract syntax tree node. Therefore, each Submatch must be yielded subsequent to all of its ancestors.

```python
from polyfile import InvalidMatch, Submatch

def parse(self, stream, match):
    header_content = stream.read(len(b"example"))
    if header_content == b"example":
        yield Submatch(
            name="Example Header",
            match_obj=header_content,
            relative_offset=0,
            length=len(header),
            parent=match
        )
        remaining_content = stream.read()
        content_node = Submatch(
            name="Content",
            match_obj=remaining_content,
            relative_offset=len(header),
            length=len(remaining_content),
            parent=match
        )
        yield content_node
        pos = remaining_content.find(b"1234")
        if pos >= 0:
            yield Submatch(
                name="1234 Position",
                match_obj=[1, 2, 3, 4],
                relative_offset=pos,  # the offset is relative to the start of the parent node
                length=4,
                parent=content_node
            )
    else:
        raise InvalidMatch("The file does not start with b\"example\"!")
```

### Registering a Parser

Subclasses of `Parser` can simply be added to the `polyfile.PARSERS` dict:
```python
import polyfile

class ExampleParser(polyfile.Parser):
    def parse(self, stream, match):
        ...

polyfile.PARSERS["application-x/example-mime"].add(ExampleParser)
```

In addition, parsers that are implemented as standalone functions can be registered using the `register_parser` annotation:

```python
from polyfile import register_parser

@register_parser("application-x/example-mime")
def parse_example(file_stream, match):
    ...
```

### Kaitai Struct Parsers

The majority of PolyFile’s parsers are automatically generated from the [Kaitai Struct format gallery](https://formats.kaitai.io/). They are compiled at build-time (in [`setup.py`](../setup.py)) to produce the pure-Python parsers in [`polyfile/kaitai/parsers/*.py`](../polyfile/kaitai/parsers/). These parsers should not be edited since they are automatically generated and will be overwritten the next time PolyFile is rebuilt.

Unfortunately, the Kaitai Struct parsers are not currently tagged based upon the MIME type of the files they parse. Therefore, PolyFile maintains a manual mapping from MIME types to Kaitai parsers. This mapping lives in [`polyfile.kaitaimatcher.KAITAI_MIME_MAPPING`](../polyfile/kaitaimatcher.py):
```python
KAITAI_MIME_MAPPING: Dict[str, str] = {
    "image/gif": "image/gif.ksy",
    "image/png": "image/png.ksy",
    "image/jpeg": "image/jpeg.ksy",
    "image/vnd.microsoft.icon": "image/ico.ksy",
    ⋮
}
```

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

## Debugging Matchers and Parsers

PolyFile implements an interactive debugger for stepping through the DSL specifications and parsers, modeled after
GDB. You can enter this debugger by passing the `--debugger` or `-db` argument to PolyFile. It is useful for both
implementing new `libmagic` DSLs, as well as figuring out why an existing DSL fails to match against a given file.
```console
$ polyfile -db input_file
PolyFile 0.5.4
Copyright ©2023 Trail of Bits
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
