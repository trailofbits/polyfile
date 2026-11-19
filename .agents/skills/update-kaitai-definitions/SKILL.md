---
name: update-kaitai-definitions
description: >-
  Refresh PolyFile's upstream Kaitai Struct format gallery and compiler, preserve parser fixes,
  audit redistribution licenses, and wire newly supported formats into MIME dispatch.
---

# Update Kaitai definitions

## Contents

- [Select the compiler and gallery revision](#select-the-compiler-and-gallery-revision)
- [Preserve local parser fixes](#preserve-local-parser-fixes)
- [Audit licenses and regenerate](#audit-licenses-and-regenerate)
- [Add parser coverage](#add-parser-coverage)
- [Verify the distributions](#verify-the-distributions)

## Select the compiler and gallery revision

Start in a clean update worktree from the target branch. Initialize both submodules at their
recorded gitlinks with `git submodule update --init --recursive`. Keep the compiler download and
virtual environment in the update worktree. Check the latest stable compiler release **before
changing the gallery**. Record the release URL, tag, current compiler pin, and old and proposed
gallery SHAs.

```sh
gh api repos/kaitai-io/kaitai_struct_compiler/releases/latest --jq '{tag_name,html_url}'
git ls-tree HEAD kaitai_struct_formats
git ls-remote --symref https://github.com/kaitai-io/kaitai_struct_formats.git HEAD
```

Use the upstream default branch's reported commit unless the user selected a particular revision.
Compare the release with `KAITAI_COMPILER_VERSION` in `polyfile/kaitai/compiler.py`. For a newer
stable release, update the pin, confirm the release asset works with the installer, and check the
generated Python's runtime requirement. Update `kaitaistruct` in `pyproject.toml` and refresh
`uv.lock` when a runtime change is needed. Verify the actual executable's `--version` for each
generation. The wrapper's `--locate` and `--install` options print the selected path, and both
can select a compiler from `PATH`. Resolve a mismatch before regenerating. If the latest release
cannot build or run with the supported runtime, report the failing version and check.

If both pins are current, run the license audit and the focused tests in
[Verify the distributions](#verify-the-distributions). Confirm the manifest matches the eligible
specs and the worktree has no unexpected changes. Report the checked pins and finish.

## Preserve local parser fixes

1. Before switching pins, inspect staged, unstaged, and committed changes in the gallery, compiler
   wrapper, and generated modules. Save any local deltas before invoking a build or installing
   PolyFile. Run `uv run --no-project python compile_kaitai_parsers.py --rebuild-all` in the clean
   update worktree with the old gitlink, scripts, and compiler. Compare its output with `HEAD` and
   the captured edits. Inspect the wrapper for fixes reproduced by the old build. Once you record
   the baseline and explain its diff, you can switch pins in the update worktree.
2. For each fix, run its original regression on **raw candidate output**. From the candidate
   gallery root, set `compiler` to the verified executable, `scratch` to an empty output
   directory, and `spec` to the affected spec path. Invoke the compiler directly.

   ```sh
   "$compiler" --target python --debug --ksc-json-output -I . \
       --python-package polyfile.kaitai.parsers --outdir "$scratch" "$spec"
   ```

   Use fresh Python processes and isolated module paths for old, raw candidate, and patched runs.
   PolyFile caches the manifest and parser imports. Find the affected specs in the manifest and run
   `python -W error::SyntaxWarning -m py_compile "$scratch/<module>.py"` with Python 3.12 or later
   when the original regression is invalid Python. Check the corresponding patched output with
   `TestGeneratedParsers` in [tests/test_kaitai.py](../../../tests/test_kaitai.py). The keyword
   workaround covers enum members, attributes, sequence field names, and debug offsets. The
   docstring workaround covers invalid escapes and syntax warnings.
3. If the raw candidate still fails, retain or port the fix in the checked-in generation path.
   Verify that the focused regression fails on raw output and passes after a fresh rebuild. Add
   a test if the existing suite misses the case. Keep build scripts standard-library-only. If
   upstream passes the original case unaided, retire the redundant workaround and keep the test.
   Account for each manual edit before replacing generated files. Record which upstream spec or
   compiler change resolved each retired fix.

## Audit licenses and regenerate

Fetch the selected revision from the gallery upstream in the submodule. Compare the old and new
commits there with `git diff --name-status -M` restricted to `*.ksy`. Record additions, renames,
deletions, and changed licenses or imports. Check out the candidate SHA and stage its gitlink as
part of the update. Initialize the repository's submodules before running tests.

```sh
uv run --no-project python compile_kaitai_parsers.py --audit
```

Use `PERMISSIVE_LICENSES` as PolyFile's redistribution policy. Exclude unrecognized or missing
licenses and keep the `MANIFEST.in` gallery exclusions equal to the audit, including removing
obsolete exclusion paths. Widening the allowlist requires maintainer approval. Trace changed
specifications' imports to their source specs, including transitive imports. An eligible root
that requires an excluded dependency blocks that parser from shipping. Resolve the dependency or
report the blocker. Preserve required license texts and attribution.
[Kaitai licensing policy](../../../docs/extending_polyfile.md#licensing-of-generated-parsers)

Run `uv run --no-project python compile_kaitai_parsers.py --rebuild-all`. The generator stages
each spec, rejects compile errors, duplicate module names, and dependencies without eligible
modules, then removes obsolete generated modules. In `polyfile/kaitai/parsers/manifest.json`,
verify that `generator.compiler_version` matches the selected release and `specs` covers the
eligible gallery paths. Save the manifest and generated modules outside the package before forcing
a second rebuild. Compare the results for lost coverage, renamed paths, and unexplained changes.
The same inputs must reproduce the manifest, parser set, and behavior. Sibling imports can change
order. Inspect these diffs and retain the tracked bytes for otherwise identical modules to keep
the PR focused. Wait for regeneration to finish before running linters or building distributions.

## Add parser coverage

For each new spec, including a replacement at a renamed path, compare its format and variants with
the MIME types from `uv run polyfile --list`, the complete `PARSERS` registry, and the Kaitai
registrations in `polyfile/kaitaimatcher.py`. Fix mappings for renames. For an eligible,
importable spec that fills a coverage gap, add its exact emitted MIME to `KAITAI_MIME_MAPPING`.
Use `EXTRA_PARSERS` when a distinct uncovered variant shares a MIME type with a working parser.
If an existing magic rule identifies the format by description alone, follow the Doom WAD inline
matcher pattern to give it a MIME in Python. Preserve the vendored Magdir copy.

Prove each addition with a valid fixture through `Matcher().match(...)`. Assert the MIME and a
format-specific child field with meaningful data and offsets. Exercise truncated input with a
timeout. Retain deliberate exclusions (such as the RAR5 parser) until the known failure has a
passing regression. Record the reason for each skipped candidate, such as existing coverage, no
usable matcher, a root-only AST, or an excluded license.
[Kaitai dispatch and fixtures](../../../docs/extending_polyfile.md#adding-a-mapping)

## Verify the distributions

```sh
uv sync --locked --extra dev --extra viewer-test
uv run --no-sync python -m pytest -q -rs tests/test_kaitai.py tests/test_licensing.py \
    tests/test_kaitai_build.py tests/test_kaitai_containers.py tests/unit/test_kaitai_loading.py \
    tests/test_parser_coordinates.py
dist_dir=$(mktemp -d)
uv build --out-dir "$dist_dir"
```

For an update, sync the environment after recording the old generation. The `viewer-test` extra
provides imports needed by the repository-wide type check. If sample tests report a download
failure, verify the pinned Corkami archive as described in the
[sync guide](../../../docs/updating_libmagic_defs.md#differential-testing). Confirm the licensing
and sample tests actually ran. Inspect the newly built sdist and its wheel in `dist_dir`
using `tarfile` and `zipfile`. Compare their generated module names with the verified manifest
(plus `__init__.py`), compare their manifests with the checkout, and verify the sdist's gallery
specs match the eligible set. Check both archives for excluded specs, stale modules, and the
downloaded compiler's bundled gallery. Update the published parser counts from the manifest and
the MIME registrations. Summarize pin changes, patch evidence, license decisions, new dispatch
coverage, skipped candidates, tests, and artifact checks for review.
