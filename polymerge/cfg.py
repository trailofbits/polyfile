import math
from collections.abc import Callable, Hashable, Iterable, Iterator
from typing import Self, cast

import graphviz
import networkx as nx

from polymerge import polymerge, polytracker
from polymerge._types import PolyfileDocument


def roots(graph: "DiGraph") -> Iterator[Hashable]:
    degrees = cast(Iterable[tuple[Hashable, int]], graph.in_degree())
    return (node for node, degree in degrees if degree == 0)


class DiGraph(nx.DiGraph):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dominator_forest: DAG | None = None
        self._roots: Iterable[Hashable] | None = None
        self._path_lengths: dict[Hashable, dict[Hashable, int]] | None = None

    def path_length(self, from_node: Hashable, to_node: Hashable) -> float:
        if self._path_lengths is None:
            self._path_lengths = cast(
                dict[Hashable, dict[Hashable, int]],
                dict(nx.all_pairs_shortest_path_length(self, cutoff=None)),
            )
        if from_node not in self._path_lengths or to_node not in self._path_lengths[from_node]:
            return math.inf
        else:
            return self._path_lengths[from_node][to_node]

    def set_roots(self, roots: Iterable[Hashable]) -> None:
        self._roots = roots

    @property
    def roots(self) -> Iterable[Hashable]:
        if self._roots is None:
            self._roots = tuple(roots(self))
        return self._roots

    def depth(self, node: Hashable) -> float:
        return min(self.path_length(root, node) for root in self.roots)

    def ancestors(self, node: Hashable) -> set[Hashable]:
        return cast(set[Hashable], nx.ancestors(self, node))

    def descendants(self, node: Hashable) -> frozenset[Hashable]:
        successors = cast(dict[Hashable, list[Hashable]], nx.dfs_successors(self, node))
        return frozenset(successors)

    @property
    def dominator_forest(self) -> "DAG":
        if self._dominator_forest is not None:
            return self._dominator_forest
        self._dominator_forest = DAG()
        for root in self.roots:
            dominators = cast(dict[Hashable, Hashable], nx.immediate_dominators(self, root))
            for node, dominated_by in dominators.items():
                if node != dominated_by:
                    self._dominator_forest.add_edge(dominated_by, node)
        return self._dominator_forest

    def to_dot(
        self, comment: str | None = None, labeler: Callable[[Hashable], str] = str,
        node_filter: Callable[[Hashable], bool] | None = None
    ) -> graphviz.Digraph:
        if comment is not None:
            dot = graphviz.Digraph(comment=comment)
        else:
            dot = graphviz.Digraph()
        node_ids = {node: i for i, node in enumerate(self.nodes)}
        for node in self.nodes:
            if node_filter is None or node_filter(node):
                dot.node(f'func{node_ids[node]}', label=labeler(node))
        for caller, callee in self.edges:
            if node_filter is None or (node_filter(caller) and node_filter(callee)):
                dot.edge(f'func{node_ids[caller]}', f'func{node_ids[callee]}')
        return dot


class DAG(DiGraph):
    def vertex_induced_subgraph(self, vertices: Iterable[Hashable]) -> Self:
        vertices = frozenset(vertices)
        subgraph = cast(Self, self.copy())
        to_remove = set(self.nodes) - vertices
        for v in vertices:
            node = v
            parent = None
            while True:
                parents = tuple(subgraph.predecessors(node))
                if not parents:
                    if parent is not None:
                        subgraph.remove_edge(parent, v)
                        subgraph.add_edge(node, v)
                    break
                assert len(parents) == 1
                ancestor = parents[0]
                if parent is None:
                    parent = ancestor
                if ancestor in vertices:
                    to_remove.add(v)
                    break
                node = ancestor
        subgraph.remove_nodes_from(to_remove)
        return subgraph


class CFG(DiGraph):
    def __init__(self, trace: "polytracker.ProgramTrace"):
        super().__init__()
        self.trace: polytracker.ProgramTrace = trace

    def to_dot(self,  # ty: ignore[invalid-method-override]  # Legacy metadata positional API.
               comment='PolyTracker Program Trace',
               merged_json_obj: PolyfileDocument | None = None,
               only_labeled_functions=False,
               labeler: Callable[["polytracker.FunctionInfo"], str] | None = None,
               **kwargs
               ) -> graphviz.Digraph:
        if merged_json_obj is not None:
            function_labels = {
                func_name: ', '.join(['::'.join(label) for label in labels])
                for func_name, labels in polymerge.function_labels(merged_json_obj).items()
            }
        else:
            function_labels = {}

        def func_labeler(node: Hashable) -> str:
            f = cast(polytracker.FunctionInfo, node)
            if labeler is not None:
                return labeler(f)
            elif f.name in function_labels:
                return f"{f.name} ({function_labels[f.name]})"
            else:
                return f.name

        return super().to_dot(comment, labeler=func_labeler, **kwargs)
