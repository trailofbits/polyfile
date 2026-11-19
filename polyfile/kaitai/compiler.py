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
from typing import cast
from collections.abc import Iterable
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
_KEYWORD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
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


def _escape_seq_fields(match: re.Match[str]) -> str:
    fields = _QUOTED_KEYWORD.sub(_QUOTED_REPLACEMENT, match.group("fields"))
    return cast(str, match.group("head")) + fields + "]"


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
    def __init__(self, class_name: str, python_path: str | Path, dependencies: Iterable["CompiledKSY"] = ()):
        self.class_name: str = class_name
        if not isinstance(python_path, Path):
            python_path = Path(python_path)
        self.python_path: Path = python_path
        self.dependencies: list[CompiledKSY] = list(dependencies)

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


def compiler_path(auto_install: bool = True) -> Path | None:
    if COMPILER_BIN.exists():
        return COMPILER_BIN
    global_path = shutil.which(KAITAI_COMPILER_NAME)
    if global_path is not None:
        return Path(global_path)
    if not auto_install:
        return None
    install_compiler()
    return compiler_path(auto_install=False)


def _run_compiler(compiler: Path, ksy_path: str, output_directory: Path) -> bytes:
    output_directory.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(compiler), "--target", "python", "--outdir", str(output_directory), ksy_path,
        "--debug", "--ksc-json-output", "-I", str(Path.cwd()),
        "--python-package", "polyfile.kaitai.parsers",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.stderr:
        raise KaitaiError(proc.stderr.decode("utf-8"))
    if proc.returncode != 0:
        raise KaitaiError(f"`{' '.join(cmd)}` returned with non-zero exit code {proc.returncode}")
    return proc.stdout


def compile(
    ksy_path: str | Path, output_directory: str | Path, auto_install: bool = True,
    *, compiler: Path | None = None,
) -> CompiledKSY:
    """Compile one specification and its imported specifications to Python.

    Args:
        ksy_path: Path to the input specification.
        output_directory: Directory for the generated modules.
        auto_install: Download the default compiler if no executable is available.
        compiler: Selected executable, when the caller has already resolved it.

    Returns:
        The generated module and its dependencies.
    """
    compiler = compiler or compiler_path(auto_install=auto_install)
    if compiler is None:
        raise KaitaiError(f"Install {KAITAI_COMPILER_NAME} or add it to PATH")
    output_directory = Path(output_directory)
    result = json.loads(_run_compiler(compiler, str(ksy_path), output_directory))[str(ksy_path)]
    if errors := result.get("errors"):
        raise KaitaiError(f"Error compiling {ksy_path}: {errors[0]['message']}")
    first_spec_name = result["firstSpecName"]
    modules = result["output"]["python"]
    first_spec = modules[first_spec_name]
    if errors := first_spec.get("errors"):
        raise CompilationError(ksy_file=errors[0]["file"], message=errors[0]["message"])

    main_python_path = output_directory / first_spec["files"][0]["fileName"]
    dependencies = [
        CompiledKSY(
            class_name=compiled["topLevelName"],
            python_path=output_directory / compiled["files"][0]["fileName"]
        )
        for spec_name, compiled in modules.items()
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

    if sys.argv[1:] in (["--install"], ["--locate"]):
        install = sys.argv[1] == "--install"
        executable = compiler_path(auto_install=install)
        if executable is not None:
            print(executable.resolve())
        sys.exit(1 if install and executable is None else 0)

    parser = argparse.ArgumentParser(description="A Kaitai Struct to Python compiler")
    parser.add_argument("--compiler", type=Path, help="use this Kaitai compiler executable")
    parser.add_argument("KSY_PATH", type=str, help="path to the Kaitai Struct definition file")
    parser.add_argument("OUTPUT_DIRECTORY", type=str, help="path to which to save the resulting Python")

    args = parser.parse_args(sys.argv[1:])

    try:
        compiled = compile(args.KSY_PATH, args.OUTPUT_DIRECTORY, compiler=args.compiler)
        print(f"{compiled.class_name}\t{compiled.python_path}")
        for dep in compiled.dependencies:
            print(f"{dep.class_name}\t{dep.python_path}")
    except KaitaiError as e:
        sys.stderr.write(f"{e!s}\n\n")
        sys.exit(1)
