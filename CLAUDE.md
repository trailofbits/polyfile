# PolyFile Development Guide

## Project Overview

PolyFile is a file analysis utility that identifies and maps the semantic and syntactic structure of files—including polyglots, chimeras, and "schizophrenic" files that are validly multiple types simultaneously.

**Key capabilities:**
- Pure-Python libmagic implementation (896 MIME types, from libmagic 5.48)
- Recursive embedded file detection (like binwalk)
- Parsers for PDF, ZIP, JPEG, iNES, and 183 compiled Kaitai Struct formats (45 of the specifications
  are dispatched, covering 67 MIME types)
- Interactive HTML hex viewer with structure mapping
- Drop-in replacement for Unix `file` command

Part of the [ALAN Parsers Project](https://github.com/trailofbits/polyfile#the-alan-parsers-project) alongside PolyTracker.

## Architecture

### Core Pattern: Matchers + Parsers

**Matchers** classify file types. Two types:
- libmagic DSL matchers (defined in `polyfile/magic_defs/`)
- Python matchers (classes extending `MagicTest`, such as `zipmatcher.RelaxedJarMatcher`)

**Parsers** create AST representations of file structure. A parser written as a function is
registered with the `register_parser` decorator:
```python
from polyfile import register_parser

@register_parser("application/zip")
def parse_zip(file_stream, parent):
    ...
```

`register_parser` wraps whatever it receives in a function wrapper, so it takes a function, not a
class. Register a `Parser` subclass by adding an instance to `PARSERS`, which is what
`polyfile/__init__.py` does for PDF, through `_LazyPDFParser`, to defer the `pdfminer` import:
```python
PARSERS["application/pdf"].add(_LazyPDFParser())
```

### Key Modules

| Module | Purpose | Size |
|--------|---------|------|
| `polyfile.py` | Core engine—Match, Parser, Submatch classes | 15 KB |
| `magic.py` | Pure-Python libmagic DSL implementation | 117 KB |
| `pdf.py` | PDF parser with embedded file detection | 48 KB |
| `debugger.py` | Interactive GDB-style debugger | 42 KB |
| `kaitaimatcher.py` | Kaitai Struct format bridge | — |

### Directory Structure

```
polyfile/
├── polyfile/                  # Main package
│   ├── magic_defs/            # libmagic definition files
│   ├── kaitai/parsers/        # auto-generated Kaitai parsers (excluded from lint)
│   └── templates/             # HTML output templates
├── polymerge/                 # Companion merge tool
├── tests/                     # Test suite
├── docs/                      # Extension guide, JSON format spec
├── kaitai_struct_formats/     # Git submodule with KSY definitions
├── pyproject.toml             # Packaging metadata
├── build_backend.py           # In-tree PEP 517 backend; regenerates the Kaitai parsers
├── compile_kaitai_parsers.py  # Kaitai compilation and license audit
└── MANIFEST.in                # Source distribution contents
```

## Development Commands

### Setup
```bash
# Install from source. Needs the submodules, and Java for the Kaitai compiler whenever the
# parsers actually have to be regenerated.
git submodule update --init --recursive
uv venv
uv pip install -e '.[dev]'

# Install from PyPI
uv tool install polyfile
```

### Building distributions
```bash
# Builds the sdist, then the wheel from that sdist
uv build

# Check the metadata before a release
uvx twine check dist/*
```

There is no `setup.py`. `pyproject.toml` selects `build_backend.py`, an in-tree PEP 517 backend
that regenerates the Kaitai parsers for wheel, sdist and editable builds.

### Linting

Both passes lint the same targets. Only the second excludes the auto-generated Kaitai parsers:
generated code never satisfies the style and complexity checks, but it must still be valid Python,
and `E9` covers `E999`.

```bash
# Blocking: syntax errors and undefined names, including the generated parsers
uv run flake8 polyfile polymerge tests build_backend.py compile_kaitai_parsers.py \
    --count --select=E9,F63,F7,F82 --show-source --statistics

# Advisory: style and complexity
uv run flake8 polyfile polymerge tests build_backend.py compile_kaitai_parsers.py \
    --max-complexity=10 --max-line-length=127 --exclude=polyfile/kaitai/parsers
```

### Testing
```bash
# Run all tests
uv run pytest tests

# Run specific test file
uv run pytest tests/test_magic.py
uv run pytest tests/test_pdf.py
uv run pytest tests/test_corkami.py  # Polyglot corpus
```

### Security Audit
```bash
uvx pip-audit
```

### Pre-Commit Checklist
Run all checks before committing changes:
```bash
# Lint (blocking)
uv run flake8 polyfile polymerge tests build_backend.py compile_kaitai_parsers.py \
    --count --select=E9,F63,F7,F82 --show-source --statistics

# Lint (advisory)
uv run flake8 polyfile polymerge tests build_backend.py compile_kaitai_parsers.py \
    --max-complexity=10 --max-line-length=127 --exclude=polyfile/kaitai/parsers

# Security audit (checks for vulnerable dependencies)
uvx pip-audit

# Tests
uv run pytest tests
```

## Code Navigation

### Finding Matchers
```bash
# Find libmagic definitions by MIME type
rg "application/pdf" polyfile/magic_defs/

# Find Python matchers
ast-grep --pattern 'class $NAME(Matcher): $$$' --lang py polyfile/
```

### Finding Parsers
```bash
# Find registered parsers
rg "@register_parser" polyfile/

# Find parser for specific MIME type
rg 'register_parser.*application/zip' polyfile/
```

### Key Entry Points
- CLI: `polyfile/__main__.py`
- Core analysis: `polyfile/polyfile.py:PolyFile.struc()`
- Magic matching: `polyfile/magic.py:MagicMatcher.match()`

## Testing

### Test Structure
```
tests/
├── test_magic.py      # libmagic implementation vs corpus
├── test_pdf.py        # PDF parsing
├── test_corkami.py    # Polyglot/chimera edge cases
├── test_kaitai.py     # Kaitai format tests
└── unit/
    ├── test_ast.py    # AST utilities
    └── test_http.py   # HTTP protocol parsing
```

### Test Conventions
- Uses real file corpus including libmagic's official test suite
- Tests polyglot files to verify multi-type detection
- Parser tests validate structure extraction

## Extending PolyFile

### Adding a Custom Matcher (Python)
```python
from typing import Optional

from polyfile.magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType


class MyMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-myformat",
            extensions=("myformat",),
            message="My Format"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        if data.startswith(b"MAGIC"):
            return MatchedTest(self, value=data, offset=0, length=len(data))
        return FailedTest(self, offset=0, message="the file does not start with MAGIC")


MagicMatcher.DEFAULT_INSTANCE.add(MyMatcher())
```

### Adding a Custom Parser
```python
from polyfile import register_parser, Submatch


@register_parser("application/x-myformat")
def parse_myformat(file_stream, parent):
    yield Submatch(
        name="header",
        match_obj=file_stream.read(8),
        relative_offset=0,
        length=8,
        parent=parent
    )
```

### Updating the libmagic Definitions

`polyfile/magic_defs/` is a hand-maintained copy of `file/magic/Magdir/` from the `file` submodule.
Nothing automates the copy, and two bundled definitions carry PolyFile-specific patches: `c-lang`
(#3411) and `gentoo` (#3473). Both rewrite a regular expression that backtracks superlinearly in
Python's `re` but is safe for libmagic's POSIX engine; #3547 tracks fixing that at the engine level,
which would let both patches be reverted.

`tests/test_magic_defs_drift.py` enforces the copy. It fails when a bundled definition drifts from
upstream, when upstream ships one PolyFile does not, and when a patch listed in its `LOCAL_PATCHES`
allowlist has been reverted by a mirroring copy.

See `docs/updating_libmagic_defs.md` for the procedure, including how to find local patches before
you overwrite them.

### Adding Kaitai Struct Format
1. Add the `.ksy` file to the `kaitai_struct_formats/` submodule (upstream, or a local commit)
2. Map the MIME type in `polyfile.kaitaimatcher.KAITAI_MIME_MAPPING`
3. Rebuild: `uv run python compile_kaitai_parsers.py`
4. Add a sample to `TestKaitaiParsing` in `tests/test_kaitai.py`

The MIME type must be one PolyFile can emit (check `polyfile --list`); dispatch is an exact lookup,
so a key nothing emits is dead code that fails silently. Several MIME types may share one spec by
repeating it as the value; use `EXTRA_PARSERS` to register a second parser for a MIME type that
already has one. When libmagic detects a format but assigns no MIME type, add the test as an
inline DSL snippet in Python (see the Doom WAD and Creative Voice File tests in
`kaitaimatcher.py`) rather than editing `magic_defs/`.

Only specifications under a permissive license are compiled—see the licensing policy below.

See `docs/extending_polyfile.md` for detailed guide.

## Internal API Patterns

### File I/O
- Use `FileStream` abstraction for seeking/reading
- `PathOrStdin`/`PathOrStdout` for CLI flexibility

### Match Hierarchy
- `Match` → top-level file type match
- `Submatch` → nested structure within a match
- Build trees for embedded files (ZIP contents, PDF streams)

### Error Handling
- Raise `InvalidMatch` when parser cannot process data
- Matchers return `None` for non-matching data

### Kaitai Licensing Policy

A generated parser is a derivative work of its `.ksy` specification, and PolyFile ships under
Apache 2.0. `compile_kaitai_parsers.py` therefore compiles a spec only if its `license` is in
`PERMISSIVE_LICENSES`; everything else is skipped and kept out of the sdist by `MANIFEST.in`.

```bash
# List the specs that are excluded, and why
uv run python compile_kaitai_parsers.py --audit
```

Run the audit after every `kaitai_struct_formats` bump. `tests/test_licensing.py` fails if a parser
from an excluded spec reaches the package, or if `MANIFEST.in` drifts from the allowlist.

### Gotchas
- `polyfile/kaitai/parsers/` is auto-generated—never edit manually
- kaitai-struct-compiler 0.11 escapes neither Python reserved words used as identifiers nor the
  backslashes in the docstrings it copies from a spec, so `polyfile/kaitai/compiler.py`
  post-processes everything it generates in `_fix_reserved_keywords()`
- `archive/rar.ksy` loops forever on RAR5, so it is deliberately unmapped
- Java is required only when the parsers must be recompiled; installing from a published sdist
  or wheel reuses the generated ones
- `build_backend.py` and `compile_kaitai_parsers.py` run at build time and must stay
  standard-library only—builds are isolated and contain nothing but `[build-system] requires`
- `uv build` builds the wheel from the sdist. `build_backend.py` deliberately skips regeneration
  there, because outside a git checkout `compile_kaitai_parsers.is_stale()` falls back to tarball
  modification times and would recompile everything
- The downloaded `polyfile/kaitai/kaitai-struct-compiler-*/` is gitignored; it bundles its own
  copy of the format gallery, copyleft specs included
- libmagic DSL has quirks—see [blog post](https://blog.trailofbits.com/2022/07/01/libmagic-the-blathering/)
