"""Debugger parser locations distinguish view, backing, and analysis-source positions."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest

from polyfile.debugger import Debugger, InstrumentedParser
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Parser
from tests.test_parser_coordinates import parser_parent, parser_stream


class EmptyParser(Parser):
    def parse(self, stream: FileStream, match: Match) -> Iterator[Match]:
        return iter(())


@pytest.mark.parametrize("backing_base", [0, 37])
@pytest.mark.parametrize("source_base", [0, 117])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("decoded", [False, True])
def test_parser_locations_label_each_coordinate_system(
    backing_base: int,
    source_base: int,
    nested: bool,
    decoded: bool,
) -> None:
    data = b"contents"
    stream = parser_stream(data, backing_base, nested)
    stream.seek(2)
    parent = parser_parent(data, source_base, decoded)
    debugger = Debugger()
    instrumented = InstrumentedParser(EmptyParser(), debugger)
    try:
        with (
            patch.object(debugger, "prompt", return_value=False),
            patch.object(debugger, "print_match"),
            patch.object(debugger, "write") as write,
        ):
            assert list(debugger.debug_parse(instrumented, stream, parent)) == []
        output = "".join(str(call.args[0]) for call in write.call_args_list if call.args)
        assert (
            f"bytes:{backing_base + 2} (stream byte 2; "
            f"source {parent.source} byte {source_base + 2})"
        ) in output
    finally:
        instrumented.uninstrument()
