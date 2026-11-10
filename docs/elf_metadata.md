# ELF identification metadata

PolyFile adds metadata from ELF headers, program and section tables, and notes to its ELF
identification description. The same description appears in `--format file`,
`polyfile.magic.join_matches`, Python identification results, and the ELF root's SBuD `value`.
The structural `Match.description` attribute carries the enriched description; `Match.match`
retains its original magic test result. Other file formats leave `description` unset.

The metadata reader reuses the existing generated Kaitai ELF layouts. It reads a byte buffer,
so you can identify in-memory data without a file descriptor. The existing Kaitai structure
parser remains registered and produces the ELF structure as before.

## Supported metadata

- ELF32 and ELF64, little-endian and big-endian, including extended header-table counts.
- Static and dynamic linkage, static PIE through `DT_FLAGS_1`, `DT_NEEDED` dependencies,
  and the `PT_INTERP` interpreter string. The existing magic rules retain control of MIME types.
- GNU build IDs, including the usual xxHash, MD5/UUID, SHA-1, and SHA-256 sizes, and Go build IDs.
  Other GNU build-ID lengths retain their bytes with an `unknown` hash description.
- GNU ABI versions for Linux, Hurd, Solaris, kFreeBSD, and kNetBSD; SuSE, NetBSD, FreeBSD,
  OpenBSD, DragonFly, and Android version notes; and Android NDK version/build strings.
- Symbol-table stripping status and `.debug_info`/`.zdebug_info` section presence. A dynamic
  symbol table alone does not make a binary unstripped. Missing tables are described separately.
- Linux/SVR4-style process commands, Linux PIDs for recognized process-info layouts and
  signals from process-status notes, FreeBSD commands/PIDs, and versioned NetBSD process notes
  with process/user/group IDs, thread counts, and available signal details.

## Invalid and unsupported metadata

PolyFile checks table sizes and byte ranges before reading metadata. Invalid tables, missing
interpreter terminators, and truncated notes add diagnostics while preserving the base ELF
classification. Valid metadata from other tables can still appear. Unsupported ELF classes,
byte orders, header versions, padding, and machine values leave the base description unchanged.

ABI-specific core layouts without a recognized process record retain any recognized core-style
label but do not fabricate a command or process ID. Register sets, auxiliary-vector details,
Solaris hardware/software capabilities, PaX flags, GNU properties, Android memory-tagging notes,
and unrecognized vendor notes do not currently add identification text. Their bytes remain
available to structural analysis. Section presence reports debug information; PolyFile does not
interpret DWARF or execute the binary or its interpreter.
