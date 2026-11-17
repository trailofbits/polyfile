"""PDF decoding applies shared admission and byte allowances before retaining output."""

import base64
import gzip
import re
from typing import BinaryIO, cast
import zlib

import pytest

from polyfile.analysis import AnalysisContext, AnalysisLimits
from polyfile.fileutils import FileStream
from polyfile.pdf import InstrumentedPDFDocument, PDFParser, RawPDFStream, pdf_parser
from polyfile.polyfile import Match, Matcher
from pdf_fixtures import CATALOG, encrypted_pdf, object_stream_pdf, pdf_fixture

PAYLOAD = b'{"bounded":true}'


def _stream(data: bytes, attributes: bytes = b"/Filter /FlateDecode") -> bytes:
    return (
        b"<< " + attributes + f" /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"
    )


def _parse(
    data: bytes,
    limits: AnalysisLimits,
    *,
    source: str = "file",
    origin: int = 0,
) -> tuple[Match, list[Match]]:
    parent = Match(
        "application/pdf",
        None,
        relative_offset=origin,
        length=len(data),
        source=source,
        matcher=Matcher(parse=False, limits=limits),
    )
    with FileStream(b"prefix" + data + b"suffix", start=6, length=len(data)) as stream:
        nodes = list(pdf_parser(stream, parent))
    return parent, nodes


def _decoded(nodes: list[Match]) -> list[bytes]:
    return [node.decoded for node in nodes if node.decoded is not None]


@pytest.mark.parametrize("limits", [AnalysisLimits(max_depth=0), AnalysisLimits(max_members=0)])
def test_optional_admission_precedes_pdf_filter_decoding(
    monkeypatch: pytest.MonkeyPatch,
    limits: AnalysisLimits,
) -> None:
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(b"A" * 65536))])

    def forbidden(*args, **kwargs):
        raise AssertionError("PDF decoder ran after optional payload admission was refused")

    monkeypatch.setattr(zlib, "decompress", forbidden)
    monkeypatch.setattr(zlib, "decompressobj", forbidden)
    _, nodes = _parse(data, limits)
    assert not _decoded(nodes)
    assert len([node for node in nodes if node.name == "PDFObject"]) == 3
    assert any(node.analysis_status == "limited" for node in nodes)


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_member_bytes=0),
        AnalysisLimits(max_total_bytes=0),
        AnalysisLimits(max_member_bytes=1),
        AnalysisLimits(max_total_bytes=1),
    ],
)
def test_pdf_flate_expansion_is_bounded_before_the_full_payload_is_created(
    monkeypatch: pytest.MonkeyPatch,
    limits: AnalysisLimits,
) -> None:
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(b"A" * 65536))])
    decompressor = zlib.decompressobj
    expanded = []

    class ObservedDecoder:
        def __init__(self):
            self.decoder = decompressor()

        def decompress(self, data, max_length):
            value = self.decoder.decompress(data, max_length)
            expanded.append(len(value))
            return value

        def __getattr__(self, name):
            return getattr(self.decoder, name)

    monkeypatch.setattr(zlib, "decompressobj", ObservedDecoder)
    _, nodes = _parse(data, limits)
    assert not _decoded(nodes)
    assert sum(expanded) <= (limits.max_member_bytes or limits.max_total_bytes or 0) + 1
    assert any(node.analysis_status == "limited" for node in nodes)
    assert not any(isinstance(node.match, bytes) and len(node.match) == 65536 for node in nodes)


