# PolyFile 0.6.0

This release is seven months of work: 253 commits and 67 pull requests since v0.5.6, which was
tagged on 2026-02-11. Two efforts dominate it.

**libmagic fidelity.** PolyFile's pure-Python libmagic implementation now reproduces what `file`
5.48 reports for every one of the 88 stems in libmagic's own test corpus. At v0.5.6 the corpus test
skipped 14 of them behind a list that asserted nothing, so a stem that started passing went
unnoticed and the list never shrank. That list is now an empty `KNOWN_FAILURES` map, and the
harness asserts that a mapped stem still *fails*, so an entry is a deliberate record of a filed bug
and deleting it is part of fixing that bug. Reaching that took corrected test strength,
deterministic match ordering, the text and binary pass split, the text encoding description, the
decoded UCS text buffer, and correct semantics for the `der`, `use`, `default`, `regex`,
`search`, `string`, and `indirect` tests.

A green corpus is not the same as a correct implementation, and an audit of the string flags
afterwards found defects the corpus never exercised. The `f` (full word) flag compiled to a word
boundary on both sides of the value, so all 60 interpreter-line definitions in
`polyfile/magic_defs/commands` could never fire and a `#! /bin/sh` script was never reported
as a `POSIX shell script`. The `W` flag compared the literal whitespace byte a value declared
rather than accepting any whitespace. The tie-break sort key left out two of the flag bits libmagic
compares. Those are fixed here as well, and each one changes what PolyFile reports for real files
that no corpus stem resembles.

**Packaging.** `setup.py` is gone. Packaging metadata is declarative in `pyproject.toml`, and
Kaitai parser generation moved into `build_backend.py`, an in-tree PEP 517 backend.

## Performance improvements

- **Binary input classifies 2.6 times faster.** Selecting a test's soft magic pass from the
  definition's own `b` and `t` flags, rather than from its subtests, moves the unflagged
  whole-buffer searches out of the pass that runs for every input. Matching every corpus test file
  went from 3.299 s to 1.247 s.
- **Three patterns that backtracked superlinearly are rewritten.** Classifying 8,192 carriage
  returns took 191 s through PolyFile's own HTTP 1.1 matcher and now takes 0.022 s. The
  `gentoo-manifest` definition went from 23.4 s to 0.014 s on a 506-byte input. The C++ class
  test in `magic_defs/c-lang` never finished on a 1,399-byte CRLF text file and now takes 0.061
  s. Each rewrite is backed by an exhaustive differential over tens of millions of inputs showing
  the two patterns accept the same language and report the same span.
- **The test suite now bounds how long a classification may take**, so a definition that does not
  terminate fails CI rather than stalling it.
- **`search/N` honors its repetition count.** Every one of the 800 `search` tests in the
  definitions used to scan the whole remaining buffer; libmagic reads at most `N` start offsets.
- **`Match` is lazy again.** An off-by-one in `Match.__getitem__` meant that reading the first
  result, calling `bool()`, or reading `mimetypes` drained the entire result generator.
- **`--no-contents`** omits the base64 copy of the input from `json` and `sbud` output. For
  a 4 MiB text file that is 5,592,965 bytes of output instead of 510.

## Bug fixes

### Matching

- Text is detected by character class, the way libmagic does, instead of by chardet's confidence
  score. A mostly-ASCII file carrying a few accented bytes was `application/octet-stream` and is
  now `text/plain`.
- A `use` test is true only when the named list it references actually matched something that
  prints. Every `use` used to succeed, so its continuation lines always ran; that produced false
  matches such as `EFI variable 3336800, total size: 0 bytes` on an ARJ archive.
- A `default` test now fires under libmagic's rule, and `clear` resets the flag it is meant to
  reset. The `clear` defect alone meant an ordinary non-animated PNG was reported as `data`.
- A `regex` test reads the relational operator off its value, so `!` negates the verdict
  instead of being compiled into the pattern. FORTRAN source went undetected because of this. Thanks
  to @LouisDeconinck, who diagnosed it and wrote the fix.
- A `regex/Nl` test searches its whole line-bounded region instead of matching each line anchored
  at column zero, and the region is clamped to 8 KiB the way libmagic clamps it. A randomized
  differential against `file` 5.48 went from 151 mismatches in 795 trials to 0 in 1,194.
- A `.i` or `.I` indirect offset decodes as an ID3 synchsafe integer, so an MP3's audio frames
  are reachable through its ID3v2 tag size.
- The `der` test is implemented rather than raising `NotImplementedError`, and the two
  workarounds that hid it are gone.
