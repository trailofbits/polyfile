# LRZIP fixtures

These project-owned JSON and TAR fixtures use the repository's Apache-2.0 license. No encoder
source, native binary, or third-party corpus is included. `provenance.json` records encoded and
decoded SHA-256 hashes, sizes, encoder commits, and commands. The short JSON and USTAR payloads
are shared with the UNIX compress regression corpus. `repeated.json` contains repeated text to
exercise RZIP backward references before secondary compression.

Version 0.6 archives were encoded by
[LRZIP 0.651](https://github.com/ckolivas/lrzip/tree/e5e9a61fccfd7eff1475bd209e5db11824d88369).
Version 0.7 archives were encoded by
[LRZIP 0.7.3](https://github.com/ckolivas/lrzip/tree/021f0931168cb5e93d2e51768c9c35528427ab0b).
Each encoder reads the committed payload as a regular file, using `-Q -p 1 -m 1 -L 1 -o -` and
optionally `-n` to disable secondary compression. The `-m 1` option bounds fixture-generation
workspace assumptions; PolyFile does not pass this option to its decoder.

Every encoded fixture round-trips byte for byte through LRZIP 0.7.3 with
`LRZIP=NOCONFIG lrzip -Q -d -o - -p 1`. Tests also exercise unknown-size archives by setting the
header's decoded-size field to zero, the format's unknown-size representation, and exercise
legacy CRC-only integrity by clearing the MD5 flag and removing the final digest from a genuine
0.6 archive. These test mutations retain their original encoded payloads and archive versions.

The [LRZIP 0.7.3 release archive](https://github.com/ckolivas/lrzip/releases/download/v0.7.3/lrzip-0.7.3.tar.xz)
SHA-256 is `6928862de7c4bbb3cfbcd12fae9fd0a7d230d5bbf27486e52c4de60717ebfdbb`.
CI verifies this hash and builds the decoder in an isolated prefix. Local tests skip real-helper
cases when LRZIP is unavailable; CI requires the pinned decoder and fails if it is missing.