@pytest.mark.parametrize("source", ["file", "decoded:0"])
@pytest.mark.parametrize("origin", [0, 117])
def test_exact_pdf_allowance_is_charged_once_and_preserves_source_coordinates(
    source: str,
    origin: int,
) -> None:
    encoded = zlib.compress(PAYLOAD)
    data = pdf_fixture([*CATALOG, _stream(encoded)])
    limits = AnalysisLimits(
        max_members=1, max_member_bytes=len(PAYLOAD), max_total_bytes=len(PAYLOAD)
    )
    parent, nodes = _parse(data, limits, source=source, origin=origin)
    assert _decoded(nodes) == [PAYLOAD]
    assert any(node.name == "application/json" for node in nodes)
    assert parent.analysis_context.total_bytes == len(PAYLOAD)
    assert parent.analysis_context.members == 1
    physical = next(node for node in nodes if node.name == "FlateDecode")
    assert physical.source == source
    assert physical.offset == origin + data.index(encoded)
    decoded = next(node for node in nodes if node.decoded is not None)
    assert decoded.source != source
    assert decoded.offset == 0


def test_shared_pdf_allowance_prevents_a_second_stream_expansion() -> None:
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(PAYLOAD)), _stream(zlib.compress(PAYLOAD))])
    parent, nodes = _parse(data, AnalysisLimits(max_total_bytes=len(PAYLOAD)))
    assert _decoded(nodes) == [PAYLOAD]
    assert parent.analysis_context.total_bytes == len(PAYLOAD)
    assert any(node.analysis_status == "limited" for node in nodes)


def _lzw_literals(data: bytes) -> bytes:
    bits = "".join(f"{code:09b}" for code in [256, *data, 257])
    bits += "0" * (-len(bits) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


@pytest.mark.parametrize(
    ("name", "encoded"),
    [
        (b"FlateDecode", zlib.compress(PAYLOAD)),
        (b"ASCII85Decode", base64.a85encode(PAYLOAD, adobe=True)),
        (b"ASCIIHexDecode", PAYLOAD.hex().encode() + b">"),
        (b"RunLengthDecode", bytes([len(PAYLOAD) - 1]) + PAYLOAD + b"\x80"),
        (b"LZWDecode", _lzw_literals(PAYLOAD)),
    ],
)
@pytest.mark.parametrize("extra", [-1, 0, 1])
def test_pdf_filters_respect_their_exact_output_boundary(
    name: bytes,
    encoded: bytes,
    extra: int,
) -> None:
    data = pdf_fixture([*CATALOG, _stream(encoded, b"/Filter /" + name)])
    parent, nodes = _parse(data, AnalysisLimits(max_member_bytes=len(PAYLOAD) + extra))
    if extra < 0:
        assert not _decoded(nodes)
        assert any(node.analysis_status == "limited" for node in nodes)
    else:
        assert _decoded(nodes) == [PAYLOAD]
        assert parent.analysis_context.total_bytes >= len(PAYLOAD)


@pytest.mark.parametrize("limit", [0, 1, 3])
def test_ascii85_zero_shorthand_does_not_expand_past_the_bound(limit: int) -> None:
    data = pdf_fixture([*CATALOG, _stream(b"z" * 16384, b"/Filter /ASCII85Decode")])
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=limit))
    assert not _decoded(nodes)
    assert any(node.analysis_status == "limited" for node in nodes)


def test_pdf_filter_chain_charges_each_retained_stage_once() -> None:
    intermediate = zlib.compress(PAYLOAD)
    encoded = zlib.compress(intermediate)
    data = pdf_fixture([*CATALOG, _stream(encoded, b"/Filter [/FlateDecode /FlateDecode]")])
    parent, nodes = _parse(data, AnalysisLimits(max_total_bytes=len(intermediate) + len(PAYLOAD)))
    assert _decoded(nodes) == [PAYLOAD, intermediate]
    assert parent.analysis_context.total_bytes == len(intermediate) + len(PAYLOAD)
    assert parent.analysis_context.members == 1


def test_refused_chain_retains_neither_the_final_nor_intermediate_payload() -> None:
    intermediate = b"A" * 65536
    data = pdf_fixture(
        [*CATALOG, _stream(zlib.compress(intermediate), b"/Filter [/FlateDecode /FlateDecode]")]
    )
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=10))
    assert not _decoded(nodes)
    assert not any(
        isinstance(node.match, bytes) and len(node.match) == len(intermediate) for node in nodes
    )


