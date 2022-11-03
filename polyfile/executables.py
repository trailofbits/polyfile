from io import BytesIO
from pathlib import Path
from typing import Iterator, Optional
from zipfile import ZipFile as PythonZip

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CsError

from .fileutils import ExactNamedTempfile, FileStream, Tempfile
from .logger import StatusLogger
from .magic import AbsoluteOffset, FailedTest, MagicMatcher, MagicTest, MatchedTest, TestResult, TestType
from .polyfile import InvalidMatch, register_parser
from .structmatcher import PolyFileStruct
from .structs import ByteField, Constant, Endianness, StructError, UInt16, UInt32

log = StatusLogger("polyfile")


class ArmMatcher(MagicTest):
    def __init__(self):
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/octet-stream",
            extensions=("exe",),
            message="ARM Executable"
        )

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(self, data: bytes, absolute_offset: int, parent_match: Optional[TestResult]) -> TestResult:
        try:
            md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
            # iterate over each instruction and print it
            num_instructions = 0
            for instruction in md.disasm(data, 0x1000):
                log.info("0x%x:\t%s\t%s" % (instruction.address, instruction.mnemonic, instruction.op_str))
                num_instructions += 1
            if num_instructions >= 7:
                return MatchedTest(self, value=data, offset=0, length=len(data))
        except CsError as e:
            log.debug("Capstone Error: %s" % e)
        return FailedTest(self, offset=0, message="ZIP file does not appear to be an ARM executable")


MagicMatcher.DEFAULT_INSTANCE.add(ArmMatcher())
