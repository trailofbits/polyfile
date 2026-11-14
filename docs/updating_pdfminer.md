# Updating PDFminer

PolyFile qualifies one PDFminer release at a time. The adapter uses internal lexer, parser,
document, xref, and decryption interfaces that can change without a public API change.
`pyproject.toml` pins the qualified release, and `uv.lock` records its dependency graph and hashes.
The lazy PDF parser checks the installed version before importing these interfaces. Unqualified
installations retain PDF identification and report `analysis_status: unsupported`.

## Instrumentation approach

The adapter owns local document and xref subclasses and explicit parser hooks. Native PDFminer
classes and singleton keywords remain unmodified. The facade in `_pdfminer_adapter.py` contains
the private imports and document lifecycle operations; `pdf.py` attaches lexical spans, tracks
supported operations, and maps physical and decoded sources.

[Oomox](https://github.com/trailofbits/oomox) combines Python audit events with execution context.
Its boundary-oriented design is useful inspiration for keeping instrumentation localized, but
audit events do not expose every arithmetic operand/result or PDF lexer span. PolyFile therefore
uses explicit hooks and value wrappers rather than adding tracing, audit hooks, or a dependency
on Oomox. This also avoids AST or bytecode rewriting and keeps upstream API differences reviewable
in one qualified adapter.

## Qualify a release

Dependabot proposes PDFminer updates through the `uv` ecosystem after a seven-day cooldown.
For a manual update, change the exact `pdfminer.six` requirement and `SUPPORTED_PDFMINER` in
`polyfile/pdf_compat.py`, then run `uv lock`. Keep these changes in the same upgrade PR.

1. Review the upstream release notes and source changes affecting `psparser.py`, `pdfparser.py`,
   `pdfdocument.py`, and `pdftypes.py`. Inspect lexer cursor/state handling, composite construction,
   xref loading, object lookup/caching, compressed-object parsing, and recursive decryption.
2. Update `polyfile/_pdfminer_adapter.py` and its parser hooks in `polyfile/pdf.py` for the new
   interfaces. Replace the old implementation; maintain one qualified adapter.
3. Run `uv run pytest -q tests/test_pdf.py tests/unit/test_pdf*.py` and the full Python CI suite on
   Python 3.11, 3.12, 3.13, and 3.14. The contract tests exercise behavior as well as call interfaces:
   unchanged signatures do not establish compatibility.
4. Compare emitted and serialized values, source IDs, locations, and dependencies for physical,
   selected, decoded, compressed-object, encrypted, and malformed fixtures. Investigate any change;
   document intentional output corrections in `CHANGELOG.md`.
5. Run the repository's lint/type checks, security audit, distribution build, and relevant viewer
   tests. Confirm that normal PDFminer parsing in the same process remains unaffected.

Merge the upgrade only after qualification passes. A security update follows the same procedure;
adapt incompatible interfaces in the upgrade PR. Do not widen the version requirement to admit an
untested release or fall back to parsing without instrumentation.

## Installation in CI

Python CI exports the locked development dependencies with
[`uv export`](https://docs.astral.sh/uv/concepts/projects/export/), verifies their hashes during
system installation, and installs PolyFile without resolving dependencies again. The system
environment remains visible to the dependency audit. Checks run on code and dependency-update PRs.
