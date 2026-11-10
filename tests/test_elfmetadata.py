"""Behavioral coverage for native ELF identification metadata."""

import contextlib
import io
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from polyfile.__main__ import main
from polyfile.elfmetadata import describe_elf
from polyfile.magic import MagicMatcher, TestResult, join_matches
from polyfile.polyfile import Matcher

Program = tuple[int, bytes]
Section = tuple[str, int, bytes]


def note(owner: bytes, kind: int, data: bytes | bytearray, order: str = "<") -> bytes:
    owner += b"\0"
    result = struct.pack(order + "III", len(owner), len(data), kind) + owner
    result += b"\0" * (-len(result) % 4)
    result += data
    return result + b"\0" * (-len(result) % 4)


def _program(kind: int, offset: int, size: int, bits: int, order: str) -> bytes:
    if bits == 64:
        return struct.pack(order + "II6Q", kind, 4, offset, 0, 0, size, size, 4)
    return struct.pack(order + "8I", kind, offset, 0, 0, size, size, 4, 4)


def _section(values: tuple[int, ...], bits: int, order: str) -> bytes:
    return struct.pack(order + ("II4QII2Q" if bits == 64 else "10I"), *values)


def _fixture_sections(
    data: bytearray, sections: tuple[Section, ...], bits: int, order: str
) -> list[bytes]:
    section_headers = []
    if sections:
        names = b"\0.shstrtab\0" + b"".join(name.encode() + b"\0" for name, _, _ in sections)
        section_headers.append(_section((0,) * 10, bits, order))
        names_offset = len(data)
        data.extend(names)
        data.extend(b"\0" * (-len(data) % 4))
        section_headers.append(
            _section((1, 3, 0, 0, names_offset, len(names), 0, 0, 1, 0), bits, order)
        )
        for name, section_kind, payload in sections:
            offset = len(data)
            data.extend(payload)
            data.extend(b"\0" * (-len(data) % 4))
            values = (
                names.index(name.encode()),
                section_kind,
                0,
                0,
                offset,
                len(payload),
                0,
                0,
                4,
                0,
            )
            section_headers.append(_section(values, bits, order))
    return section_headers


def build_elf(
    *,
    bits: int = 64,
    order: str = "<",
    kind: int = 2,
    programs: tuple[Program, ...] = (),
    sections: tuple[Section, ...] = (),
) -> bytes:
    header_size, program_size, section_size = (64, 56, 64) if bits == 64 else (52, 32, 40)
    data = bytearray(header_size + program_size * len(programs))
    for index, (program_kind, payload) in enumerate(programs):
        offset = len(data)
        data.extend(payload)
        data.extend(b"\0" * (-len(data) % 4))
        start = header_size + index * program_size
        end = start + program_size
        data[start:end] = _program(program_kind, offset, len(payload), bits, order)
    section_headers = _fixture_sections(data, sections, bits, order)
    section_offset = len(data) if sections else 0
    data.extend(b"".join(section_headers))
    ident = b"\x7fELF" + bytes((2 if bits == 64 else 1, 1 if order == "<" else 2, 1)) + b"\0" * 9
    values = (
        ident,
        kind,
        62 if bits == 64 else 3,
        1,
        0,
        header_size if programs else 0,
        section_offset,
        0,
        header_size,
        program_size,
        len(programs),
        section_size,
        len(section_headers),
        1 if sections else 0,
    )
    layout = "16sHHI3QI6H" if bits == 64 else "16sHHI4I6H"
    data[:header_size] = struct.pack(order + layout, *values)
    return bytes(data)