@pytest.mark.parametrize("limit", [2, 3])
def test_pdf_predictor_output_and_its_input_share_the_byte_allowance(limit: int) -> None:
    attributes = b"/Filter /FlateDecode /DecodeParms << /Predictor 12 /Columns 1 >>"
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(b"\x00A"), attributes)])
    parent, nodes = _parse(data, AnalysisLimits(max_total_bytes=limit))
    if limit == 2:
        assert not _decoded(nodes)
        assert any(node.analysis_status == "limited" for node in nodes)
    else:
        assert _decoded(nodes) == [b"\x00A", b"A"]
        assert parent.analysis_context.total_bytes == 3


def test_bounded_predictor_rejects_an_unbounded_row_allocation() -> None:
    attributes = b"/Filter /FlateDecode /DecodeParms << /Predictor 12 /Columns 1000000000 >>"
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(b"\x00A"), attributes)])
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=100))
    assert not _decoded(nodes)
    assert any(node.analysis_status == "invalid" for node in nodes)


def test_unsupported_bounded_pdf_filter_keeps_framing_without_calling_the_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Unbounded CCITT backend called under a byte allowance")

    monkeypatch.setattr("polyfile.pdf.ccittfaxdecode", forbidden)
    data = pdf_fixture([*CATALOG, _stream(b"encoded", b"/Filter /CCITTFaxDecode")])
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=1024))
    assert not _decoded(nodes)
    assert any(node.name == "PDFDictionary" for node in nodes)
    assert any(node.analysis_status == "unsupported" for node in nodes)


@pytest.mark.parametrize("caching", [False, True])
def test_structural_pdf_streams_are_charged_once_across_repeated_lookups(caching: bool) -> None:
    data, decoded = object_stream_pdf([b"42"])
    context = AnalysisContext(AnalysisLimits(max_members=2))
    with FileStream(data) as stream:
        document = InstrumentedPDFDocument(
            PDFParser(cast(BinaryIO, RawPDFStream(stream))),
            analysis_context=context,
            caching=caching,
        )
        for _ in range(3):
            assert document.getobj(3) == 42
        assert context.members == 2
        assert context.total_bytes == 42 + len(decoded)


@pytest.mark.parametrize("root", [1, 3])
def test_structural_decoding_is_available_at_zero_optional_content_depth(root: int) -> None:
    data, decoded = object_stream_pdf([CATALOG[0]], root=root)
    limits = AnalysisLimits(max_depth=0, max_members=2, max_total_bytes=42 + len(decoded))
    parent, nodes = _parse(data, limits)
    assert parent.analysis_status is None
    assert len([node for node in nodes if node.name == "PDFObject"]) == 4
    assert parent.analysis_context.members == 2
    assert parent.analysis_context.total_bytes == 42 + len(decoded)


@pytest.mark.parametrize(
    "limits",
    [
        AnalysisLimits(max_members=0),
        AnalysisLimits(max_member_bytes=0),
        AnalysisLimits(max_total_bytes=0),
        AnalysisLimits(max_member_bytes=1),
    ],
)
def test_refused_structural_decode_preserves_the_known_physical_stream(
    limits: AnalysisLimits,
) -> None:
    data, _ = object_stream_pdf([CATALOG[0]], root=3)
    parent, nodes = _parse(data, limits)
    assert parent.analysis_status == "limited"
    assert any(node.name == "PDFObject" for node in nodes)
    assert any(node.name == "PDFDictionary" for node in nodes)
    assert not _decoded(nodes)


