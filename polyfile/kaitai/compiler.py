#!/usr/bin/env python3

"""
This module automates compilation of Kaitai Struct definitions into Python code.

This script is called from PolyFile's setup.py to compile the entire Kaitai Struct format library at build time.
Therefore, this script should always be self-contained and not require any dependencies other than the Python standard
library.

"""
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Iterable, List, Optional, Union
from urllib.request import urlopen
from zipfile import ZipFile


if os.name == "nt":
    KAITAI_COMPILER_NAME: str = "kaitai-struct-compiler.bat"
else:
    KAITAI_COMPILER_NAME = "kaitai-struct-compiler"


COMPILER_DIR = Path(__file__).absolute().parent / "kaitai-struct-compiler-0.9"
COMPILER_BIN_DIR = COMPILER_DIR / "bin"
COMPILER_BIN = COMPILER_BIN_DIR / KAITAI_COMPILER_NAME


class KaitaiError(RuntimeError):
    pass


class CompilationError(KaitaiError):
    def __init__(self, ksy_file: str, message: str):
        super().__init__(message)
        self.ksy_file: str = ksy_file

    def __str__(self):
        return f"{self.ksy_file}: {super().__str__()}"


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


def install_compiler():
    resp = urlopen("https://github.com/kaitai-io/kaitai_struct_compiler/releases/download/0.9/"
                   "kaitai-struct-compiler-0.9.zip")
    zipfile = ZipFile(BytesIO(resp.read()))
    COMPILER_DIR.mkdir(exist_ok=True)
    zipfile.extractall(COMPILER_DIR.parent)
    if COMPILER_BIN.exists():
        COMPILER_BIN.chmod(COMPILER_BIN.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        sys.stderr.write(f"Installed the Kaitai Struct Compiler to {COMPILER_BIN}\n")


def compiler_path(auto_install: bool = True) -> Optional[Path]:
    if COMPILER_BIN.exists():
        return COMPILER_BIN
    global_path = shutil.which(KAITAI_COMPILER_NAME)
    if global_path is not None:
        return Path(global_path)
    if not auto_install:
        return None
    install_compiler()
    return compiler_path(auto_install=False)


def compile(ksy_path: Union[str, Path], output_directory: Union[str, Path], auto_install: bool = True) -> CompiledKSY:
    """Returns the list of compiled KSYs; the original spec being first, followed by its dependencies"""
    compiler = compiler_path(auto_install=auto_install)
    if compiler is None:
        raise KaitaiError(f"{KAITAI_COMPILER_NAME} not found! Please make sure it is in your PATH. "
                          f"See https://kaitai.io/#download")

    # sys.stderr.write(f"Using Kaitai Struct Compiler: {compiler!s}\n")

    if not isinstance(output_directory, Path):
        output_directory = Path(output_directory)

    output_directory.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(compiler), "--target", "python", "--outdir", str(output_directory), str(ksy_path),
        "--debug", "--ksc-json-output", "-I", str(Path.cwd()), "--python-package", "polyfile.kaitai.parsers"
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
    if "errors" in first_spec:
        for error in first_spec["errors"]:
            raise CompilationError(ksy_file=error["file"], message=error["message"])
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

    if len(sys.argv) == 2 and sys.argv[1] == "--install":
        if compiler_path() is None:
            sys.exit(1)
        else:
            sys.exit(0)

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
