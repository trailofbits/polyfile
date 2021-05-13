import concurrent.futures
import json
import shutil
from multiprocessing import cpu_count
import os
from pathlib import Path
from setuptools import setup, find_packages
from shutil import which
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

VERSION_MODULE_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "polyfile", "version.py")


# Build the entire Kaitai struct format library:
POLYFILE_DIR: Path = Path(__file__).absolute().parent
COMPILE_SCRIPT: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "compiler.py"
KAITAI_FORMAT_LIBRARY: Path = POLYFILE_DIR / "kaitai_struct_formats"
KAITAI_PARSERS_DIR: Path = POLYFILE_DIR / "polyfile" / "kaitai" / "parsers"
MANIFEST_PATH: Path = KAITAI_PARSERS_DIR / "manifest.json"
README_PATH: Path = POLYFILE_DIR / "README.md"


# Make sure the ktaitai_struct_formats submodlue is cloned:
if not (KAITAI_FORMAT_LIBRARY / "README.md").exists():
    subprocess.check_call(["git", "submodule", "init"], cwd=str(POLYFILE_DIR))
    subprocess.check_call(["git", "submodule", "update"], cwd=str(POLYFILE_DIR))


def compile_ksy(path: Path) -> List[Tuple[str, str]]:
    output = subprocess.check_output(
        [sys.executable, str(COMPILE_SCRIPT), str(path), str(KAITAI_PARSERS_DIR)],
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ).decode("utf-8")
    return [  # type: ignore
        tuple(line.split("\t")[:2])  # (class_name, python_path)
        for line in output.split("\n") if line.strip()
    ]


# see if any of the files are out of date and need to be recompiled
newest_definition: Optional[float] = None
for definition in KAITAI_FORMAT_LIBRARY.glob("**/*.ksy"):
    mtime = definition.stat().st_mtime
    if newest_definition is None or newest_definition < mtime:
        newest_definition = mtime

if not MANIFEST_PATH.exists() or newest_definition > MANIFEST_PATH.stat().st_mtime:
    # the definitions have been updated, so we need to recompile everything

    if shutil.which("kaitai-struct-compiler") is None:
        sys.stderr.write("Error: You must have kaitai-struct-compiler installed")
        sys.exit(1)

    num_files = sum(1 for _ in KAITAI_FORMAT_LIBRARY.glob("**/*.ksy"))

    try:
        from tqdm import tqdm
    except ModuleNotFoundError:
        def tqdm(*args, **kwargs):
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

    ksy_manifest: Dict[str, Dict[str, Any]] = {}

    with tqdm(leave=False, desc="Compiling the Kaitai Struct Format Library", total=num_files) as t:
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count()) as executor:
            futures_to_path: Dict[concurrent.futures.Future, Path] = {
                executor.submit(compile_ksy, file): file
                for file in KAITAI_FORMAT_LIBRARY.glob("**/*.ksy")
            }
            for future in concurrent.futures.as_completed(futures_to_path):
                t.update(1)
                path = futures_to_path[future]
                relative_path = str(path.relative_to(KAITAI_FORMAT_LIBRARY))
                if relative_path in ksy_manifest:
                    raise ValueError(f"{relative_path} appears twice in the Kaitai format library!")
                try:
                    (first_spec_class_name, first_spec_python_path), *dependencies = future.result()
                    ksy_manifest[relative_path] = {
                        "class_name": first_spec_class_name,
                        "python_path": str(Path(first_spec_python_path).relative_to(KAITAI_PARSERS_DIR)),
                        "dependencies": [
                            {
                                "class_name": class_name,
                                "python_path": str(Path(python_path).relative_to(KAITAI_PARSERS_DIR))
                            }
                            for class_name, python_path in dependencies
                        ]
                    }
                    t.write(f"Compiled {path.name}")
                except Exception as e:
                    t.write(f"Warning: Failed to compile {path}: {e}\n")

    with open(MANIFEST_PATH, "w") as f:
        json.dump(ksy_manifest, f)


def get_version_string():
    version = {}
    with open(VERSION_MODULE_PATH) as f:
        exec(f.read(), version)
    return version['VERSION_STRING']


with open(README_PATH, "r") as readme:
    README = readme.read()

setup(
    name='polyfile',
    description='A utility to recursively map the structure of a file.',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://github.com/trailofbits/polyfile',
    author='Trail of Bits',
    version=get_version_string(),
    packages=find_packages(exclude=("tests",)),
    python_requires='>=3.6',
    install_requires=[
        "dataclasses;python_version<'3.7'",  # dataclasses were only added in Python 3.7
        'graphviz',
        'intervaltree',
        'jinja2',
        'kaitaistruct>=0.7',
        'networkx',
        'Pillow>=5.0.0',
        'pyyaml>=3.13',
        'setuptools'
    ],
    extras_require={
        'demangle': ['cxxfilt'],
        "dev": ["mypy", "pytest", "flake8"]
    },
    entry_points={
        'console_scripts': [
            'polyfile = polyfile.__main__:main',
            'polymerge = polymerge.__main__:main'
        ]
    },
    package_data={"polyfile": [
        os.path.join("templates", "*"),
        os.path.join("kaitai", "parsers", "*.py"),
        os.path.join("kaitai", "parsers", "manifest.json"),
        os.path.join("magic_defs", "*")
    ]},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Security',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities'
    ]
)
