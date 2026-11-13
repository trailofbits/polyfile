"""Nested BrainFu loops retain their immediate parent's source coordinates."""

import pytest

from polyfile.fileutils import FileStream
from polyfile.languagematcher import parse_bf
from polyfile.polyfile import Match, Matcher


@pytest.mark.parametrize(
    "program", [b"+[[.>+<-]-].", b"+[[[.>+<-]-]-].", b"+[.>+<-][[.>+<-]-]."]
)
@pytest.mark.parametrize("source_origin", [0, 117])
@pytest.mark.parametrize("source", ["file", "decoded:brainfu"])
def test_nested_loop_offsets_follow_the_immediate_parent(
    program: bytes, source_origin: int, source: str
) -> None:
    parent = Match(
        "application/x-brainfuck",
        program,
        relative_offset=source_origin,
        length=len(program),
        matcher=Matcher(parse=False),
        source=source,
    )
    with FileStream(bytes(37) + program + b"outside", start=13) as outer:
        with FileStream(outer, start=24, length=len(program)) as stream:
            assert stream.offset() == 37
            nodes = list(parse_bf(stream, parent))

    loops = [node for node in nodes if node.name == "Loop"]
    assert [loop.offset for loop in loops] == [
        source_origin + index for index, byte in enumerate(program) if byte == ord("[")
    ]
    commands = [node for node in nodes if node.name != "Loop"]
    assert [(node.offset, node.match) for node in commands] == [
        (source_origin + index, bytes((byte,))) for index, byte in enumerate(program)
    ]
    assert all(node.relative_offset >= 0 and node.source == source for node in nodes)
    assert all(
        node.relative_offset == 0 for node in commands if node.name == "LoopStart"
    )
    assert parent.offset == source_origin
    assert parent.length == len(program)
