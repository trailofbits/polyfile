"""Project-owned non-block LZW literal fixture encoder."""


def literal_lzw(data: bytes, maxbits: int) -> bytes:
    """Encodes literals with UNIX compress non-block width transitions.

    Args:
        data: Project-owned payload bytes.
        maxbits: Maximum dictionary code width, from 9 through 16.

    Returns:
        A non-block LZW stream using literals and alignment padding only.
    """
    output = bytearray(b"\x1f\x9d" + bytes([maxbits]))
    segment = bytearray()
    bits = used = 0
    width = 9
    free = 256
    maximum = 511
    first = True
    for value in data:
        if free > maximum and width < maxbits:
            if used:
                segment.append(bits & 255)
            segment.extend(bytes((-len(segment)) % width))
            output.extend(segment)
            segment.clear()
            bits = used = 0
            width += 1
            maximum = (1 << maxbits) if width == maxbits else (1 << width) - 1
        bits |= value << used
        used += width
        while used >= 8:
            segment.append(bits & 255)
            bits >>= 8
            used -= 8
        if first:
            first = False
        elif free < (1 << maxbits):
            free += 1
    if used:
        segment.append(bits & 255)
    output.extend(segment)
    return bytes(output)
