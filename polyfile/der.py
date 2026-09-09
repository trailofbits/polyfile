"""Support for the libmagic ``der`` pseudo-datatype.

The ``der`` tests in ``polyfile/magic_defs/der`` walk a Distinguished Encoding Rules document one
tag-length-value (TLV) triple at a time. Each test compares the tag, and optionally the length and
the value, of the single TLV that starts at the test's offset. This module implements that
comparison, mirroring ``src/der.c`` of the upstream ``file`` utility so that PolyFile reports the
same results.

Nothing here parses a whole ASN.1 document: a ``der`` test only needs the TLV header at one offset,
and reading no further lets the tests match DER that is embedded in a larger file.
"""

from typing import NamedTuple, Optional, Tuple


TAG_NAMES: Tuple[str, ...] = (
    "eoc", "bool", "int", "bit_str", "octet_str",
    "null", "obj_id", "obj_desc", "ext", "real",
    "enum", "embed", "utf8_str", "rel_oid", "time",
    "res2", "seq", "set", "num_str", "prt_str",
    "t61_str", "vid_str", "ia5_str", "utc_time", "gen_time",
    "gr_str", "vis_str", "gen_str", "univ_str", "char_str",
    "bmp_str", "date", "tod", "datetime", "duration",
    "oid-iri", "rel-oid-iri",
)

UTF8_STRING_TAG: int = 0x0C
PRINTABLE_STRING_TAG: int = 0x13
IA5_STRING_TAG: int = 0x16
UTC_TIME_TAG: int = 0x17

HIGH_TAG_NUMBER: int = 0x1F
UINT32_MAX: int = 0xFFFFFFFF

MAX_FORMATTED_CHARS: int = 127
"""``der_data`` formats into a 128 byte buffer, so text is truncated to 127 characters."""

MAX_FORMATTED_HEX_BYTES: int = 63
"""``der_data`` stops writing hex digits once it reaches the end of its 128 byte buffer."""


class InvalidDER(ValueError):
    """Raised when the bytes at an offset are not a well-formed DER tag-length-value header."""


class DERMismatch(InvalidDER):
    """Raised when a well-formed DER header does not satisfy a :class:`DERSpecification`."""


def read_tag(data: bytes, offset: int) -> Tuple[int, int]:
    """Reads the tag number of the DER object that starts at ``offset``.

    Args:
        data: The buffer to read from.
        offset: The absolute offset of the identifier octet.

    Returns:
        The tag number and the absolute offset of the first length octet.

    Raises:
        InvalidDER: If the tag runs past the end of ``data``.
    """
    if offset >= len(data):
        raise InvalidDER(f"the identifier octet at offset {offset} is past the end of the data")
    tag = data[offset] & HIGH_TAG_NUMBER
    offset += 1
    if tag != HIGH_TAG_NUMBER:
        return tag, offset
    # A high tag number continues over every octet that has its most significant bit set. This
    # mirrors `gettag` in der.c, which leaves the last octet of the tag for `getlength` to read.
    while True:
        if offset >= len(data):
            raise InvalidDER(f"the high tag number at offset {offset} is past the end of the data")
        elif data[offset] < 0x80:
            return tag, offset
        tag = tag * 128 + data[offset] - 0x80
        offset += 1


def read_length(data: bytes, offset: int) -> Tuple[int, int]:
    """Reads the length of a DER value.

    Args:
        data: The buffer to read from.
        offset: The absolute offset of the first length octet.

    Returns:
        The length of the value and the absolute offset of its first octet.

    Raises:
        InvalidDER: If the length runs past the end of ``data``, or describes a value that does.
    """
    if offset >= len(data):
        raise InvalidDER(f"the length octet at offset {offset} is past the end of the data")
    first_octet = data[offset]
    offset += 1
    num_octets = first_octet & 0x7F
    if offset + num_octets >= len(data):
        raise InvalidDER(f"a {num_octets} octet length at offset {offset} runs past the data")
    elif first_octet & 0x80 == 0:
        return num_octets, offset
    length = int.from_bytes(data[offset:offset + num_octets], "big")
    offset += num_octets
    if length > UINT32_MAX - offset or offset + length > len(data):
        raise InvalidDER(f"a value of {length} bytes at offset {offset} runs past the data")
    return length, offset


MIME_TYPES: Tuple[Tuple[str, str], ...] = (
    ("Certificate, Version=", "application/pkix-cert"),
    ("DER Encoded Certificate, ", "application/pkix-cert"),
    ("DER Encoded Certificate request", "application/pkcs10"),
    ("DER Encoded PKCS#7 Signed Data", "application/pkcs7-mime"),
)
"""Maps the message of a ``der`` test to the MIME type of what that test identifies.

Upstream ``der`` carries no ``!:mime`` line, so PolyFile supplies these. The key is the start of the
message rather than the whole message, because the certificate rules end in a key size that upstream
extends as larger keys come into use. The ``DER Encoded Key Pair`` rules are deliberately absent:
there is no registered media type for a raw PKCS#1 key pair.
"""


