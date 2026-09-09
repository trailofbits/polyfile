import concurrent.futures
from datetime import datetime, timezone
import json
from multiprocessing import cpu_count
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Pattern, Tuple

POLYFILE_DIR: Path = Path(__file__).absolute().parent
COMPILE_SCRIPT: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "compiler.py"
KAITAI_FORMAT_LIBRARY: Path = POLYFILE_DIR / "kaitai_struct_formats"
KAITAI_PARSERS_DIR: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "parsers"
MANIFEST_PATH: Path = KAITAI_PARSERS_DIR / "manifest.json"

# PolyFile is distributed under the Apache 2.0 license. A parser generated from a format
# specification is a derivative work of that specification, so PolyFile can only ship parsers
# generated from specifications under a compatible permissive license. Every specification whose
# license is not in this set is excluded from compilation, including specifications that declare no
# license at all. See docs/extending_polyfile.md before adding a license here.
PERMISSIVE_LICENSES: FrozenSet[str] = frozenset({
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


def spec_license(spec: Path) -> Optional[str]:
    """Reads the license declared by a Kaitai Struct format specification.

    Args:
        spec: the ``.ksy`` specification to read.

    Returns:
        The value of the specification's ``license`` key, or :const:`None` if it declares none.

    Raises:
        ValueError: if the specification is not valid UTF-8.
    """
    try:
        with open(spec, "r", encoding="utf-8") as f:
            for line in f:
                match = LICENSE_PATTERN.match(line)
                if match is not None:
                    return match.group("license")
    except UnicodeDecodeError as e:
        raise ValueError(f"Could not read the license of {spec}: it is not valid UTF-8") from e
    return None


def excluded_specs(library: Path = KAITAI_FORMAT_LIBRARY) -> Dict[Path, Optional[str]]:
    """Finds the format specifications that PolyFile is not permitted to redistribute.

    Args:
        library: the root of the Kaitai Struct format library to scan.

    Returns:
        Each specification whose license is not in :data:`PERMISSIVE_LICENSES`, mapped to the
        license it declares, or :const:`None` if it declares none.
    """
    excluded: Dict[Path, Optional[str]] = {}
    for spec in sorted(library.glob("**/*.ksy")):
        license_name = spec_license(spec)
        if license_name not in PERMISSIVE_LICENSES:
            excluded[spec] = license_name
    return excluded


def report_excluded(excluded: Dict[Path, Optional[str]]):
    if not excluded:
        return
    print(f"Excluding {len(excluded)} format specification(s) without a permissive license:")
    for spec, license_name in excluded.items():
        print(f"  {license_name or 'no license':<24} {spec.relative_to(KAITAI_FORMAT_LIBRARY)}")


def compile_ksy(path: Path) -> List[Tuple[str, str]]:
    output = subprocess.check_output(
        [sys.executable, str(COMPILE_SCRIPT), str(path), str(KAITAI_PARSERS_DIR)],
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ).decode("utf-8")
    return [  # type: ignore
        tuple(line.split("\t")[:2])  # (class_name, python_path)
        for line in output.split("\n") if line.strip()
    ]


def mtime(path: Path) -> datetime:
    # has the file been modified?
    was_modified = subprocess.call(
        ["git", "diff", "--exit-code", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ) != 0
    if was_modified:
        # the file was modified since the last commit, so use its filesystem mtime
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    # the file has not been modified since the last commit, so use the last commit time
    last_commit_date = subprocess.check_output(["git", "log", "-1", "--format=\"%cd\"", str(path)],
                                               cwd=str(KAITAI_FORMAT_LIBRARY)).decode("utf-8").strip()
    return datetime.strptime(last_commit_date, "\"%a %b %d %H:%M:%S %Y %z\"")


def is_stale(specs: Iterable[Path]) -> bool:
    """Determines whether any specification has been modified since the manifest was written."""
    newest_definition: Optional[datetime] = None
    for definition in specs:
        modtime = mtime(definition)
        if newest_definition is None or newest_definition < modtime:
            newest_definition = modtime
    return newest_definition is not None and newest_definition > mtime(MANIFEST_PATH)


def progress_bar(total: int):
    try:
        from tqdm import tqdm
    except ModuleNotFoundError:
        class TQDM:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def write(self, message, *_, **__):
                sys.stderr.write(message)
                sys.stderr.write("\n")
                sys.stderr.flush()

            def update(self, n: int):
                pass
        return TQDM()
    return tqdm(leave=False, desc="Compiling the Kaitai Struct Format Library", total=total)


def manifest_entry(compiled: List[Tuple[str, str]]) -> Dict[str, Any]:
    (class_name, python_path), *dependencies = compiled
    return {
        "class_name": class_name,
        "python_path": str(Path(python_path).relative_to(KAITAI_PARSERS_DIR)),
        "dependencies": [
            {
                "class_name": dependency_class_name,
                "python_path": str(Path(dependency_python_path).relative_to(KAITAI_PARSERS_DIR))
            }
            for dependency_class_name, dependency_python_path in dependencies
        ]
    }


def compile_all(specs: List[Path]) -> Dict[str, Dict[str, Any]]:
    """Compiles format specifications in parallel and returns the manifest describing them."""
    ksy_manifest: Dict[str, Dict[str, Any]] = {}
    with progress_bar(len(specs)) as t:
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count()) as executor:
            futures_to_path: Dict[concurrent.futures.Future, Path] = {
                executor.submit(compile_ksy, spec): spec
                for spec in specs
            }
            for future in concurrent.futures.as_completed(futures_to_path):
                t.update(1)
                path = futures_to_path[future]
                relative_path = str(path.relative_to(KAITAI_FORMAT_LIBRARY))
                if relative_path in ksy_manifest:
                    raise ValueError(f"{relative_path} appears twice in the Kaitai format library!")
                try:
                    ksy_manifest[relative_path] = manifest_entry(future.result())
                    t.write(f"Compiled {path.name}")
                except Exception as e:
                    t.write(f"Warning: Failed to compile {path}: {e}\n")
    return ksy_manifest


def rebuild(force: bool = False):
    excluded = excluded_specs()
    specs = [spec for spec in sorted(KAITAI_FORMAT_LIBRARY.glob("**/*.ksy")) if spec not in excluded]

    # Remove the manifest file to force a rebuild:
    if force or not MANIFEST_PATH.exists():
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink()
        needs_rebuild = True
    else:
        needs_rebuild = is_stale(specs)

    if not needs_rebuild:
        return

    # the definitions have been updated, so we need to recompile everything
    report_excluded(excluded)

    if subprocess.call([sys.executable, str(COMPILE_SCRIPT), "--install"]) != 0:
        sys.stderr.write("Error: You must have kaitai-struct-compiler installed\nSee https://kaitai.io/#download\n")
        sys.exit(1)

    with open(MANIFEST_PATH, "w") as f:
        json.dump(compile_all(specs), f)


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