def description(data: bytes) -> str:
    return next(
        str(match)
        for match in MagicMatcher.DEFAULT_INSTANCE.match(data)
        if str(match).startswith("ELF ")
    )


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_issue_fixture_identification(bits: int, order: str) -> None:
    build_id = bytes(range(20))
    dynamic = struct.pack(order + ("QQ" if bits == 64 else "II"), 0, 0)
    data = build_elf(
        bits=bits,
        order=order,
        programs=((2, dynamic), (3, b"/lib/loader.so\0"), (4, note(b"GNU", 3, build_id, order))),
    )
    message = description(data)
    assert f"BuildID[sha1]={build_id.hex()}" in message
    assert ", dynamically linked, interpreter /lib/loader.so, no section header" in message
    assert join_matches(MagicMatcher.DEFAULT_INSTANCE.match(data), raw=True).startswith(message)


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_linkage_and_stripping(bits: int, order: str) -> None:
    for sections, expected in (
        ((), "no section header"),
        (((".text", 1, b"code"),), "stripped"),
        (((".symtab", 2, b"symbols"),), "not stripped"),
        (((".debug_info", 1, b"debug"),), "with debug_info, not stripped"),
    ):
        data = build_elf(bits=bits, order=order, programs=((1, b"code"),), sections=sections)
        assert description(data).endswith(f", statically linked, {expected}")


def test_path_raw_cli_and_structure_descriptions_agree(tmp_path: Path) -> None:
    data = build_elf(programs=((4, note(b"GNU", 3, bytes(range(20)))),))
    path = tmp_path / "sample.elf"
    path.write_bytes(data)
    expected = description(data)
    assert expected in [str(match) for match in Matcher().identify(path)]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "--quiet", "--format", "file", str(path)])
    assert expected in output.getvalue().splitlines()
    match = next(
        match for match in Matcher(parse=False).match(path) if match.description is not None
    )
    assert isinstance(match.match, TestResult)
    assert match.description == expected
    assert match.to_obj()["value"] == expected


def test_non_elf_description_is_unchanged() -> None:
    assert describe_elf(b"\x7fELF", "other file") == "other file"
    assert describe_elf(b"\x7fELF", "ELF invalid") == "ELF invalid"


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
@pytest.mark.parametrize("kind", (2, 3))
def test_pie_linkage(bits: int, order: str, kind: int) -> None:
    """Static PIE requires PIE flags and the absence of dependencies and an interpreter."""
    layout = order + ("QQ" if bits == 64 else "II")
    flags = struct.pack(layout, 0x6FFFFFFB, 0x08000000)
    terminator = struct.pack(layout, 0, 0)
    data = build_elf(bits=bits, order=order, kind=kind, programs=((2, flags + terminator),))
    assert "static-pie linked" in description(data)
    needed = struct.pack(layout, 1, 1)
    data = build_elf(
        bits=bits, order=order, kind=kind, programs=((2, flags + needed + terminator),)
    )
    assert "dynamically linked" in description(data)
    data = build_elf(
        bits=bits, order=order, kind=kind, programs=((2, flags + terminator), (3, b"/lib/loader\0"))
    )
    assert "dynamically linked, interpreter /lib/loader" in description(data)


@pytest.mark.parametrize(
    "size,label", ((8, "xxHash"), (16, "md5/uuid"), (20, "sha1"), (32, "sha256"), (5, "unknown"))
)
def test_build_id_types(size: int, label: str) -> None:
    """GNU IDs retain their bytes and report the known hash-length descriptions."""
    data = build_elf(programs=((4, note(b"GNU", 3, bytes(range(size)))),))
    assert f"BuildID[{label}]={bytes(range(size)).hex()}" in description(data)


def test_go_build_id_and_duplicate_note_regions() -> None:
    """A build ID seen through program and section tables is described once."""
    payload = note(b"Go", 4, b"id-for-this-build")
    data = build_elf(programs=((4, payload),), sections=((".note.go.buildid", 7, payload),))
    assert description(data).count("Go BuildID=id-for-this-build") == 1


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
@pytest.mark.parametrize(
    "system,name",
    ((0, "Linux"), (1, "Hurd"), (2, "Solaris"), (3, "kFreeBSD"), (4, "kNetBSD"), (99, "<unknown>")),
)
def test_gnu_abi_notes(bits: int, order: str, system: int, name: str) -> None:
    """ABI version words follow the ELF byte order in both classes."""
    payload = note(b"GNU", 1, struct.pack(order + "4I", system, 2, 0, 0), order)
    data = build_elf(bits=bits, order=order, programs=((4, payload),))
    assert f"for GNU/{name} 2.0.0" in description(data)


