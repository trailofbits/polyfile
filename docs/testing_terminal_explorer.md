# Use and test the terminal explorer

Run the explorer with a named file:

```console
polyfile --explore archive.zip
```

PolyFile shows its normal scan progress, completes the analysis, and opens the explorer. You can
inspect the structure tree beside the byte pane in a wide terminal. Narrow terminals show one pane
at a time; press **F2** to switch. Smaller terminal heights reduce the details panel to preserve
space for visible bytes.

The explorer requires stdin, stdout, and stderr to be attached to an interactive terminal. It does
not accept piped contents, redirected streams, image previews, or simultaneous batch output. Run
`--format html` separately when you need a standalone report with image previews. Do not combine
`--explore` with output, listing, debugger, version-only, or `--no-contents` options.

Existing matcher selection, `--only-match`, recursive analysis limits, `--max-matches`, and
`--require-match` apply. If you retain an interrupted scan or stop at a match limit, the title
identifies partial analysis. Parser failures and unsupported features remain visible on their
structure nodes.

## Navigate structure and bytes

Every offset belongs to the source named beside it. The `file` source refers to the original input.
Decoded archive members, PDF streams, and other decoded data have independent source identifiers
and offsets. Selecting a decoded node switches to its own bytes. It does not interpret a decoded
offset as an offset in compressed input.

Select a structure node to reveal and highlight its bytes. Move the byte cursor to inspect every
containing interpretation through **Reveal a containing node**. Hex mode shows hex bytes beside
ASCII; text mode displays UTF-8 while preserving byte offsets for multibyte characters. Invalid
sequences and control characters remain visible. Dim, underlined bytes have no describing leaf
node. Yellow bytes and structure labels match the active search.

| Control | Action |
| --- | --- |
| Tab / Shift+Tab | Move between controls |
| Tree arrows / Enter | Expand, collapse, navigate, or inspect a node |
| Byte arrows | Move the byte cursor |
| Shift+arrows / mouse drag | Select a byte range |
| Home / End | Move to the first / last byte in the row |
| Ctrl+Home / Ctrl+End | Move to the first / last byte in the source |
| Page Up / Page Down | Move a page of bytes |
| g | Go to a decimal or `0x` hexadecimal byte offset |
| t | Switch hex and UTF-8 text views |
| s | Focus the source selector |
| F2 | Switch structure and byte panes |
| F1 | Open keyboard help |
| q / Ctrl+Q | Exit the explorer |
| Ctrl+C | Interrupt and exit with status 130 |

## Search

Press **/** to focus search. Choose **Combined**, **Text**, **Hex bytes**, or **Structure** and
**All sources** or **Current source**. Combined search is the default and merges identical byte
ranges found through multiple search kinds. Results are ordered by source, offset, and length;
the original file precedes decoded sources.

Text queries search UTF-8 bytes. Case-insensitive text and structure queries fold ASCII letters;
they do not apply Unicode case folding. Hex queries accept byte pairs, optional leading `0x`, and
whitespace, such as `0x48 65 6c 6c 6f`. Structure queries search node names, types, analysis status,
and status messages. Unavailable decoded buffers retain searchable structure metadata, and the
search status identifies unavailable buffers.

Use **n** / **Shift+N**, the arrow buttons, or **Enter** / **Shift+Enter** in search to navigate
results. Navigation wraps, switches sources, reveals matching structure, and selects the result's
exact byte range. Manually switching sources reruns a current-source query and preserves an
all-source query. Clearing the query removes its highlights. Search work runs in the background;
changing the query cancels obsolete work. **Ctrl+G** cancels active background work.

## Extract and copy bytes

Press **e** to export the selection or **Shift+E** to export the complete active source. Enter the
destination path explicitly; PolyFile never derives a path from an archive member's name. Confirm
replacement when a destination exists. The analyzed input, its symlinks, and its hard links cannot
be export destinations.

Extraction writes exact binary bytes from the selected source, including decoded content. It
publishes the destination after writing succeeds. Cancelling with **Ctrl+G**, or a read or write
failure before publication, preserves existing destination contents.

Press **o** to prepare the selected offset or **y** to prepare selected bytes as space-separated
hexadecimal. A read-only dialog keeps the text available for terminal selection. Its **Copy to
clipboard** button requests terminal clipboard integration; support depends on the terminal. You
can use the terminal's own selection and copy command when integration is unavailable.

## Development checks

Install the development dependencies in a checkout with initialized submodules:

```bash
uv venv --python 3.13
uv pip install -e '.[dev,viewer-test]'
```

Run the explorer's source, rendering, headless UI, command-line, and terminal lifecycle tests:

```bash
uv run pytest -q tests/unit/test_explorer_model.py tests/unit/test_explorer_rendering.py \
    tests/unit/test_explorer_app.py tests/unit/explorer \
    tests/test_explorer_cli.py tests/test_explorer_terminal.py
```

Textual Pilot tests run headlessly without a terminal or additional test plugin. They exercise
selection, source transitions, search cancellation and stale results, extraction prompts, clipboard
text, and narrow layouts. Source tests use a large sparse file to verify bounded reads; extraction
tests verify decoded ZIP bytes and destination preservation. PTY tests check terminal settings,
signal cleanup, and ordinary exit. PTY tests skip on platforms without POSIX terminal support.

Run Ruff, blocking Flake8, `ty check --error-on-warning`, and `prek run` before committing. For a
manual check, open a ZIP containing text or a PDF containing decoded streams, select decoded nodes,
search across sources, switch panes in an 80-column terminal, export a range, and verify the output
bytes. Exit with **q** and verify that the shell's input echo and cursor return.
