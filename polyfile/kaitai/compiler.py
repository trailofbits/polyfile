#!/usr/bin/env python3

"""
This module automates compilation of Kaitai Struct definitions into Python code.

This script is called from PolyFile's setup.py to compile the entire Kaitai Struct format library at build time.
Therefore, this script should always be self-contained and not require any dependencies outside of the Python standard
library.

"""
import json
from pathlib import Path
import shutil
import subprocess
from typing import Iterable, List, Union


KAITAI_COMPILER_NAME: str = "kaitai-struct-compiler"


class KaitaiError(RuntimeError):
    pass


def has_kaitai_compiler() -> bool:
    return shutil.which(KAITAI_COMPILER_NAME) is not None


class CompiledKSY:
    def __init__(self, class_name: str, python_path: Union[str, Path], dependencies: Iterable["CompiledKSY"] = ()):
        self.class_name: str = class_name
        if not isinstance(python_path, Path):
            python_path = Path(python_path)
        self.python_path: Path = python_path
        self.dependencies: List[CompiledKSY] = list(dependencies)

    def __repr__(self):
        return f"{self.__class__.__name__}(class_name={self.class_name!r}, python_path={self.python_path!r}, "\
               f"dependencies={self.dependencies!r})"


def compile(ksy_path: Union[str, Path], output_directory: Union[str, Path]) -> CompiledKSY:
    """Returns the list of compiled KSYs; the original spec being first, followed by its dependencies"""
    if not has_kaitai_compiler():
        raise KaitaiError(f"{KAITAI_COMPILER_NAME} not found! Please make sure it is in your PATH")

    if not isinstance(output_directory, Path):
        output_directory = Path(output_directory)

    output_directory.mkdir(parents=True, exist_ok=True)

    cmd = [
        KAITAI_COMPILER_NAME, "--target", "python", "--outdir", str(output_directory), str(ksy_path),
        "--debug", "--ksc-json-output", "-I", Path.cwd(), "--python-package", "polyfile.kaitai.parsers"
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if err:
        raise KaitaiError(err.decode("utf-8"))
    elif proc.returncode != 0:
        raise KaitaiError(f"`{' '.join(cmd)}` returned with non-zero exit code {proc.returncode}")

    result = json.loads(out)

    if "errors" in result[ksy_path] and result[ksy_path]["errors"]:
        raise KaitaiError(f"Error compiling {ksy_path}: {result[ksy_path]['errors'][0]['message']}")

    first_spec_name = result[ksy_path]["firstSpecName"]
    first_spec = result[ksy_path]["output"]["python"][first_spec_name]
    return CompiledKSY(
        class_name=first_spec["topLevelName"],
        python_path=output_directory / first_spec["files"][0]["fileName"],
        dependencies=(
            CompiledKSY(
                class_name=compiled["topLevelName"],
                python_path=output_directory / compiled["files"][0]["fileName"]
            )
            for spec_name, compiled in result[ksy_path]["output"]["python"].items()
            if spec_name != first_spec_name
        )
    )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="A Kaitai Struct to Python compiler")
    parser.add_argument("KSY_PATH", type=str, help="path to the Kaitai Struct definition file")
    parser.add_argument("OUTPUT_DIRECTORY", type=str, help="path to which to save the resulting Python")

    args = parser.parse_args(sys.argv[1:])

    try:
        compiled = compile(args.KSY_PATH, args.OUTPUT_DIRECTORY)
        print(f"{compiled.class_name}\t{compiled.python_path}")
        for dep in compiled.dependencies:
            print(f"{dep.class_name}\t{dep.python_path}")
    except KaitaiError as e:
        sys.stderr.write(f"{e!s}\n\n")
        sys.exit(1)
