import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type, Union

from .compiler import CompiledKSY

from kaitaistruct import KaitaiStruct

PARSER_DIR: Path = Path(__file__).absolute().parent / "parsers"
MANIFEST_FILE: Path = PARSER_DIR / "manifest.json"

with open(MANIFEST_FILE, "r") as f:
    MANIFEST: Dict[str, Dict[str, Any]] = json.load(f)
COMPILED_INFO_BY_KSY: Dict[str, CompiledKSY] = {
    ksy_path: CompiledKSY(
        class_name=component["class_name"],
        python_path=PARSER_DIR / component["python_path"],
        dependencies=(
            CompiledKSY(class_name=dep["class_name"], python_path=PARSER_DIR / dep["python_path"])
            for dep in component["dependencies"]
        )
    )
    for ksy_path, component in MANIFEST.items()
}
del MANIFEST

_IMPORTED_SPECS: Set[Path] = set()
_PARSERS_BY_KSY: Dict[str, Type[KaitaiStruct]] = {}


def import_spec(compiled: CompiledKSY) -> Optional[Type[KaitaiStruct]]:
    if compiled.python_path in _IMPORTED_SPECS:
        return None
    _IMPORTED_SPECS.add(compiled.python_path)
    module_name = compiled.python_path.name
    assert module_name.lower().endswith(".py")
    module_name = module_name[:-3]
    module_name = f"{__name__}.parsers.{module_name}"
    spec = importlib.util.spec_from_file_location(module_name, compiled.python_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for objname, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and objname == compiled.class_name:
            return obj
    raise ImportError(f"Could not find parser class {compiled.class_name!r} in {compiled.python_path}")


class KaitaiInspector:
    def __init__(self, struct: KaitaiStruct):
        self.struct: KaitaiStruct = struct


class KaitaiParser:
    def __init__(self, struct_type: Type[KaitaiStruct]):
        self.struct_type: Type[KaitaiStruct] = struct_type

    @staticmethod
    def load(ksy_path: str) -> "KaitaiParser":
        """Returns a parser for the given KSY file and input file.

        The KSY file is specified as a relative path to the file within the Kaitai struct format library.
        Examples:

             "executable/dos_mz.ksy"
             "image/jpeg.ksy"
             "network/pcap.ksy"

        """
        if ksy_path not in _PARSERS_BY_KSY:
            if ksy_path not in COMPILED_INFO_BY_KSY:
                raise KeyError(ksy_path)
            info = COMPILED_INFO_BY_KSY[ksy_path]
            _PARSERS_BY_KSY[ksy_path] = import_spec(info)  # type: ignore
        return KaitaiParser(_PARSERS_BY_KSY[ksy_path])

    def parse(self, input_file_path: Union[str, Path]) -> KaitaiInspector:
        if isinstance(input_file_path, Path):
            input_file_path = str(input_file_path)

        struct = self.struct_type.from_file(input_file_path)
        struct._read()
        return KaitaiInspector(struct)