- A `!:strength` factor followed by a comment is no longer discarded.
- Newline-delimited JSON is detected as `application/x-ndjson`.

### Parsers and structure

- **A ZIP archive appended to other data is parsed, not only detected.** Record offsets are relative
  to the start of the archive, not the start of the file, so a PNG/ZIP polyglot now maps its ZIP
  structure and a JAR appended to a PNG reports `application/java-archive`.
- **Every archive in a file of concatenated ZIP archives is mapped**, not only the last one. A
  candidate end of central directory record is validated before an archive is reported, so signature
  bytes inside a comment or a stored member do not invent one.
- **A parsed struct's signature fields are no longer re-matched as embedded files.** Each ZIP record
  carried a spurious nested match under its `magic` field, and the end of central directory
  signature satisfied the relaxed ZIP test well enough to raise a parser warning on every archive.
- **Passing an open stream gives the same match tree as passing a path.** `FileStream` did not
  seek to its start when it wrapped an already-open stream, so a parser was handed a stream at EOF.
  Of 1,023 files, 383 produced a different tree from a stream than from a path; now none do.
- **Three byte-provenance dereferences in the PDF parser are guarded.** A PDF with an integer
  dictionary key, an empty trailer, or a reconstructed cross-reference table lost part of its match
  tree to an `AttributeError` or a `ValueError`. Each now reports what it skipped and maps the
  rest.
- **Cross-reference row cells are parsed.** `Position` and `Generation` were passed the wrong
  object and yielded nothing; each now carries the integer it holds.
- **Four generated Kaitai parsers were not valid Python.** `wmf`, `regf`,
  `openpgp_message`, and `sudoers_ts` used Python keywords as identifiers or wrote backslashes
  into non-raw docstrings. Reserved words are now escaped at generation time, `image/wmf` is
  mapped again, and the blocking flake8 pass no longer excludes the generated directory, so this
  cannot recur silently. Thanks to @andrewmonostate for the diagnosis and for taking it upstream.
- **The Kaitai MIME mapping is repaired and expanded.** Eight mapped keys named MIME types PolyFile
  never emits, so those parsers had never run. 44 specifications are now reachable across 67 MIME
  types, up from 20. A `busybox` ELF goes from 1 element to 23, a QuickTime file from 1 to 146, a
  DICOM study from 1 to 213.

### Output and tooling

- `--format html` no longer crashes on a zero-length file.
- The HTML hex viewer marks bytes that no match describes, with a hatch pattern and a legend, so you
  can see what PolyFile passed over. A 548 KB PDF has 96,882 such bytes.
- `json` and `sbud` output is byte-identical between runs. Three ZIP record elements rendered
  an object `repr`, address included, which changed on every run.
- `--format file` is accepted, `json` no longer appears twice in the `--format` choices,
  and the example in `--format`'s help text uses `-r` rather than `-f`, which is
  `--filetype`.
- `README.md` and `CLAUDE.md` no longer describe a PDF parser that was deleted in 2022, a
  matcher base class that does not exist, or a parser registration example that raises
  `TypeError`. Both replacement examples were run before being committed.

## New features

- **`--no-contents`** omits `b64contents` from `json` and `sbud` output, and skips the
  base64 encoding rather than computing it and discarding the result. It is refused alongside HTML
  output, because the hex viewer is built from those bytes.
- **`polyfile.magic.join_matches`** renders a set of matches the way `file -k` renders them,
  joined with `\012- ` and carrying one text encoding description on the last part.
- **An empty file is classified.** It reports `empty` and `inode/x-empty`, from a short
  circuit placed where libmagic places it, ahead of every test.
- **Undescribed bytes are marked in the HTML viewer**, with two independent visual cues so the
  marking survives grayscale printing and color vision deficiency.
- **`tests/test_magic_defs_drift.py`** compares `polyfile/magic_defs/` against the `file`
  submodule in both directions. It fails when an upstream definition is missing, when a local patch
  has been reverted by a sync, and when a definition differs without an allowlist entry naming the
  issue that justifies it.
- **`compile_kaitai_parsers.py --audit`** reports which specifications are excluded from
  compilation and why, and `tests/test_licensing.py` fails if an excluded parser reaches the
  package or if `MANIFEST.in` drifts from the allowlist.

## Magic definitions

- **Updated to `FILE5_48`**, released 2026-06-07, from `FILE5_46-172-g6403d2b3`. 34
  definitions changed and six were added: `a2ml`, `andrew`, `atari`, `k9`, `nix`, and
  `partclone`. Reachable MIME types go from 876 to 895.