@pytest.mark.parametrize(
    "owner,version,expected",
    (
        (b"NetBSD", 903000000, "for NetBSD 9.3"),
        (b"NetBSD", 899010000, "for NetBSD 8.99A"),
        (b"NetBSD", 199905, "for NetBSD"),
        (b"FreeBSD", 1302000, "for FreeBSD 13.2"),
        (b"FreeBSD", 460002, "for FreeBSD 4.6.2"),
        (b"OpenBSD", 0, "for OpenBSD"),
        (b"DragonFly", 600001, "for DragonFly 6.0.1"),
    ),
)
@pytest.mark.parametrize("order", ("<", ">"))
def test_bsd_abi_notes(owner: bytes, version: int, expected: str, order: str) -> None:
    """BSD ABI version notes use their respective published numeric encodings."""
    payload = note(owner, 1, struct.pack(order + "I", version), order)
    assert expected in description(build_elf(order=order, programs=((4, payload),)))


def test_android_and_suse_abi_notes() -> None:
    """Android includes the available NDK fields, while SuSE has a two-byte version."""
    android = struct.pack("<I", 28) + b"r26".ljust(64, b"\0") + b"123456".ljust(64, b"\0")
    payload = note(b"Android", 1, android) + note(b"SuSE", 1, b"\x0f\x03")
    message = description(build_elf(programs=((4, payload),)))
    assert "for Android 28, built by NDK r26 (123456)" in message
    assert "for SuSE 15.3" in message


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_linux_core_notes(bits: int, order: str) -> None:
    """Linux process and status notes expose the command, PID, and signal."""
    info = bytearray(136 if bits == 64 else 124)
    command_offset, pid_offset = (56, 24) if bits == 64 else (44, 12)
    command = b"/usr/bin/example --flag"
    command_end = command_offset + len(command)
    info[command_offset:command_end] = command
    struct.pack_into(order + "I", info, pid_offset, 1234)
    status = bytearray(16)
    struct.pack_into(order + "H", status, 12, 11)
    payload = note(b"CORE", 3, info, order) + note(b"CORE", 1, status, order)
    message = description(build_elf(bits=bits, order=order, kind=4, programs=((4, payload),)))
    assert "SVR4-style, from '/usr/bin/example --flag', pid=1234, signal 11" in message


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_freebsd_core_notes(bits: int, order: str) -> None:
    """FreeBSD's class-dependent process note layout remains separate from Linux."""
    offset = 33 if bits == 64 else 25
    info = bytearray(offset + 87)
    end = offset + 7
    info[offset:end] = b"program"
    struct.pack_into(order + "I", info, offset + 83, 4321)
    data = build_elf(
        bits=bits, order=order, kind=4, programs=((4, note(b"FreeBSD", 3, info, order)),)
    )
    assert "FreeBSD-style, from 'program', pid=4321" in description(data)


@pytest.mark.parametrize("order", ("<", ">"))
def test_netbsd_core_notes(order: str) -> None:
    """NetBSD versioned process notes expose only fields that are present."""
    words = [0] * 31
    for index, value in (
        (0, 1),
        (1, 160),
        (2, 11),
        (3, 1),
        (20, 567),
        (25, 1000),
        (28, 1001),
        (30, 3),
    ):
        words[index] = value
    info = struct.pack(order + "31I", *words) + b"program".ljust(32, b"\0")
    info += struct.pack(order + "I", 2)
    data = build_elf(order=order, kind=4, programs=((4, note(b"NetBSD-CORE", 1, info, order)),))
    message = description(data)
    assert "NetBSD-style, from 'program', pid=567, uid=1000, gid=1001, nlwps=3" in message
    assert "lwp=2, signal 11/code 1" in message


@pytest.mark.parametrize("bits,offset", ((32, 100), (64, 136)))
def test_svr4_core_command(bits: int, offset: int) -> None:
    """SVR4 command layouts do not invent a Linux PID from unrelated fields."""
    info = bytearray(offset + 80)
    end = offset + 7
    info[offset:end] = b"command"
    data = build_elf(bits=bits, kind=4, programs=((4, note(b"CORE", 3, info)),))
    message = description(data)
    assert "SVR4-style, from 'command'" in message
    assert "pid=" not in message


