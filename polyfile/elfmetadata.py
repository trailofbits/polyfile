"""ELF identification metadata from the existing Kaitai header and table layouts."""

import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from kaitaistruct import KaitaiStructError

from polyfile.kaitai.parsers.elf import Elf


class _Program(Protocol):
    type: int
    ofs_body: int
    len_body: int
    align: int


class _Section(_Program, Protocol):
    ofs_name: int
    linked_section_idx: int
    info: int


class _Header(Protocol):
    e_type: int
    e_version: int
    e_ehsize: int
    machine: int
    ofs_program_headers: int
    ofs_section_headers: int
    program_header_size: int
    num_program_headers: int
    section_header_size: int
    num_section_headers: int
    section_names_idx: int
    program_headers: Sequence[_Program]
    section_headers: Sequence[_Section]


class _Elf(Protocol):
    bits: int
    endian: int
    header: _Header


@dataclass(frozen=True)
class _View:
    data: bytes
    elf: _Elf

    @property
    def order(self) -> str:
        return "<" if self.elf.endian == 1 else ">"

    @property
    def wide(self) -> bool:
        return self.elf.bits == 2


@dataclass(frozen=True)
class _Note:
    owner: bytes
    kind: int
    data: bytes


def _load(data: bytes) -> _View | None:
    if len(data) < 16 or data[:4] != b"\x7fELF":
        return None
    if data[4] not in (1, 2) or data[5] not in (1, 2):
        return None
    try:
        parsed = Elf.from_bytes(data)
        parsed._read()
        elf = cast(_Elf, parsed)
        if elf.header.e_version != 1 or elf.header.e_ehsize != (64 if elf.bits == 2 else 52):
            return None
        return _View(data, elf)
    except (EOFError, ValueError, KaitaiStructError):
        return None


def _region(data: bytes, offset: int, size: int) -> bytes | None:
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        return None
    end = offset + size
    return data[offset:end]


def _extended_counts(view: _View, errors: list[str]) -> None:
    header = view.elf.header
    if not header.ofs_section_headers:
        return
    if (
        header.num_section_headers
        and header.num_program_headers != 0xFFFF
        and header.section_names_idx != 0xFFFF
    ):
        return
    size = 64 if view.wide else 40
    data = _region(view.data, header.ofs_section_headers, size)
    if data is None or header.section_header_size != size:
        errors.append("invalid or truncated ELF section header table")
        return
    values = struct.unpack(view.order + ("IIQQQQIIQQ" if view.wide else "10I"), data)
    if header.num_section_headers == 0:
        header.num_section_headers = values[5]
    if header.num_program_headers == 0xFFFF:
        header.num_program_headers = values[7]
    if header.section_names_idx == 0xFFFF:
        header.section_names_idx = values[6]


