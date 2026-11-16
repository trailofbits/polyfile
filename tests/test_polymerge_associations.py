"""Function associations retain all tainted functions for each output element."""

import pytest

from polymerge._types import PolyfileElement
from polymerge.polymerge import IDHashable, merge
from polymerge.polytracker import FunctionInfo, ProgramTrace


@pytest.mark.parametrize("offsets", [[0], [0, 0, 1, 1, 2]])
def test_shared_element_keeps_all_functions_outside_dominance_filtering(
    offsets: list[int],
) -> None:
    trace = ProgramTrace(
        (0, 0, 1),
        [
            FunctionInfo("caller", {None: offsets}),
            FunctionInfo("reader", {None: offsets}, called_from=("caller",)),
            FunctionInfo("parser", {None: offsets}, called_from=("reader",)),
        ],
    )

    merged = merge({"struc": [{"type": "header", "offset": 0, "size": 3}]}, trace)

    assert set(merged["struc"][0]["functions"]) == {"caller", "reader", "parser"}
    assert len(merged["struc"][0]["functions"]) == 3
    assert merged["best_function_matches"] == {"header": ["caller"]}


def test_overlapping_elements_keep_their_own_function_associations() -> None:
    trace = ProgramTrace(
        (0, 0, 1),
        [
            FunctionInfo("left", {None: [0, 1, 1]}),
            FunctionInfo("right", {None: [1, 2, 2]}),
            FunctionInfo("tail", {None: [3]}),
        ],
    )

    merged = merge(
        {
            "struc": [
                {"type": "first", "offset": 0, "size": 2},
                {"type": "second", "offset": 1, "size": 3},
            ]
        },
        trace,
    )

    assert set(merged["struc"][0]["functions"]) == {"left", "right"}
    assert set(merged["struc"][1]["functions"]) == {"left", "right", "tail"}


def test_identity_keys_preserve_equal_distinct_elements() -> None:
    first: PolyfileElement = {"type": "header", "offset": 0, "size": 1}
    second = first.copy()
    associations = {
        IDHashable(first): {"caller"},
        IDHashable(second): {"reader"},
    }

    associations[IDHashable(first)].add("parser")

    assert len(associations) == 2
    assert associations[IDHashable(first)] == {"caller", "parser"}
    assert associations[IDHashable(second)] == {"reader"}


def test_equal_distinct_elements_each_receive_function_associations() -> None:
    first: PolyfileElement = {"type": "header", "offset": 0, "size": 1}
    second = first.copy()
    trace = ProgramTrace(
        (0, 0, 1),
        [
            FunctionInfo("caller", {None: [0]}),
            FunctionInfo("reader", {None: [0]}, called_from=("caller",)),
        ],
    )

    merged = merge({"struc": [first, second]}, trace)

    assert merged["struc"][0] is not merged["struc"][1]
    for element in merged["struc"]:
        assert set(element["functions"]) == {"caller", "reader"}
    assert "functions" not in first
    assert "functions" not in second
