from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import compile_kaitai_parsers as compiler


def test_compiler_output_retains_class_path_pairs() -> None:
    output = b"Root\troot.py\tadditional information\n\nDependency\tdependency.py\n"

    with patch("compile_kaitai_parsers.subprocess.check_output", return_value=output):
        compiled = compiler.compile_ksy(Path("format.ksy"))

    assert compiled == [("Root", "root.py"), ("Dependency", "dependency.py")]


def test_manifest_entry_retains_relative_paths_and_dependencies() -> None:
    compiled = [
        ("Root", str(compiler.KAITAI_PARSERS_DIR / "root.py")),
        ("Dependency", str(compiler.KAITAI_PARSERS_DIR / "dependency.py")),
    ]

    assert compiler.manifest_entry(compiled) == {
        "class_name": "Root",
        "python_path": "root.py",
        "dependencies": [{"class_name": "Dependency", "python_path": "dependency.py"}],
    }


def test_progress_fallback_requires_no_optional_dependency(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "compile_kaitai_parsers.import_module", side_effect=ModuleNotFoundError("tqdm")
    ):
        with compiler.progress_bar(1) as progress:
            progress.update(1)
            progress.write("compiled format")

    assert capsys.readouterr().err == "compiled format\n"


def test_progress_bar_uses_the_installed_optional_factory() -> None:
    progress = MagicMock()
    factory = MagicMock(return_value=progress)
    module = SimpleNamespace(tqdm=factory)

    with patch("compile_kaitai_parsers.import_module", return_value=module):
        assert compiler.progress_bar(3) is progress

    factory.assert_called_once_with(
        leave=False, desc="Compiling the Kaitai Struct Format Library", total=3
    )
