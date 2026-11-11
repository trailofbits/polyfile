# Freeze and gzip 0.5 reference fixtures

The `.F` fixtures use the original freeze 1.1 encoder from the
[November 24, 1990 source posting](https://utzoo.superglobalmegacorp.com/usenet/b190/alt/sources/2631.txt).
`provenance.json` records the source hashes, compiler invocation, fixture hashes, and decoded hashes.
The inputs contain project-owned JSON, a Python-generated USTAR archive, seeded random bytes,
spaces, and repeated `abc` bytes. The encoder can return status 2 when compression expands an
input, even with `-f`; its encoded output is retained and independently verified.

Ancient 2.3.0 verifies these streams against their decoded bytes. The 80,000-byte random fixture
exercises adaptive frequency rebuilding. `initial-spaces.F` exercises references into the initial
space-filled dictionary. `ring-wrap.F` exercises overlapping copies across the 4,096-byte window.
`method-collision.F` starts with `1f 9e 08`, despite being freeze rather than gzip.

`document.gz05` contains Python-generated DEFLATE with gzip framing, CRC32, and decoded size,
using the historical `1f 9e` gzip 0.5 signature. GNU gzip 1.15 independently decodes it to
`document.json`; it is not represented as output from an original gzip 0.5 encoder.
`dual-prefix.F` is the first 37 bytes of that gzip stream. Ancient independently decodes the
complete prefix as freeze, illustrating that a truncated gzip candidate can be a valid freeze file.

The production freeze decoder adapts only the freeze 1.x and adaptive Huffman algorithms from
[Ancient 2.3.0](https://github.com/temisu/ancient/tree/v2.3.0).
Its BSD 2-Clause license is retained in `polyfile/freeze1.py`, including in built distributions.
Neither the reference encoder nor Ancient is a production dependency.
