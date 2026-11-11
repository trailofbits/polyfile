# SCO compress -H (LZH) fixtures

These fixtures and decoded payloads were created for issue #3632 and use the repository's
Apache-2.0 license. The project-owned generator in `tests/sco_fixture.py` emits SCO LZH blocks
with a single-symbol code tree, plus a zero-sized end block. The JSON and POSIX USTAR payloads
are the project-owned #3628 payloads. `backreference.lzh` emits literal `A`, then length-three,
distance-one code 256, and decodes to `AAAA`. `empty.lzh` contains only an end block.

Every file was decoded by GNU gzip 1.15 with fixed arguments `-d -c` and compared byte for byte
with its `.decoded` payload. `provenance.json` records encoded and decoded hashes and sizes.
The reference source archive SHA-256 is
`9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48`.
No GNU gzip source, binary, or third-party corpus data is included.

The block layout was checked against the separately built GNU gzip 1.15 reference decoder and
its `unlzh.c` format implementation. The [GNU gzip manual](https://www.gnu.org/software/gzip/manual/gzip.html)
describes the SCO format's lack of CRC and limited consistency checks. The fixture generator
emits format fields directly and contains no copied GNU gzip implementation code.