- **Six definitions upstream deleted between 2021 and 2024 were still shipped and still matching**,
  because the sync had historically been a `cp` that never deleted. `dsf`, `guile`,
  `neko`, `pc88`, `alpha`, and `rinex` are gone. No MIME type or extension is lost; the
  definitions that absorbed them declare the same ones.
- **The `beguid` data type is implemented.** libmagic 5.48 split `guid` into `guid`,
  `leguid`, and `beguid`, and the ZIM archive test uses `beguid`. Without it,
  `import polyfile` raised `ValueError` outright, because the default matcher is built during
  package import.
- **Two definitions carry local patches**, both to remove superlinear regex backtracking that
  libmagic's POSIX engine does not suffer from: `c-lang` and `gentoo`. Both are recorded in
  the drift test's allowlist, so a future sync cannot revert them silently.
- **`docs/updating_libmagic_defs.md`** documents the procedure, including how to find local
  patches before you overwrite them.

## Breaking changes

This release changes observable output in many ways. If you parse PolyFile's output, read this
section.

### Output format

- **An SBuD element that describes no content of its own now omits `value` entirely.** It is
  absent rather than empty or null. If you read `element["value"]` by direct subscript, use a
  default. This affects the `LocalFileHeader`, `CentralDirectory`, and
  `EndOfCentralDirectory` elements, whose `value` previously held a Python object `repr`
  including a memory address. Their field elements are unchanged.
- **`--no-contents` omits `b64contents`** from the top of a `json` or `sbud` object. The
  default output is unchanged.
- **An empty file now reports a match.** `--format file` prints `empty` where it printed a blank
  line, `--format mime` prints `inode/x-empty` and `--format explain` prints its test where both
  printed nothing, and `struc` holds one element instead of being empty. `--format html` renders a
  viewer where it raised `ValueError`.
- **`--format explain` labels a match found in a decoded text buffer.** Offsets reported for a
  UTF-16 or UTF-32 file are offsets into the decoded text, not into the file, and the output now
  says so.
- **`versions.polyfile` in SBuD output reports `0.6.0`.**

### Command line

- **`--format file` is accepted.** It was the documented default but argparse rejected it
  explicitly with exit status 2.
- **`json` no longer appears twice** in the `--format` choices, so the usage line and every
  error message that lists them have changed.
- **`--no-contents` is new**, and is refused with exit status 1 when any output format is
  `html`.

### Python API

- **`try_all_offsets` is removed** from `Matcher.__init__` and `Analyzer.__init__`. Nothing
  read either attribute, and `Analyzer` never forwarded it, so passing it was already a silent
  no-op.
- **`Analyzer.sbud` takes `include_contents: bool = True`.** The default is the previous
  behavior.
- **`polyfile.html.generate` raises `ValueError`** for an SBuD object with no
  `b64contents`, naming the input and the fix, where it used to raise a bare `KeyError` from
  inside template rendering.
- **`FileStream(stream, start=N, length=L)` counts `L` bytes from `start`** in both of the
  constructor's branches. The raw-stream branch previously read `L` as an offset from the
  beginning of the underlying stream and could produce a negative length, which made the first
  `read()` raise.
- **`MagicMatcher.text_tests` and `non_text_tests` return a `KeysView`** rather than a
  `set`, so they have a defined iteration order. `&`, `|`, `in`, and `len` all still
  work.
- **`DataType.is_text` is replaced by `DataType.test_types`**, which returns pass bits rather
  than a boolean, because a definition carrying both `b` and `t` belongs to both passes.
- **A malformed definition now raises instead of being skipped.** A `!:strength` factor that is
  not an integer, and a definition line that is not valid UTF-8, each raise a `ValueError` naming
  the file and the line. Both were previously swallowed, dropping a test with no error and no log
  record.
- **A data type declaration whose flags its name omits raises `ValueError` at load time**, which
  closes the interning collision where two declarations differing only in their flags shared one
  instance.

### Classification and messages

- **Text matches carry libmagic's encoding description.** A text file's message now ends with the
  clauses `file` appends: the encoding name, and where applicable
  `, with CRLF line terminators`, `, with no line terminators`,
  `, with very long lines (N)`, `, with escape sequences`, and `, with overstriking`.
  `GEDCOM genealogy text version 5.5` becomes `GEDCOM genealogy text version 5.5, ASCII text`.
  Over a 63-file mixed sample, the number of files whose `file -b` verdict appears among
  PolyFile's matches went from 15 to 54.
- **Encoding names use libmagic's spelling and capitalization.** PolyFile reported the lower-case
  `UTF-16 text` from chardet's statistical guess; it now reports
  `Unicode text, UTF-16, little-endian text`. The corpus comparison no longer folds case, so a
  capitalization difference is a failure rather than a silent pass.
