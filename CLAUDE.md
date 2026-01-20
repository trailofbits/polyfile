# PolyFile Development Guide

## Project Overview

PolyFile is a file analysis utility that identifies and maps the semantic and syntactic structure of files—including polyglots, chimeras, and "schizophrenic" files that are validly multiple types simultaneously.

**Key capabilities:**
- Pure-Python libmagic implementation (263+ MIME types)
- Recursive embedded file detection (like binwalk)
- Parsers for PDF, ZIP, JPEG, iNES, and 188 Kaitai Struct formats
- Interactive HTML hex viewer with structure mapping
- Drop-in replacement for Unix `file` command

Part of the [ALAN Parsers Project](https://github.com/trailofbits/polyfile#the-alan-parsers-project) alongside PolyTracker.

## Architecture

### Core Pattern: Matchers + Parsers

**Matchers** classify file types. Two types:
- libmagic DSL matchers (defined in `polyfile/magic_defs/`)
- Python matchers (classes extending `Matcher`)

**Parsers** create AST representations of file structure. Registered via decorator:
```python
from polyfile import register_parser

@register_parser("application/pdf")
def parse_pdf(file_stream, match):
    # Return parsed structure
    ...
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
├── polyfile/              # Main package
│   ├── magic_defs/        # 354 libmagic definition files
│   ├── kaitai/parsers/    # 188 auto-generated Kaitai parsers (excluded from lint)
│   └── templates/         # HTML output templates
├── polymerge/             # Companion merge tool
├── tests/                 # Test suite
├── docs/                  # Extension guide, JSON format spec
└── kaitai_struct_formats/ # Git submodule with KSY definitions
```

## Development Commands

### Setup
```bash
# Install from source (requires Java for Kaitai compiler)
pip install -e .[dev]

# Install from PyPI
pip install polyfile
```

### Linting
```bash
# Run flake8 (excludes auto-generated kaitai parsers)
flake8 polyfile polymerge --max-complexity=10 --max-line-length=127 \
    --exclude=polyfile/kaitai/parsers
```

### Testing
```bash
# Run all tests
pytest tests

# Run specific test file
pytest tests/test_magic.py
pytest tests/test_pdf.py
pytest tests/test_corkami.py  # Polyglot corpus
```

### Security Audit
```bash
pip-audit
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
from polyfile import Matcher, Match

class MyMatcher(Matcher):
    def match(self, data: bytes) -> Match | None:
        if data.startswith(b'MAGIC'):
            return Match(
                mime_type="application/x-myformat",
                name="My Format",
                offset=0,
                length=len(data)
            )
        return None
```

### Adding a Custom Parser
```python
from polyfile import register_parser, Parser, Submatch

@register_parser("application/x-myformat")
class MyParser(Parser):
    def parse(self, file_stream, match) -> Iterator[Submatch]:
        # Yield Submatch objects representing structure
        yield Submatch(
            name="header",
            start=0,
            length=8,
            value=file_stream.read(8)
        )
```

### Adding Kaitai Struct Format
1. Add `.ksy` file to `kaitai_struct_formats/`
2. Map MIME type in `polyfile/kaitai/parsers/__init__.py`
3. Rebuild: `python compile_kaitai_parsers.py`

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

### Gotchas
- `polyfile/kaitai/parsers/` is auto-generated—never edit manually
- Java required at install time for Kaitai compilation
- libmagic DSL has quirks—see [blog post](https://blog.trailofbits.com/2022/07/01/libmagic-the-blathering/)
