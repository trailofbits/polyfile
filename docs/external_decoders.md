# External decoders

PolyFile automatically decodes UNIX compress (`.Z`) streams when `ggzip` or `gzip` on your `PATH`
identifies itself as GNU gzip 1.15 or newer. Install GNU gzip separately using your platform's
package manager. Python installation does not install this native executable. GNU gzip 1.15 is the
reference version used by the test suite. Other gzip implementations and older versions preserve
the file's classification and physical structure and report `analysis_status: "unsupported"` with
an installation message.

The adapter invokes the selected executable directly with fixed `-d -c` arguments and encoded
bytes on standard input. It drains standard output and error concurrently, retains only the first
4 KiB of diagnostic text, and analyzes decoded bytes only after successful exit. The helper runs
in a temporary working directory with locale and temporary-directory settings supplied by
PolyFile. Inherited options such as `GZIP`, Python import paths, and loader configuration are
excluded. No archive paths or file-supplied arguments are passed to the helper.

All analysis limits default to unlimited. You can configure decoded-output, member, depth, and
aggregate limits through `AnalysisLimits` or the corresponding command-line arguments.
`helper_timeout` / `--helper-timeout` accepts positive finite seconds and applies separately to
version queries and decoding invocations. A timeout or decoded-output limit stops and reaps the
helper and reports `limited`, without publishing partial decoded content.

`max_codec_memory` / `--max-codec-memory` sets a hard helper address-space ceiling on Linux. An
isolated Python launcher applies `RLIMIT_AS` before executing the decoder; this ceiling includes
the native executable's libraries and allocations. The helper may need more memory than its
codec dictionary alone. Other platforms support ordinary helper decoding and report `unsupported`
if you configure this hard ceiling. The ceiling does not constrain PolyFile's own memory use.

The UNIX compress adapter supports block and non-block LZW with maximum code widths from 10
through 16; codes begin at 9 bits and grow to the declared maximum. A declared 9-bit maximum
reports unsupported status because GNU gzip 1.15 does not handle dictionary saturation correctly
for that variant. Reserved header bits and smaller widths are invalid; larger widths report
unsupported status.
GNU gzip validates the code stream. The format has no checksum or decoded-size field, and some
truncations at complete-code boundaries decode successfully as shorter files. PolyFile cannot
infer the intended original size in those cases. Concatenated `.Z` files are not treated as
independent members: UNIX compress has no framed member terminator.

The project-owned fixtures and their encoder/decoder versions, hashes, and commands are recorded
in [the fixture provenance](../tests/fixtures/compress/README.md). The CI workflow builds the
reference decoder from the [GNU gzip 1.15 source archive](https://ftp.gnu.org/gnu/gzip/gzip-1.15.tar.xz)
and verifies its SHA-256 before compiling it. GNU gzip remains a separately installed executable;
no GNU gzip source or binaries are included in PolyFile distributions.

## SCO compress -H (LZH)

The exact `1f a0` signature now dispatches through `application/x-sco-compress`. Its existing
`SCO compress -H (LZH) data` description remains unchanged and appears once in file output.
The parser supports the SCO LZH variant implemented by GNU gzip 1.15, with an 8 KiB history
window. Other LHA/LZH container signatures do not use this adapter. All helper availability,
output, timeout, recursion, and Linux hard-memory controls described above apply.

Physical `sco_lzh_header` and `lzh_data` regions remain in the original source. Successful
helper output becomes a separate decoded source, so TAR contents are recursively scanned.
Malformed Huffman tables reported by the helper retain invalid status and publish no partial
content. As the [GNU gzip manual](https://www.gnu.org/software/gzip/manual/gzip.html) explains,
SCO LZH has no CRC and permits only limited consistency checking. The decoder zero-pads its
bit lookahead at EOF, so some truncated streams can be accepted as shorter or complete files.
PolyFile validates minimum framing and preserves this format limitation; successful exit does
not establish an original size or checksum that the format does not store.

[Project-owned SCO fixtures](../tests/fixtures/sco/README.md) include literal and back-reference
blocks, JSON, TAR recursion, and empty content, verified against the pinned reference decoder.

## UNIX pack

The `1f 1e` UNIX pack signature dispatches through `application/x-unix-pack`, replacing the
bundled generic `application/octet-stream` alias. File descriptions retain their declared-size
text and appear once. The parser validates complete canonical Huffman trees with code lengths
from 1 through 25 bits, at most 256 literal bytes, and an explicit EOF code. It preserves the
physical signature, declared size, code-length counts, literal table, and encoded body.
The declared decoded size is checked against configured output limits before helper execution
and against the complete decoded buffer before recursive analysis.

GNU gzip 1.15 is the reference decoder; the same helper availability and optional resource
controls apply. It checks decoded length, as documented in the
[GNU gzip manual](https://www.gnu.org/software/gzip/manual/gzip.html). UNIX pack has no CRC, so
length-preserving corruption can remain undetected. Historical `1f 1f` pack files also receive
the format-specific MIME type but report `unsupported`, because GNU gzip does not decode that
variant. Other generic binary data never dispatches this parser.

[Project-owned pack fixtures](../tests/fixtures/pack/README.md) cover all byte values, JSON/TAR
recursion, empty and one-byte content, and complete trees reaching the 1-bit and 25-bit limits.
