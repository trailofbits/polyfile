"""Check ZIP member diagnostics through the matcher and both report formats."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.html import generate
from polyfile.polyfile import Analyzer, Matcher
from polyfile.zipmatcher import CENTRAL_DIRECTORY_SIGNATURE, LOCAL_FILE_HEADER_SIGNATURE


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    stream = BytesIO()
    with ZipFile(stream, "w") as writer:
        writer.writestr("opaque.json", b'{"raw": true}')
        writer.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\n\n")
    data = bytearray(b"prefix" + stream.getvalue())
    # Both test method IDs are unassigned. The payload is ordinary JSON.
    local = data.index(LOCAL_FILE_HEADER_SIGNATURE) + 8
    directory = data.index(CENTRAL_DIRECTORY_SIGNATURE) + 10
    data[local:local + 2] = (65000).to_bytes(2, "little")
    data[directory:directory + 2] = (65001).to_bytes(2, "little")
    path = tmp_path / "members.jar"
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("limits", [AnalysisLimits(), AnalysisLimits(max_members=2)])
def test_conflict_skips_only_the_affected_member(archive: Path, limits: AnalysisLimits) -> None:
    with patch.object(ZipFile, "open", autospec=True, side_effect=ZipFile.open) as opened:
        nodes = list(Matcher(limits=limits).match(archive))
    assert [call.args[1].filename for call in opened.call_args_list] == ["META-INF/MANIFEST.MF"]
    assert {"application/zip", "application/java-archive"} <= {m.name for m in nodes}
    assert nodes[0].analysis_context.members == 2
    conflict, = (m for m in nodes if m.analysis_status == "invalid")
    assert conflict.name == "compressed_data"
    assert conflict.children == ()
    data = archive.read_bytes()
    assert data[conflict.offset:conflict.offset + conflict.length] == b'{"raw": true}'
    decoded = [m.decoded for m in nodes if m.name == "decoded_content"]
    assert decoded == [b"Manifest-Version: 1.0\n\n"]


@pytest.mark.parametrize(
    "error",
    [
        BadZipFile("unavailable"), NotImplementedError("version"),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid name"),
    ],
)
def test_conflict_evidence_survives_reader_refusal(archive: Path, error: Exception) -> None:
    with patch("polyfile.zipmatcher.PythonZip", side_effect=error):
        report = Analyzer(archive).sbud()
    records = [record for root in report["struc"] for record in root["subEls"]]
    assert sum(record["name"] == "CentralDirectory" for record in records) == 2
    fields = [field for record in records for field in record["subEls"]]
    conflict, = (f for f in fields if f.get("analysis_status") == "invalid")
    assert conflict["subEls"] == []
    message = conflict["analysis_message"]
    data = archive.read_bytes()
    labels = (("LocalFileHeader", "local header"), ("CentralDirectory", "central directory"))
    for record_name, label in labels:
        record = next(r for r in records if r["name"] == record_name)
        method = next(f for f in record["subEls"] if f["name"] == "compression_method")
        start = method["offset"]
        end = start + method["size"]
        value = int.from_bytes(data[start:end], "little")
        assert f"{label} {value} at file[{start}:{end}]" in message
    assert message in generate(str(archive), report)


def test_nested_conflict_names_the_decoded_source(archive: Path) -> None:
    outer = BytesIO()
    with ZipFile(outer, "w", ZIP_DEFLATED) as writer:
        writer.writestr("nested.jar", archive.read_bytes())
    nodes = list(Matcher().match(outer.getvalue()))
    conflict, = (m for m in nodes if m.analysis_status == "invalid")
    assert conflict.source != "file"
    assert conflict.analysis_message is not None
    assert conflict.analysis_message.count(f"at {conflict.source}[") == 2


def test_entry_limit_preserves_the_admitted_members_directory_record(archive: Path) -> None:
    nodes = list(Matcher(limits=AnalysisLimits(max_members=1)).match(archive))
    assert sum(m.name == "LocalFileHeader" for m in nodes) == 1
    directory, = (m for m in nodes if m.name == "CentralDirectory")
    assert any(m.name == "compression_method" and m.match == 65001 for m in directory)
    assert any(m.name == "compressed_data" and m.analysis_status == "invalid" for m in nodes)
    assert any(m.name == "EndOfCentralDirectory" for m in nodes)
