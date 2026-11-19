import concurrent.futures
from collections.abc import Callable, Iterable
import hashlib
from importlib import import_module
import json
from multiprocessing import cpu_count
from pathlib import Path
import re
from re import Pattern
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Protocol, Self, TypedDict, cast

POLYFILE_DIR: Path = Path(__file__).absolute().parent
COMPILE_SCRIPT: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "compiler.py"
KAITAI_FORMAT_LIBRARY: Path = POLYFILE_DIR / "kaitai_struct_formats"
KAITAI_PARSERS_DIR: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "parsers"
MANIFEST_PATH: Path = KAITAI_PARSERS_DIR / "manifest.json"


class _ParserReference(TypedDict):
    class_name: str
    python_path: str


class _ParserManifestEntry(_ParserReference):
    dependencies: list[_ParserReference]
    source_sha256: str


class _ProgressBar(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None,
        traceback: TracebackType | None, /
    ) -> None: ...

    def write(self, message: str) -> None: ...

    def update(self, n: int) -> object: ...


# PolyFile is distributed under the Apache 2.0 license. A parser generated from a format
# specification is a derivative work of that specification, so PolyFile can only ship parsers
# generated from specifications under a compatible permissive license. Every specification whose
# license is not in this set is excluded from compilation, including specifications that declare no
# license at all. See docs/extending_polyfile.md before adding a license here.
PERMISSIVE_LICENSES: frozenset[str] = frozenset({
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause-Attribution",
    "CC0-1.0",
    "MIT",
    "Unlicense",
    "WTFPL",
})

LICENSE_PATTERN: Pattern[str] = re.compile(r"^\s*license:\s*(?P<license>\S+)\s*$")


# Make sure the ktaitai_struct_formats submodlue is cloned:
if not (KAITAI_FORMAT_LIBRARY / "README.md").exists():
    subprocess.check_call(["git", "submodule", "init"], cwd=str(POLYFILE_DIR))
    subprocess.check_call(["git", "submodule", "update"], cwd=str(POLYFILE_DIR))


def spec_license(spec: Path) -> str | None:
    """Reads the license declared by a Kaitai Struct format specification.

    Args:
        spec: the ``.ksy`` specification to read.

    Returns:
        The value of the specification's ``license`` key, or :const:`None` if it declares none.

    Raises:
        ValueError: if the specification is not valid UTF-8.
    """
    try:
        with open(spec, encoding="utf-8") as f:
            for line in f:
                match = LICENSE_PATTERN.match(line)
                if match is not None:
                    return cast(str, match.group("license"))
    except UnicodeDecodeError as e:
        raise ValueError(f"Could not read the license of {spec}: it is not valid UTF-8") from e
    return None


def excluded_specs(library: Path = KAITAI_FORMAT_LIBRARY) -> dict[Path, str | None]:
    """Finds the format specifications that PolyFile is not permitted to redistribute.

    Args:
        library: the root of the Kaitai Struct format library to scan.

    Returns:
        Each specification whose license is not in :data:`PERMISSIVE_LICENSES`, mapped to the
        license it declares, or :const:`None` if it declares none.
    """
    excluded: dict[Path, str | None] = {}
    for spec in sorted(library.glob("**/*.ksy")):
        license_name = spec_license(spec)
        if license_name not in PERMISSIVE_LICENSES:
            excluded[spec] = license_name
    return excluded


def report_excluded(excluded: dict[Path, str | None]):
    if not excluded:
        return
    print(f"Excluding {len(excluded)} format specification(s) without a permissive license:")
    for spec, license_name in excluded.items():
        print(f"  {license_name or 'no license':<24} {spec.relative_to(KAITAI_FORMAT_LIBRARY)}")


def compile_ksy(path: Path, output_directory: Path) -> list[tuple[str, str]]:
    output = subprocess.check_output(
        [sys.executable, str(COMPILE_SCRIPT), str(path), str(output_directory)],
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ).decode("utf-8")
    compiled = []
    for line in output.splitlines():
        if line.strip():
            class_name, python_path = line.split("\t")[:2]
            compiled.append((class_name, python_path))
    return compiled


