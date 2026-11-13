"""The generated parser boundary rejects unavailable loaders and unrelated classes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from polyfile.kaitai.compiler import CompiledKSY
from polyfile.kaitai.parser import import_spec


def test_import_reports_an_unavailable_module_loader(tmp_path: Path) -> None:
    compiled = CompiledKSY("Example", tmp_path / "example.py")
    with patch("importlib.util.spec_from_file_location", return_value=None):
        with pytest.raises(ImportError, match="Could not load a Python module"):
            import_spec(compiled)


def test_import_rejects_a_class_without_the_kaitai_interface(tmp_path: Path) -> None:
    path = tmp_path / "unrelated.py"
    path.write_text("class Unrelated:\n    pass\n", encoding="utf-8")
    compiled = CompiledKSY("Unrelated", path)
    with pytest.raises(ImportError, match="Could not find parser class 'Unrelated'"):
        import_spec(compiled)
