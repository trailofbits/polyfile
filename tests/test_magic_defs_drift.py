from pathlib import Path
from typing import Dict, FrozenSet, Set
from unittest import TestCase, skipUnless

POLYFILE_DIR: Path = Path(__file__).absolute().parent.parent
MAGIC_DEFS_DIR: Path = POLYFILE_DIR / "polyfile" / "magic_defs"
UPSTREAM_MAGDIR: Path = POLYFILE_DIR / "file" / "magic" / "Magdir"
UPSTREAM_COPYING: Path = POLYFILE_DIR / "file" / "COPYING"

HAVE_MAGDIR: bool = UPSTREAM_MAGDIR.is_dir() and any(UPSTREAM_MAGDIR.iterdir())

SYNC_DOC: str = "docs/updating_libmagic_defs.md"

IGNORED: FrozenSet[str] = frozenset({"magic.mgc", "__pycache__"})
"""Entries `polyfile.magic.MAGIC_DEFS` skips, so they are neither definitions nor PolyFile's own."""

POLYFILE_OWNED: FrozenSet[str] = frozenset({
    "__init__.py", "COPYING", "csv", "json", "polyfile_zip"
})
"""The entries of `polyfile/magic_defs` that PolyFile writes rather than copies from upstream."""

LOCAL_PATCHES: Dict[str, str] = {
    "c-lang": "https://github.com/trailofbits/polyfile/issues/3411",
    "gentoo": "https://github.com/trailofbits/polyfile/issues/3473",
}
"""Definitions that deliberately differ from upstream, each mapped to the issue that justifies it.

Add an entry only alongside the issue explaining why the patch has to exist, and delete it in the
change that drops the patch. Anything not listed here has to be a byte-for-byte copy of upstream.
"""

PENDING_PATCHES: FrozenSet[str] = frozenset({"gentoo"})
"""Allowlist entries whose patch is still in review, so the bundled file still matches upstream.

The pull request for #3473 rewrites the `gentoo-manifest` regex. Until it merges, `gentoo` is an
ordinary copy, and holding it to the allowlist would fail. Delete the name once that pull request
merges; `test_shared_definitions_are_byte_identical` fails with that instruction the moment the
patch lands, so the allowlist cannot stay disarmed by accident.
"""


def definition_names(directory: Path) -> Set[str]:
    """Lists the entries of a definition directory that `MAGIC_DEFS` loads as definitions."""
    return {
        entry.name
        for entry in directory.iterdir()
        if entry.name not in IGNORED and not entry.name.startswith(".")
    }


@skipUnless(HAVE_MAGDIR, "the file submodule is not checked out")
class TestMagicDefsDrift(TestCase):
    """Guards the rule that `polyfile/magic_defs` is a copy of the `file` submodule's `Magdir`.

    The copy is maintained by hand and is not append-only in either direction. Definitions upstream
    deletes keep matching until someone notices, and a plain copy of `Magdir` silently reverts the
    local patches. These tests fail on both, and on the third case the allowlist exists for:
    upstream rewriting the lines a local patch touches.
    """

    def setUp(self):
        self.upstream = definition_names(UPSTREAM_MAGDIR)
        self.bundled = definition_names(MAGIC_DEFS_DIR)
        self.assertTrue(self.upstream, f"{UPSTREAM_MAGDIR} holds no definitions")

    def test_every_upstream_definition_is_bundled(self):
        missing = self.upstream - self.bundled
        self.assertEqual(
            set(), missing,
            f"{', '.join(sorted(missing))} is in file/magic/Magdir/ but not in"
            f" polyfile/magic_defs/. Mirror the directory again, as {SYNC_DOC} describes"
        )

    def test_polyfile_s_own_entries_are_all_present(self):
        missing = POLYFILE_OWNED - self.bundled
        self.assertEqual(
            set(), missing,
            f"{', '.join(sorted(missing))} is PolyFile's own and is gone from polyfile/magic_defs/."
            f" A mirror of Magdir has to exclude it, as {SYNC_DOC} describes"
        )

    def test_the_only_extra_entries_are_polyfile_s_own(self):
        extras = self.bundled - self.upstream - POLYFILE_OWNED
        self.assertEqual(
            set(), extras,
            f"{', '.join(sorted(extras))} is in polyfile/magic_defs/ but not in file/magic/Magdir/."
            f" Upstream no longer ships it, so PolyFile matches a definition libmagic has dropped:"
            f" mirror the directory with `rsync -a --delete`, as {SYNC_DOC} describes. If PolyFile"
            f" owns the file, add it to POLYFILE_OWNED instead"
        )

    def test_shared_definitions_are_byte_identical(self):
        allowed_to_differ = set(LOCAL_PATCHES) - PENDING_PATCHES
        for name in sorted((self.upstream & self.bundled) - allowed_to_differ):
            with self.subTest(definition=name):
                if (UPSTREAM_MAGDIR / name).read_bytes() != (MAGIC_DEFS_DIR / name).read_bytes():
                    self.fail(self.drift_message(name))

    def test_local_patches_are_still_applied(self):
        for name, issue in sorted(LOCAL_PATCHES.items()):
            if name in PENDING_PATCHES:
                continue
            with self.subTest(definition=name):
                if (UPSTREAM_MAGDIR / name).read_bytes() == (MAGIC_DEFS_DIR / name).read_bytes():
                    self.fail(
                        f"polyfile/magic_defs/{name} is identical to file/magic/Magdir/{name}, so"
                        f" the patch from {issue} is gone. Mirroring Magdir reverts local patches;"
                        f" re-apply it, as {SYNC_DOC} describes. If upstream has fixed the problem"
                        f" the patch worked around, drop the entry from LOCAL_PATCHES instead"
                    )

    def test_copying_matches_upstream(self):
        if UPSTREAM_COPYING.read_bytes() != (MAGIC_DEFS_DIR / "COPYING").read_bytes():
            self.fail(
                "polyfile/magic_defs/COPYING is not the license the definitions ship under."
                " Copy it again: `cp file/COPYING polyfile/magic_defs/COPYING`"
            )

    @staticmethod
    def drift_message(name: str) -> str:
        """Explains one definition's disagreement with upstream, and what to do about it."""
        if name in PENDING_PATCHES:
            return (
                f"polyfile/magic_defs/{name} now carries the patch from {LOCAL_PATCHES[name]}."
                f" Delete {name!r} from PENDING_PATCHES, which arms the allowlist check that keeps"
                f" the patch from being reverted"
            )
        return (
            f"polyfile/magic_defs/{name} differs from file/magic/Magdir/{name}. If this is a"
            f" deliberate local patch, add it to LOCAL_PATCHES along with the issue that justifies"
            f" it; otherwise copy the definition again, as {SYNC_DOC} describes"
        )
