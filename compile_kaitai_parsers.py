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
from typing import NamedTuple, Protocol, Self, TypedDict, cast

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


class _Compiler(NamedTuple):
    path: Path
    version: str


class _Generator(TypedDict):
    compiler_version: str | None
    scripts_sha256: dict[str, str]


class _Manifest(TypedDict):
    generator: _Generator
    specs: dict[str, _ParserManifestEntry]


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


def compile_ksy(
    path: Path, output_directory: Path, executable: Path | None = None,
) -> list[tuple[str, str]]:
    options = ["--compiler", str(executable)] if executable else []
    output = subprocess.check_output(
        [sys.executable, COMPILE_SCRIPT, *options, path, output_directory],
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ).decode("utf-8")
    compiled = []
    for line in output.splitlines():
        if line.strip():
            class_name, python_path = line.split("\t")[:2]
            compiled.append((class_name, python_path))
    return compiled


def _source_hash(path: Path) -> str:
    # Text mode normalizes Git checkout line endings on Windows.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _probe_compiler(*, install: bool = False) -> _Compiler | None:
    option = "--install" if install else "--locate"
    location = subprocess.check_output([sys.executable, COMPILE_SCRIPT, option], text=True).strip()
    if not location:
        return None
    path = Path(location).resolve()
    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, text=True, check=True, timeout=15,
        )
        banner = result.stdout.strip()
        match = re.fullmatch(r"kaitai-struct-compiler[ \t]+(\S[^\r\n]*)", banner)
        if match is None:
            raise ValueError(f"Unexpected compiler version output: {banner!r}")
        return _Compiler(path, match[1])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        if install:
            raise RuntimeError(f"Cannot verify {path} --version: {error}") from error
        return None


def _generator(compiler: _Compiler | None) -> _Generator:
    return {
        "compiler_version": compiler.version if compiler else None,
        "scripts_sha256": {
            "compile_kaitai_parsers.py": _source_hash(Path(__file__)),
            "polyfile/kaitai/compiler.py": _source_hash(COMPILE_SCRIPT),
        },
    }


def is_stale(specs: Iterable[Path], *, generator: _Generator | None = None) -> bool:
    """Check the generator, eligible specifications, and installed module names."""
    if generator is None:
        generator = _generator(_probe_compiler())
    inputs = {spec.relative_to(KAITAI_FORMAT_LIBRARY).as_posix(): _source_hash(spec)
              for spec in specs}
    try:
        with MANIFEST_PATH.open(encoding="utf-8") as source:
            manifest: _Manifest = json.load(source)
        previous = manifest["generator"]
        version = previous["compiler_version"]
        entries = manifest["specs"]
        sources = {key: entry["source_sha256"] for key, entry in entries.items()}
        expected = {entry["python_path"] for entry in entries.values()} | {"__init__.py"}
        scripts_match = previous["scripts_sha256"] == generator["scripts_sha256"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return True
    if not isinstance(version, str) or not version or not scripts_match or sources != inputs:
        return True
    if generator["compiler_version"] is not None and version != generator["compiler_version"]:
        return True
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


def _compile_spec(
    spec: Path, staging: Path, executable: Path,
) -> tuple[str, _ParserManifestEntry, Path]:
    key = spec.relative_to(KAITAI_FORMAT_LIBRARY).as_posix()
    directory = staging / "specs" / key
    source_hash = _source_hash(spec)
    try:
        entry = manifest_entry(compile_ksy(spec, directory, executable), directory, source_hash)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Failed to compile {key}: {error}") from error
    return key, entry, directory / entry["python_path"]


def compile_all(
    specs: list[Path], staging: Path, executable: Path,
) -> dict[str, _ParserManifestEntry]:
    """Compile eligible inputs separately so concurrent compilers cannot overwrite dependencies."""
    ksy_manifest: dict[str, _ParserManifestEntry] = {}
    with progress_bar(len(specs)) as progress, concurrent.futures.ThreadPoolExecutor(
        max_workers=cpu_count()
    ) as executor:
        futures = [executor.submit(_compile_spec, spec, staging, executable) for spec in specs]
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

    compiler = _probe_compiler()
    generator = _generator(compiler)
    if not force and not is_stale(specs, generator=generator):
        return

    report_excluded(excluded)
    if compiler is None:
        compiler = _probe_compiler(install=True)
        if compiler is None:
            raise RuntimeError("Install the Kaitai compiler to regenerate the parsers")
        generator["compiler_version"] = compiler.version

    with TemporaryDirectory(dir=KAITAI_PARSERS_DIR.parent) as directory:
        staging = Path(directory)
        entries = compile_all(specs, staging, compiler.path)
        manifest: _Manifest = {"generator": generator, "specs": dict(sorted(entries.items()))}
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        modules = {entry["python_path"] for entry in entries.values()}
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
