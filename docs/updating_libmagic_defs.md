# Updating the libmagic definitions

PolyFile's libmagic matchers are generated from a copy of upstream's pattern library in
[`polyfile/magic_defs`](../polyfile/magic_defs). That copy is kept in sync by hand with the
[`file`](https://github.com/file/file) git submodule at `file/`. This page describes the procedure.

Follow it whenever you bump the `file` submodule. Nothing automates the copy, but
[`tests/test_magic_defs_drift.py`](../tests/test_magic_defs_drift.py) checks the result. It fails
when a definition goes missing, when one upstream has deleted stays behind, when a copy stops being
byte-identical, and when a local patch gets reverted, so run it after each step below:

```bash
pytest tests/test_magic_defs_drift.py
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

`MAGIC_DEFS` in [`polyfile/magic.py`](../polyfile/magic.py) globs this directory and skips only
`COPYING`, `magic.mgc`, `__pycache__`, and dotfiles. Adding a file is enough to load it; there is no
list of filenames to update.

Those five entries are also the `POLYFILE_OWNED` set in the drift test, which rejects any other
entry `Magdir` does not ship. If you add a sixth definition of PolyFile's own, add its name there
too.

`file/magic/Header`, `file/magic/Localstuff`, and `file/magic/Makefile.am` sit one level above
`Magdir/`, so a `Magdir/` sync never sees them. PolyFile doesn't need any of them.

## Local patches

A definition file copied from `Magdir` may still carry a PolyFile-specific patch. `LOCAL_PATCHES` in
[`tests/test_magic_defs_drift.py`](../tests/test_magic_defs_drift.py) is the list of them, and it is
the one place that list lives. Each name maps to the issue that justifies the patch, and the test
enforces the mapping in both directions: a definition that differs without an entry fails, and an
entry whose file has gone back to matching upstream fails as a reverted patch.

The sync overwrites these patches, so read the list before you copy. To confirm it is complete
against the submodule commit you are moving away from:

```bash
# Compare each definition against the Magdir of the *currently pinned* submodule commit.
# Anything that differs carries a local patch you must re-apply after the sync.
rm -rf /tmp/old-magdir && mkdir /tmp/old-magdir
git -C file archive HEAD magic/Magdir | tar -x -C /tmp/old-magdir --strip-components=2
for f in /tmp/old-magdir/*; do
  cmp -s "$f" "polyfile/magic_defs/$(basename "$f")" || echo "LOCAL PATCH: $(basename "$f")"
done
```

Run this **before** moving the submodule, while `file` still points at the old commit. It should
print exactly the names in `LOCAL_PATCHES`.

### Adding an allowlist entry

Patch a definition only when PolyFile cannot match upstream's text as written, such as a regex that
a POSIX engine runs in linear time and Python's `re` does not. Then:

1. File an issue, or use the one that sent you here, explaining what the patch changes and why
   upstream's text does not work. `c-lang` carries the rewrite from
   [#3411](https://github.com/trailofbits/polyfile/issues/3411), and `gentoo` the one from
   [#3473](https://github.com/trailofbits/polyfile/issues/3473).
2. Add one line to `LOCAL_PATCHES`, mapping the definition's file name to that issue's URL.
3. Run `pytest tests/test_magic_defs_drift.py`. The entry fails until the patch is actually in the
   file, which is the point: the allowlist records patches that exist, not intentions.

Dropping a patch is the same in reverse. Restore the definition from `Magdir` and delete its line,
in the same commit.

## Procedure

1. Find the release to move to. Use a tagged release, such as `FILE5_48`, rather than upstream's
   `master`. The `file/tests` corpus is part of PolyFile's test suite, so tracking an untagged
   commit makes the expected results a moving target.

   ```bash
   git -C file fetch --tags origin
   git -C file tag --sort=-creatordate | head
   ```

2. Record the local patches, using the loop above.

3. Move the submodule:

   ```bash
   git -C file checkout FILE5_48
   ```

4. Mirror `Magdir` into `magic_defs`, and refresh the license text:

   ```bash
   rsync -a --delete \
     --exclude='__init__.py' --exclude='__pycache__' --exclude='COPYING' \
     --exclude='csv' --exclude='json' --exclude='polyfile_zip' \
     file/magic/Magdir/ polyfile/magic_defs/

   cp file/COPYING polyfile/magic_defs/COPYING
   ```

   Use `rsync -a --delete`, not `cp`. A plain copy adds and updates files but never removes the ones
   upstream deleted. Six such files accumulated between 2021 and 2024 and kept matching until the
   5.48 update removed them.

5. Re-apply each local patch from step 2. Reusing the original commit is the least error-prone
   way, and a three-way apply tells you when upstream has changed the same lines:

   ```bash
   git log --oneline -- polyfile/magic_defs/c-lang        # find the patch commit

   # Stage the synced definitions first; `git apply -3` compares against the index.
   git add polyfile/magic_defs
   git apply -3 <(git show 938779e -- polyfile/magic_defs/c-lang)
   ```

   If the apply conflicts, upstream has rewritten the code the patch touches. Re-derive the patch
   against the new text rather than forcing it, and check whether upstream has since fixed the
   problem the patch worked around, in which case drop it.

   Then verify the result:

   ```bash
   pytest tests/test_magic_defs_drift.py
   ```

   This is the check to run after both step 4 and step 5. It reports a definition that the mirror
   dropped, an entry upstream no longer ships, a copy that is not byte-identical, and a patch from
   `LOCAL_PATCHES` that the mirror reverted. A failure names the file and what to do about it.

6. Confirm your diff matches upstream's, which catches a botched exclude list:

   ```bash
   git add file polyfile/magic_defs
   git diff --cached --stat -- polyfile/magic_defs | tail -1
   git -C file diff --stat <old commit> FILE5_48 -- magic/Magdir | tail -1
   ```

   The two totals agree, except for lines inside a locally patched file.

7. Test, and fix what breaks. See the next two sections.

## Testing the update

```bash
# The copy itself: nothing missing, nothing stale, nothing silently modified
pytest tests/test_magic_defs_drift.py

# Definition parsing, the text test partition, and the upstream corpus
pytest tests/test_magic.py

# Everything, including the differential test against a locally built `file`
pytest tests
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

### What the tests cannot see

Two paths in `_parse_file` discard input without raising or logging, so no test reports them:

- A line that is not valid UTF-8 is skipped entirely.
- A `!:strength` factor that does not parse as an integer is ignored, leaving the factor at 0. This
  already happens: `ctf` line 23 reads `!:strength + 5` followed by a trailing comment, so the test
  above it scores 20 rather than 25.

If a definition you are updating uses `!:strength`, check that the factor is a bare number. Grep
for the second case across the tree with `grep -rn '^!:strength' polyfile/magic_defs/ | grep '#'`.

`tests/test_corkami.py` then compares PolyFile against a `file` binary built from the submodule. It
runs `autoreconf`, `./configure`, and `make`, so it needs a C toolchain and autotools. Note that it
compiles its oracle from `file/magic/Magdir`, not from `polyfile/magic_defs`: if the two have
drifted, the differential compares PolyFile against a different rule set than the one it is running,
and says nothing about it. `tests/test_magic_defs_drift.py` is what tells you, so read its result
before you trust a corkami run.

The build tree it leaves behind in `file/` is ignored by git, so `git status` reports the submodule
clean even when `configure` and the binary predate the release you just checked out. `make` normally
regenerates them, but if the build fails or the oracle looks wrong, confirm the version with
`file/src/file --version` and force a clean rebuild with `git -C file clean -xfd`.

## Fixing what breaks

Work in this order:

1. **Parse errors.** Implement the construct in `polyfile/magic.py`. New data types go in
   `DataType.parse`; new type modifiers usually mean widening the relevant `*_TYPE_FORMAT` regex.
2. **`test_file_corpus` failures.** Fix `polyfile/magic.py`. The skip list in that test names stems
   that fail because of known PolyFile bugs; add to it only when the cause is a pre-existing bug this
   update exposed, and record which bug in a comment.
3. **corkami differences.** `KNOWN_BAD_FILES` holds the same kind of exception, keyed by MD5, and
   deserves the same standard of justification.

Also check whether any MIME type or file extension disappeared, which the tests do not catch:

```bash
# Before you touch anything, on a clean tree:
python -m polyfile --list > /tmp/mimes-before.txt

# After the sync and any code fixes:
python -m polyfile --list > /tmp/mimes-after.txt
diff /tmp/mimes-before.txt /tmp/mimes-after.txt
```

If you forgot to capture the "before" list, take it from a worktree at the base commit rather than
stashing, which cannot cleanly undo a submodule move:

```bash
git worktree add --detach /tmp/polyfile-base origin/master
git -C /tmp/polyfile-base submodule update --init file
(cd /tmp/polyfile-base && python -m polyfile --list) > /tmp/mimes-before.txt
git worktree remove --force /tmp/polyfile-base
```

A removal is usually deliberate on upstream's part, such as a rename, or a `use` of a named test
being commented out, which makes everything under that test unreachable. Confirm the cause of each
one rather than assuming.

## Committing

Definition files contain trailing whitespace that carries meaning: the message of a test is
everything after the last tab, and it is sometimes only spaces. The example hook in
[`hooks/pre-commit`](../hooks/pre-commit) runs `git diff-index --check`, which rejects those lines.
If you have installed it, commit the definitions with `git commit --no-verify`.

Keep the submodule bump and the definition copy in one commit, since the copy tracks the submodule,
and put code fixes, deletions, and test updates in their own commits.
