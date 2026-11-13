import copy
from collections import Counter, defaultdict
from collections.abc import Hashable as HashableValue, Iterable, Sized
import heapq
import math
from statistics import stdev
from typing import cast

from intervaltree import IntervalTree

from polyfile import logger, __version__

from polymerge import polytracker, cfg
from polymerge._types import PolyfileDocument, PolyfileElement

log = logger.getStatusLogger("PolyMerge")


def _function_labels(
    merged: PolyfileElement, labeling: dict[str, set[tuple[str, ...]]],
    ancestry: tuple[str, ...] = ()
) -> None:
    if 'type' in merged:
        name = merged['type']
    else:
        name = merged['name']
    label = ancestry + (name,)
    for f in merged.get('functions', ()):
        labeling[f].add(label)
    for s in merged.get('subEls', ()):
        _function_labels(s, labeling, ancestry=label)


def function_labels(merged_json_obj: PolyfileDocument) -> dict[str, set[tuple[str, ...]]]:
    labels: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for merged in merged_json_obj['struc']:
        _function_labels(merged, labels)
    return labels


class Hashable:
    def __init__(self, value):
        self.value = value
        self._hash = None

    @staticmethod
    def deephash(obj):
        if isinstance(obj, dict):
            return hash(tuple(Hashable.deephash(o) for o in sorted(obj.items())))
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return hash(tuple(Hashable.deephash(o) for o in obj))
        else:
            return hash(obj)

    def __hash__(self):
        if self._hash is None:
            self._hash = Hashable.deephash(self.value)
        return self._hash

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r})"


class IDHashable:
    def __init__(self, value: PolyfileElement):
        self.value = value

    def __hash__(self):
        return id(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r})"


def build_intervals(
    elem: PolyfileElement, tree: IntervalTree | None = None
) -> IntervalTree:
    if tree is None:
        tree = IntervalTree()
    if 'size' in elem:
        elem_size = elem['size']
        if elem_size > 0:
            tree[elem['offset']:elem['offset']+elem_size] = elem
    if 'subEls' in elem:
        for child in elem['subEls']:
            build_intervals(child, tree)
    return tree


def shannon_entropy(data: Iterable[HashableValue]) -> float:
    if not hasattr(data, '__len__'):
        data = list(data)

    length = len(cast(Sized, data))
    if length <= 1:
        return 0

    counts = Counter(data)

    probabilities = [float(c) / length for c in counts.values()]

    return -sum(p * math.log(p, 2) for p in probabilities if p > 0.)


def _build_type_graph(
    graph: cfg.DiGraph, elem: PolyfileElement, parent: str | None = None
) -> None:
    node_name = elem['type']
    graph.add_node(node_name)
    if parent is not None:
        graph.add_edge(parent, node_name)
    if 'subEls' in elem:
        for child in elem['subEls']:
            _build_type_graph(graph, child, node_name)


def polyfile_type_graph(polyfile_json_obj: PolyfileDocument) -> cfg.DiGraph:
    graph = cfg.DiGraph()
    roots = []
    for match in polyfile_json_obj['struc']:
        roots.append(match['type'])
        _build_type_graph(graph, match)
    graph.set_roots(roots)
    return graph


def _filter_function_matches(
        type_dominators: cfg.DAG,
        node: str,
        matches: dict[str, list[str]],
        disallowed: dict[str, int],
        depth: int = 0):
    if node in matches:
        orig_matches = matches[node]
        for disallowed_depth in range(depth, -1, -1):
            matches[node] = [
                func for func in orig_matches if func not in disallowed or disallowed[func] >= disallowed_depth
            ]
            if matches[node]:
                break
        for func in matches[node]:
            if func not in disallowed:
                disallowed[func] = depth
    for child in type_dominators.successors(node):
        _filter_function_matches(type_dominators, child, matches, disallowed, depth + 1)


def filter_function_matches(type_dominators: cfg.DAG, matches: dict[str, list[str]]) -> None:
    for root in type_dominators.roots:
        _filter_function_matches(type_dominators, cast(str, root), matches, {})


