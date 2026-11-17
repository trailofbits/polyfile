"""Bound semantic-value previews before converting large binary fields to text."""

from itertools import islice


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    suffix = f"… ({len(text):,} characters total)"
    return text[: max(0, limit - len(suffix))] + suffix


def _binary_preview(value: bytes | bytearray | memoryview, limit: int) -> str:
    view = memoryview(value)
    if not view.c_contiguous:
        return f"<memoryview: {view.nbytes:,} bytes; non-contiguous>"
    data = view.cast("B")
    count = min(len(data), max(0, (limit - 48) // 4))
    text = repr(bytes(data[:count]))
    if count < len(data):
        text += f"… ({len(data):,} bytes total)"
    return _truncate(text, limit)


def _item_preview(value: object, depth: int, limit: int) -> str:
    if isinstance(value, str):
        return _truncate(repr(_truncate(value, limit)), limit)
    return value_preview(value, depth=depth - 1, limit=limit)


def _container_preview(
    value: list[object]
    | tuple[object, ...]
    | dict[object, object]
    | set[object]
    | frozenset[object],
    depth: int,
    limit: int,
) -> str:
    if depth == 0:
        return f"<{type(value).__name__}: {len(value):,} items>"
    budget = max(48, limit // 4)
    if isinstance(value, dict):
        parts = [
            f"{_item_preview(key, depth, budget)}: {_item_preview(item, depth, budget)}"
            for key, item in islice(value.items(), 4)
        ]
        opening, closing = "{", "}"
    else:
        parts = [_item_preview(item, depth, budget) for item in islice(value, 4)]
        opening, closing = "[", "]"
        if isinstance(value, tuple):
            opening, closing = "(", ")"
        elif isinstance(value, (set, frozenset)):
            opening, closing = "{", "}"
            if isinstance(value, frozenset):
                opening, closing = "frozenset({", "})"
    if len(value) > 4:
        parts.append(f"… ({len(value):,} items total)")
    return _truncate(opening + ", ".join(parts) + closing, limit)


def value_preview(value: object, *, depth: int = 3, limit: int = 1024) -> str:
    """Render a bounded preview without copying complete binary fields.

    Args:
        value: Parsed semantic value or description.
        depth: Maximum number of builtin container levels to inspect.
        limit: Maximum preview length, including a truncation indicator.

    Returns:
        A textual preview with explicit sizes when content is omitted.
    """
    if isinstance(value, str):
        return _truncate(value, limit)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _binary_preview(value, limit)
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        return _container_preview(value, depth, limit)
    if isinstance(value, int) and value.bit_length() > limit * 3:
        return f"<integer: {value.bit_length():,} bits>"
    return _truncate(str(value), limit)
