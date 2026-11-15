# Standalone search and serialization utilities

## Maintenance status

`polyfile.search` and `polyfile.serialization` are retained, tested library utilities.
PolyFile's analyzer and command-line workflows currently have no callers of these modules.
They remain available for direct library use and future integration. Their tests, lint, and type
checks run with the rest of the project.

The modules originated in the TRiD matcher. Trie caching was added on August 28, 2019,
[disabled the following day because rebuilding was faster](https://github.com/trailofbits/polyfile/commit/e51135ebda7c87012399c62df0949602829ae89a),
and the TRiD consumer was [removed on January 19, 2022](https://github.com/trailofbits/polyfile/commit/1f766d9907f34d6872d7f9635bb21d43bebbcc99).
The absence of an internal caller describes their current integration status; it does not mark
them as deprecated or scheduled for removal.

When you change these utilities, preserve their documented behavior and add regression coverage
for library callers. When you integrate them into another PolyFile workflow, update this status
and add a test for that integration. A change to constructor arguments, readable record layouts,
or matching semantics needs an explicit compatibility decision and a changelog entry.

## Search behavior

`MultiSequenceSearch` finds overlapping occurrences of multiple patterns using an Aho–Corasick
trie. Patterns must be hashable sequences, such as `bytes`, `str`, or tuples of hashable symbols.
Sequence-valued symbols, such as words inside a tuple, are treated as individual symbols.
Use a tuple when your original pattern is a list.

```python
from polyfile.search import MultiSequenceSearch

search = MultiSequenceSearch(b"he", b"she", b"hers")
assert sorted(search.search(b"ushers")) == [
    (1, b"she"),
    (2, b"he"),
    (2, b"hers"),
]

words = MultiSequenceSearch(("word", "token"))
assert list(words.search(("a", "word", "token"))) == [(1, ("word", "token"))]
```

Each result contains the zero-based start offset and original matching pattern. Duplicate
patterns produce one result per occurrence. Results follow input-consumption order, so their
start offsets are not necessarily sorted; order among matches completed at the same position
is unspecified. An empty pattern matches every input boundary, including zero and the end.

Inputs can be iterables of symbols, binary streams, or text streams. Stream searches start at
the current cursor, consume through the end, and report offsets relative to that starting
position. Binary offsets count bytes; text offsets count characters; other iterables count
symbols. Searching a stream advances its cursor. Use consistent pattern and input symbol types.

`StartsWithMatcher` reports matching prefixes at offset zero. It reports an empty pattern once.
A stream is consumed through the first mismatching symbol or the end of input.

`TrieNode.add()` associates a path with a hashable source label; an omitted label uses the path
itself. `find()` tests a complete inserted path, and `find_prefix()` yields labels below a prefix.
For existing callers, `in` interprets sequence operands as paths, with a single-symbol operand
testing child presence. Other operands test child keys directly. Use `children` or indexing for
sequence-valued child keys, and `find()` to distinguish inserted paths from prefixes.
Traversals and prefix lookup are iterative,
and `bfs()` and `dfs()` visit each node identity once. Node equality compares values, as before;
traversal identity does not depend on node equality.

`ACNode.finalize()` validates a structural tree and rebuilds parent and failure links. Call it
after manually modifying an Aho–Corasick trie. Shared nodes, cycles, mismatched child symbols,
and non-`ACNode` children are invalid in this structure. `to_dot()` returns escaped Graphviz source
for a subtree; it omits links to nodes outside that subtree and does not invoke a renderer.
Representations summarize nodes without recursively printing parent/failure graphs.

## Saving and loading searches

```python
from io import BytesIO

from polyfile.search import MultiSequenceSearch

search = MultiSequenceSearch(b"ab", b"b")
cache = BytesIO()
search.save(cache)
cache.seek(0)
restored = MultiSequenceSearch.load(cache)
assert sorted(restored.search(b"ab")) == [(0, b"ab"), (1, b"b")]
```

Saving preserves the established five-field `ACNode` record layout: value, source labels,
children, parent, and failure link. The two derived-link fields are written as `None` to avoid
serializing cycles. Loading reconstructs those links from the structural tree. Saving does not
clear or modify the live search's links.

The original `ACNode(value, sources, _children, parent, _fall)` constructor remains available.
Existing acyclic five-field records are readable by the updated loader. New nonempty caches
require the updated loader to rebuild failure links; older readers cannot be assumed to use them
correctly.

The binary codec supports fewer symbol types than in-memory search. A search can be saved only
when its values and source labels use supported encodable types. For example, negative integers
and floating-point symbols can be searched in memory but cannot be encoded by the unsigned codec.
An unsupported value raises `serialization.EncodingError`.

## Binary serialization contract

Use `dump(value, binary_stream)` and `load(binary_stream)` for streams, or `dumps(value)` and
`loads(data)` for byte strings. Records start at the stream's current position. The format is
intended for one complete object graph per stream; `load()` consumes it through the end.

Supported built-in values are `None`, booleans, nonnegative integers, UTF-8 strings, bytes,
lists, tuples, dictionaries, sets, and frozensets. The codec preserves shared object references
within an acyclic graph. Cycles are rejected, and traversal is iterative so deep nesting does
not depend on Python's recursion limit. Negative integers are rejected instead of being silently
changed into positive values. `read_int()` and `write_int()` use the format's unsigned base-128
integer encoding.

A class registered with `@serialization.serializable` supplies `serialize()` arguments for its
constructor. The encoder snapshots those arguments once per object. Re-registering the same
class does not change its identifier. Register the same classes in the same order in every
process that exchanges records: custom class identifiers depend on registration order.
Import `polyfile.search` before registering additional classes when exchanging trie caches.

The record tags and existing readable layouts are retained. Object identifiers and record order
are implementation details; serialized output is not a canonical byte representation. Keep
fixed legacy fixtures in tests when changing the codec so new writers and readers cannot hide
an incompatible change from one another.

Malformed or truncated data, unsupported values, and cyclic graphs raise `EncodingError` with
operation or record context. Stream I/O failures propagate to the caller. Binary streams must
follow Python's `read()`/`write()` contracts.

Load only trusted records. Custom decoding invokes registered constructors; the format does not
provide authentication, a resource budget, or a sandbox for those constructors. It is not an
interchange format for untrusted uploaded files. PolyFile's analysis reports continue to use
`Match.to_obj()`, `Analyzer.sbud()`, and standard JSON serialization independently.

## Regression checks

The regular Python test job includes standalone API tests, bounded cycle/shared-graph checks,
fixed pre-PR cache fixtures, and search/save/load tests. A focused local run is:

```sh
uv run pytest -q -W error tests/test_search_api.py tests/test_search_roundtrip.py \
  tests/test_search_loader.py tests/unit/test_search_contracts.py \
  tests/unit/test_serialization_contracts.py tests/unit/test_serialization_edges.py
```

Run the codec's error and graph tests too when changing serialization. Keep these checks active
while the utilities have no internal callers: application-level scans cannot cover their API.
