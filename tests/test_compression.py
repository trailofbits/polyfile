"""Behavioral tests for shared compressed-content output handling."""

import pytest

from polyfile.compression import DecodeError, OutputBuffer


def test_output_is_unlimited_by_default():
    output = OutputBuffer()
    output.append(b"first")
    output.append(b"second")
    assert output.remaining is None
    assert output.finish() == b"firstsecond"


def test_output_limit_accepts_the_boundary_and_rejects_one_more_byte():
    output = OutputBuffer(5)
    output.append(b"first")
    assert output.remaining == 0
    assert output.next_size == 1
    with pytest.raises(DecodeError, match="5-byte") as error:
        output.append(b"x")
    assert error.value.status == "limited"
    assert output.finish() == b"first"


def test_a_zero_limit_accepts_empty_output():
    output = OutputBuffer(0)
    output.append(b"")
    assert output.finish() == b""
