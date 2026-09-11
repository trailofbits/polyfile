#!/usr/bin/env python3

"""
This module automates compilation of Kaitai Struct definitions into Python code.

This script is called from PolyFile's PEP 517 build backend, by way of compile_kaitai_parsers.py, to compile the
entire Kaitai Struct format library at build time. Builds run in an isolated environment that contains nothing but the
`[build-system] requires` of pyproject.toml, so this script must always be self-contained and must not require any
dependencies other than the Python standard library.

"""
import ast
from io import BytesIO, StringIO
import json
import keyword
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tokenize
from typing import Iterable, List, Optional, Tuple, Union
from urllib.request import urlopen
import warnings
from zipfile import ZipFile


if os.name == "nt":
    KAITAI_COMPILER_NAME: str = "kaitai-struct-compiler.bat"
else:
    KAITAI_COMPILER_NAME = "kaitai-struct-compiler"


KAITAI_COMPILER_VERSION = "0.11"
COMPILER_DIR = Path(__file__).absolute().parent / f"kaitai-struct-compiler-{KAITAI_COMPILER_VERSION}"
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


_HARD_KEYWORDS: str = "|".join(keyword.kwlist)

# kaitai-struct-compiler 0.11 copies a specification's identifiers into Python verbatim, so these
# are the three shapes in which a field or enum member named after a hard keyword reaches the
# generated source. Every one of them is a syntax error, which is what makes matching them safe.
_KEYWORD_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    # An enum member: `not = 6`
    (re.compile(rf"^(?P<indent>[ \t]+)(?P<kw>{_HARD_KEYWORDS})(?P<tail> = )", re.MULTILINE),
     r"\g<indent>\g<kw>_\g<tail>"),
    # A sequence field being assigned: `self.class = self._io.read_u1()`
    (re.compile(rf"(?<=\bself\.)(?P<kw>{_HARD_KEYWORDS})\b"), r"\g<kw>_"),
    # The debugger offsets recorded for that field: `self._debug['class']['start']`
    (re.compile(rf"(?<=_debug\[')(?P<kw>{_HARD_KEYWORDS})(?='\])"), r"\g<kw>_"),
)

# The names the debugger walks, which must stay in step with the attributes they name:
# `SEQ_FIELDS = ["class", "public_key_algorithm", "fingerprint"]`
_SEQ_FIELDS = re.compile(r"^(?P<head>[ \t]*SEQ_FIELDS = \[)(?P<fields>[^\]]*)\]", re.MULTILINE)
_QUOTED_KEYWORD = re.compile('"(?P<kw>' + _HARD_KEYWORDS + ')"')
_QUOTED_REPLACEMENT = '"\\g<kw>_"'


def _escape_seq_fields(match: "re.Match") -> str:
    fields = _QUOTED_KEYWORD.sub(_QUOTED_REPLACEMENT, match.group("fields"))
    return match.group("head") + fields + "]"


def _decodes(literal: str) -> bool:
    """Determines whether Python can evaluate a string literal without complaining about it."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        try:
            ast.literal_eval(literal)
        except (SyntaxError, SyntaxWarning, ValueError):
            return False
    return True


def _escape_docstrings(source: str) -> str:
    """Marks every undecodable string literal in the source as raw.

    The compiler copies a specification's ``doc`` key into a triple-quoted docstring without
    escaping it, so documentation that mentions a Windows path or a regular expression yields
    either a ``SyntaxError`` or a ``SyntaxWarning``. Making the literal raw preserves the
    documentation exactly as the specification wrote it.
    """
    starts = [
        token.start
        for token in tokenize.generate_tokens(StringIO(source).readline)
        if token.type == tokenize.STRING and "\\" in token.string
        and token.string.startswith(("\"", "'")) and not _decodes(token.string)
    ]
    if not starts:
        return source
    lines = source.splitlines(keepends=True)
    for row, column in sorted(starts, reverse=True):
        line = lines[row - 1]
        lines[row - 1] = f"{line[:column]}r{line[column:]}"
    return "".join(lines)


def _fix_reserved_keywords(python_path: Path) -> None:
    """Rewrites the parts of a generated parser that are not valid Python.

    kaitai-struct-compiler 0.11 escapes neither Python's reserved words nor the backslashes in the
    documentation it copies from a specification, so a handful of the format library's parsers do
    not even parse. Hard keywords used as identifiers gain a trailing underscore, following PEP 8,
    and undecodable string literals become raw. Soft keywords such as ``type`` and ``match`` are
    legal identifiers and are deliberately left alone: over forty parsers rely on them.

    Args:
        python_path: the generated Python file to rewrite in place.
    """
    source = python_path.read_text(encoding="utf-8")
    fixed = _SEQ_FIELDS.sub(_escape_seq_fields, source)
    for pattern, replacement in _KEYWORD_PATTERNS:
        fixed = pattern.sub(replacement, fixed)
    fixed = _escape_docstrings(fixed)
    if fixed != source:
        python_path.write_text(fixed, encoding="utf-8")


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
    resp = urlopen(f"https://github.com/kaitai-io/kaitai_struct_compiler/releases/download/"
                   f"{KAITAI_COMPILER_VERSION}/kaitai-struct-compiler-{KAITAI_COMPILER_VERSION}.zip")
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

    main_python_path = output_directory / first_spec["files"][0]["fileName"]
    dependencies = [
        CompiledKSY(
            class_name=compiled["topLevelName"],
            python_path=output_directory / compiled["files"][0]["fileName"]
        )
        for spec_name, compiled in result[ksy_path]["output"]["python"].items()
        if spec_name != first_spec_name
    ]

    _fix_reserved_keywords(main_python_path)
    for dep in dependencies:
        _fix_reserved_keywords(dep.python_path)

    return CompiledKSY(
        class_name=first_spec["topLevelName"],
        python_path=main_python_path,
        dependencies=dependencies
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