def test_nested_optional_content_still_consumes_a_separate_member_and_bytes() -> None:
    payload = gzip.compress(PAYLOAD)
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(payload))])
    parent = Match(
        "application/pdf",
        None,
        length=len(data),
        matcher=Matcher(limits=AnalysisLimits(max_members=1)),
    )
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    assert payload in _decoded(nodes)
    assert PAYLOAD not in _decoded(nodes)
    assert parent.analysis_context.members == 1
    assert any(node.analysis_status == "limited" for node in nodes)


def test_unlimited_pdf_stream_output_remains_available() -> None:
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(PAYLOAD))])
    _, nodes = _parse(data, AnalysisLimits())
    assert _decoded(nodes) == [PAYLOAD]


def _compressed_xref(data: bytes) -> bytes:
    position = int(data.split(b"startxref\n")[1].splitlines()[0])
    start = data.index(b"stream\n", position) + len(b"stream\n")
    end = data.index(b"\nendstream", start)
    encoded = zlib.compress(data[start:end])
    header = data[position:start].replace(
        f"/Length {end - start}".encode(),
        f"/Filter /FlateDecode /Length {len(encoded)}".encode(),
    )
    return data[:position] + header + encoded + data[end:]


@pytest.mark.parametrize("root", [1, 3])
def test_compressed_xref_initialization_honors_the_decoded_byte_allowance(root: int) -> None:
    data, _ = object_stream_pdf([CATALOG[0]], root=root)
    parent, nodes = _parse(_compressed_xref(data), AnalysisLimits(max_member_bytes=1))
    assert parent.analysis_status == "limited"
    assert any(node.name == "PDFDictionary" for node in nodes)
    assert not _decoded(nodes)
    assert parent.analysis_context.total_bytes == 0
    assert parent.analysis_context.members == 1


def test_compressed_xref_and_object_stream_share_an_exact_budget() -> None:
    data, decoded = object_stream_pdf([b"42"])
    limits = AnalysisLimits(max_members=2, max_total_bytes=42 + len(decoded))
    parent, nodes = _parse(_compressed_xref(data), limits)
    assert parent.analysis_status is None
    assert len([node for node in nodes if node.name == "PDFObject"]) == 5
    assert parent.analysis_context.total_bytes == 42 + len(decoded)
    assert parent.analysis_context.members == 2


@pytest.mark.parametrize("limit", [1, 100])
def test_fallback_object_stream_decoding_honors_limits_and_reuses_failed_admission(
    limit: int,
) -> None:
    data, _ = object_stream_pdf([b"42"])
    data = data.replace(b"startxref", b"wrongxref")
    parent, nodes = _parse(data, AnalysisLimits(max_member_bytes=limit))
    assert any(node.name == "PDFObject" for node in nodes)
    assert any(node.name == "PDFDictionary" for node in nodes)
    if limit == 1:
        assert parent.analysis_status == "limited"
        assert not _decoded(nodes)
        assert parent.analysis_context.members == 1
    else:
        assert any(node.name == "PDFObject" and node.source != "file" for node in nodes)


def test_nested_decoding_cannot_spend_prepaid_pdf_bytes_again() -> None:
    payload = gzip.compress(PAYLOAD)
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(payload))])
    parent = Match(
        "application/pdf",
        None,
        length=len(data),
        matcher=Matcher(limits=AnalysisLimits(max_total_bytes=len(payload))),
    )
    with FileStream(data) as stream:
        nodes = list(pdf_parser(stream, parent))
    assert _decoded(nodes) == [payload]
    assert parent.analysis_context.total_bytes == len(payload)
    assert any(node.analysis_status == "limited" for node in nodes)


