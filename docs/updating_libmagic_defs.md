# Updating the libmagic definitions

PolyFile's libmagic matchers are generated from a copy of upstream's pattern library in
[`polyfile/magic_defs`](../polyfile/magic_defs). That copy is kept in sync by hand with the
[`file`](https://github.com/file/file) git submodule at `file/`. This page describes the procedure.

Follow it whenever you bump the `file` submodule. Nothing automates the copy, but
[`tests/test_magic_defs_drift.py`](../tests/test_magic_defs_drift.py) checks the result. It fails
when a definition goes missing, when one upstream has deleted stays behind, when a copy stops being
byte-identical, and when a local patch gets reverted, so run it after each step below:

```bash
uv run --extra dev python -m pytest tests/test_magic_defs_drift.py
```

## What lives in `polyfile/magic_defs`

The directory holds a byte-for-byte copy of `file/magic/Magdir/`, plus five entries PolyFile owns:

| Entry | Purpose |
|---|---|
| `__init__.py` | Empty. Makes the directory an importable package, so `MAGIC_DEFS` can find it through `importlib.resources`. |
| `COPYING` | A copy of `file/COPYING`, the license the definitions are distributed under. |
| `csv` | Declares PolyFile's `csv` test type, which libmagic implements in C rather than in the DSL. |
| `json` | Declares PolyFile's `json` and `ndjson` test types, for the same reason. |
| `polyfile_zip` | An extra backwards search for a ZIP end-of-central-directory record, which helps detect ZIP polyglots. |

Git preserves the bundled files' line endings. The drift tests compare them against committed
upstream bytes because Git settings can convert line endings in the `file` submodule checkout.

`MAGIC_DEFS` in [`polyfile/magic.py`](../polyfile/magic.py) globs this directory and skips only
`COPYING`, `magic.mgc`, `__pycache__`, and dotfiles. Adding a file is enough to load it; there is no
list of filenames to update.

Those five entries are also the `POLYFILE_OWNED` set in the drift test, which rejects any other
entry `Magdir` does not ship. If you add a sixth definition of PolyFile's own, add its name there
too.

`file/magic/Header`, `file/magic/Localstuff`, and `file/magic/Makefile.am` sit one level above
`Magdir/`, so a `Magdir/` sync never sees them. PolyFile doesn't need any of them.

## Local patches

The `c-lang` and `gentoo` patches were retired when RE2 could evaluate the original expressions.
For reference comparisons, exclude PolyFile's `csv` and `json` definitions: their test types are
implemented by PolyFile and cannot be loaded by libmagic. `gentoo` needs no exclusion.

A definition file copied from `Magdir` may still carry a PolyFile-specific patch. `LOCAL_PATCHES` in
[`tests/test_magic_defs_drift.py`](../tests/test_magic_defs_drift.py) is the list of them, and it is
the one place that list lives. Each name maps to the issue that justifies the patch, and the test
enforces the mapping in both directions: a definition that differs without an entry fails, and an
entry whose file has gone back to matching upstream fails as a reverted patch. Entries also listed in
`PENDING_PATCHES` represent proposed patches that have not landed.

Run the drift checks at the old pin to verify that the patch list is complete. Before mirroring,
create a temporary directory with `patch_dir=$(mktemp -d)`. For each applied patch, set `name` to
its filename and save both committed versions for comparison.

```bash
old_commit=$(git rev-parse HEAD:file)
git -C file show "$old_commit:magic/Magdir/$name" > "$patch_dir/$name.upstream"
git show "HEAD:polyfile/magic_defs/$name" > "$patch_dir/$name.polyfile"
git diff --no-index -- "$patch_dir/$name.upstream" "$patch_dir/$name.polyfile"
```

`git diff --no-index` exits with status 1 when the files differ. Keep the saved bytes until you
have tested the fix against the candidate release, including any renamed or replacement rule.

### Adding an allowlist entry

Patch a definition only when PolyFile cannot match upstream's text as written. Then:

1. Fix engine incompatibilities before changing a vendored definition. When a patch is necessary,
   identify the issue explaining what it changes and why the upstream text fails.
2. Add one line to `LOCAL_PATCHES`, mapping the definition's file name to that issue's URL.
3. Run the drift tests. An applied patch entry must correspond to a definition that differs.

Dropping a patch is the same in reverse. Restore the definition from `Magdir` and delete its line,
in the same commit.

## Procedure

1. Work in a clean update checkout with both submodules initialized. Verify that `git -C file
   rev-parse HEAD` matches `git rev-parse HEAD:file`. Record that commit and select the latest
   stable numeric release tag from [upstream file](https://github.com/file/file/tags), or the
   release the maintainer requested. Inspect remote tags in version order, excluding prereleases.
   Set `release_tag` to the selected name.

   ```bash
   old_commit=$(git rev-parse HEAD:file)
   git -C file ls-remote --refs --tags --sort=-version:refname origin 'FILE*'
   ```

2. Fetch the selected tag with `git -C file fetch origin tag "$release_tag"`. Run the drift tests
   at the old pin and confirm they execute. If `git -C file rev-parse "$release_tag^{commit}"`
   matches `old_commit` and the checks pass, the mirror is current. Otherwise, resolve any
   unexpected drift, record local patches, and take the [baseline coverage snapshot](#fixing-what-breaks).

3. Move the submodule:

   ```bash
   git -C file checkout --detach "$release_tag"
   ```

4. Review upstream changes to `file/COPYING` and notices in changed definitions before shipping
   them. Check added filenames against `POLYFILE_OWNED` for collisions and reconcile any overlap.
   Extract the committed definitions and license into a temporary directory, then mirror
   `Magdir`, adjusting the exclusions below to the current owned entries. Inspect the itemized
   dry run, then repeat it without `--dry-run` and refresh the license text.

   ```bash
   mirror_dir=$(mktemp -d)
   git -C file -c core.autocrlf=false -c core.eol=lf archive HEAD magic/Magdir COPYING \
     | tar -xf - -C "$mirror_dir"
   rsync -a --checksum --dry-run --itemize-changes --delete \
     --exclude='__init__.py' --exclude='__pycache__' --exclude='COPYING' \
     --exclude='csv' --exclude='json' --exclude='polyfile_zip' \
     "$mirror_dir/magic/Magdir/" polyfile/magic_defs/
   ```

   After the mirror, run `cp "$mirror_dir/COPYING" polyfile/magic_defs/COPYING`.

   Keep `--checksum` so files with the same size and modification time are compared by content.
   Keep `--delete` to remove retired definitions. Six such files continued matching until the
   5.48 update removed them.

5. Run the regression for each applied local patch against the unpatched candidate. If it still
   fails, use the saved diff and patch history to reapply the fix to the new definition and rerun
   the test. If upstream now passes the regression for the intended reason, drop the patch and its
   allowlist entry together. If the filename disappeared, trace renames and moved rules in the
   upstream diff. Move a still-needed fix and its allowlist key to the surviving rule. If the rule
   was deleted, remove the obsolete filename from the mirror and allowlist. If its behavior is
   still needed, preserve that behavior in a tested PolyFile matcher. Check pending entries for
   renamed or deleted targets as well.

   Then verify the result:

   ```bash
   uv run --extra dev python -m pytest tests/test_magic_defs_drift.py
   ```

   This is the check to run after both step 4 and step 5. It reports a definition that the mirror
   dropped, an entry upstream no longer ships, a copy that is not byte-identical, and a patch from
   `LOCAL_PATCHES` that the mirror reverted. A failure names the file and what to do about it.

6. Compare your diff with upstream's additions, changes, renames, and deletions. Include new files
   in the staged diff. Account for local patches and `COPYING` when comparing the two lists.

   ```bash
   git add file polyfile/magic_defs
   git diff --cached --name-status -- polyfile/magic_defs
   git -C file diff --name-status "$old_commit" HEAD -- magic/Magdir COPYING
   ```

7. Test, and fix what breaks. See the next two sections.

## Testing the update

```bash
# The copy itself: nothing missing, nothing stale, nothing silently modified
uv run --extra dev python -m pytest tests/test_magic_defs_drift.py

# Definition parsing, the text test partition, and the upstream corpus
uv run --extra dev python -m pytest tests/test_magic.py

# Corkami differential against the locally built candidate
uv run --extra dev python -m pytest tests/test_corkami.py

# Full integration
uv run --extra dev python -m pytest tests
```

`tests/test_magic_defs_drift.py` covers the copy, and three tests in `tests/test_magic.py` cover
what the copy says:

- `test_parsing` calls `MagicMatcher.parse(*MAGIC_DEFS)`. A DSL construct PolyFile doesn't implement
  raises `ValueError` or `NotImplementedError` here, prefixed with the definition file and line
  number. Because the default matcher is built during package import, an unsupported construct
  breaks `import polyfile` outright, so this failure is hard to miss.
- `test_text_tests` compares the set of text tests against a golden set keyed by definition file and
  line number. It fails on nearly every update, because inserting a line into a definition shifts
  every line number below it.

  Regenerate it with the command below, which sorts and wraps the entries so the diff stays
  readable. The snippet commented out just above the set in the test file emits an unsorted `repr`,
  which rewrites the whole literal and hides what actually changed.

  ```bash
  python -c "
  import polyfile.magic
  polyfile.magic.local_date = polyfile.magic.utc_date
  from polyfile.magic import MagicMatcher, MAGIC_DEFS
  entries = sorted(f'{t.source_info.path.name}:{t.source_info.line}'
                   for t in MagicMatcher.parse(*MAGIC_DEFS).text_tests
                   if t.source_info is not None)
  indent, limit, lines, cur = ' ' * 12, 100, [], ' ' * 12
  for e in entries:
      piece = repr(e) + ','
      cand = cur + (' ' if cur != indent else '') + piece
      if len(cand) > limit:
          lines.append(cur); cur = indent + piece
      else:
          cur = cand
  print('\n'.join(lines + ([cur] if cur.strip() else [])))
  "
  ```

  Then read the diff. Entries that move within a file are line shifts. An entry that disappears from
  a file which gained none is a test that stopped being a text test, and that needs explaining:
  in the 5.48 update, `mail.news` lost the `/t` flag on its `Received:` test and `ruby` deleted its
  `require` test. Note the assertion only prints diagnostics when the count *grows*, so a drop gives
  you a bare count mismatch and you have to diff the sets yourself.
- `test_file_corpus` runs every `file/tests/*.testfile` through the matcher and checks the expected
  description is among the matches. Bumping the submodule also updates this corpus, so new upstream
  test cases start being enforced.

### Differential testing

`tests/test_corkami.py` then compares PolyFile against a `file` binary built from the submodule. It
runs `autoreconf`, `./configure`, and `make`, so it needs a C toolchain and autotools. Note that it
compiles its oracle from `file/magic/Magdir`, not from `polyfile/magic_defs`: if the two have
drifted, the differential compares PolyFile against a different rule set than the one it is running,
and says nothing about it. `tests/test_magic_defs_drift.py` is what tells you, so read its result
before you trust a corkami run.

The Corkami tests download and verify the revision and SHA-256 in `tests/corkami_corpus.py`.
To update the corpus, select an upstream commit, download its ZIP archive from the commit-specific
`CORKAMI_URL`, and verify the archive's contents against that revision. Update `CORKAMI_COMMIT`
and `CORKAMI_SHA256` together. Run `uv run pytest tests/test_corkami.py tests/test_kaitai.py`
to check the updated inventory and sample paths. A stale cache is replaced after the new archive
passes verification.

The build tree it leaves behind in `file/` is ignored by git, so `git status` reports the submodule
clean even when `configure` and the binary predate the release you just checked out. `make` normally
regenerates them. Confirm the version with `file/src/file --version`. If it is stale, rebuild the
oracle in a fresh checkout of the candidate.

## Fixing what breaks

Work in this order:

1. **Parse errors.** Implement the construct in `polyfile/magic.py`. New data types go in
   `DataType.parse`; new type modifiers usually mean widening the relevant `*_TYPE_FORMAT` regex.
2. **`test_file_corpus` failures.** Fix the matcher and add a regression. `KNOWN_FAILURES` maps
   existing exceptions to issue numbers, and the test checks each still fails.
3. **corkami differences.** `KNOWN_BAD_FILES` holds the same kind of exception, keyed by MD5, and
   deserves the same standard of justification.

Compare both MIME types and file extensions before and after the update. Run the following
snapshot at the old pin, and run it again after the update with `phase=after` and the same
`snapshot_dir`. The CLI lists MIME types. The matcher exposes the extension set separately.

```bash
snapshot_dir=$(mktemp -d)
phase=before
uv run python -m polyfile --list > "$snapshot_dir/mimes-$phase.txt"
uv run python -c '
from polyfile.magic import MagicMatcher
print(*sorted(MagicMatcher.DEFAULT_INSTANCE.extensions), sep="\n")
' > "$snapshot_dir/extensions-$phase.txt"
```

Diff each pair of snapshots. Check the cause of each removal, such as an upstream rename or a
removed `use` of a named test. Run the Kaitai MIME mapping tests to catch unreachable parsers.

## Committing

Definition files contain trailing whitespace that carries meaning: the message of a test is
everything after the last tab, and it is sometimes only spaces. Keep that whitespace byte-for-byte
when reviewing the vendored diff. Run the repository's configured checks before committing.

Keep the submodule bump, copied definitions, and upstream deletions in one commit. Group related
engine and test changes together.
