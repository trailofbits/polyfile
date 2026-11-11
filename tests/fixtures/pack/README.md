# UNIX pack fixtures

These encoded fixtures, their `.decoded` payloads, and `tests/pack_fixture.py` were created for
issue #3633 and use the repository's Apache-2.0 license. The JSON and POSIX USTAR payloads are
the project-owned #3628 payloads. No third-party corpus data, source code, or binaries are included.

The generator emits a complete canonical Huffman tree containing 255 eight-bit literals, one
nine-bit literal, and one nine-bit EOF symbol. The header stores the exact decoded size and
code-length counts, with the last count excluding the implicit final literal and EOF entries.
`deep-tree.z` uses a complete skewed tree reaching 25-bit codes; `shallow-tree.z` uses a single
one-bit literal and one-bit EOF. Empty and one-byte payloads are valid decoder inputs even though
historical pack encoders may refuse to create them.

Every encoded file was decoded using GNU gzip 1.15 with fixed arguments `-d -c`, and its output
was compared byte for byte with the committed payload. `provenance.json` records encoded and
decoded SHA-256 hashes and sizes. The reference source archive SHA-256 is
`9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48`.

The format layout was checked against the separately built GNU gzip 1.15 `unpack.c` reference
implementation. The [GNU gzip manual](https://www.gnu.org/software/gzip/manual/gzip.html)
documents the decoded-length integrity check. The fixture generator emits format fields directly
and contains no copied GNU gzip implementation code.
