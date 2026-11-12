# Custom magic compatibility

PolyFile follows the pinned libmagic 5.48 definitions and matching rules. The cases below resolve
the custom-definition catalogue in [issue #3576](https://github.com/trailofbits/polyfile/issues/3576).
They cover declarations that the bundled definitions do not exercise, plus the one-byte fallback.

## Supported declarations

You can separate modifier groups with slashes and place ranges before or after flag groups.
For example, `string/W/c`, `search/40c/f`, `search/c/40/f`, and `regex/C/40/c` load successfully.
Ranges use decimal, octal, or hexadecimal notation; the last declared range takes precedence.
A zero range keeps the type's default bound.
Empty modifier groups, trailing slashes, and invalid flags raise a definition error.

`regex/c` and `regex/C` both enable ASCII case-insensitive matching. Their distinct modifier bits
remain part of the canonical type and sorting metadata.

`pstring` honors `t` and `b`, including both flags together. The last length modifier among `B`,
`H`, `h`, `L`, and `l` determines the prefix width and byte order.

A bare `regex/l` imposes no line-count limit. The normal 8 KiB regex byte limit still applies.
An explicit count, such as `regex/100l`, retains its line-count and byte limits.

## Values and file boundaries

A top-level one-byte input reports `very short file (no magic)` with MIME type
`application/octet-stream`, before any custom definition runs. An `indirect` continuation still
runs soft magic against a one-byte embedded buffer.

A wildcard `search` value extends through carriage returns and line feeds, stopping at the first
NUL or the end of the buffer. Its range limits candidate start offsets rather than the reported
value's length. `T` strips surrounding whitespace from the printed value. An unflagged wildcard
search runs in the text pass, so a text verdict includes its encoding description.

## Intentional differences

| Catalogue case | PolyFile behavior | Reason |
|---|---|---|
| Multi-byte `pstring` equality | Actual content. | Avoid stale tail bytes. |
| Locale sensitivity | ASCII case and C-locale whitespace. | Stable across locales. |
| Truncated UTF-8 | Binary. | Incomplete sequences are invalid UTF-8. |
| Leading regex `^` | Anchor. | Preserve direct regex anchoring. |

For portable regex definitions, write an explicit equality relation before an anchor, such as
`0 regex =^target found`.

The corresponding reference rules are in libmagic's
[modifier and pass parser](https://github.com/file/file/blob/FILE5_48/src/apprentice.c),
[soft magic matcher](https://github.com/file/file/blob/FILE5_48/src/softmagic.c),
and [file-buffer dispatcher](https://github.com/file/file/blob/FILE5_48/src/funcs.c).
