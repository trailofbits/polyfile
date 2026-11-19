from collections.abc import Iterable
from io import BytesIO
from pathlib import Path, PurePath, PurePosixPath
import subprocess
import tarfile
from unittest import TestCase, skipUnless

POLYFILE_DIR: Path = Path(__file__).absolute().parent.parent
MAGIC_DEFS_DIR: Path = POLYFILE_DIR / "polyfile" / "magic_defs"
UPSTREAM_ROOT: Path = POLYFILE_DIR / "file"
MAGDIR: PurePosixPath = PurePosixPath("magic/Magdir")
COPYING: PurePosixPath = PurePosixPath("COPYING")
UPSTREAM_MAGDIR: Path = UPSTREAM_ROOT / MAGDIR

HAVE_MAGDIR: bool = UPSTREAM_MAGDIR.is_dir() and any(UPSTREAM_MAGDIR.iterdir())

SYNC_DOC: str = "docs/updating_libmagic_defs.md"

IGNORED: frozenset[str] = frozenset({"magic.mgc", "__pycache__"})
"""Entries `polyfile.magic.MAGIC_DEFS` skips, so they are neither definitions nor PolyFile's own."""

POLYFILE_OWNED: frozenset[str] = frozenset({
    "__init__.py", "COPYING", "csv", "json", "polyfile_zip"
})
"""The entries of `polyfile/magic_defs` that PolyFile writes rather than copies from upstream."""

LOCAL_PATCHES: dict[str, str] = {}
"""Definitions that deliberately differ from upstream, each mapped to the issue that justifies it.

Add an entry only alongside the issue explaining why the patch has to exist, and delete it in the
change that drops the patch. Anything not listed here has to be a byte-for-byte copy of upstream.
"""

PENDING_PATCHES: frozenset[str] = frozenset()
"""Allowlist entries whose patch is still in review, so the bundled file still matches upstream.

Naming an entry here disarms the allowlist check for it, which lets a `LOCAL_PATCHES` entry land
before the pull request that patches the definition does. Delete the name once that pull request
merges; `test_shared_definitions_are_byte_identical` fails with that instruction the moment the
patch lands, so the allowlist cannot stay disarmed by accident.
"""


def definition_names(paths: Iterable[PurePath]) -> set[str]:
    """List the entry names that `MAGIC_DEFS` loads as definitions."""
    return {path.name for path in paths if path.name not in IGNORED and not path.name.startswith(".")}


def read_upstream_files() -> dict[PurePosixPath, bytes]:
    """Read the committed bytes or their copy in the source distribution."""
    if not (UPSTREAM_ROOT / ".git").exists():
        files = [UPSTREAM_ROOT / COPYING, *UPSTREAM_MAGDIR.iterdir()]
        return {
            PurePosixPath(path.relative_to(UPSTREAM_ROOT).as_posix()): path.read_bytes()
            for path in files
            if path.is_file()
        }

    data = subprocess.check_output(
        [
            "git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
            "archive", "--format=tar", "HEAD", str(COPYING), str(MAGDIR),
        ],
        cwd=UPSTREAM_ROOT,
    )
    files_by_path = {}
    with tarfile.open(fileobj=BytesIO(data), mode="r:") as archive:
        for member in archive:
            if member.isfile():
                source = archive.extractfile(member)
                assert source is not None, member.name
                with source:
                    files_by_path[PurePosixPath(member.name)] = source.read()
    return files_by_path


@skipUnless(HAVE_MAGDIR, "the file submodule is not checked out")
class TestMagicDefsDrift(TestCase):
    """Guards the rule that `polyfile/magic_defs` is a copy of the `file` submodule's `Magdir`.

    The copy is maintained by hand and is not append-only in either direction. Definitions upstream
    deletes keep matching until someone notices, and a plain copy of `Magdir` silently reverts the
    local patches. These tests fail on both, and on the third case the allowlist exists for:
    upstream rewriting the lines a local patch touches.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.upstream_files = read_upstream_files()
        cls.upstream = definition_names(path for path in cls.upstream_files if path.parent == MAGDIR)
        cls.bundled = definition_names(MAGIC_DEFS_DIR.iterdir())
        assert cls.upstream, f"{UPSTREAM_MAGDIR} holds no definitions"

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
                if self.upstream_files[MAGDIR / name] != (MAGIC_DEFS_DIR / name).read_bytes():
                    self.fail(self.drift_message(name))

    def test_local_patches_are_still_applied(self):
        for name, issue in sorted(LOCAL_PATCHES.items()):
            if name in PENDING_PATCHES:
                continue
            with self.subTest(definition=name):
                if self.upstream_files[MAGDIR / name] == (MAGIC_DEFS_DIR / name).read_bytes():
                    self.fail(
                        f"polyfile/magic_defs/{name} is identical to file/magic/Magdir/{name}, so"
                        f" the patch from {issue} is gone. Mirroring Magdir reverts local patches;"
                        f" re-apply it, as {SYNC_DOC} describes. If upstream has fixed the problem"
                        f" the patch worked around, drop the entry from LOCAL_PATCHES instead"
                    )

    def test_copying_matches_upstream(self):
        if self.upstream_files.get(COPYING) != (MAGIC_DEFS_DIR / COPYING).read_bytes():
            self.fail(
                "polyfile/magic_defs/COPYING differs from the upstream license."
                f" Copy the committed license again, as {SYNC_DOC} describes."
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