def merge(
    polyfile_json_obj: PolyfileDocument, program_trace: polytracker.ProgramTrace
) -> PolyfileDocument:
    ret = copy.deepcopy(polyfile_json_obj)
    if 'versions' in ret:
        ret['versions']['polymerge'] = __version__
    else:
        ret['versions'] = {'polymerge': __version__}
    intervals = IntervalTree()
    for match in ret['struc']:
        intervals = build_intervals(match, tree=intervals)
    matches: dict[IDHashable, set[str]] = defaultdict(set)
    elems_by_function: dict[str, set[IDHashable]] = defaultdict(set)
    functions_by_type: dict[str, set[str]] = defaultdict(set)
    elems_by_type: dict[str, set[IDHashable]] = defaultdict(set)
    ret['versions']['polytracker'] = '.'.join(map(str, program_trace.polytracker_version))
    # The following code assumes that taint was tracked from a single input file.
    total_bytes = 0
    progress = 0
    if log.isEnabledFor(logger.STATUS):
        for function_info in program_trace.functions.values():
            for _, tainted_bytes in function_info.items():
                total_bytes += len(tainted_bytes)
    for function_name, function_info in program_trace.functions.items():
        function_bytes = 0
        function_progress = 0
        function_percent = -1
        if log.isEnabledFor(logger.STATUS):
            function_bytes = sum(len(tainted_bytes) for _, tainted_bytes in function_info.items())#.cmp_bytes.items())
        for input_source, tainted_bytes in function_info.items():#cmp_bytes.items():
            for offset in tainted_bytes:
                if log.isEnabledFor(logger.STATUS):
                    progress += 1
                    function_progress += 1
                    last_percent = function_percent
                    function_percent = int((function_progress / function_bytes) * 100.0)
                    if function_percent > last_percent:
                        log.status(f"{(progress / total_bytes) * 100.0:.2f}% processing function {function_name}... ({function_percent}%)")
                for interval in intervals[offset]:
                    elem = IDHashable(cast(PolyfileElement, interval.data))
                    elems_by_function[function_name].add(elem)
                    elem_type = elem.value['type']
                    functions_by_type[elem_type].add(function_name)
                    elems_by_type[elem_type].add(elem)
                    matches[elem].add(function_name)
    log.clear_status()
    dominator_tree = program_trace.cfg.dominator_forest
    ret['best_function_matches'] = {}
    for elem_type, elems in elems_by_type.items():
        # find the function that is most specialized in operating on elems of this type:
        specialization = [
            (shannon_entropy(elem.value['type'] for elem in elems_by_function[func]), func)
            for func in functions_by_type[elem_type]
        ]
        if not specialization:
            continue
        elif len(specialization) == 1:
            func_matches = [specialization[0][1]]
        else:
            std_dev = stdev(entropy for entropy, _ in specialization)
            heapq.heapify(specialization)
            best_value, best_match_func = heapq.heappop(specialization)
            value_threshold = best_value + std_dev
            func_matches = [best_match_func]
            while specialization:
                best_value, best_match_func = heapq.heappop(specialization)
                if best_value > value_threshold:
                    break
                func_matches.append(best_match_func)
        # now choose the functions that are roots in the vertex-induced subgraph of the CFG dominator tree:
        ret['best_function_matches'][elem_type] = [
            cast(polytracker.FunctionInfo, root).name
            for root in cfg.roots(
                dominator_tree.vertex_induced_subgraph(program_trace.functions[func] for func in func_matches)
            )
        ]
    # finally, remove redundant functions in the best matches based upon the semantic hierarchy:
    # first step in that is to build the dominator tree of the PolyFile hierarchy:
    type_dominators: cfg.DAG = polyfile_type_graph(polyfile_json_obj).dominator_forest
    # for each type in the 'best_function_matches' mapping, only include a function if that function is not
    # included for any ancestor of the type in `type_dominators`
    filter_function_matches(type_dominators, ret['best_function_matches'])
    for elem, functions in matches.items():
        elem.value['functions'] = list(functions)
    return ret


