# Recursive ICO and universal Mach-O analysis

PolyFile maps ICO PNG images and universal Mach-O architecture members beneath their directory
entries. PNG members use the existing PNG parser and image previews. Mach-O members retain
their architecture's CPU type and subtype fields, and each member receives its own file
classification and parsed structure even though it shares the outer container's MIME type.

ICO DIB image decoding is unsupported. A DIB payload is not a complete BMP file. Universal
Mach-O support follows the existing Kaitai specification: the big-endian, 32-bit fat header.
This feature does not add other universal-header variants.

## Ranges and incomplete analysis

Each payload uses a bounded view of the same analysis source as its container. Its offset and
length must describe a nonempty region after the complete directory and within the input.
Invalid ranges retain the directory entry and its fields with `analysis_status: "invalid"`.
A truncated directory retains the available header and table bytes and reports invalid status.

Overlapping payload references are not analyzed repeatedly. PolyFile orders ranges by offset,
using directory order to break ties, and reserves each valid range that does not overlap an
earlier reserved range. Duplicate and overlapping entries retain their fields with
`analysis_status: "unsupported"` and an explanatory message. Unsupported non-PNG ICO payloads
also retain their bounded regions.

## Sources and resource limits

Member offsets refer to the containing physical or decoded source. A container inside a stored
TAR member keeps the TAR source's coordinates; inside a compressed TAR, its members refer to
the decoded TAR source. A selected input view remains relative to its own analysis origin,
independently of the view's position in its backing stream.

Recursive content uses the existing depth, member-count, per-member-byte, and shared-byte
limits. Directory fields do not consume a content allowance. Each analyzed payload consumes
one member and its bounded byte length; malformed, repeated, and unsupported payloads do not
consume recursive-analysis bytes. A refused region remains beneath its entry with
`analysis_status: "limited"`, without classifying or parsing its payload.
