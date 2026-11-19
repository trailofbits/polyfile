"""Exercise checkout rebuilds against an isolated format library and compiler."""

import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
from unittest.mock import patch
from zipfile import ZipFile

import pytest

import compile_kaitai_parsers as compiler
from polyfile.kaitai import parser


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    formats = tmp_path / "formats"
    (formats / "image").mkdir(parents=True)
    output = tmp_path / "parsers"
    output.mkdir()
    (output / "__init__.py").touch()
    script = tmp_path / "compiler.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "if sys.argv[1] == '--install': sys.exit(0)\n"
        "spec, output = map(Path, sys.argv[1:])\n"
        "if 'invalid' in spec.read_text(): sys.exit(1)\n"
        "output.mkdir(parents=True, exist_ok=True)\n"
        "module = output / (spec.stem + '.py')\n"
        "module.write_text('from kaitaistruct import KaitaiStruct\\n'"
        " + 'class Example(KaitaiStruct): pass\\n' + '#' + repr(spec.read_text()))\n"
        "print(f'Example\\t{module}')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(compiler, "KAITAI_FORMAT_LIBRARY", formats)
    monkeypatch.setattr(compiler, "KAITAI_PARSERS_DIR", output)
    monkeypatch.setattr(compiler, "MANIFEST_PATH", output / "manifest.json")
    monkeypatch.setattr(compiler, "COMPILE_SCRIPT", script)
    return formats


def test_rebuild_retains_previous_generation_on_failure_and_can_retry(library: Path) -> None:
    spec = library / "image" / "example.ksy"
    spec.write_text("license: MIT\n", encoding="utf-8")
    compiler.rebuild(force=True)
    output = compiler.KAITAI_PARSERS_DIR
    previous = {p.name: p.read_bytes() for p in output.iterdir()}
    spec.write_text("license: MIT\n# changed\n", encoding="utf-8")
    broken = library / "broken.ksy"
    broken.write_text("license: MIT\ninvalid", encoding="utf-8")

    with pytest.raises(RuntimeError, match="broken.ksy"):
        compiler.rebuild(force=True)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == previous

    broken.write_text("license: MIT\n", encoding="utf-8")
    compiler.rebuild()
    assert set(json.loads(compiler.MANIFEST_PATH.read_bytes())) == {
        "image/example.ksy", "broken.ksy",
    }
    assert b"changed" in (output / "example.py").read_bytes()


def test_runtime_loads_regenerated_nested_spec(library: Path) -> None:
    (library / "image" / "example.ksy").write_text("license: MIT\n", encoding="utf-8")
    compiler.rebuild(force=True)
    with patch("importlib.resources.files", return_value=compiler.KAITAI_PARSERS_DIR):
        loader = runpy.run_path(parser.__file__)["KaitaiParser"]
    assert loader.load("image/example.ksy").struct_type.__name__ == "Example"


def test_repair_a_truncated_manifest_and_reuse_the_result(library: Path) -> None:
    (library / "image" / "example.ksy").write_text("license: MIT\n", encoding="utf-8")
    compiler.MANIFEST_PATH.write_text("{", encoding="utf-8")
    compiler.rebuild()
    compiler.COMPILE_SCRIPT.unlink()
    compiler.rebuild()
    assert set(json.loads(compiler.MANIFEST_PATH.read_bytes())) == {"image/example.ksy"}


def test_freshness_tracks_staged_and_untracked_inputs(library: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=library, check=True)
    spec = library / "image" / "example.ksy"
    spec.write_text("license: MIT\n", encoding="utf-8")
    compiler.rebuild(force=True)
    subprocess.run(["git", "add", "."], cwd=library, check=True)
    subprocess.run(
        ["git", "-c", "user.email=tests@example.org", "-c", "user.name=Test",
         "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Add a format"],
        cwd=library, check=True,
    )
    assert not compiler.is_stale([spec])

    spec.write_text("license: MIT\n# changed\n", encoding="utf-8")
    assert compiler.is_stale([spec])
    subprocess.run(["git", "add", "."], cwd=library, check=True)
    assert compiler.is_stale([spec])
    compiler.rebuild()
    assert not compiler.is_stale([spec])
    added = library / "new.ksy"
    added.write_text("license: MIT\n", encoding="utf-8")
    assert compiler.is_stale([spec, added])
    subprocess.run(["git", "add", "."], cwd=library, check=True)
    assert compiler.is_stale([spec, added])


@pytest.mark.parametrize("remove", [True, False])
def test_rebuild_drops_obsolete_parsers(library: Path, remove: bool) -> None:
    spec = library / "image" / "example.ksy"
    spec.write_text("license: MIT\n", encoding="utf-8")
    compiler.rebuild(force=True)
    if remove:
        spec.unlink()
    else:
        spec.write_text("license: unknown\n", encoding="utf-8")
    compiler.rebuild()
    assert json.loads(compiler.MANIFEST_PATH.read_bytes()) == {}
    assert {p.name for p in compiler.KAITAI_PARSERS_DIR.iterdir()} == {
        "__init__.py", "manifest.json",
    }
    assert not compiler.is_stale([])


def test_distributions_drop_modules_from_an_earlier_build(library: Path, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    for name in ("pyproject.toml", "MANIFEST.in", "compile_kaitai_parsers.py", "build_backend.py",
                 "CHANGELOG.md", "LICENSE", "README.md"):
        shutil.copyfile(compiler.POLYFILE_DIR / name, project / name)
    gallery = project / "kaitai_struct_formats"
    library.rename(gallery)
    (gallery / "README.md").touch()
    for name in ("polyfile", "polyfile/kaitai", "polyfile/kaitai/parsers"):
        directory = project / name
        directory.mkdir()
        (directory / "__init__.py").touch()
    shutil.copyfile(compiler.COMPILE_SCRIPT, project / "polyfile/kaitai/compiler.py")
    removed = gallery / "image" / "removed.ksy"
    removed.write_text("license: MIT\n", encoding="utf-8")
    (gallery / "keep.ksy").write_text("license: MIT\n", encoding="utf-8")
    dist = project / "dist"
    dist.mkdir()
    build = [sys.executable, "-c", "import build_backend as b; b.build_wheel('dist')"]
    subprocess.run(build, cwd=project, check=True, stdout=subprocess.DEVNULL)
    wheel, = dist.glob("*.whl")
    with ZipFile(wheel) as archive:
        assert "polyfile/kaitai/parsers/removed.py" in archive.namelist()
    removed.unlink()
    subprocess.run(build, cwd=project, check=True, stdout=subprocess.DEVNULL)
    with ZipFile(wheel) as archive:
        assert "polyfile/kaitai/parsers/removed.py" not in archive.namelist()
        assert "polyfile/kaitai/parsers/keep.py" in archive.namelist()
    subprocess.run(
        [sys.executable, "-c", "import build_backend as b; b.build_sdist('dist')"],
        cwd=project, check=True, stdout=subprocess.DEVNULL,
    )
    sdist, = dist.glob("*.tar.gz")
    with tarfile.open(sdist) as archive:
        assert not any(name.endswith("/parsers/removed.py") for name in archive.getnames())
        assert any(name.endswith("/parsers/keep.py") for name in archive.getnames())
