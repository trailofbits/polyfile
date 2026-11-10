# Zlib streams

PolyFile recursively analyzes validated `application/zlib` streams with Python's built-in
zlib decoder. The structural view retains the CMF/FLG header, compressed bytes, and Adler-32
checksum. Decoded bytes use their own byte source and offsets.

A zlib stream contains one compressed stream. Unexpected trailing bytes, incomplete streams,
invalid header fields, and checksum failures produce an invalid analysis status without
decoded children. Preset-dictionary streams retain their dictionary identifier and an unsupported
status because PolyFile does not supply external dictionaries.

Analysis has no configured resource limits by default. The analysis limit options can cap
decoded output, cumulative child-content bytes, recursion, member count, and codec memory.
The zlib adapter requires a conservative 64 KiB codec-memory allowance when that limit is set;
this describes decoder state rather than total process memory.
