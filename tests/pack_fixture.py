"""Project-owned UNIX pack encoder with a fixed complete canonical Huffman tree."""


def pack_fixture(data: bytes) -> bytes:
    """Encodes a payload using all literal bytes and an explicit end-of-block code.

    Args:
        data: Project-owned payload bytes.

    Returns:
        UNIX pack bytes with 255 eight-bit literals and one nine-bit literal plus EOF.
    """
    header = b"\x1f\x1e" + len(data).to_bytes(4, "big") + bytes([9])
    header += bytes(7) + bytes([255, 0]) + bytes(range(256))
    bits = "".join("0" * 9 if value == 255 else f"{value + 1:08b}" for value in data)
    bits += f"{1:09b}"
    bits += "0" * (-len(bits) % 8)
    return header + int(bits, 2).to_bytes(len(bits) // 8, "big")


def pack_deep_fixture(data: bytes) -> bytes:
    """Encodes literals 0 through 24 with a complete tree reaching 25-bit codes.

    Args:
        data: Project-owned payload containing only byte values 0 through 24.

    Returns:
        UNIX pack bytes with one literal at each depth and a 25-bit EOF code.
    """
    header = b"\x1f\x1e" + len(data).to_bytes(4, "big") + bytes([25])
    header += bytes([1]) * 24 + bytes([0]) + bytes(range(25))
    bits = "".join("0" * value + "1" if value < 24 else "0" * 25 for value in data)
    bits += "0" * 24 + "1"
    bits += "0" * (-len(bits) % 8)
    return header + int(bits, 2).to_bytes(len(bits) // 8, "big")


def pack_shallow_fixture(data: bytes) -> bytes:
    """Encodes a project-owned repeated A payload using one-bit literal and EOF codes."""
    bits = "0" * len(data) + "1"
    bits += "0" * (-len(bits) % 8)
    return (
        b"\x1f\x1e"
        + len(data).to_bytes(4, "big")
        + b"\x01\x00A"
        + int(bits, 2).to_bytes(len(bits) // 8, "big")
    )