@pytest.mark.parametrize(
    "owner,kind,data",
    ((b"unknown", 9, b"data"), (b"GNU", 1, b"short"), (b"GNU", 3, b""), (b"Android", 1, b"\0")),
)
def test_unknown_and_short_notes(owner: bytes, kind: int, data: bytes) -> None:
    """Unrecognized and short notes retain the base ELF classification."""
    payload = note(owner, kind, data)
    result = describe_elf(build_elf(programs=((4, payload),)), "ELF fixture")
    assert result == "ELF fixture, statically linked, no section header"


@pytest.mark.parametrize("kind", (1, 3))
@pytest.mark.parametrize("owner", (b"CORE", b"FreeBSD", b"NetBSD-CORE", b"unrecognized"))
def test_short_core_notes(owner: bytes, kind: int) -> None:
    """A truncated ABI-specific core descriptor never fabricates process fields."""
    data = build_elf(kind=4, programs=((4, note(owner, kind, b"\0")),))
    message = description(data)
    assert message.startswith("ELF ")
    assert "from '" not in message and "pid=" not in message and "signal" not in message


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_extended_header_counts(bits: int, order: str) -> None:
    """Extended section/program counts are bounded before reading lazy Kaitai tables."""
    data = bytearray(
        build_elf(
            bits=bits, order=order, programs=((1, b"code"),), sections=((".symtab", 2, b"symbols"),)
        )
    )
    wide = bits == 64
    sh_offset = struct.unpack_from(order + ("Q" if wide else "I"), data, 40 if wide else 32)[0]
    for offset, value in (
        (56 if wide else 44, 0xFFFF),
        (60 if wide else 48, 0),
        (62 if wide else 50, 0xFFFF),
    ):
        struct.pack_into(order + "H", data, offset, value)
    struct.pack_into(order + ("Q" if wide else "I"), data, sh_offset + (32 if wide else 20), 3)
    struct.pack_into(order + "I", data, sh_offset + (40 if wide else 24), 1)
    struct.pack_into(order + "I", data, sh_offset + (44 if wide else 28), 1)
    assert description(bytes(data)).endswith(", statically linked, not stripped")


@pytest.mark.parametrize(
    "offset,layout,value,diagnostic",
    (
        (32, "Q", 2**63, "program header table"),
        (54, "H", 0, "program header table"),
        (56, "H", 0xFFFE, "program header table"),
        (40, "Q", 2**63, "section header table"),
        (58, "H", 1, "section header table"),
        (60, "H", 0xFFFF, "section header table"),
        (62, "H", 0xFFFE, "section name table index"),
    ),
)
def test_malformed_tables_preserve_classification(
    offset: int, layout: str, value: int, diagnostic: str
) -> None:
    """Malformed tables produce diagnostics without erasing the ELF verdict."""
    data = bytearray(build_elf(programs=((1, b"code"),), sections=((".text", 1, b"code"),)))
    struct.pack_into("<" + layout, data, offset, value)
    message = description(bytes(data))
    assert message.startswith("ELF ")
    assert diagnostic in message


@pytest.mark.parametrize(
    "payload,diagnostic",
    (
        (b"short", "truncated ELF note"),
        (struct.pack("<III", 2**31, 0, 1), "truncated ELF note"),
        (struct.pack("<III", 4, 2**31, 3) + b"GNU\0", "truncated ELF note"),
    ),
)
def test_malformed_note_bounds(payload: bytes, diagnostic: str) -> None:
    """Note sizes are validated before slicing or decoding fields."""
    data = build_elf(programs=((4, payload),))
    assert diagnostic in description(data)


@pytest.mark.parametrize(
    "kind,payload,expected",
    (
        (2, b"short", "invalid or truncated ELF dynamic table"),
        (3, b"no terminator", "invalid or truncated ELF interpreter"),
        (3, b"", "invalid or truncated ELF interpreter"),
    ),
)
def test_malformed_segment_payloads(kind: int, payload: bytes, expected: str) -> None:
    """Incomplete payloads never become valid interpreter or dynamic entries."""
    assert expected in description(build_elf(programs=((kind, payload),)))


