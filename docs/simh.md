# SIMH tape images

PolyFile identifies SIMH tape images as `application/SIMH-tape-data` and maps each record's
length word, flags, payload, odd-byte padding, and trailing length word. Tape marks and the
end-of-medium marker remain separate physical regions.

A tape record can be a fragment of a file. PolyFile classifies each record payload's bytes and recursively
parses any independently recognized formats; it does not combine adjacent records into files.
Unrecognized payloads retain their generic data classification. Records carrying the tape error flag retain their physical structure and an invalid
analysis status without recursive payload analysis.

Detection follows libmagic's native record probe. An image with a valid complete record can
still be identified when a later record is truncated. Its structural analysis preserves the
complete preceding records and reports the incomplete region as invalid. All-zero buffers
containing only tape marks are not identified as tape images.

Recursive analysis has no configured limits by default. Use the analysis limit options to
bound record counts, recursive depth, member bytes, or cumulative recursively analyzed bytes.
