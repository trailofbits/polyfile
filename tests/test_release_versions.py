"""Exercise the release version check on wheel and sdist files."""

from io import BytesIO
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest


CHECK = Path(__file__).resolve().parents[1] / "scripts" / "check_release_versions.py"
WHEEL_NAME = "polyfile-1.2.3-py3-none-any.whl"
SDIST_NAME = "polyfile-1.2.3.tar.gz"


def _run_check(directory: Path, tag: str = "v1.2.3") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), "--", tag],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_changelog(directory: Path, version: str) -> None:
    (directory / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [{version}] - 2026-10-01\n\n"
        "## [1.2.2] - 2026-09-01\n",
        encoding="utf-8",
    )


def _write_wheel(path: Path, metadata: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("polyfile-1.2.3.dist-info/METADATA", metadata)


def _write_sdist(path: Path, metadata: str) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, contents in (
            ("polyfile-1.2.3/polyfile.egg-info/PKG-INFO", "Version: 1.2.2\n"),
            ("polyfile-1.2.3/PKG-INFO", metadata),
        ):
            data = contents.encode("utf-8")
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            archive.addfile(entry, BytesIO(data))


@pytest.fixture
def release(tmp_path: Path) -> Path:
    """Create a release with matching changelog and distribution metadata."""
    dist = tmp_path / "dist"
    dist.mkdir()
    _write_changelog(tmp_path, "1.2.3")
    _write_wheel(dist / WHEEL_NAME, "Version: 1.2.3\n")
    _write_sdist(dist / SDIST_NAME, "Version: 1.2.3\n")
    return tmp_path


def test_accepts_matching_release_versions(release: Path) -> None:
    result = _run_check(release)
    assert result.returncode == 0, result.stderr
    assert "Verified release version 1.2.3" in result.stdout


@pytest.mark.parametrize("source", ["release tag", "changelog", "wheel metadata", "sdist metadata"])
def test_rejects_a_mismatch_in_any_source(release: Path, source: str) -> None:
    tag = "v1.2.2" if source == "release tag" else "v1.2.3"
    if source == "changelog":
        _write_changelog(release, "1.2.4")
    elif source == "wheel metadata":
        _write_wheel(release / "dist" / WHEEL_NAME, "Version: 1.2.2\n")
    elif source == "sdist metadata":
        _write_sdist(release / "dist" / SDIST_NAME, "Version: 1.2.2\n")

    result = _run_check(release, tag)
    assert result.returncode == 1
    assert "Release versions disagree" in result.stderr
    expected = "1.2.4" if source == "changelog" else "1.2.2"
    assert f"{source}={expected!r}" in result.stderr


@pytest.mark.parametrize(
    ("heading", "reason"),
    [
        ("", "no dated release heading"),
        ("## [1.2.3]\n\n## [1.2.2] - 2026-09-01\n", "invalid release heading"),
    ],
)
def test_requires_a_dated_release_heading(release: Path, heading: str, reason: str) -> None:
    (release / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n{heading}", encoding="utf-8"
    )

    result = _run_check(release)
    assert result.returncode == 1
    assert reason in result.stderr


@pytest.mark.parametrize("artifact", [WHEEL_NAME, SDIST_NAME])
def test_rejects_a_missing_distribution(release: Path, artifact: str) -> None:
    (release / "dist" / artifact).unlink()

    result = _run_check(release)
    assert result.returncode == 1
    assert "found 0" in result.stderr


@pytest.mark.parametrize("artifact", [WHEEL_NAME, SDIST_NAME])
def test_rejects_a_corrupt_distribution(release: Path, artifact: str) -> None:
    path = release / "dist" / artifact
    path.write_bytes(path.read_bytes()[:20])

    result = _run_check(release)
    assert result.returncode == 1
    assert "Release version check failed" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("metadata", ["Name: polyfile\n", "Version: 1.2.3\nVersion: 1.2.2\n"])
def test_rejects_missing_or_duplicate_version_headers(release: Path, metadata: str) -> None:
    _write_wheel(release / "dist" / WHEEL_NAME, metadata)

    result = _run_check(release)
    assert result.returncode == 1
    assert "exactly one nonempty Version field" in result.stderr