@pytest.mark.parametrize("kind", [b"ObjStm", b"XRef"])
def test_structural_type_labels_alone_do_not_bypass_optional_depth(
    monkeypatch: pytest.MonkeyPatch,
    kind: bytes,
) -> None:
    attributes = b"/Type /" + kind + b" /N 0 /First 0 /Filter /FlateDecode"
    data = pdf_fixture([*CATALOG, _stream(zlib.compress(b"A" * 65536), attributes)])

    def forbidden(*args, **kwargs):
        raise AssertionError("An unused structural type label bypassed the depth allowance")

    monkeypatch.setattr(zlib, "decompress", forbidden)
    monkeypatch.setattr(zlib, "decompressobj", forbidden)
    parent, nodes = _parse(data, AnalysisLimits(max_depth=0))
    assert not _decoded(nodes)
    assert any(node.analysis_status == "limited" for node in nodes)
    assert parent.analysis_context.members == 0


@pytest.mark.parametrize("separator", [b"", b"\n", b"\r\n"])
@pytest.mark.parametrize(
    ("compressed", "structural"),
    [
        (False, False),
        (True, False),
        (True, True),
    ],
)
def test_encrypted_fallback_streams_refresh_bytes_and_callbacks_without_duplicates(
    separator: bytes,
    compressed: bool,
    structural: bool,
) -> None:
    plaintext = zlib.compress(PAYLOAD) if compressed else PAYLOAD
    template = encrypted_pdf(b"{secret}", plaintext=plaintext)
    match = re.search(rb"3 0 obj\n<([0-9a-f]+)>", template)
    assert match is not None
    encoded = bytes.fromhex(match.group(1).decode())
    attributes = b"/Filter /FlateDecode " if compressed else b""
    if structural:
        attributes += b"/Type /ObjStm /N 0 /First 0 "
    body = b"<< " + attributes + f"/Length {len(encoded)} >>\nstream\n".encode()
    body += encoded + separator + b"endstream"
    data = encrypted_pdf(body, plaintext=plaintext)
    normal_parent, normal = _parse(data, AnalysisLimits())
    parent, nodes = _parse(data.replace(b"startxref", b"wrongxref"), AnalysisLimits())
    assert PAYLOAD in _decoded(nodes)
    assert _decoded(nodes).count(PAYLOAD) == 1
    assert sorted(_decoded(nodes)) == sorted(_decoded(normal))
    assert len([node for node in nodes if node.name == "PDFObject"]) == 4
    assert not any(node.display_name == "PDFObjectNone.None" for node in nodes)
    assert parent.analysis_context.members == normal_parent.analysis_context.members


def test_unfiltered_fallback_structural_stream_uses_its_declared_payload_size() -> None:
    data, decoded = object_stream_pdf([b"42"], compressed=False)
    data = data.replace(b"startxref", b"wrongxref")
    parent, nodes = _parse(data, AnalysisLimits(max_member_bytes=42))
    assert decoded in _decoded(nodes)
    assert decoded + b"\n" not in _decoded(nodes)
    assert parent.analysis_context.members == 2


@pytest.mark.parametrize(
    ("name", "encoded"),
    [
        (b"ASCIIHexDecode", b"GG"),
        (b"RunLengthDecode", b"\x03a"),
    ],
)
def test_malformed_bounded_filters_report_invalid_without_retaining_partial_output(
    name: bytes,
    encoded: bytes,
) -> None:
    data = pdf_fixture([*CATALOG, _stream(encoded, b"/Filter /" + name)])
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=1024))
    assert not _decoded(nodes)
    assert any(node.analysis_status == "invalid" for node in nodes)


def test_bounded_stream_decryption_reports_unsupported_without_retaining_plaintext() -> None:
    template = encrypted_pdf(b"{secret}", plaintext=PAYLOAD)
    match = re.search(rb"3 0 obj\n<([0-9a-f]+)>", template)
    assert match is not None
    encoded = bytes.fromhex(match.group(1).decode())
    data = encrypted_pdf(_stream(encoded, b""), plaintext=PAYLOAD)
    _, nodes = _parse(data, AnalysisLimits(max_member_bytes=1024))
    assert PAYLOAD not in _decoded(nodes)
    physical = next(node for node in nodes if node.display_name == "PDFObject3.0")
    assert physical.analysis_status == "unsupported"