def test_invalid_note_region_and_alignment() -> None:
    """Note bodies stay within the file and unsupported alignments are diagnosed."""
    data = bytearray(build_elf(programs=((4, note(b"GNU", 3, bytes(range(20)))),)))
    struct.pack_into("<Q", data, 64 + 48, 3)
    assert "invalid ELF note alignment" in description(bytes(data))
    struct.pack_into("<Q", data, 64 + 8, 2**63)
    assert "invalid or truncated ELF note region" in description(bytes(data))


@pytest.mark.parametrize("offset,value", ((4, 0), (5, 0), (6, 2), (15, 1), (20, 2), (52, 0)))
def test_unsupported_identification_fields(offset: int, value: int) -> None:
    """Invalid classes, encodings, versions, and padding retain the original description."""
    data = bytearray(build_elf())
    data[offset] = value
    assert describe_elf(bytes(data), "ELF fixture") == "ELF fixture"


def test_all_header_truncations_preserve_base_description() -> None:
    """Every prefix shorter than an ELF header is handled without a parser exception."""
    for bits in (32, 64):
        data = build_elf(bits=bits)
        for end in range(len(data)):
            assert describe_elf(data[:end], "ELF fixture") == "ELF fixture"


def test_structural_parser_remains_registered(tmp_path: Path) -> None:
    """Enrichment leaves the existing ELF Kaitai structure available."""
    path = tmp_path / "sample.elf"
    path.write_bytes(build_elf(programs=((1, b"code"),)))
    matches = list(Matcher().match(path))
    root = next(match for match in matches if match.parent is None and match.description)
    assert root.children


def test_every_fixture_truncation_retains_base_description() -> None:
    """Every truncation of valid tables and payloads remains safe to identify."""
    payload = note(b"GNU", 3, bytes(range(20)))
    data = build_elf(programs=((4, payload),), sections=((".note.gnu.build-id", 7, payload),))
    for end in range(len(data) + 1):
        assert describe_elf(data[:end], "ELF fixture").startswith("ELF fixture")
    result = describe_elf(data[:-1], "ELF fixture")
    assert "BuildID[sha1]=" in result
    assert "invalid or truncated ELF section header table" in result


@pytest.mark.parametrize("command", (b'python -c "print(1)"', b"python -c 'print(1)'"))
def test_core_commands_preserve_quoted_arguments(command: bytes) -> None:
    """Valid quoted arguments remain visible in a core's process command."""
    info = bytearray(136)
    end = 56 + len(command)
    info[56:end] = command
    data = build_elf(kind=4, programs=((4, note(b"CORE", 3, info)),))
    assert command.decode().replace("'", "\\'") in description(data)


def test_powerpc_core_uses_the_declared_linux_layout() -> None:
    """A long PowerPC process name cannot be mistaken for the command's suffix."""
    info = bytearray(128)
    info[32:48] = b"longprocessname\0"
    command = b"/usr/bin/longprocessname --flag"
    end = 48 + len(command)
    info[48:end] = command
    struct.pack_into(">I", info, 16, 1234)
    data = bytearray(
        build_elf(bits=32, order=">", kind=4, programs=((4, note(b"CORE", 3, info, ">")),))
    )
    struct.pack_into(">H", data, 18, 20)
    assert "from '/usr/bin/longprocessname --flag', pid=1234" in description(bytes(data))


def test_netbsd_declared_size_bounds_optional_fields() -> None:
    """Bytes after the declared descriptor cannot become optional NetBSD process fields."""
    words = [1, 156] + [0] * 29
    info = struct.pack("<31I", *words) + b"program".ljust(32, b"\0") + b"JUNK"
    data = build_elf(kind=4, programs=((4, note(b"NetBSD-CORE", 1, info)),))
    assert "from 'program'" in description(data)
    assert "lwp=" not in description(data)


@pytest.mark.parametrize("size", (0, 64))
def test_missing_extended_section_zero_is_diagnosed(size: int) -> None:
    """An indirect count needs a real section-zero record before it can describe an empty table."""
    data = bytearray(build_elf())
    struct.pack_into("<Q", data, 40, 64)
    struct.pack_into("<H", data, 58, size)
    message = description(bytes(data))
    assert "invalid or truncated ELF section header table" in message
    assert "no section header" not in message


