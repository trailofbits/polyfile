"""Container resource controls must apply before backend decoding."""

import tarfile
from io import BytesIO
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_LZMA, ZipFile

import pytest

from polyfile import AnalysisLimits
from polyfile.magic import MagicMatcher
from polyfile.polyfile import Matcher

PAYLOAD = b'{"bounded": true}'


def zip_bytes(payload: bytes = PAYLOAD, *, method: int = ZIP_DEFLATED) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=method) as archive:
        archive.writestr("document.json", payload)
    return stream.getvalue()


def test_one_zip_entry_does_not_charge_its_structural_fields() -> None:
    nodes = list(Matcher(limits=AnalysisLimits(max_members=1)).match(zip_bytes()))
    assert any(node.name == "application/json" for node in nodes)
    assert nodes[0].analysis_context.members == 1


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_member_bytes=0),
        AnalysisLimits(max_total_bytes=0),
        AnalysisLimits(max_members=0),
    ],
)
def test_zero_limits_do_not_retain_expanded_zip_content(limits: AnalysisLimits) -> None:
    nodes = list(Matcher(limits=limits).match(zip_bytes(b"A" * 1_048_576)))
    assert not any(node.decoded is not None for node in nodes)
    assert any(node.analysis_status == "limited" for node in nodes)


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_depth=0),
        AnalysisLimits(max_members=0),
        AnalysisLimits(max_codec_memory=1),
    ],
)
def test_admission_limits_precede_zip_backend_open(
    monkeypatch, limits: AnalysisLimits
) -> None:
    data = zip_bytes()

    def unexpected_open(*args, **kwargs):
        raise AssertionError("ZIP payload decoder opened despite its admission limit")

    monkeypatch.setattr(ZipFile, "open", unexpected_open)
    nodes = list(Matcher(limits=limits).match(data))
    assert any(node.analysis_status == "limited" for node in nodes)
    assert not any(node.decoded is not None for node in nodes)


@pytest.mark.parametrize("method", [ZIP_BZIP2, ZIP_LZMA])
def test_unbounded_zip_backend_reports_requested_limit_as_unsupported(
    method: int,
    monkeypatch,
) -> None:
    data = zip_bytes(method=method)

    def unexpected_open(*args, **kwargs):
        raise AssertionError(
            "Unbounded ZIP backend opened despite a configured byte limit"
        )

    monkeypatch.setattr(ZipFile, "open", unexpected_open)
    nodes = list(Matcher(limits=AnalysisLimits(max_member_bytes=1024)).match(data))
    encoded = next(
        node
        for node in nodes
        if node.name == "compressed_data"
        and node.parent is not None
        and node.parent.name == "LocalFileHeader"
    )
    assert encoded.analysis_status == "unsupported"
    assert not any(child.name == "decoded_content" for child in encoded)


def gpkg_archive(payload: bytes, *, nested: bool) -> bytes:
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        marker = tarfile.TarInfo("package/gpkg-1")
        archive.addfile(marker, BytesIO())
        member = tarfile.TarInfo("nested.tar" if nested else "document.json")
        member.size = len(payload)
        archive.addfile(member, BytesIO(payload))
    return output.getvalue()


def test_nested_gpkg_is_traversed_once_per_archive() -> None:
    payload = PAYLOAD
    for depth in range(4):
        payload = gpkg_archive(payload, nested=depth > 0)
    nodes = list(Matcher().match(payload))
    assert sum(node.name == "TarMember" for node in nodes) == 8
    assert sum(node.name == "application/json" for node in nodes) == 1
    assert nodes[0].name == "application/vnd.gentoo.gpkg"


def test_filtered_generic_tar_still_parses_gpkg() -> None:
    matcher = MagicMatcher.DEFAULT_INSTANCE.only_match(
        mimetypes=["application/x-ustar"]
    )
    nodes = list(Matcher(matcher=matcher).match(gpkg_archive(PAYLOAD, nested=False)))
    assert nodes[0].name == "application/x-ustar"
    assert sum(node.name == "TarMember" for node in nodes) == 2


def test_nested_stored_zip_retains_labels_without_duplicate_structure() -> None:
    from zipfile import ZIP_STORED

    data = PAYLOAD
    for _ in range(6):
        data = zip_bytes(data, method=ZIP_STORED)
    nodes = list(Matcher().match(data))
    assert sum(node.name == "LocalFileHeader" for node in nodes) == 6
    assert sum(node.name == "application/json" for node in nodes) <= 2


def test_nested_zip_bzip_preserves_raw_type_without_duplicate_expansion(
    monkeypatch,
) -> None:
    import bz2

    from polyfile.compression import match_decoded
    from polyfile.polyfile import PARSERS, ParserFunctionWrapper

    def parse_bzip(stream, parent):
        yield from match_decoded(parent, bz2.decompress(stream.read()))

    monkeypatch.setitem(
        PARSERS,
        "application/x-bzip2",
        {ParserFunctionWrapper(parse_bzip)},
    )
    data = PAYLOAD
    for _ in range(4):
        data = zip_bytes(data, method=ZIP_BZIP2)
    nodes = list(Matcher().match(data))
    assert any(node.name == "application/x-bzip2" for node in nodes)
    assert sum(node.name == "LocalFileHeader" for node in nodes) == 4
    assert sum(node.name == "application/json" for node in nodes) == 1
