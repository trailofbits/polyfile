# 7z archive analysis

PolyFile parses `application/x-7z-compressed` archives with the required
`py7zr==1.1.4` dependency. Identification remains independent of decoding: text and MIME
identification retain every matching format, including a ZIP appended to a 7z archive.

The parser validates the 32-byte signature header, start-header CRC, next-header bounds and
CRC, optional packed-stream CRCs, decoded folder CRCs, and member CRCs before publishing
decoded members. It supports solid and non-solid archives, compressed headers, empty files,
and directories. A checksum that the archive does not store cannot be validated.

## Structure and coordinates

`signature_header` contains the version and next-header fields. `encoded_data` covers bytes
between the signature and the next header; its `packed_stream` and `packed_header` children
identify member streams and compressed-header streams. `next_header` preserves the physical
plain header or encoded-header descriptor. Bytes after that header remain `trailing_data`.

Member nodes retain names, sizes, directory/special-file flags, and optional CRCs. They are
zero-size metadata anchors under `next_header`, rather than claims that every member's metadata
occupies the beginning of that physical header. Each regular member's `decoded_content` uses
its own source identifier and offsets starting at zero. Nested formats recurse in that source.
Solid members do not receive invented, independent compressed byte ranges.

## Isolation and limits

All py7zr imports, header parsing, and decompression run in isolated Python child processes.
One invocation obtains metadata; another extracts validated member bytes. Each receives the
archive on standard input and uses anonymous temporary files for seekable input and output.
Output sinks use internal ordinal names, so duplicate names stay distinct, and archive names
are never used to create filesystem paths. The output spool uses one descriptor for all members.
No decoded bytes reach the parent before extraction and integrity checks succeed.

Depth and zero-member admission checks run before helper startup. The metadata pass bounds the
backend's file-count allocation using the remaining member allowance. Both passes check declared
member and aggregate byte sizes before member decoding; actual sink writes must match the
admitted sizes. The parent checks the current byte/member budgets again between recursive member
analyses, because earlier nested content can consume the remaining allowance. Empty files and
directories each consume one member entry.

`--helper-timeout` applies separately to each invocation, including header parsing. A timeout or
decoded-byte limit reports `limited`. `--max-codec-memory` imposes the existing hard helper
address-space ceiling on Linux, including the Python interpreter, imports, headers, and codec
state. Other platforms report `unsupported` when you configure this ceiling. See
[external decoder resource controls](external_decoders.md) for termination and memory semantics.
The ceiling does not limit the parent process or temporary-file disk use.

Analysis limits are otherwise unlimited by default. The pinned backend also has its own format
bounds, including a 256 MiB decoded-header limit, 8,388,608 files, and 65,536 packed streams.
Metadata transport has a conservative bound derived from those header/file limits, the actual
plain-header size, JSON escaping, and fixed per-entry metadata; it does not allocate that bound
in advance.

## Unsupported and invalid results

Encrypted headers or members report `unsupported` with a password message; PolyFile does not
accept passwords. Unsupported codecs, special-file entries, archive properties, additional
metadata streams, and anti-file entries also report `unsupported`. The last three are valid
7z features that the pinned backend does not parse. A missing or different py7zr version reports
`unsupported` with the required version.

Malformed framing, truncated streams, nonempty directory streams, checksum failures, and decoded
size mismatches report `invalid`. Failure preserves the physical framing available before the
decoder stopped and publishes no partial member contents. A configured member-count refusal
reports `limited`, including refusal during header parsing.

The parser follows the [7z format specification](https://github.com/ip7z/7zip/blob/26.06/DOC/7zFormat.txt)
and the pinned backend's [custom output interface](https://github.com/miurahr/py7zr/blob/v1.1.4/docs/advanced.rst).
[Project-owned fixtures](../tests/fixtures/sevenzip/README.md) record reference commands and hashes.
