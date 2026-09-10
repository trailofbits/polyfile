"""PEP 517 build backend for PolyFile.

PolyFile's Kaitai Struct parsers are generated at build time, so a build has to run
``compile_kaitai_parsers.rebuild()`` before setuptools collects the files that go into a
distribution. This module wraps :mod:`setuptools.build_meta` to do that, and nothing else.

Only the three hooks that produce a distribution regenerate the parsers. The metadata hooks and
the ``get_requires_for_build_*`` hooks are re-exported unchanged, so tools that want nothing but
PolyFile's metadata never trigger a compile, which would need a Java runtime and a network
download.

Like ``polyfile/kaitai/compiler.py``, this module must stay standard-library-only apart from
setuptools: builds run in an isolated environment containing nothing but the
``[build-system] requires`` of ``pyproject.toml``. ``compile_kaitai_parsers`` is imported lazily
because importing it runs ``git submodule init`` and ``git submodule update`` when the Kaitai
format library is missing.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from setuptools import build_meta as _setuptools

get_requires_for_build_wheel = _setuptools.get_requires_for_build_wheel
get_requires_for_build_sdist = _setuptools.get_requires_for_build_sdist
get_requires_for_build_editable = _setuptools.get_requires_for_build_editable
prepare_metadata_for_build_wheel = _setuptools.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _setuptools.prepare_metadata_for_build_editable

PROJECT_ROOT: Path = Path(__file__).absolute().parent

# Spelled out rather than imported so that the short circuit below does not have to import
# compile_kaitai_parsers. Keep in sync with compile_kaitai_parsers.MANIFEST_PATH.
GENERATED_MANIFEST: Path = PROJECT_ROOT / "polyfile" / "kaitai" / "parsers" / "manifest.json"

# A source distribution always carries a PKG-INFO at its root; a checkout never does.
SDIST_MARKER: Path = PROJECT_ROOT / "PKG-INFO"


def _rebuild_parsers() -> None:
    """Generates the Kaitai Struct parsers that this build is about to package."""
    if SDIST_MARKER.is_file() and GENERATED_MANIFEST.is_file():
        # This is an unpacked source distribution, which already carries the parsers that were
        # generated when it was built. Recompiling would need a Java runtime and a network
        # download, and compile_kaitai_parsers.is_stale() cannot decide whether that is
        # necessary here: with no repository to consult it falls back to file modification
        # times, and the times in a tarball depend on the order in which git wrote the working
        # tree and its submodules.
        print("build_backend: reusing the parsers already generated in this source distribution")
        return

    import compile_kaitai_parsers

    compile_kaitai_parsers.rebuild()


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Dict[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    _rebuild_parsers()
    return _setuptools.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(
    wheel_directory: str,
    config_settings: Optional[Dict[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    _rebuild_parsers()
    return _setuptools.build_editable(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory: str, config_settings: Optional[Dict[str, Any]] = None) -> str:
    _rebuild_parsers()
    return _setuptools.build_sdist(sdist_directory, config_settings)
