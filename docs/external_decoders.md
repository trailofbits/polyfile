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

## LRZIP

LRZIP decoding automatically uses `lrzip` from `PATH` when its version banner identifies version
0.7.3 or newer. Install LRZIP separately; Python installation does not install the executable.
PolyFile supports unencrypted LRZIP archive versions 0.6 and 0.7, with known or unknown decoded
sizes. Other archive versions and encrypted archives report `unsupported` before decoder startup.
The adapter invokes fixed `-Q -d -o - -p 1` arguments and supplies `LRZIP=NOCONFIG` to disable
configuration files. It passes no `-m` option: that option changes LRZIP's available-memory
assumption and does not impose a hard process-memory ceiling. The optional output, timeout, and
Linux address-space controls described above apply to LRZIP.

The parser preserves the 24-byte physical header, first RZIP chunk framing, remaining encoded
chunks, and optional final MD5 digest. The chunk's capacity can exceed its decoded payload size;
output limits use the archive's decoded-size field when known and bound helper output in all
cases. Internal chunk records are part of one archive and do not consume separate member entries.
The installed decoder validates secondary compression, RZIP backward references, per-chunk CRC
where present, and final integrity. PolyFile also verifies a declared decoded size and final MD5
before publishing any decoded source. Archives can require substantial native memory; configure
`--max-codec-memory` on Linux to impose a hard ceiling. No codec-memory ceiling applies by default.

LRZIP's linked internal streams are not fully represented as physical AST fields. Framing and
trailing-data acceptance follow the installed decoder; successful decoding does not imply that
every encoded byte was referenced. Concatenated archives are not treated as independent members.
See [the LRZIP fixture provenance](../tests/fixtures/lrzip/README.md) for the two reference archive
versions and [the upstream header description](https://github.com/ckolivas/lrzip/blob/v0.7.3/doc/magic.header.txt)
for header semantics. The 0.7 chunk prefilter byte is defined by the
[reference decoder](https://github.com/ckolivas/lrzip/blob/v0.7.3/runzip.c).
