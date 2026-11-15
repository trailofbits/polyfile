"""Build, runtime, and lock metadata exclude vulnerable setuptools releases."""

from pathlib import Path
import tomllib

from packaging.requirements import Requirement
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(params=("build", "runtime", "lock"))
def setuptools_requirement(request: pytest.FixtureRequest) -> Requirement:
    """Read the setuptools requirement supplied to each installation path."""
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    if request.param == "build":
        requirements = metadata["build-system"]["requires"]
    elif request.param == "runtime":
        requirements = metadata["project"]["dependencies"]
    else:
        lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())
        package = next(package for package in lock["package"] if package["name"] == "polyfile")
        requirements = [
            item["name"] + item.get("specifier", "")
            for item in package["metadata"]["requires-dist"]
        ]
    for value in requirements:
        requirement = Requirement(value)
        if requirement.name == "setuptools":
            return requirement
    raise AssertionError(f"Missing setuptools requirement in {request.param} metadata")


@pytest.mark.parametrize("version", ("38.2.2", "83.0.0", "84.0.0"))
def test_installation_metadata_excludes_vulnerable_setuptools(
    setuptools_requirement: Requirement,
    version: str,
) -> None:
    assert version not in setuptools_requirement.specifier


def test_installation_metadata_accepts_the_qualified_setuptools(
    setuptools_requirement: Requirement,
) -> None:
    assert "84.2.1" in setuptools_requirement.specifier
