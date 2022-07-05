from io import BytesIO
from pathlib import Path
from typing import IO, Optional, Type, TypeVar, Union

from .kaitai.parser import KaitaiParser
from .kaitai.parsers.asn1_der import Asn1Der

DER_PARSER = KaitaiParser.load("serialization/asn1/asn1_der.ksy")

C = TypeVar("C", bound="DERQuery")


class DERQuery:
    def __init__(self, der: Asn1Der, parent: Optional["DERQuery"] = None):
        self.der: Asn1Der = der  # type: ignore
        self.parent = parent

    @property
    def is_seq(self) -> bool:
        return self.der.type_tag.value == 0x10 or self.der.type_tag.value == 0x30

    @classmethod
    def parse(cls: Type[C], data: Union[bytes, str, Path, BytesIO]) -> Optional[C]:
        try:
            ast = DER_PARSER.parse(data).ast
            if isinstance(ast.obj, DER_PARSER.struct_type):
                return DERQuery(ast.obj)
        except EOFError:
            pass
        return None
