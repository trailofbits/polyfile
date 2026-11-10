"""Optional resource controls shared by one recursive file analysis."""

import math
from dataclasses import dataclass, field, fields


@dataclass(frozen=True)
class AnalysisLimits:
    """Configure recursive analysis; each omitted limit is unlimited.

    Byte limits count content handed to recursive matching, excluding the original input.
    Depth counts content transitions rather than structural nodes; the input has depth zero.
    """

    max_depth: int | None = None
    max_member_bytes: int | None = None
    max_total_bytes: int | None = None
    max_members: int | None = None
    max_codec_memory: int | None = None
    helper_timeout: float | None = None

    def __post_init__(self) -> None:
        for item in fields(self):
            if item.name == "helper_timeout":
                continue
            value = getattr(self, item.name)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{item.name} must be a nonnegative integer or None")
        if self.max_codec_memory == 0:
            raise ValueError("max_codec_memory must be a positive integer or None")
        timeout = self.helper_timeout
        if timeout is not None and (
            not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0
        ):
            raise ValueError("helper_timeout must be positive finite seconds or None")


@dataclass
class AnalysisContext:
    """Track recursive content admitted during one root analysis."""

    limits: AnalysisLimits
    total_bytes: int = 0
    members: int = 0
    _source_count: int = field(default=0, init=False, repr=False)

    def next_source(self) -> str:
        """Return the next deterministic decoded-buffer identifier in this analysis."""
        source = f"decoded:{self._source_count}"
        self._source_count += 1
        return source

    @property
    def remaining_members(self) -> int | None:
        """Return the remaining container-entry allowance, or None if unlimited."""
        if self.limits.max_members is None:
            return None
        return max(0, self.limits.max_members - self.members)

    @property
    def member_limit(self) -> int | None:
        """Return the remaining output allowance for one member, or None if unlimited."""
        bounds = []
        if self.limits.max_member_bytes is not None:
            bounds.append(self.limits.max_member_bytes)
        if self.limits.max_total_bytes is not None:
            bounds.append(max(0, self.limits.max_total_bytes - self.total_bytes))
        return min(bounds) if bounds else None

    def claim_entry(self) -> str | None:
        """Admit a container entry, including metadata-only entries and codec members."""
        limit = self.limits.max_members
        if limit is not None and self.members >= limit:
            return f"Container entry exceeds --max-members={limit}"
        self.members += 1
        return None

    def claim_member(self, size: int, depth: int, *, count: bool = True) -> str | None:
        """Admit one recursive content region or return the limit that rejects it.

        Args:
            size: Number of bytes in the region.
            depth: Number of content transitions from the original input.
            count: Whether this region has not already consumed a container entry.

        Returns:
            An actionable rejection message, or None after charging the region.
        """
        checks = (
            ("max_depth", depth),
            ("max_member_bytes", size),
            ("max_total_bytes", self.total_bytes + size),
            ("max_members", self.members + int(count)),
        )
        for name, value in checks:
            limit = getattr(self.limits, name)
            if limit is not None and value > limit:
                flag = "--" + name.replace("_", "-")
                return f"Recursive analysis requires {value}, exceeding {flag}={limit}"
        self.members += int(count)
        self.total_bytes += size
        return None
