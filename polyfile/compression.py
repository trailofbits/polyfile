"""Bound incremental decoder output before retaining recursive content."""

CHUNK_SIZE = 64 * 1024


class DecodeError(ValueError):
    """Report an invalid, unsupported, or resource-limited decoding attempt."""

    def __init__(self, message: str, *, status: str = "invalid") -> None:
        super().__init__(message)
        self.status = status


class OutputBuffer:
    """Collects incremental output, checking an optional limit before storage."""

    def __init__(self, max_output: int | None = None) -> None:
        self.max_output = max_output
        self._data = bytearray()

    @property
    def remaining(self) -> int | None:
        """The remaining output allowance, or None when unlimited."""
        if self.max_output is None:
            return None
        return max(self.max_output - len(self._data), 0)

    @property
    def next_size(self) -> int:
        """A bounded output chunk, including one byte to detect limit exhaustion."""
        remaining = self.remaining
        if remaining is None:
            return CHUNK_SIZE
        return min(CHUNK_SIZE, remaining + 1)

    def append(self, data: bytes) -> None:
        """Appends decoded bytes or reports the configured output limit."""
        if (
            self.max_output is not None
            and len(self._data) + len(data) > self.max_output
        ):
            raise DecodeError(
                f"decoded content exceeds the {self.max_output}-byte analysis allowance",
                status="limited",
            )
        self._data.extend(data)

    def finish(self) -> bytes:
        """Returns the validated output as an immutable buffer."""
        return bytes(self._data)