def _valid_table(view: _View, values: tuple[int, int, int], expected: int) -> bool:
    offset, size, count = values
    return (
        size == expected
        and 0 < offset <= len(view.data)
        and (count <= (len(view.data) - offset) // expected)
    )


def _programs(view: _View, errors: list[str]) -> Sequence[_Program] | None:
    header = view.elf.header
    if not header.num_program_headers:
        return ()
    values = header.ofs_program_headers, header.program_header_size, header.num_program_headers
    if not _valid_table(view, values, 56 if view.wide else 32):
        errors.append("invalid or truncated ELF program header table")
        return None
    return header.program_headers


def _sections(view: _View, errors: list[str]) -> Sequence[_Section] | None:
    header = view.elf.header
    if not header.num_section_headers:
        if header.ofs_section_headers:
            errors.append("invalid or truncated ELF section header table")
            return None
        return ()
    values = header.ofs_section_headers, header.section_header_size, header.num_section_headers
    if not _valid_table(view, values, 64 if view.wide else 40):
        errors.append("invalid or truncated ELF section header table")
        return None
    return header.section_headers


def _string(data: bytes) -> str:
    value = data.split(b"\0", 1)[0].decode("utf-8", errors="backslashreplace")
    return "".join(char if char.isprintable() else f"\\{ord(char):03o}" for char in value)


def _read_notes(
    data: bytes, order: str, align: int, errors: list[str]
) -> Iterator[tuple[int, int, _Note]]:
    offset = 0
    while offset < len(data):
        if len(data) - offset < 12:
            if any(data[offset:]):
                errors.append("truncated ELF note")
            return
        namesize, descsize, kind = struct.unpack_from(order + "III", data, offset)
        name_offset = offset + 12
        desc_offset = (name_offset + namesize + align - 1) & -align
        end = desc_offset + descsize
        if end > len(data):
            errors.append("truncated ELF note")
            return
        name_end = name_offset + namesize
        next_offset = (end + align - 1) & -align
        note = _Note(data[name_offset:name_end].rstrip(b"\0"), kind, data[desc_offset:end])
        yield offset, end, note
        offset = next_offset


def _covered_note_end(covered: dict[tuple[int, int], int], start: int, align: int) -> int:
    offsets: list[int] = []
    end = start
    while covered.get((end, align), end) > end:
        offsets.append(end)
        end = covered[end, align]
    for offset in offsets:
        covered[offset, align] = end
    return end


def _notes(view: _View, records: Sequence[_Program], errors: list[str]) -> Iterator[_Note]:
    covered: dict[tuple[int, int], int] = {}
    boundaries: set[tuple[int, int]] = set()
    for record in sorted(records, key=lambda item: (item.ofs_body, -item.len_body)):
        align = record.align
        if align not in (0, 1, 4, 8):
            errors.append("invalid ELF note alignment")
        align = 8 if align == 8 else 4
        start, end = record.ofs_body, record.ofs_body + record.len_body
        previous_end = _covered_note_end(covered, start, align)
        if previous_end >= end and start < end:
            if (end, align) not in boundaries:
                errors.append("truncated ELF note")
            continue
        start = previous_end
        data = _region(view.data, start, end - start)
        if data is None:
            errors.append("invalid or truncated ELF note region")
            continue
        starts = [record.ofs_body]
        parsed_end = start
        for offset, note_end, note in _read_notes(data, view.order, align, errors):
            starts.append(start + offset)
            parsed_end = min(start + ((note_end + align - 1) & -align), end)
            boundaries.update((value, align) for value in range(start + note_end, parsed_end + 1))
            yield note
        for offset in starts:
            covered[offset, align] = max(covered.get((offset, align), offset), parsed_end)


def _build_id(note: _Note) -> str | None:
    if note.owner == b"GNU" and note.kind == 3 and note.data:
        label = {8: "xxHash", 16: "md5/uuid", 20: "sha1", 32: "sha256"}.get(
            len(note.data), "unknown"
        )
        return f"BuildID[{label}]={note.data.hex()}"
    if note.owner == b"Go" and note.kind == 4:
        return f"Go BuildID={_string(note.data)}"
    return None


def _netbsd_version(version: int) -> str:
    if version <= 100000000:
        return "for NetBSD"
    major, minor = version // 100000000, version // 1000000 % 100
    release, patch = version // 10000 % 100, version // 100 % 100
    if major >= 9:
        patch += release * 100
        release = 0
    suffix = ""
    if release:
        suffix = "Z" * ((release - 1) // 26) + chr(65 + (release - 1) % 26)
    elif patch:
        suffix = f".{patch}"
    return f"for NetBSD {major}.{minor}{suffix}"


def _freebsd_version(version: int) -> str:
    if version == 460002:
        return "for FreeBSD 4.6.2"
    major = version // 100000
    if version < 460100:
        minor = version // 10000 % 10
        patch = version // 1000 % 10
        suffix = f".{patch}" if patch else ""
        if version % 1000 or not version % 100000:
            suffix += f" ({version})"
    else:
        minor = version // 1000 % 100
        if version < 500000:
            minor = version // 10000 % 10 + version // 1000 % 10
        suffix = f" ({version})" if version // 100 % 10 or not version % 100000 else ""
        if not suffix and version // 10 % 10:
            suffix = f".{version // 10 % 10}"
    return f"for FreeBSD {major}.{minor}{suffix}"


def _os_note(note: _Note, order: str) -> str | None:
    if note.kind != 1:
        return None
    if note.owner == b"GNU" and len(note.data) == 16:
        os, major, minor, patch = struct.unpack(order + "4I", note.data)
        name = {0: "Linux", 1: "Hurd", 2: "Solaris", 3: "kFreeBSD", 4: "kNetBSD"}
        return f"for GNU/{name.get(os, '<unknown>')} {major}.{minor}.{patch}"
    if note.owner == b"SuSE" and len(note.data) == 2:
        return f"for SuSE {note.data[0]}.{note.data[1]}"
    if len(note.data) < 4:
        return None
    version = struct.unpack_from(order + "I", note.data)[0]
    render = {b"NetBSD": _netbsd_version, b"FreeBSD": _freebsd_version}
    if note.owner in render and len(note.data) == 4:
        return render[note.owner](version)
    return _other_os_note(note, version)


def _other_os_note(note: _Note, version: int) -> str | None:
    if note.owner == b"OpenBSD" and len(note.data) == 4:
        return "for OpenBSD"
    if note.owner == b"DragonFly" and len(note.data) == 4:
        return f"for DragonFly {version // 100000}.{version // 10000 % 10}.{version % 10000}"
    if note.owner == b"Android":
        text = f"for Android {version}"
        if len(note.data) >= 132:
            text += f", built by NDK {_string(note.data[4:68])} ({_string(note.data[68:132])})"
        return text
    return None


def _dynamic(view: _View, programs: Sequence[_Program], errors: list[str]) -> tuple[bool, bool]:
    pie = needed = False
    for program in programs:
        if program.type != 2:
            continue
        data = _region(view.data, program.ofs_body, program.len_body)
        size = 16 if view.wide else 8
        if data is None or len(data) % size:
            errors.append("invalid or truncated ELF dynamic table")
            continue
        table_pie = table_needed = False
        for offset in range(0, len(data), size):
            tag, value = struct.unpack_from(
                view.order + ("QQ" if view.wide else "II"), data, offset
            )
            if tag == 0:
                pie |= table_pie
                needed |= table_needed
                break
            table_needed |= tag == 1
            table_pie |= tag == 0x6FFFFFFB and bool(value & 0x08000000)
        else:
            errors.append("unterminated ELF dynamic table")
    return pie, needed


def _linkage(view: _View, programs: Sequence[_Program], errors: list[str]) -> list[str]:
    if not programs:
        return ["no program header"]
    pie, needed = _dynamic(view, programs, errors)
    interpreters = [record for record in programs if record.type == 3]
    dynamic = any(record.type == 2 for record in programs)
    linkage = "dynamically" if dynamic else "statically"
    if dynamic and pie and not needed and not interpreters:
        linkage = "static-pie"
    details = [f"{linkage} linked"]
    for record in interpreters:
        data = _region(view.data, record.ofs_body, record.len_body)
        if data is None or not data or data[-1] != 0:
            errors.append("invalid or truncated ELF interpreter")
        else:
            details.append(f"interpreter {_string(data) or '*empty*'}")
    return details


def _section_state(view: _View, sections: Sequence[_Section], errors: list[str]) -> list[str]:
    if not sections:
        return ["no section header"]
    names = b""
    index = view.elf.header.section_names_idx
    if 0 < index < len(sections):
        table = sections[index]
        value = _region(view.data, table.ofs_body, table.len_body)
        if value is not None:
            names = value
        else:
            errors.append("invalid or truncated ELF section name table")
    elif index:
        errors.append("invalid ELF section name table index")
    debug = False
    for section in sections:
        offset = section.ofs_name
        if names.startswith((b".debug_info\0", b".zdebug_info\0"), offset):
            debug = True
    stripped = not debug and not any(section.type == 2 for section in sections)
    return (["with debug_info"] if debug else []) + ["stripped" if stripped else "not stripped"]


def _core_command(view: _View, note: _Note) -> list[str]:
    if note.kind != 3:
        return []
    if note.owner == b"FreeBSD":
        offset = 33 if view.wide else 25
        if len(note.data) < offset + 81:
            return []
        end = offset + 80
        parts = [_core_origin(note.data[offset:end])]
        if len(note.data) >= offset + 87:
            pid = struct.unpack_from(view.order + "I", note.data, offset + 83)[0]
            parts.append(f"pid={pid}")
        return parts
    layouts = {136: (56,)} if view.wide else {124: (44,), 128: (48,)}
    offsets = layouts.get(len(note.data), (136, 152) if view.wide else (100, 104))
    for offset in offsets:
        if offset >= len(note.data):
            continue
        end = offset + 80
        command = note.data[offset:end].split(b"\0", 1)[0].rstrip()
        if command and all(32 <= value < 127 for value in command):
            return [_core_origin(command), *_linux_pid(view, note)]
    return []


def _core_origin(data: bytes) -> str:
    command = _string(data).replace("'", "\\'")
    return f"from '{command}'"


def _linux_pid(view: _View, note: _Note) -> list[str]:
    offsets = {136: 24} if view.wide else {124: 12, 128: 16}
    if len(note.data) not in offsets:
        return []
    pid = struct.unpack_from(view.order + "I", note.data, offsets[len(note.data)])[0]
    return [f"pid={pid}"]


def _netbsd_core(view: _View, note: _Note) -> list[str]:
    if note.kind != 1 or len(note.data) < 156:
        return []
    values = struct.unpack_from(view.order + "31I", note.data)
    if values[0] != 1 or not 156 <= values[1] <= len(note.data):
        return []
    details = [
        _core_origin(note.data[124:156]),
        f"pid={values[20]}",
        f"uid={values[25]}",
        f"gid={values[28]}",
        f"nlwps={values[30]}",
    ]
    if values[1] >= 160:
        details.append(f"lwp={struct.unpack_from(view.order + 'I', note.data, 156)[0]}")
    details.append(f"signal {values[2]}/code {values[3]}")
    return details


def _core_note(view: _View, note: _Note) -> list[str]:
    if note.owner.startswith(b"NetBSD-CORE"):
        return ["NetBSD-style", *_netbsd_core(view, note)]
    if note.owner == b"FreeBSD":
        return ["FreeBSD-style", *_core_command(view, note)]
    if note.owner not in (b"CORE", b"LINUX"):
        return []
    parts = ["SVR4-style", *_core_command(view, note)]
    if note.kind == 1 and len(note.data) >= 14:
        signal = struct.unpack_from(view.order + "H", note.data, 12)[0]
        if signal:
            parts.append(f"signal {signal}")
    return parts


def describe_elf(data: bytes, description: str) -> str:
    """Appends validated ELF metadata to an existing identification description.

    Args:
        data: The bytes classified by the magic matcher.
        description: The description that the ELF magic rules produced.

    Returns:
        The enriched description, or the original when the ELF header is unsupported or invalid.
        Invalid tables and notes add diagnostics without removing the underlying classification.
    """
    if not description.startswith("ELF "):
        return description
    view = _load(data)
    if view is None:
        return description
    errors: list[str] = []
    _extended_counts(view, errors)
    programs, sections = _programs(view, errors), _sections(view, errors)
    records = [record for record in programs or () if record.type == 4]
    records.extend(record for record in sections or () if record.type == 7)
    details: list[str] = []
    for note in _notes(view, records, errors):
        if view.elf.header.e_type == 4:
            details.extend(_core_note(view, note))
        else:
            details.extend(part for part in (_build_id(note), _os_note(note, view.order)) if part)
    if view.elf.header.e_type in (2, 3) and programs is not None:
        details.extend(_linkage(view, programs, errors))
    if view.elf.header.e_type != 4 and sections is not None:
        details.extend(_section_state(view, sections, errors))
    return description + "".join(f", {part}" for part in dict.fromkeys([*details, *errors]))
