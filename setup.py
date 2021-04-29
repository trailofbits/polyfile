import concurrent.futures
import json
from multiprocessing import cpu_count
import os
from pathlib import Path
from setuptools import setup, find_packages
import subprocess
import sys
from typing import Any, Dict, List, Tuple

VERSION_MODULE_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "polyfile", "version.py")


# Build the entire Kaitai struct format library:
POLYTRACKER_DIR: Path = Path(__file__).absolute().parent
COMPILE_SCRIPT: Path = POLYTRACKER_DIR / "polyfile" / "kaitai" / "compiler.py"
KAITAI_FORMAT_LIBRARY: Path = POLYTRACKER_DIR / "kaitai_struct_formats"
KAITAI_PARSERS_DIR: Path = POLYTRACKER_DIR / "polyfile" / "kaitai" / "parsers"


# Make sure the ktaitai_struct_formats submodlue is cloned:
if not (KAITAI_FORMAT_LIBRARY / "README.md").exists():
    subprocess.check_call(["git", "submodule", "init"], cwd=str(POLYTRACKER_DIR))
    subprocess.check_call(["git", "submodule", "update"], cwd=str(POLYTRACKER_DIR))


def compile_ksy(path: Path) -> List[Tuple[str, str]]:
    output = subprocess.check_output(
        [sys.executable, str(COMPILE_SCRIPT), str(path), str(KAITAI_PARSERS_DIR)],
        cwd=str(KAITAI_FORMAT_LIBRARY)
    ).decode("utf-8")
    return [  # type: ignore
        tuple(line.split("\t")[:2])  # (class_name, python_path)
        for line in output.split("\n") if line.strip()
    ]


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
            def write(self, message, *args, **kwargs):
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

with open(KAITAI_PARSERS_DIR / "manifest.json", "w") as f:
    json.dump(ksy_manifest, f)


def get_version_string():
    version = {}
    with open(VERSION_MODULE_PATH) as f:
        exec(f.read(), version)
    return version['VERSION_STRING']


setup(
    name='polyfile',
    description='A utility to recursively map the structure of a file.',
    url='https://github.com/trailofbits/polyfile',
    author='Trail of Bits',
    version=get_version_string(),
    packages=find_packages(exclude=("tests",)),
    python_requires='>=3.6',
    install_requires=[
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
    },
    entry_points={
        'console_scripts': [
            'polyfile = polyfile.__main__:main',
            'polymerge = polymerge.__main__:main'
        ]
    },
    package_data={"polyfile": [
        os.path.join("templates", "*"),
        str(KAITAI_PARSERS_DIR / "*.py"),
        str(KAITAI_PARSERS_DIR / "manifest.json")
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
