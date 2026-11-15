"""Dominator forests retain isolated roots when associating file types and functions."""

import pytest

from polymerge.cfg import DiGraph
from polymerge.polymerge import merge
from polymerge.polytracker import FunctionInfo, ProgramTrace


@pytest.mark.parametrize(
    ("nodes", "edges", "dominator_edges"),
    [
        ((), (), ()),
        (("isolated",), (), ()),
        (("first", "second"), (), ()),
        (
            ("caller", "reader"),
            (("caller", "reader"),),
            (("caller", "reader"),),
        ),
        (
            ("isolated", "caller", "reader"),
            (("caller", "reader"),),
            (("caller", "reader"),),
        ),
        (
            ("caller", "left", "right", "reader"),
            (("caller", "left"), ("caller", "right"), ("left", "reader"), ("right", "reader")),
            (("caller", "left"), ("caller", "right"), ("caller", "reader")),
        ),
    ],
)
def test_dominator_forests_keep_all_component_roots(
    nodes: tuple[str, ...],
    edges: tuple[tuple[str, str], ...],
    dominator_edges: tuple[tuple[str, str], ...],
) -> None:
    graph = DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    forest = graph.dominator_forest

    assert set(forest.nodes) == set(nodes)
    assert set(forest.edges) == set(dominator_edges)


def test_isolated_tainted_function_matches_a_nonempty_structure() -> None:
    trace = ProgramTrace((0, 0, 1), [FunctionInfo("reader", {None: [0]})])

    merged = merge({"struc": [{"type": "header", "offset": 0, "size": 1, "subEls": []}]}, trace)

    assert merged["struc"][0]["functions"] == ["reader"]
    assert merged["best_function_matches"] == {"header": ["reader"]}


def test_mixed_cfg_components_preserve_both_tainted_functions() -> None:
    trace = ProgramTrace(
        (0, 0, 1),
        [
            FunctionInfo("isolated", {None: [0]}),
            FunctionInfo("reader", {None: [1]}, called_from=("caller",)),
        ],
    )

    merged = merge(
        {
            "struc": [
                {"type": "first", "offset": 0, "size": 1, "subEls": []},
                {"type": "second", "offset": 1, "size": 1, "subEls": []},
            ]
        },
        trace,
    )

    assert merged["struc"][0]["functions"] == ["isolated"]
    assert merged["struc"][1]["functions"] == ["reader"]
    assert merged["best_function_matches"] == {"first": ["isolated"], "second": ["reader"]}


def test_connected_tainted_functions_keep_the_dominating_match() -> None:
    trace = ProgramTrace(
        (0, 0, 1),
        [
            FunctionInfo("caller", {None: [0]}),
            FunctionInfo("reader", {None: [0]}, called_from=("caller",)),
        ],
    )

    merged = merge({"struc": [{"type": "header", "offset": 0, "size": 1, "subEls": []}]}, trace)

    assert merged["best_function_matches"] == {"header": ["caller"]}
