"""Archive identification remains complete when recursive analysis is disabled."""

import contextlib
import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from polyfile.__main__ import main

# Generated from b'{"sevenzip":true}\n' in document.json with p7zip 17.05:
# 7z a -t7z -m0=Copy -mhc=off -mtc=off -mta=off -mtm=off copy.7z document.json
# `7z t copy.7z` verifies the Copy stream and archive checksums.
SEVEN_ZIP = bytes.fromhex(
    "377abcaf271c0004560797411200000000000000460000000000000017b0c9ec"
    "7b22736576656e7a6970223a747275657d0a0104060001091200070b0100010100"
    "0c1200080a01ea6abae300000501111d0064006f00630075006d0065006e007400"
    "2e006a0073006f006e000000150601002080a4810000"
)


def zip_archive() -> bytes:
    """Returns a compressed ZIP member whose decoded content is JSON."""
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("document.json", b'{"zip_member":true}\n')
    return output.getvalue()


def cli_output(path: Path, *options: str) -> str:
    """Runs the CLI and returns its output without terminal-dependent formatting."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "--quiet", *options, str(path)])
    return output.getvalue()


def structure_nodes(roots: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yields each node in a serialized structure tree."""
    for node in roots:
        yield node
        yield from structure_nodes(node["subEls"])


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ((), "7-zip archive data, version 0.4"),
        (("--format", "mime"), "application/x-7z-compressed"),
    ],
)
def test_seven_zip_identification(
    tmp_path: Path, options: tuple[str, ...], expected: str
) -> None:
    path = tmp_path / "copy.7z"
    path.write_bytes(SEVEN_ZIP)

    assert cli_output(path, *options).splitlines() == [expected]


@pytest.mark.parametrize("options", [(), ("--max-depth", "0")])
def test_seven_zip_identification_keeps_a_secondary_zip(
    tmp_path: Path, options: tuple[str, ...]
) -> None:
    path = tmp_path / "polyglot.7z"
    path.write_bytes(SEVEN_ZIP + zip_archive())

    assert set(cli_output(path, "--format", "mime", *options).splitlines()) == {
        "application/x-7z-compressed",
        "application/zip",
    }


def test_depth_zero_preserves_root_identification_and_limits_decoded_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "member.zip"
    path.write_bytes(zip_archive())

    identified = cli_output(path, "--format", "mime")
    assert cli_output(path, "--format", "mime", "--max-depth", "0") == identified
    assert set(identified.splitlines()) == {"application/zip"}

    full = json.loads(cli_output(path, "--format", "json", "--no-contents"))
    limited = json.loads(
        cli_output(path, "--format", "json", "--no-contents", "--max-depth", "0")
    )
    assert full["struc"][0]["type"] == limited["struc"][0]["type"] == "application/zip"
    full_types = {node["type"] for node in structure_nodes(full["struc"])}
    limited_nodes = list(structure_nodes(limited["struc"]))
    limited_types = {node["type"] for node in limited_nodes}
    assert {"decoded_content", "application/json"} <= full_types
    assert not {"decoded_content", "application/json"} & limited_types
    assert any(node.get("analysis_status") == "limited" for node in limited_nodes)
