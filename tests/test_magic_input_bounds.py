"""Bounded magic tests do not allocate a copy of the remaining input."""

import tracemalloc

import pytest

from polyfile.magic import AbsoluteOffset, ConstantMatchTest, DataType


@pytest.mark.parametrize(
    "declaration,value",
    [
        ("lelong", "123"),
        ("guid", "x"),
        ("lestring16", "TOKEN"),
        ("string", "TOKEN"),
        ("string", "x"),
        ("regex", "TOKEN"),
        ("regex/1l", "TOKEN"),
    ],
)
@pytest.mark.parametrize("flipped", [False, True])
def test_fixed_magic_allocation_does_not_grow_with_input(
    declaration: str, value: str, flipped: bool
) -> None:
    data_type = DataType.parse(declaration)
    test = ConstantMatchTest(AbsoluteOffset(1), data_type, data_type.parse_expected(value))
    run = test.test_flip_endianness if flipped else test.test
    inputs = (b"x" * 1_048_576, b"x" * 16_777_216)
    peaks = []
    for data in inputs:
        tracemalloc.start()
        try:
            run(data, 1, None)
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    assert peaks[1] - peaks[0] < 65_536
