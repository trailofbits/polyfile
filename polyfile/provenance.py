"""Source-qualified input intervals shared by structural and derived values."""

from collections.abc import Iterable
from dataclasses import dataclass
from operator import index


@dataclass(frozen=True)
class SourceSpan:
    """A contributing byte interval; None identifies an unattached parser view.

    Unattached intervals must acquire an analysis source before report serialization.
    Intervals describe dependencies, not a byte-for-byte output mapping.
    """

    source: str | None
    offset: int
    size: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "offset", index(self.offset))
        object.__setattr__(self, "size", index(self.size))
        if self.offset < 0 or self.size < 0:
            raise ValueError("Source span offset and size must be nonnegative")
        if self.source is not None and not isinstance(self.source, str):
            raise TypeError("Source span identifiers must be strings or None")

    def to_obj(self) -> dict[str, str | int]:
        """Serialize a bound interval using the report's source/offset/size vocabulary."""
        if self.source is None:
            raise ValueError("Bind the dependency to an analysis source before serialization")
        return {"source": str.__str__(self.source), "offset": self.offset, "size": self.size}


def normalize_spans(spans: Iterable[SourceSpan]) -> tuple[SourceSpan, ...]:
    """Deduplicate intervals and merge touching ranges within the same source.

    Args:
        spans: Input dependencies, including optional unattached parser-view intervals.

    Returns:
        Deterministically ordered, nonempty intervals without filling disjoint gaps.
    """
    ordered = sorted(
        {span for span in spans if span.size},
        key=lambda span: (span.source is not None, span.source or "", span.offset, span.size),
    )
    result: list[SourceSpan] = []
    for span in ordered:
        if result and result[-1].source == span.source:
            previous = result[-1]
            end = previous.offset + previous.size
            if span.offset <= end:
                end = max(end, span.offset + span.size)
                result[-1] = SourceSpan(span.source, previous.offset, end - previous.offset)
                continue
        result.append(span)
    return tuple(result)