def mime_type_for_message(message: str) -> Optional[str]:
    """Returns the MIME type that a ``der`` test's message identifies, if PolyFile assigns one.

    Args:
        message: The message of a single ``der`` test, as written in the definition file.

    Returns:
        A MIME type from :data:`MIME_TYPES`, or ``None`` if the message identifies nothing that has
        a registered media type.
    """
    message = message.strip()
    for prefix, mime in MIME_TYPES:
        if message.startswith(prefix):
            return mime
    return None


def tag_name(tag: int) -> str:
    """Returns the libmagic name of a tag number, or its hexadecimal form if it has none."""
    if tag < len(TAG_NAMES):
        return TAG_NAMES[tag]
    return f"{tag:#x}"


def format_value(tag: int, value: bytes) -> str:
    """Renders a DER value the way libmagic substitutes it into a ``%s`` in a test's message."""
    if tag in (PRINTABLE_STRING_TAG, UTF8_STRING_TAG, IA5_STRING_TAG):
        return value[:MAX_FORMATTED_CHARS].decode("utf-8", errors="replace")
    elif tag == UTC_TIME_TAG and len(value) >= 12:
        d = value[:12].decode("ascii", errors="replace")
        return f"20{d[0:2]}-{d[2:4]}-{d[4:6]} {d[6:8]}:{d[8:10]}:{d[10:12]} GMT"
    return value[:MAX_FORMATTED_HEX_BYTES].hex()


class DERHeader(NamedTuple):
    """The tag and length of a single DER object."""

    tag: int
    start: int
    """The absolute offset of the identifier octet."""
    value_start: int
    """The absolute offset of the first octet of the value."""
    length: int
    """The number of octets in the value."""

    @property
    def name(self) -> str:
        return tag_name(self.tag)

    @property
    def header_length(self) -> int:
        return self.value_start - self.start

    @property
    def end(self) -> int:
        """The absolute offset of the first octet after this object."""
        return self.value_start + self.length

    def formatted_value(self, data: bytes) -> str:
        return format_value(self.tag, data[self.value_start:self.end])

    @classmethod
    def parse(cls, data: bytes, offset: int) -> "DERHeader":
        """Reads the header of the DER object that starts at ``offset``.

        Raises:
            InvalidDER: If ``data`` does not hold a well-formed DER object at ``offset``.
        """
        tag, after_tag = read_tag(data, offset)
        length, value_start = read_length(data, after_tag)
        return cls(tag=tag, start=offset, value_start=value_start, length=length)


def _leading_digits(text: str) -> str:
    for i, c in enumerate(text):
        if not c.isdigit():
            return text[:i]
    return text


class DERSpecification:
    """The operand of a ``der`` test, such as ``seq``, ``int1=00``, or ``obj_id3=550406``.

    The operand names the expected tag, optionally followed by the expected length in decimal and by
    ``=`` and the expected value. A value of ``x`` matches any value.
    """

    def __init__(self, specification: str):
        self.specification: str = specification

    def match(self, header: DERHeader, data: bytes) -> Optional[str]:
        """Tests a DER header against this specification.

        Args:
            header: The header to test.
            data: The buffer that ``header`` was read from.

        Returns:
            The formatted value of the object if this specification constrains the value, otherwise
            ``None``.

        Raises:
            DERMismatch: If the header does not satisfy this specification.
        """
        name = header.name
        if not self.specification.startswith(name):
            raise DERMismatch(f"expected {self.specification!r} but the tag at offset "
                              f"{header.start} is {name!r}")
        remainder = self.specification[len(name):]
        digits = _leading_digits(remainder)
        if digits:
            if header.length != int(digits):
                raise DERMismatch(f"expected a {name!r} of {int(digits)} bytes but it is "
                                  f"{header.length} bytes")
            remainder = remainder[len(digits):]
        if not remainder:
            return None
        elif not remainder.startswith("="):
            raise DERMismatch(f"{self.specification!r} is not a valid DER test")
        expected = remainder[1:]
        actual = header.formatted_value(data)
        if expected != "x" and expected != actual:
            raise DERMismatch(f"expected the {name!r} value {expected!r} but found {actual!r}")
        return actual

    def __eq__(self, other):
        return isinstance(other, DERSpecification) and other.specification == self.specification

    def __hash__(self):
        return hash(self.specification)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.specification!r})"

    def __str__(self):
        return self.specification
