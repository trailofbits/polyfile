---
name: update-libmagic-definitions
description: >-
  Update PolyFile's bundled libmagic definitions from a stable file release, preserve local
  matching behavior, and connect newly detectable formats to eligible bundled parsers.
---

# Update libmagic definitions

## Contents

- [Select the release](#select-the-release)
- [Mirror the definitions](#mirror-the-definitions)
- [Check detection and parser coverage](#check-detection-and-parser-coverage)

## Select the release

Start in a clean update worktree with the `file` submodule initialized at the gitlink in
`HEAD:file`. Read the [sync guide](../../../docs/updating_libmagic_defs.md) for mirror commands,
coverage snapshots, and test procedures. Run the [drift checks](../../../tests/test_magic_defs_drift.py)
against the old pin and verify they executed. Investigate unexpected differences before copying.

Check the upstream `file/file` tags for the latest stable numeric `FILE` release unless the user
requested a specific release. Record the old gitlink, candidate tag, and resolved commit. If
the candidate already matches the pin and the mirror passes the drift checks, report that result
and finish. If you cannot verify the upstream tag, report what prevented verification.

## Mirror the definitions

1. Capture the baseline MIME and extension sets. Use the drift test's `POLYFILE_OWNED`,
   `LOCAL_PATCHES`, and `PENDING_PATCHES` to distinguish owned entries, applied fixes, and fixes
   still in review. Save the actual diff against the old pin and the regression each fix covers.
2. Inspect the upstream diff for `magic/Magdir/`, `COPYING`, and the test corpus. Resolve any
   collision between an upstream filename and an owned entry before mirroring. Review changes to
   license terms and notices for compatibility with PolyFile's distribution before copying them.
3. Check out the candidate commit and mirror additions, changes, and deletions using the guide.
   Preserve upstream bytes and PolyFile-owned definitions, and refresh `COPYING` from the pin.
4. Exercise each applied fix's regression against the unpatched candidate. If it still fails,
   adapt the fix and verify the regression passes. If it passes for the intended reason, retire
   the patch and its allowlist entry together. Trace moved rules to their new filenames and update
   the allowlist accordingly. If upstream deleted the rule, remove its obsolete entry and cover
   any still-needed behavior with a PolyFile matcher and regression. Check pending entries for
   renames or deletions. Run the drift checks again.

## Check detection and parser coverage

Run the definition parsing, text/binary partition, and upstream corpus tests. Explain changed
golden entries using the upstream diff. Fix new DSL incompatibilities in PolyFile's matcher and
add focused regressions. Run the Corkami differential against the binary and magic database built
from the candidate submodule. The guide describes its build prerequisites.

Compare the before and after MIME and extension sets and explain removals or renames. For newly
detectable formats, check the full parser registry (`polyfile.PARSERS`) for existing coverage.
When the format lacks a parser, check the current Kaitai manifest for a bundled spec matching the
actual format and variant. Confirm its license meets the repository allowlist and check documented
format exclusions. If eligible, register its exact emitted MIME in `KAITAI_MIME_MAPPING`. Use
`EXTRA_PARSERS` when an uncovered variant shares a MIME with an existing Kaitai mapping. Add a
sample that reaches the parser through normal `Matcher.match` dispatch and verifies meaningful
fields and offsets. Follow the [mapping guide](../../../docs/extending_polyfile.md#adding-a-mapping).
Run the [Kaitai mapping tests](../../../tests/test_kaitai.py) and
[licensing tests](../../../tests/test_licensing.py) for a new mapping. Keep the Kaitai gallery at
its existing pin for this update.

Update published version and coverage figures affected by the sync using the measured inventory.
Summarize the pins, mirror and license changes, patch decisions, detection changes, parser
additions or skips, and test results. Identify any test that could not run and the reason.
