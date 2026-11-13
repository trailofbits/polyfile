from collections.abc import Mapping
from pathlib import Path
from typing import NotRequired, TypeAlias, TypedDict


SourceBytes: TypeAlias = Mapping[str | None, list[int]]
SourceBytesInput: TypeAlias = (
    Mapping[str, list[int]] | Mapping[None, list[int]] | SourceBytes
)


class PolyfileElement(TypedDict, total=False):
    type: str
    name: str
    offset: int
    relative_offset: int
    size: int
    source: str
    value: str
    img_data: str
    decoded: str
    extension: str
    analysis_status: str
    analysis_message: str | None
    subEls: list["PolyfileElement"]
    functions: list[str]


class PolyfileDocument(TypedDict):
    struc: list[PolyfileElement]
    MD5: NotRequired[str]
    SHA1: NotRequired[str]
    SHA256: NotRequired[str]
    b64contents: NotRequired[str]
    fileName: NotRequired[str | Path]
    length: NotRequired[int]
    versions: NotRequired[dict[str, str]]
    best_function_matches: NotRequired[dict[str, list[str]]]


class FunctionData(TypedDict, total=False):
    cmp_bytes: SourceBytesInput
    input_bytes: SourceBytesInput
    called_from: list[str]


class VersionedTrace(TypedDict):
    version: str
    tainted_functions: dict[str, FunctionData]
    runtime_cfg: dict[str, list[str]]