- **A UTF-8 byte order mark is named**: `Unicode text, UTF-8 (with BOM)`. The mark is no longer
  measured as a character, so the line-shape clauses agree with `file` too.
- **Match ordering changed, and is now deterministic.** Tests were stored in `set`s and iterated
  in hash order, so the first reported match — which a reader takes as the primary type — varied
  between runs of the same input. Matches now come out in libmagic's own order: descending strength,
  then libmagic's `memcmp` tie-break over every field it compares, which since this release
  includes every string flag and a `search`'s declared range. Ten multi-match inputs were stable
  under six hash seeds in 2 cases of 10 before and 10 of 10 after, and agreement with the corpus's
  primary type went from 77-82 of 86, depending on the seed, to 83 of 86 under every seed. Adding
  the missing flag bits alone moved 1,232 of the 3,877 level 0 tests.
- **Test strength changed for nearly every test.** `base_strength` returned a constant 20, so
  3,732 of 3,868 level 0 tests tied. Every bundled level 0 test now scores exactly what `file -l`
  reports.
- **The `f` (full word) flag makes 60 previously unfirable definitions match.** It anchored the
  value on both sides; libmagic only looks at the byte that follows. Every definition in
  `magic_defs/commands` declares a value starting with `#`, so none of the 60 could fire. Of
  274 real files carrying a shebang, 88 gain a description: 72 `POSIX shell script`, 13
  `Bourne-Again shell script`, 2 `Paul Falstad's zsh script`, and 1 `Korn shell script`.
- **The `W` (compact whitespace) flag accepts any whitespace byte** for a declared blank, rather
  than the literal byte the value wrote. `@echo\toff` is now a `DOS batch file`, and
  `magic_defs/perl`'s POD definitions match a vertical tab where they previously demanded a line
  feed.
- **String and search tests refuse a value longer than the buffer.** The two-byte file `#!` was
  reported as `a  script, ASCII text executable`. A negated (`!`) string test still matches
  such a buffer, as libmagic's does.
- **A flagged search stops one start offset earlier.** libmagic's flagless fast path reaches offset
  `N` and its flagged loop stops at `N - 1`. The bound is also on where a match starts rather
  than where it ends, which `w` and `W` make observable in both directions: over a 93-case
  grid against `file` 5.48, 22 cases diverged before this change and none do now.
- **An untyped indirect offset reads in host byte order** rather than big endian. PolyFile's two
  verdicts for a PA-RISC executable's dynamic-link marker were exactly inverted with respect to
  `file`.
- **EBCDIC text and NUL-padded text are classified as text.** Both previously fell through to
  `application/octet-stream`.
- **Both soft magic passes gate on the untrimmed classification**, so a definition flagged `b`
  runs against NUL-padded text. A Nullsoft AVS preset now reports `Winamp plug in`.
- **BOM-prefixed JSON reports both verdicts.** `JSON text data` and the Unicode text description
  both appear, where PolyFile previously reported JSON alone and `file` reports the text
  description alone. RFC 8259 section 8.1 permits either reading.
- **A bare top-level JSON scalar is no longer JSON.** `42` parses as JSON to Python and is plain
  text to libmagic, which requires an object or an array.
- **A `regex` test reports only its matched extent**, so `%s` no longer interpolates the bytes
  that precede the match, and a following relative offset resolves from the match rather than from
  where the test ran. A leading `=` is consumed as a relation, which is what made the 40
  `=`-prefixed regex tests in the definitions compile to patterns that could never match.
- **A `regex` does not see the last byte of its region, or anything past a NUL already in it.**
  libmagic NUL-terminates the copy it hands to `regexec`. This is what stopped a Hancom HWPX file
  from being reported as `Microsoft OOXML`.
- **A `string` value stops at the first carriage return, line feed, or 128 bytes.** One GEDCOM
  definition reported four lines of the file in its message.
- **A relative offset after a `search` resolves from the declared length** at the position the
  search found its value, and the `s` flag resolves it from the start of the match instead.
- **UTF-16 and UTF-32 documents gain their real types.** Text tests run against libmagic's decoded
  UTF-8 buffer with the byte order mark removed, so a UTF-16 SVG reports
  `SVG Scalable Vector Graphics image` rather than only
  `Unicode text, UTF-16, little-endian text`. Over a 97-file sample, agreement with `file -b`
  went from 68 to 84.
- **DER input is classified.** A certificate reports `application/pkix-cert`, a certificate
  request `application/pkcs10`, and PKCS#7 signed data `application/pkcs7-mime`, where all
  three were `application/octet-stream`. Upstream `der` carries no `!:mime` line at all, so
  these MIME types are PolyFile's, supplied in `polyfile/der.py`.
