"""String-match extents describe physical bytes rather than comparison padding."""

from pathlib import Path

import pytest

from polyfile.magic import MagicMatcher, MatchedTest, StringType


@pytest.mark.parametrize("flags", ["W", "w", "Ww"])
def test_comparison_padding_is_not_reported(flags: str) -> None:
    data_type = StringType.parse(f"string/{flags}")
    result = data_type.match(b"A  ", data_type.parse_expected(r"A\ \0"))

    assert result.raw_match == b"A  "
    assert result.value == "A  "


@pytest.mark.parametrize("flags", ["W", "w", "Ww"])
@pytest.mark.parametrize("copy_length", [2, 127])
def test_comparison_copy_limit_bounds_reported_bytes(flags: str, copy_length: int) -> None:
    declaration = f"string/{copy_length}/{flags}" if copy_length == 2 else f"string/{flags}"
    data_type = StringType.parse(declaration)
    data = b"A" + b" " * (copy_length - 1) + b"X"
    result = data_type.match(data, data_type.parse_expected(r"A\ \0"))

    assert result.raw_match == data[:copy_length]
    assert result.value == data[:copy_length].decode("ascii")


@pytest.mark.parametrize("flags", ["W", "w", "Ww"])
def test_real_nul_bytes_remain_in_the_match(flags: str) -> None:
    data_type = StringType.parse(f"string/{flags}")
    result = data_type.match(b"A \0Z", data_type.parse_expected(r"A\ \0"))

    assert result.raw_match == b"A \0"
    assert result.value == "A \0"


def test_nonzero_match_extent_and_explanation_use_file_bytes(tmp_path: Path) -> None:
    definition = tmp_path / "extent.magic"
    definition.write_text("2\tstring/W\tA\\ \\0\tfound\n")
    data = b"xxA  "
    match = next(MagicMatcher.parse(definition).match(data))
    result = match[0]

    assert isinstance(result, MatchedTest)
    assert result.offset == 2
    assert result.length == 3
    assert result.value == "A  "
    assert result.offset + result.length == len(data)
    assert "Matched 3 bytes at offset 2" in match.explain(file=data, ansi_color=False)


def test_continuation_keeps_the_declared_relative_base(tmp_path: Path) -> None:
    definition = tmp_path / "continuation.magic"
    definition.write_text("0\tstring/2/W\tA\\ \\0\thead\n>&0\tbyte\t90\tcontinuation\n")
    match = next(MagicMatcher.parse(definition).match(b"A XZ"))
    first, continuation = match[0], match[1]

    assert isinstance(first, MatchedTest)
    assert first.length == 2
    assert first.relative_base == 3
    assert continuation.offset == 3
    assert str(match) == "head continuation"
