"""Nested physical and decoded inputs keep FileStream and match coordinates separate."""

import gzip
import struct
import tarfile
from io import BytesIO
from pathlib import Path

import pytest

from polyfile.fileutils import FileStream
from polyfile.gzipmatcher import parse_gzip
from polyfile.polyfile import Match, Matcher, Parser
from polyfile.simh import MIME_TYPE, parse_simh
from polyfile.tarmatcher import parse_tar

JSON = b'{"nested": true}'


def container_bytes(kind: str) -> tuple[str, bytes, Parser, int]:
    """Return a container and the JSON payload's offset within its analysis source."""
    if kind == "gzip":
        return "application/gzip", gzip.compress(JSON, mtime=0), parse_gzip, 0
    if kind == "simh":
        word = struct.pack("<I", len(JSON))
        data = word + JSON + bytes(len(JSON) % 2) + word
        return MIME_TYPE, data, parse_simh, 4
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo("document.json")
        member.size = len(JSON)
        archive.addfile(member, BytesIO(JSON))
    return "application/x-tar", buffer.getvalue(), parse_tar, 512


@pytest.mark.parametrize("kind", ("gzip", "tar", "simh"))
@pytest.mark.parametrize("origin", (0, 5, 17))
@pytest.mark.parametrize("backing", ("memory", "file"))
@pytest.mark.parametrize("source_name", ("file", "decoded:input"))
def test_nested_container_offsets_follow_the_current_source(
    kind: str, origin: int, backing: str, source_name: str, tmp_path: Path
) -> None:
    mimetype, data, parser, payload_offset = container_bytes(kind)
    source: bytes | Path = b"prefix" + bytes(origin) + data + b"outside the view"
    if backing == "file":
        path = tmp_path / "container.bin"
        path.write_bytes(source)
        source = path
    with FileStream(source, start=6) as parent_view:
        with FileStream(parent_view, start=origin, length=len(data)) as view:
            parent = Match(
                mimetype,
                None,
                relative_offset=origin + 6,
                length=len(data),
                matcher=Matcher(),
                source=source_name,
            )
            nodes = list(parser(view, parent))
            assert view.offset() == origin + 6
    matches = [node for node in nodes if node.name == "application/json"]
    assert len(matches) == 1
    if kind == "gzip":
        assert matches[0].source != source_name
        assert matches[0].offset == 0
        encoded = next(node for node in nodes if node.name == "gzip_member")
        assert encoded.source == source_name
        assert encoded.offset == origin + 6
    else:
        assert matches[0].source == source_name
        assert matches[0].offset == origin + 6 + payload_offset
