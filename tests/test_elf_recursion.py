"""ELF description enrichment within bounded recursive container analysis."""

import gzip
import io
import tarfile
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.magic import TestResult
from polyfile.polyfile import Matcher
from tests.test_elfmetadata import build_elf, description, note


def wrapped_elf(data: bytes, container: str) -> bytes:
    if container == "gzip":
        return gzip.compress(data, mtime=0)
    stream = io.BytesIO()
    if container == "tar":
        with tarfile.open(
            fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT
        ) as archive:
            entry = tarfile.TarInfo("program.elf")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
    else:
        with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
            archive.writestr("program.elf", data)
    return stream.getvalue()


@pytest.mark.parametrize("container", ("gzip", "tar", "zip"))
def test_nested_elf_keeps_description_source_and_shared_limits(container: str) -> None:
    data = build_elf(
        programs=((3, b"/lib/test-loader\0"), (4, note(b"GNU", 3, bytes(range(20)))))
    )
    encoded = wrapped_elf(data, container)
    total_allowance = len(data) + len(encoded)
    limits = AnalysisLimits(
        max_depth=1,
        max_members=1,
        max_member_bytes=len(data),
        max_total_bytes=total_allowance,
    )
    nodes = list(Matcher(limits=limits).match(encoded))
    elf = next(node for node in nodes if node.description is not None)
    assert elf.description == description(data)
    assert elf.to_obj()["value"] == elf.description
    assert isinstance(elf.match, TestResult)
    assert "BuildID[sha1]" in elf.description
    assert "interpreter /lib/test-loader" in elf.description
    assert elf.source == ("file" if container == "tar" else "decoded:0")
    assert elf.offset == (512 if container == "tar" else 0)
    assert elf.analysis_depth == 1
    assert all(node.analysis_context is elf.analysis_context for node in nodes)
    assert elf.analysis_context.members == 1
    assert len(data) <= elf.analysis_context.total_bytes <= total_allowance


@pytest.mark.parametrize("container", ("gzip", "tar", "zip"))
def test_depth_limit_stops_container_before_elf_enrichment(container: str) -> None:
    data = build_elf()
    nodes = list(
        Matcher(limits=AnalysisLimits(max_depth=0)).match(wrapped_elf(data, container))
    )
    assert all(node.description is None for node in nodes)
    assert any(node.analysis_status == "limited" for node in nodes)