def _source_hash(spec: Path) -> str:
    # Text mode normalizes Git checkout line endings on Windows.
    return hashlib.sha256(spec.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def is_stale(specs: Iterable[Path]) -> bool:
    """Check whether the generated modules describe the current eligible specifications."""
    inputs = {spec.relative_to(KAITAI_FORMAT_LIBRARY).as_posix(): _source_hash(spec)
              for spec in specs}
    try:
        with MANIFEST_PATH.open(encoding="utf-8") as source:
            manifest: dict[str, _ParserManifestEntry] = json.load(source)
    except (FileNotFoundError, json.JSONDecodeError):
        return True
    if inputs != {key: entry.get("source_sha256") for key, entry in manifest.items()}:
        return True
    expected = {entry["python_path"] for entry in manifest.values()} | {"__init__.py"}
    return expected != {module.name for module in KAITAI_PARSERS_DIR.glob("*.py")}


def progress_bar(total: int) -> _ProgressBar:
    try:
        tqdm = cast(Callable[..., _ProgressBar], getattr(import_module("tqdm"), "tqdm"))
    except ModuleNotFoundError:
        class TQDM:
            def __enter__(self) -> Self:
                return self

            def __exit__(
                self, exc_type: type[BaseException] | None, exc_val: BaseException | None,
                exc_tb: TracebackType | None
            ) -> None:
                pass

            def write(self, message: str, *_: object, **__: object) -> None:
                sys.stderr.write(message)
                sys.stderr.write("\n")
                sys.stderr.flush()

            def update(self, n: int) -> None:
                pass
        return TQDM()
    return tqdm(leave=False, desc="Compiling the Kaitai Struct Format Library", total=total)


def manifest_entry(
    compiled: list[tuple[str, str]], directory: Path, source_hash: str
) -> _ParserManifestEntry:
    (class_name, python_path), *dependencies = compiled
    return {
        "class_name": class_name,
        "python_path": Path(python_path).relative_to(directory).as_posix(),
        "source_sha256": source_hash,
        "dependencies": [
            {
                "class_name": dependency_class_name,
                "python_path": Path(dependency_python_path).relative_to(directory).as_posix(),
            }
            for dependency_class_name, dependency_python_path in dependencies
        ]
    }


def _compile_spec(spec: Path, staging: Path) -> tuple[str, _ParserManifestEntry, Path]:
    key = spec.relative_to(KAITAI_FORMAT_LIBRARY).as_posix()
    directory = staging / "specs" / key
    source_hash = _source_hash(spec)
    try:
        entry = manifest_entry(compile_ksy(spec, directory), directory, source_hash)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Failed to compile {key}: {error}") from error
    return key, entry, directory / entry["python_path"]


def compile_all(specs: list[Path], staging: Path) -> dict[str, _ParserManifestEntry]:
    """Compile eligible inputs separately so concurrent compilers cannot overwrite dependencies."""
    ksy_manifest: dict[str, _ParserManifestEntry] = {}
    with progress_bar(len(specs)) as progress, concurrent.futures.ThreadPoolExecutor(
        max_workers=cpu_count()
    ) as executor:
        futures = [executor.submit(_compile_spec, spec, staging) for spec in specs]
        for future in concurrent.futures.as_completed(futures):
            key, entry, module = future.result()
            target = staging / module.name
            if target.exists():
                raise ValueError(f"{key} generates a duplicate module: {module.name}")
            module.replace(target)
            ksy_manifest[key] = entry
            progress.write(f"Compiled {key}")
            progress.update(1)
    modules = {entry["python_path"] for entry in ksy_manifest.values()}
    for key, entry in ksy_manifest.items():
        missing = {dep["python_path"] for dep in entry["dependencies"]} - modules
        if missing:
            raise ValueError(f"{key} requires modules without eligible specs: {sorted(missing)}")
    return ksy_manifest


def rebuild(force: bool = False):
    excluded = excluded_specs(KAITAI_FORMAT_LIBRARY)
    specs = [spec for spec in sorted(KAITAI_FORMAT_LIBRARY.glob("**/*.ksy")) if spec not in excluded]

    if not force and not is_stale(specs):
        return

    # the definitions have been updated, so we need to recompile everything
    report_excluded(excluded)

    if subprocess.call([sys.executable, str(COMPILE_SCRIPT), "--install"]) != 0:
        sys.stderr.write("Error: You must have kaitai-struct-compiler installed\nSee https://kaitai.io/#download\n")
        sys.exit(1)

    with TemporaryDirectory(dir=KAITAI_PARSERS_DIR.parent) as directory:
        staging = Path(directory)
        manifest = compile_all(specs, staging)
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(json.dumps(dict(sorted(manifest.items()))), encoding="utf-8")
        modules = {entry["python_path"] for entry in manifest.values()}
        for name in modules:
            (staging / name).replace(KAITAI_PARSERS_DIR / name)
        for obsolete in KAITAI_PARSERS_DIR.glob("*.py"):
            if obsolete.name != "__init__.py" and obsolete.name not in modules:
                obsolete.unlink()
        staged_manifest.replace(MANIFEST_PATH)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-all", "-a", action="store_true", help="rebuilds all parsers from scratch")
    parser.add_argument("--audit", action="store_true",
                        help="lists the format specifications that are excluded from compilation, and exits")

    args = parser.parse_args()

    if args.audit:
        report_excluded(excluded_specs())
    else:
        rebuild(force=args.rebuild_all)
