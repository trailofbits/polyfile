from collections.abc import Iterator
from unittest.mock import patch

from polyfile.debugger import Debugger, InstrumentedParser
from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Matcher, Parser, Submatch


def test_aborting_parser_debugging_stops_without_yielding_none() -> None:
    class HeaderParser(Parser):
        def parse(self, stream: FileStream, match: Match) -> Iterator[Match]:
            yield Submatch("header", stream.read(1), length=1, parent=match)

    debugger = Debugger(break_on_parsing=False)
    parser = HeaderParser()
    instrumented = InstrumentedParser(parser, debugger)
    parent = Match("root", b"abc", length=3, matcher=Matcher())

    try:
        with (
            FileStream(b"abc") as stream,
            patch("builtins.input", return_value="y"),
            patch("sys.gettrace", return_value=None),
            patch("polyfile.debugger.Pdb") as pdb,
        ):
            pdb.return_value.runcall.return_value = None

            matches = list(parser.parse(stream, parent))

            assert matches == []
            pdb.return_value.runcall.assert_called_once()
            assert debugger._pdb is None
    finally:
        instrumented.uninstrument()
