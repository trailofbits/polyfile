"""Verify that a release tag and its distributions agree on the release version."""

from argparse import ArgumentParser
from email.parser import BytesHeaderParser
from pathlib import Path
import re
import tarfile
import zipfile


def _changelog_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = line.rstrip()
        if heading.startswith("## [") and heading != "## [Unreleased]":
            release = re.fullmatch(r"## \[([^\]]+)\] - \d{4}-\d{2}-\d{2}", heading)
            if release is None:
                raise ValueError(f"{path} has an invalid release heading: {heading!r}")
            return str(release[1])
    raise ValueError(f"{path} has no dated release heading")


def _metadata_version(data: bytes, path: Path) -> str:
    versions = BytesHeaderParser().parsebytes(data).get_all("Version") or []
    if len(versions) != 1 or not str(versions[0]).strip():
        raise ValueError(f"{path} metadata must contain exactly one nonempty Version field")
    return str(versions[0]).strip()


def _wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as wheel:
        entries = [
            entry
            for entry in wheel.infolist()
            if re.fullmatch(r"[^/]+\.dist-info/METADATA", entry.filename)
        ]
        if len(entries) != 1:
            raise ValueError(f"{path} must contain exactly one .dist-info/METADATA file")
        return _metadata_version(wheel.read(entries[0]), path)


def _sdist_version(path: Path) -> str:
    with tarfile.open(path, "r:gz") as sdist:
        entries = [
            entry
            for entry in sdist.getmembers()
            if re.fullmatch(r"[^/]+/PKG-INFO", entry.name) and entry.isfile()
        ]
        if len(entries) != 1:
            raise ValueError(f"{path} must contain exactly one top-level PKG-INFO file")
        metadata = sdist.extractfile(entries[0])
        assert metadata is not None
        with metadata:
            return _metadata_version(metadata.read(), path)


def _only_artifact(directory: Path, pattern: str) -> Path:
    artifacts = list(directory.glob(pattern))
    if len(artifacts) != 1:
        raise ValueError(f"Expected one {pattern} in {directory}, found {len(artifacts)}")
    return artifacts[0]


def _verify_release(tag: str, changelog: Path, dist: Path) -> str:
    versions = {
        "release tag": tag.removeprefix("v"),
        "changelog": _changelog_version(changelog),
        "wheel metadata": _wheel_version(_only_artifact(dist, "*.whl")),
        "sdist metadata": _sdist_version(_only_artifact(dist, "*.tar.gz")),
    }
    if len(set(versions.values())) != 1:
        detail = ", ".join(f"{source}={version!r}" for source, version in versions.items())
        raise ValueError(f"Release versions disagree ({detail})")
    return versions["release tag"]


def main() -> None:
    """Check the release tag, changelog, and artifacts in the working directory."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Git tag for the release")
    arguments = parser.parse_args()
    try:
        version = _verify_release(arguments.tag, Path("CHANGELOG.md"), Path("dist"))
    except (EOFError, OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Release version check failed: {error}\n")
    print(f"Verified release version {version}")


if __name__ == "__main__":
    main()
