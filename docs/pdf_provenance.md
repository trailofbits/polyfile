# PDF token provenance

Instrumented PDF values carry a lexical location and contributing input intervals separately.
`pdf_location` is a `SourceSpan(source, offset, size)`, or `None` for computed values without a
lexeme. `pdf_dependencies` contains normalized input intervals. The view-relative legacy fields
`pdf_offset` and `pdf_bytes` describe a lexical location only when `pdf_location` is present.
Unattached parser values use `source=None`; mapping binds them to the selected analysis view.
Qualified locations stay in their original source when a value is consumed elsewhere.

Conversions, selection, copying, and pickling preserve this metadata. A transformed value keeps
the complete available input intervals when individual output positions cannot be mapped to
individual source bytes. Concatenation merges lexical locations only for adjacent inputs in the
same source. Adding an untagged prefix retains the available tagged input span without inventing
positions for the prefix. Noncontiguous or cross-source inputs produce a computed value.

Literal and hex strings map their raw bodies, excluding delimiters. Literal names map their
complete lexeme, including `/`; their wrapped name maps the raw body. `PDFLiteral.raw_name`
and dictionary-key `pdf_raw_name` retain the original encoded name bytes, including escapes.
Dictionary lookup uses PDFminer's decoded name or its existing byte-repr fallback for invalid
UTF-8. Shared PDFminer keyword singletons carry no parser-specific positions.

Object-stream values use offsets within a registered `decoded_content` buffer. Their
`pdf_source` identifies that buffer, including for nested values and reference IDs. Physical
stream framing stays in the containing source. Repeated lookups reuse the decoded source;
instrumentation also covers compressed catalogs loaded during document initialization.

Decryption preserves array containers and their original delimiters rather than inferring
their bounds from children. Decrypted strings have a physical `PDFDeciphered` region and a
separate decoded buffer. Empty strings retain native PDFminer behavior, and authentication
failures propagate unchanged.

Hex strings, escaped strings, stream filters, predictors, and decryption recurse into separate
decoded buffers when the output has no direct byte mapping. Opaque transformation dependencies
include the complete tagged input buffers and available tagged parameters. Encryption inputs
include tagged object IDs, generations, identifiers, and encryption dictionary data available at
the adapter boundary. These are conservative input sets, not per-output-byte mappings or a
cryptographic execution trace. Passwords and other untagged inputs have no file span.

## Stream resource controls

Optional stream decoding checks the remaining member allowance and content depth before running
filters. A refused payload retains its dictionary and physical encoded-byte region with
`analysis_status: limited`; the report does not retain its decoded output. Each stream admitted
for decoding consumes one member entry, including when a later decoding stage reports a
limitation or unsupported feature.

`max_member_bytes` bounds each filter or predictor output. `max_total_bytes` bounds the combined
decoded outputs across the analysis, including intermediate filter stages. Completed stages are
charged once before another stage runs; a later failure does not refund bytes already expanded.
Mapping and recursively classifying a prepaid stage do not charge those same bytes again.
Further embedded content consumes its own member and byte allowances. Encoded-byte regions that
are independently passed to recursive matching remain subject to the existing matching budgets.

Flate, LZW, ASCII85, ASCIIHex, and RunLength decoding bound output during expansion. PNG predictor
dimensions and output sizes are checked before their buffers are constructed. CCITT decoding and
stream decryption report `unsupported` when a decoded-byte bound is requested because their
current backends cannot honor it. Without byte bounds, their existing backend behavior applies.
JPEG, JPEG 2000, and JBIG2 stream filters continue to pass their encoded image bytes through.

Cross-reference and object streams are structural inputs, including when a compressed catalog
requires an object stream during document initialization. A type label alone does not make an
unused stream a required structural input. Structural reads respect member and byte budgets,
and repeated lookups reuse the stream's admission and decoded bytes even with document caching
disabled. Reading structural objects does not add an optional-content depth transition. Recursive
classification and emission of those decoded objects still respect content depth. If required
structural decoding is refused, the report retains the physical objects and stream framing that
the parser has already located, with an explicit limitation status.

These controls bound decoded content, rather than the PDF parser's input storage or total Python
heap. Source coordinates and dependency tracking remain unchanged for admitted content.

## Arithmetic and report dependencies

Numeric `+`, `-`, `*`, `/`, `//`, and `%`, reflected forms, and unary `+`, `-`, and `abs()` retain
all tagged operands' dependencies. Operations preserve Python values, exceptions, and reflected
dispatch. They do not infer a lexical location for the result. Integer powers, bit operations,
comparisons, formatting, arbitrary native methods, and caller code outside these hooks use
native behavior and do not promise tracking.

Reports add optional `dependencies` entries using the existing `source`, `offset`, and `size`
vocabulary. Overlapping or adjacent intervals merge only within one source; disjoint ranges and
source boundaries remain separate. Computed elements have size zero at their consuming parent
and carry their inputs through `dependencies`. This anchor is not a claim that input bytes occur
at the parent's position. Lexical elements retain their usual location fields. Existing viewers
continue to highlight lexical regions; dependency visualization is not implemented.

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
location, dependencies, nonlinear mapping state, and transformation attributes. Arrays and
dictionaries retain their recorded delimiter spans and support recursive container reconstruction.

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

These guarantees cover the structural parser paths PolyFile executes and the operations listed
above. PDFminer graphics and layout computations fall outside this structural adapter's executed
paths. Normalized builtins and arbitrary external code can discard metadata.
