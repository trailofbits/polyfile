# 7z reference fixtures

These archives contain project-owned JSON, an empty file, a directory, and a ZIP containing
project-owned JSON. They were generated with **7-Zip 26.02 arm64**, dated June 25, 2026.
Every archive passed `7zz t -pfixture-password ARCHIVE`. The password is fixture data.

`provenance.json` records the exact encoder commands and SHA-256 of every committed archive.
Encrypted archives contain randomized salts, so regeneration changes their hashes. Other
archives can also reflect platform-specific attributes; the recorded hashes identify the
tested bytes.

Prepare the source directory with Python 3.13:

```python
from pathlib import Path
from zipfile import ZipFile, ZipInfo

Path("first.json").write_bytes(b'{"first":true}\n')
Path("other.json").write_bytes(b'{"other":true}\n')
Path("empty").write_bytes(b"")
Path("directory").mkdir()
with ZipFile("nested.zip", "w") as archive:
    info = ZipInfo("inside.json", (2026, 11, 16, 10, 21, 2))
    archive.writestr(info, b'{"nested":true}\n')
```

Run each command in `provenance.json` from that directory, placing the resulting archive outside
the source tree. `copy.7z` uses Copy compression and a plain header. `nonsolid.7z` uses independent
LZMA2 folders and a plain header. `solid.7z` combines regular files in one LZMA2 folder and
compresses the header. `empty.7z` contains only the directory and empty file.

Generate `many-empty.7z` separately, from a directory containing only 100 empty files named
`entry-000` through `entry-099`. Its regression constrains the decoder process to 48 descriptors
and allows zero decoded bytes.

Tests derive malformed, duplicated-name, traversal-name, unsupported-codec, nonzero-PackPos,
packed-CRC, and encoded-header-CRC cases from these fixtures in memory. The valid nonzero-PackPos
and empty ArchiveProperties variants were independently accepted by `7zz t` from the same
reference version. No fixture requires extracting archive-controlled paths.