- **Three MIME types are gone with the 5.48 sync**, all deliberate upstream changes:
  `application/javascript` was renamed `text/javascript`, `application/x-hwp` became
  `application/hwp+zip`, and `image/x-gem` with the `ximg` extension became unreachable
  when upstream commented out every `use gem_info` call.
- **Four corpus files no longer report a `Zip archive data, made by ...` message.** Their central
  directory signature sits past the 1,024-byte window the `search/1024` test declares, which
  PolyFile previously ignored. `file` does not report it for them either.

### Match structure

- **A file of concatenated ZIP archives yields records for every archive**, not only the last. Over
  a 351-file differential, no match was lost on any file and 250 were gained.
- **`Constant` struct fields carry no children.** Each ZIP record's `magic` field previously
  carried a nested `application/octet-stream` or `application/zip` match.
- **Cross-reference row cells carry a `PSInt` child.** Over 15 PDFs this is 944 new matches, two
  per row, with nothing lost.
- **Many more file types now produce a parse tree**, because 44 Kaitai specifications are reachable
  rather than 20, and two that were disabled in 2021 work again. WebP, AVI, WAV, Ogg, QuickTime/MP4,
  Mach-O, PE, TGA, PCX, Sun/NeXT audio, Python pickle, DER, gettext `.mo`, dBase, macOS resource
  forks, OLE2 compound files, DICOM, and ICC profiles are among them, and ELF is mapped for four
  more MIME types than `application/x-pie-executable`.
- **`archive/rar.ksy` is deliberately unmapped.** Its `blocks` field loops forever on RAR5,
  which has been the default since 2013, and a 76-byte file is enough to exhaust memory. The dead
  `application/x-rar` key had been masking this.

### Distribution

- **`setup.py` is deleted.** Build from `pyproject.toml`; `pip`, `uv build`, and
  `python -m build` all select `build_backend.py` through `[build-system]`. Java is needed
  only when the Kaitai parsers must be regenerated, and no longer during dependency resolution.
- **Six copyleft Kaitai parsers no longer ship**, because a generated parser is a derivative work of
  its specification and PolyFile ships under Apache 2.0. `vdi`, `nt_mdt`, `broadcom_trx`,
  `lvm2`, and `pif` were compiled from GPL, LGPL, or GFDL specifications;
  `renderware_binary_stream` declares no license at all. None was reachable from the MIME
  mapping. The compiler now uses an allowlist of permissive licenses, so a submodule bump cannot
  admit a new one unnoticed.
- **The source distribution no longer carries a local build tree.** `graft file` walked the
  filesystem rather than asking git what is tracked, so 140 artifacts from a local autotools build
  of the `file` submodule — a platform-specific `libmagic.dylib` among them — shipped to
  anyone who ran the tests before building a release.
- **Package metadata is version 2.4**, with `License-Expression: Apache-2.0` and no
  `License :: OSI Approved` classifier. The two together are a hard error on setuptools 77 and
  newer.
- **`.travis.yml` is deleted.** It targeted Python 3.6 through 3.8, all older than the
  `requires-python` floor.

## Dependencies

- **Removed `chardet`.** Text membership is decided by character class, and the encoding name
  comes from PolyFile's port of libmagic's `file_encoding`, so nothing used it any more.
- **`kaitaistruct` moves from `~=0.10` to `~=0.11`**, matching the Kaitai Struct compiler
  bump from 0.9 to 0.11. The compiler bump is required rather than incidental: 17 of the updated
  specifications declare a minimum compiler version of 0.10 or 0.11, and 0.9 refuses to build them,
  including `png`, `elf`, `dex`, `ethernet_frame`, and `ipv4_packet`.
- **`setuptools` moves from `>=65.5.1` to `>=83.0.0`**, and the floor is now declared in
  `[build-system] requires` as well as in `dependencies`. 83.0.0 is the first release that
  normalizes Unicode when matching `MANIFEST.in` `exclude` directives (PYSEC-2026-3447), which
  is what keeps the copyleft specifications out of the source distribution.
- **`kaitai_struct_formats` moves from `17629c7` to `e0bda45`**, 289 commits, with seven
  new specifications.
- GitHub Actions: `actions/checkout` 7.0.1, `actions/setup-python` 7.0.0,
  `pypa/gh-action-pypi-publish` 1.14.2, `zizmorcore/zizmor-action` 0.6.3, and
  `actions/add-to-project` 2.0.0. Releases publish through PyPI Trusted Publishing, and
  `zizmor` audits the workflows on every run.
