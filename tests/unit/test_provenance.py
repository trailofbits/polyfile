"""Report dependencies retain exact input intervals and deterministic source identities."""

from typing import cast

import pytest

from polyfile import SourceSpan
from polyfile.polyfile import Match, Matcher
from polyfile.provenance import normalize_spans


def test_dependency_normalization_preserves_gaps_and_source_boundaries() -> None:
    spans = [
        SourceSpan("file", 4, 2),
        SourceSpan("file", 2, 3),
        SourceSpan("file", 2, 3),
        SourceSpan("file", 9, 2),
        SourceSpan("file", 6, 1),
        SourceSpan("file", 12, 0),
        SourceSpan("decoded:0", 2, 5),
    ]
    expected = (
        SourceSpan("decoded:0", 2, 5),
        SourceSpan("file", 2, 5),
        SourceSpan("file", 9, 2),
    )
    assert normalize_spans(spans) == expected
    assert normalize_spans(reversed(spans)) == expected
    root = Match("computed", 7, length=0, matcher=Matcher(False), dependencies=spans)
    assert root.to_obj()["dependencies"] == [span.to_obj() for span in expected]


@pytest.mark.parametrize(("offset", "size"), [(-1, 1), (0, -1)])
def test_negative_intervals_are_rejected(offset: int, size: int) -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        SourceSpan("file", offset, size)


@pytest.mark.parametrize(("offset", "size"), [(1.5, 1), (0, 1.5)])
def test_nonintegral_intervals_are_rejected(offset: float, size: float) -> None:
    with pytest.raises(TypeError):
        SourceSpan("file", cast(int, offset), cast(int, size))


def test_coordinate_inputs_normalize_once_to_native_indexes() -> None:
    class Coordinate:
        calls = 0

        def __index__(self) -> int:
            self.calls += 1
            return 3

    offset = Coordinate()
    span = SourceSpan("file", cast(int, offset), 1)
    assert offset.calls == 1
    assert type(span.offset) is int
    assert span.to_obj() == {"source": "file", "offset": 3, "size": 1}


def test_unbound_dependencies_cannot_escape_into_reports() -> None:
    span = SourceSpan(None, 2, 3)
    with pytest.raises(ValueError, match="Bind"):
        span.to_obj()
    with pytest.raises(ValueError, match="analysis source"):
        Match("computed", None, matcher=Matcher(False), dependencies=[span])
    with pytest.raises(TypeError, match="identifiers"):
        SourceSpan(cast(str, 1), 0, 1)


def test_uninstrumented_matches_omit_optional_dependencies() -> None:
    root = Match("native", None, matcher=Matcher(False))
    assert "dependencies" not in root.to_obj()


def test_explicit_source_names_reserve_decoded_buffer_ids() -> None:
    root = Match("root", None, source="decoded:0", matcher=Matcher(False))
    Match("nested", None, source="decoded:2", parent=root)
    assert root.analysis_context.next_source() == "decoded:1"
    assert root.analysis_context.next_source() == "decoded:3"
