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
  "fileName": "The input filename, or 'STDIN' if the file was read from STDIN",
  "length": 1337, /* integer number of bytes in the file */
  "struc": [
    /* SBuD does not use a list here; there is just one element   *
     * PolyFile uses a list to enable labeling multiple filetypes *
     * in the case of a polyglot                                  */
    {
      "name":   "ADOBE_PDF",  /* the filetype                     */
      "offset": 0,            /* the offset of this file object   *
                               * within the input file            */
      "subEls": [
        /* sub-elements of this filetype                          */
        {
          "offset": 0         /* once again, the global offset    */
          "relative_offset: 0 /* the offset of this element       *
                               * relative to its parent           */
          "name": "header"    /* a descriptive element name       */
          "type": "magic"     /* the type of this element         */
          "size": 9           /* size of the element in bytes     */
          "value": "%PDF1.3\n"
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