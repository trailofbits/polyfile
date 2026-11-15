"""PDF byte iterators expose the containers and structure in their serialized trees."""

import pytest

from polyfile.analysis import AnalysisLimits
from polyfile.pdf import (
    PDFDeciphered,
    PDFDict,
    PDFStreamFilter,
    PNGPredictor,
    PSBytes,
    PSInt,
    PSStr,
    parse_object,
)
from polyfile.polyfile import Match, Matcher


KINDS = ("PSBytes", "PNGPredictor", "PDFStreamFilter", "PDFDeciphered")


def _token(kind: str, payload: bytes) -> PSBytes:
    if kind == "PSBytes":
        return PSBytes(payload, pdf_offset=24, pdf_bytes=len(payload))
    original = PSBytes(b"encoded", pdf_offset=24, pdf_bytes=7)
    if kind == "PNGPredictor":
        key = PSStr("Predictor", pdf_offset=3, pdf_bytes=9)
        params = PDFDict(
            {key: PSInt(12, pdf_offset=14, pdf_bytes=2)},
            pdf_offset=0,
            pdf_bytes=18,
        )
        return PNGPredictor(
            payload,
            original_bytes=original,
            params=params,
            pdf_offset=24,
            pdf_bytes=7,
        )
    if kind == "PDFStreamFilter":
        return PDFStreamFilter(
            payload,
            original_bytes=original,
            name="FlateDecode",
            pdf_offset=24,
            pdf_bytes=7,
        )
    return PDFDeciphered(payload, original_bytes=original, pdf_offset=24, pdf_bytes=7)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("payload", (b"", b"abc", b'{"decoded":true}'))
@pytest.mark.parametrize("source", ("file", "decoded:0"))
@pytest.mark.parametrize("origin", (0, 117))
def test_byte_containers_are_yielded_once_before_their_descendants(
    kind: str,
    payload: bytes,
    source: str,
    origin: int,
) -> None:
    token = _token(kind, payload)
    matcher = Matcher(parse=False)
    parent = Match("PDF", None, relative_offset=origin, length=64, matcher=matcher, source=source)

    yielded = list(parse_object(token, matcher, parent, pdf_header_offset=origin))

    assert len(parent.children) == 1
    container = parent.children[0]
    assert yielded[0] is container
    assert sum(node is container for node in yielded) == 1
    assert (container.offset, container.length, container.source) == (
        origin + 24,
        token.pdf_bytes,
        source,
    )
    output = parent.to_obj()["subEls"][0]
    assert (output["offset"], output["size"], output["source"]) == (
        origin + 24,
        token.pdf_bytes,
        source,
    )
    assert output["type"] == ("FlateDecode" if kind == "PDFStreamFilter" else kind)
    descendants = list(parent.children)
    for node in descendants:
        descendants.extend(node.children)
    assert len({id(node) for node in yielded}) == len(yielded)
    assert {id(node) for node in yielded} == {id(node) for node in descendants}


@pytest.mark.parametrize("filtered_original", (False, True))
def test_predictor_inputs_and_recursive_matches_are_visited_once(filtered_original: bool) -> None:
    token = _token("PNGPredictor", b'{"decoded":true}')
    assert isinstance(token, PNGPredictor)
    if filtered_original:
        token = PNGPredictor(
            bytes(token),
            original_bytes=_token("PDFStreamFilter", b"encoded"),
            params=token.params,
            pdf_offset=24,
            pdf_bytes=7,
        )
    matcher = Matcher(parse=False)
    parent = Match("PDF", None, length=64, matcher=matcher)

    yielded = list(parse_object(token, matcher, parent))

    container = parent.children[0]
    output = container.to_obj()
    descendants = [output]
    for node in descendants:
        descendants.extend(node["subEls"])
    assert sum(node["type"] == "PSBytes" for node in descendants) == 1
    assert sum(child.name == "PDFDictionary" for child in container.children) == 1
    assert sum(node.name == "PSBytes" for node in yielded) == 1
    assert sum(node.name == "PSInt" for node in yielded) == 1
    assert sum(node.name == "text/plain" for node in yielded) == 1 + filtered_original
    assert sum(node.name == "application/json" for node in yielded) == 1
    assert sum(node.name == "decoded_content" for node in yielded) == 1 + filtered_original
    original = next(node for node in yielded if node.name == "PSBytes")
    assert original.match == b"encoded"
    assert original.to_obj()["offset"] == 24
    assert sum(child["type"] == "PDFDictionary" for child in output["subEls"]) == 1


@pytest.mark.parametrize("kind", ("PSBytes", "PNGPredictor"))
@pytest.mark.parametrize(
    "limits",
    (
        AnalysisLimits(max_members=0),
        AnalysisLimits(max_member_bytes=0),
        AnalysisLimits(max_depth=0),
    ),
)
def test_limited_byte_analysis_still_yields_its_container(
    kind: str, limits: AnalysisLimits
) -> None:
    matcher = Matcher(parse=False, limits=limits)
    parent = Match("PDF", None, length=64, matcher=matcher)

    yielded = list(parse_object(_token(kind, b'{"decoded":true}'), matcher, parent))

    assert yielded[0] is parent.children[0]
    assert any(node.analysis_status == "limited" for node in yielded)
    assert not any(node.name == "application/json" for node in yielded)
    assert parent.analysis_context.members == 0
