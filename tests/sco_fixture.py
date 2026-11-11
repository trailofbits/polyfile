"""Project-owned SCO LZH fixtures built from constant-symbol Huffman blocks."""


def sco_codes(codes: list[int]) -> bytes:
    """Encodes literal or length-three/distance-one codes as fixed-symbol blocks.

    Args:
        codes: Literal bytes, or code 256 for a three-byte back reference at distance one.

    Returns:
        A SCO LZH stream containing single-code blocks and a zero-sized end block.
    """
    blocks = [f"{1:016b}" + "0" * 19 + f"{code:09b}" + "0" * 8 for code in codes]
    bits = "".join(blocks) + "0" * 16
    bits += "0" * (-len(bits) % 8)
    return b"\x1f\xa0" + int(bits, 2).to_bytes(len(bits) // 8, "big")