@pytest.mark.parametrize(
    "name,expected", ((".debug_info", True), (".zdebug_info", True), (".debug_information", False))
)
def test_debug_section_names_are_exact(name: str, expected: bool) -> None:
    """Debug-section recognition compares complete names without decoding unrelated table tails."""
    data = build_elf(sections=((name, 1, b"debug"),))
    assert ("with debug_info" in description(data)) == expected


@pytest.mark.parametrize("bits", (32, 64))
@pytest.mark.parametrize("order", ("<", ">"))
def test_unterminated_dynamic_table_does_not_claim_static_pie(bits: int, order: str) -> None:
    """Incomplete dynamic entries cannot establish the absence of runtime dependencies."""
    flags = struct.pack(order + ("QQ" if bits == 64 else "II"), 0x6FFFFFFB, 0x08000000)
    data = build_elf(bits=bits, order=order, kind=3, programs=((2, flags),))
    result = description(data)
    assert "unterminated ELF dynamic table" in result
    assert "static-pie linked" not in result


@pytest.mark.parametrize("order", ("<", ">"))
def test_overlapping_note_regions_preserve_distinct_notes(order: str) -> None:
    """Overlapping program-note regions share parsing while retaining distinct metadata."""
    first = note(b"GNU", 3, bytes(range(20)), order)
    second = note(b"GNU", 1, struct.pack(order + "4I", 0, 3, 2, 1), order)
    data = bytearray(build_elf(order=order, programs=((4, first + second), (4, b""))))
    start = struct.unpack_from(order + "Q", data, 64 + 8)[0]
    struct.pack_into(order + "Q", data, 64 + 56 + 8, start + len(first))
    struct.pack_into(order + "Q", data, 64 + 56 + 32, len(second))
    message = description(bytes(data))
    assert message.count("BuildID[sha1]=") == 1
    assert message.count("for GNU/Linux 3.2.1") == 1


def test_short_overlapping_note_region_is_diagnosed() -> None:
    """A containing note region does not hide a second region's truncated descriptor."""
    payload = note(b"GNU", 3, bytes(range(20)))
    data = bytearray(build_elf(programs=((4, payload), (4, b""))))
    start = struct.unpack_from("<Q", data, 64 + 8)[0]
    struct.pack_into("<Q", data, 64 + 56 + 8, start)
    struct.pack_into("<Q", data, 64 + 56 + 32, len(payload) - 1)
    message = description(bytes(data))
    assert "BuildID[sha1]=" in message
    assert "truncated ELF note" in message


def test_overlapping_note_prefixes_finish_within_a_subprocess_deadline() -> None:
    """Repeated references to the same physical notes cannot multiply identification work."""
    count = 6000
    data = bytearray(build_elf(programs=tuple((4, b"") for _ in range(count))))
    start = len(data)
    data += note(b"unknown", 99, b"") * 12000
    size = len(data) - start
    for index in range(count):
        struct.pack_into("<Q", data, 64 + 56 * index + 8, start + 20 * index)
        length = size // 2 if index == 0 else size - 20 * index
        struct.pack_into("<Q", data, 64 + 56 * index + 32, length)
    script = (
        "import sys; from polyfile.elfmetadata import describe_elf; "
        "print(describe_elf(sys.stdin.buffer.read(), 'ELF fixture'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], input=data, capture_output=True, check=True, timeout=20
    )
    assert result.stdout == b"ELF fixture, statically linked, no section header\n"


def test_empty_note_region_can_share_a_nonempty_region_start() -> None:
    """An empty note region remains valid when another region has already covered its offset."""
    payload = note(b"GNU", 3, bytes(range(20)))
    data = bytearray(build_elf(programs=((4, payload), (4, b""))))
    offset = struct.unpack_from("<Q", data, 64 + 8)[0]
    struct.pack_into("<Q", data, 64 + 56 + 8, offset)
    message = description(bytes(data))
    assert "BuildID[sha1]=" in message
    assert "invalid" not in message and "truncated" not in message
