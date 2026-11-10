# PolyFile Output Format

PolyFile outputs its mapping to STDOUT in a JSON schema extended from the the [SBuD](https://github.com/corkami/sbud) format.

The following gives examples of the format.
Notes, additions to SBuD, as well as any breaking changes are listed in C-style comments.

## Annotated Example

```javascript
{
  "MD5": "MD5 hex string of the input file", 
  "SHA1": "SHA1 hex string for the input file", 
  "SHA256": "SHA256 hex string for the input file", 
  "b64contents": "base64 encoded contents of the input file", 
  /* the b64contents key is absent when PolyFile runs with --no-contents */
  "fileName": "The input filename, or 'STDIN' if the file was read from STDIN",
  "length": 1337, /* integer number of bytes in the file */
  "struc": [
    /* SBuD does not use a list here; there is just one element   *
     * PolyFile uses a list to enable labeling multiple filetypes *
     * in the case of a polyglot                                  */
    {
      "name":   "ADOBE_PDF",  /* the filetype                     */
      "source": "file",       /* the buffer containing this node  */
      "offset": 0,            /* the offset within that buffer    */
      "subEls": [
        /* sub-elements of this filetype                          */
        {
          "source": "file",  /* inherited by ordinary children   */
          "offset": 0         /* the offset within this source    */
          "relative_offset: 0 /* the offset of this element       *
                               * relative to its parent           */
          "name": "header"    /* a descriptive element name       */
          "type": "magic"     /* the type of this element         */
          "size": 9           /* size of the element in bytes     */
          "value": "%PDF1.3\n" /* the content of this element,    *
                                * omitted when the element has    *
                                * none of its own; see below      */
          "img_data": "Optional base64 encoded image" /* not in SBud */ 
          "subEls": [
            /* any child elements, in the same format */
          ]
        }
      ] 
    }
    /* additional dictionaries will be included here              *
     * if the file is a polyglot                                  */
  ]
}
```

## Element values

`value` holds the content that an element describes, rendered as a string. What the rendering
looks like depends on what the element matched: a text description for a file type, a Python
byte-string literal such as `b'PK\x03\x04'` for a raw byte field, or a decimal number for an
integer field.

An element that describes no content of its own omits `value` entirely. Structural elements are
the case that arises in practice: a ZIP `LocalFileHeader` spans its fields and nothing else, so
its child elements carry every byte it covers and there is nothing left for it to report. Read
`value` with a default rather than by direct subscript.

PolyFile 0.5.6 and earlier gave such an element the Python `repr` of the internal object that
produced it, which embedded a heap address and so differed between runs over the same input.

## Incomplete content analysis

An element can include `analysis_status` and `analysis_message` when content analysis cannot
complete. Statuses are `invalid` for malformed input, `unsupported` for a recognized feature the
parser cannot process, and `limited` when an explicitly configured resource limit stops work.
The message gives the reason. These fields are absent when no such condition is reported;
the element's existing structure and classification remain available.

## Physical and decoded sources

Every element has a `source` identifier. `file` refers to the original input in `b64contents`.
Offsets and sizes always refer to bytes in the named source. A child with the same source has an
`offset` equal to its parent's offset plus its `relative_offset`.

Decompression creates a `decoded_content` child with a new source, such as `decoded:0`, offset
zero, and the size of the decoded buffer. Its `decoded` field contains that buffer as base64.
Its parent describes the physical encoded region, while its children describe the decoded bytes.
At a source boundary, `relative_offset` is relative to the new buffer's origin, not the parent.
Source identifiers are deterministic within an analysis; a nested decoder creates another source.

This changes earlier output, which added decoded offsets to the containing compressed region's
physical offset. Consumers must use `(source, offset)` to identify a byte location. HTML highlights,
downloads, and coverage use the selected source. The source selector lets you inspect the original
input and each decoded buffer separately.

Gzip analysis preserves headers, optional fields, compressed bodies, and trailers for each member.
It validates header checksums, payload CRCs, and decoded sizes before analyzing the concatenated
decoded content. Zero padding is preserved; other trailing data reports an invalid stream without
publishing decoded children. Configured output, member, depth, and codec-memory limits report
`limited` instead. All limits are unlimited by default; codec-memory limits govern decoder state,
not the total memory used by the Python process or report.

When a container has already analyzed a member's contents, the raw encoded region can retain
its own format labels without repeating the same recursive expansion. For example, a ZIP bzip2
member keeps its raw bzip2 classification while the validated decoded tree appears once under
the ZIP member's decoded-content region. Other raw polyglot interpretations remain eligible
for their own parsers.

LZ4 analysis supports modern frames, concatenated frames, and skippable metadata frames. Header,
block, and content checksums are validated before decoded children are published. Legacy frames
and nonzero external dictionary IDs report `unsupported`; a zero dictionary ID needs no dictionary.
The required `lz4==4.4.5` dependency supplies bounded incremental decoding on supported Python
runtimes. No external decoder command is needed.

For LZ4, `--max-codec-memory` is checked before decompression against a conservative native-buffer
allowance: twice the frame's maximum block size, 128 KiB for linked-block history when present,
and 4 KiB for context metadata. Output and frame-count limits apply across concatenated and
skippable frames. All limits remain unlimited by default.

The buffer allowance follows the
[LZ4 frame decoder's input, output, and history allocations](https://github.com/lz4/lz4/blob/v1.9.4/lib/lz4frame.c).
