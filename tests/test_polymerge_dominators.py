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
        (("left", "right", "reader"), (("left", "reader"), ("right", "reader")), ()),
        (("recursive",), (("recursive", "recursive"),), ()),
        (
            ("a", "b", "leaf"),
            (("a", "b"), ("b", "a"), ("b", "leaf")),
            (("b", "leaf"),),
        ),
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


def test_declared_entry_in_recursive_component_dominates_its_callee() -> None:
    graph = DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "a")])
    graph.set_roots(["a"])
    assert set(graph.dominator_forest.edges) == {("a", "b")}


@pytest.mark.parametrize("callers", [("left", "right"), ("reader",)])
def test_merge_retains_reader_reached_from_multiple_entries_or_recursion(
    callers: tuple[str, ...],
) -> None:
    reader = FunctionInfo("reader", {None: [0]}, called_from=callers)
    trace = ProgramTrace((0, 0, 1), [reader])
    merged = merge({"struc": [{"type": "byte", "offset": 0, "size": 1}]}, trace)
    assert merged["struc"][0]["functions"] == ["reader"]
    assert merged["best_function_matches"] == {"byte": ["reader"]}


def test_converging_tainted_roots_have_a_stable_order() -> None:
    functions = [
        FunctionInfo("b", {None: [0]}), FunctionInfo("a", {None: [0]}),
        FunctionInfo("reader", {None: [0]}, called_from=("b", "a")),
    ]
    for order in (functions, reversed(functions)):
        merged = merge(
            {"struc": [{"type": "byte", "offset": 0, "size": 1}]},
            ProgramTrace((0, 0, 1), order),
        )
        assert merged["struc"][0]["functions"] == ["a", "b", "reader"]
        assert merged["best_function_matches"] == {"byte": ["a", "b", "reader"]}


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
