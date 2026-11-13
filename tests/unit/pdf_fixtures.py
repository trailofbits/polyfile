"""Deterministic PDF fixtures with byte-accurate cross-reference tables."""


def pdf_fixture(objects: list[bytes], trailer: bytes = b"/Root 1 0 R") -> bytes:
    """Build a PDF from numbered object bodies and trailer entries."""
    data = b"%PDF-1.7\n"
    positions = []
    for number, body in enumerate(objects, 1):
        positions.append(len(data))
        data += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for position in positions:
        data += f"{position:010} 00000 n \n".encode()
    data += b"trailer\n<< " + trailer + b" >>\nstartxref\n"
    return data + str(start).encode() + b"\n%%EOF\n"


CATALOG = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"]
