from io import BytesIO
import json
from typing import BinaryIO, Dict, List, Optional, Type, Union

from .fileutils import FileStream
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType
from .structs import ByteField, Endianness, Struct, StructError, StructReadError, T, UInt64
from .structmatcher import PolyFileStruct


JSONValue = Union[str, int, "StrDict", List["JSONValue"]]
StrDict = Dict[str, JSONValue]


class JSONByteField(ByteField):
    json_object: StrDict

    @classmethod
    def read(cls: Type[T], struct: Struct, field_name: str, stream: BinaryIO, endianness: Endianness) -> T:
        raw_bytes = super().read(struct=struct, field_name=field_name, stream=stream, endianness=endianness)
        try:
            json_string = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise StructReadError(f"JSON byte string {raw_bytes!r} could not be decoded to UTF-8")
        try:
            raw_bytes.json_object = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise StructReadError(f"Error decoding JSON: {e!s}")
        return raw_bytes


class SafeTensorsHeader(PolyFileStruct):
    endianness = Endianness.LITTLE

    header_length: UInt64
    header: JSONByteField["header_length"]


class SafeTensorsTest(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-safetensors",
            extensions=("safetensors",),
            message="Safetensors Model"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        # speed optimization: make sure the JSON starts with '{' before trying to decode/parse it!
        for b in data[8:]:
            if b == ord("{"):
                # it looks like the start of JSON
                break
            elif b not in (ord(" "), ord("\t"), ord("\n"), ord("\r")):
                # this is not whitespace
                return FailedTest(self, offset=absolute_offset, message="JSON does not start with '{'")
        else:
            # we never found the starting "{"
            return FailedTest(self, offset=absolute_offset, message="JSON does not start with '{'")
        bstream = BytesIO(data)
        setattr(bstream, "name", "SafetensorsBytes")
        stream = FileStream(bstream)
        try:
            _ = SafeTensorsHeader.read(stream)  # type: ignore
            return MatchedTest(self, value=data, offset=0, length=len(data))
        except StructError as e:
            return FailedTest(self, offset=absolute_offset, message=str(e))


MagicMatcher.DEFAULT_INSTANCE.add(SafeTensorsTest())
