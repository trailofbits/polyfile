# UNIX pack analysis

The exact `1f 1e` UNIX pack signature dispatches through `application/x-unix-pack`, replacing the
bundled generic `application/octet-stream` alias. Existing file descriptions retain their declared
size text and appear once. Other generic binary data never dispatches this parser.

The native parser validates complete canonical Huffman trees with code lengths from 1 through
25 bits, at most 256 literal bytes, and an explicit EOF code. It preserves each `pack_member` with
its physical `pack_header` and `huffman_data` regions. Header fields map the signature, declared
size, code-length counts, and literal table. Concatenated members are framed and counted
individually, and each decoded size is checked before concatenated content enters recursive
analysis. JSON and TAR contents use a separate decoded source with offsets relative to that source.

All analysis limits default to unlimited. Configured decoded-output allowances are checked against
each declared size before decoding. Member attempts, including malformed members, consume the
shared member allowance. The decoder uses bounded input/output chunks and at most 25 code-range
entries. A configured `max_codec_memory` must allow a conservative 256 KiB of codec workspace
on every supported platform; this excludes retained decoded output, the original input, report
objects, and the Python process's other memory. External-helper timeouts do not apply to this
native decoder.

UNIX pack stores a decoded size but has no CRC, so length-preserving corruption can remain
undetected. Trailing bytes must form another supported pack member. Historical `1f 1f` pack files
also receive the format-specific MIME type and keep their existing description, but report
`unsupported` decoding status.

[Project-owned fixtures](../tests/fixtures/pack/README.md) cover all byte values, JSON/TAR recursion,
empty and one-byte content, and complete trees reaching the 1-bit and 25-bit limits. Their decoded
bytes were independently verified against GNU gzip 1.15. GNU gzip is a test reference and is not
required for native pack analysis. Its [manual](https://www.gnu.org/software/gzip/manual/gzip.html)
documents the format's decoded-length integrity check.
