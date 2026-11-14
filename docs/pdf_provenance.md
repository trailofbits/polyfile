# PDF token provenance

Instrumented PDF values retain their original byte spans through supported conversions,
selection, copying, and pickling. A transformed value keeps the complete available input span
when individual output positions cannot be mapped to individual source bytes.

Literal and hex strings map their raw bodies, excluding delimiters. Literal names map their
complete lexeme, including `/`; their wrapped name maps the raw body. `PDFLiteral.raw_name`
and dictionary-key `pdf_raw_name` retain the original encoded name bytes, including escapes.
Dictionary lookup uses PDFminer's decoded name or its existing byte-repr fallback for invalid
UTF-8. Shared PDFminer keyword singletons carry no parser-specific positions.

Object-stream values use offsets within a registered `decoded_content` buffer. Their
`pdf_source` identifies that buffer, including for nested values and reference IDs. Physical
stream framing stays in the containing source. Repeated lookups reuse the decoded source;
instrumentation also covers compressed catalogs loaded during document initialization.

## Conversion boundaries

Python normalizes `int()`, `float()`, and `operator.index()` results to native numbers.
`as_int()` and `as_float()` preserve token spans when subsequent structure mapping needs them.
Native conversion protocols retain Python's value and error behavior.

Supported token `str()` conversions return positioned `PSStr` values. Numeric and byte-repr
conversions keep conservative whole-token spans. Report serialization converts these values to
plain text and stores their location separately. `bytes(PSBytes)` retains the byte token;
`bytes(PSInt)` uses Python's zero-filled count semantics and retains the integer's whole span.
Text requires an explicit encoding, and floating-point values cannot be converted to bytes.

Copies and pickle protocols 0 through the current highest protocol preserve the wrapper family,
span, nonlinear mapping state, and transformation attributes. Arrays and dictionaries retain
their recorded delimiter spans and support recursive container reconstruction.

## Index audit

The structural adapter distinguishes selected values from control inputs:

- Sequence selection normalizes an index once, then derives the returned value's provenance
  from the selected source bytes or the selected container element.
- Split limits, seeks, iteration bounds, and object-cache indexes are control inputs. They use
  native integers; their conversion does not replace the original mapped token.
- Cross-reference row cells use explicit `as_int()` conversion because their returned values
  are subsequently emitted as positioned structure.
- Indirect-reference construction retains the parsed object ID for the reference span.
  PDFminer lookup conversions operate on the lookup key, not the emitted reference.
- Lexer numeric constructors produce native numbers; the token attachment hook records their
  lexical span before the values enter the structural parser.

These guarantees cover the structural parser paths PolyFile executes. Primitive wrappers alone
do not track arbitrary arithmetic or preserve metadata through normalized builtins in caller code.
