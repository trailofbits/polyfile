"""Deterministic PDF fixtures with byte-accurate cross-reference tables."""

import zlib
from hashlib import md5
import struct

from pdfminer.arcfour import Arcfour
from pdfminer.pdfdocument import PDFStandardSecurityHandler


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


def _stream_object(attributes: bytes, data: bytes) -> bytes:
    return (
        b"<< " + attributes + f" /Length {len(data)} >>\nstream\n".encode()
        + data + b"\nendstream"
    )


def object_stream_pdf(
    bodies: list[bytes], *, compressed: bool = True, root: int = 1,
) -> tuple[bytes, bytes]:
    """Build a PDF with compressed indirect values and a binary cross-reference stream."""
    data = b"%PDF-1.7\n"
    positions = {}
    for number, body in enumerate(CATALOG, 1):
        positions[number] = len(data)
        data += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    header, contents = b"", b""
    for number, body in enumerate(bodies, 3):
        header += f"{number} {len(contents)} ".encode()
        contents += body + b"\n"
    decoded = header + contents
    attributes = f"/Type /ObjStm /N {len(bodies)} /First {len(header)}".encode()
    encoded = decoded
    if compressed:
        attributes += b" /Filter /FlateDecode"
        encoded = zlib.compress(decoded)
    stream_id = len(bodies) + 3
    positions[stream_id] = len(data)
    data += f"{stream_id} 0 obj\n".encode() + _stream_object(attributes, encoded) + b"\nendobj\n"
    xref_id = stream_id + 1
    positions[xref_id] = len(data)
    xref_data = b"\x00\x00\x00\x00\x00\xff\xff"
    for number in range(1, xref_id + 1):
        if number in positions:
            kind, value, generation = 1, positions[number], 0
        else:
            kind, value, generation = 2, stream_id, number - 3
        xref_data += bytes([kind]) + value.to_bytes(4, "big") + generation.to_bytes(2, "big")
    attributes = f"/Type /XRef /Size {xref_id + 1} /Root {root} 0 R /W [1 4 2]".encode()
    data += f"{xref_id} 0 obj\n".encode() + _stream_object(attributes, xref_data) + b"\nendobj\n"
    data += f"startxref\n{positions[xref_id]}\n%%EOF\n".encode()
    return data, decoded


def encrypted_pdf(body: bytes, *, plaintext: bytes = b"a\nb") -> bytes:
    """Build a revision-2 encrypted PDF with a blank user password and object 3."""
    padding = PDFStandardSecurityHandler.PASSWORD_PADDING
    owner_key = md5((b"owner" + padding)[:32]).digest()[:5]
    owner_entry = Arcfour(owner_key).encrypt(padding)
    identifier = b"polyfile-fixture"
    key = md5(padding + owner_entry + struct.pack("<i", -4) + identifier).digest()[:5]
    user_entry = Arcfour(key).encrypt(padding)
    object_key = md5(key + b"\x03\x00\x00\x00\x00").digest()[:10]
    ciphertext = Arcfour(object_key).encrypt(plaintext)
    body = body.replace(b"{secret}", b"<" + ciphertext.hex().encode() + b">")
    encryption = (
        b"<< /Filter /Standard /V 1 /R 2 /Length 40 /P -4 /O <"
        + owner_entry.hex().encode() + b"> /U <" + user_entry.hex().encode() + b"> >>"
    )
    identifier = identifier.hex().encode()
    trailer = b"/Root 1 0 R /Encrypt 4 0 R /ID [<" + identifier + b"> <" + identifier + b">]"
    return pdf_fixture([*CATALOG, body, encryption], trailer)
