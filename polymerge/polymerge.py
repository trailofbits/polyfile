import copy
from collections import Counter, defaultdict
import heapq
import math
from statistics import stdev
from typing import Dict, Set, Tuple

from intervaltree import IntervalTree

from polyfile import logger, version

from . import polytracker
from . import cfg

log = logger.getStatusLogger("PolyMerge")


def _function_labels(merged: dict, labeling: Dict[str, Set[Tuple[str]]], ancestry: Tuple[str] = ()):
    if 'type' in merged:
        name = merged['type']
    else:
        name = merged['name']
    label: Tuple[str] = ancestry + (name,)
    for f in merged.get('functions', ()):
        labeling[f].add(label)
    for s in merged.get('subEls', ()):
        _function_labels(s, labeling, ancestry=label)


def function_labels(merged_json_obj: dict) -> Dict[str, Set[Tuple[str]]]:
    labels = defaultdict(set)
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
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return id(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r})"


def build_intervals(elem: dict, tree: IntervalTree = None):
    if tree is None:
        tree = IntervalTree()
    if 'size' in elem:
        tree[elem['offset']:elem['offset']+elem['size']] = elem
    if 'subEls' in elem:
        for child in elem['subEls']:
            build_intervals(child, tree)
    return tree


def shannon_entropy(data):
    if not hasattr(data, '__len__'):
        data = list(data)

    if len(data) <= 1:
        return 0

    counts = Counter(data)

    probabilities = [float(c) / len(data) for c in counts.values()]

    return -sum(p * math.log(p, 2) for p in probabilities if p > 0.)


def merge(polyfile_json_obj: dict, program_trace: polytracker.ProgramTrace) -> dict:
    ret = copy.deepcopy(polyfile_json_obj)
    if 'versions' in ret:
        ret['versions']['polymerge'] = version.VERSION_STRING
    else:
        ret['versions'] = {'polymerge': version.VERSION_STRING}
    intervals = None
    for match in ret['struc']:
        intervals = build_intervals(match, tree=intervals)
    matches = defaultdict(set)
    elems_by_function = defaultdict(set)
    functions_by_type = defaultdict(set)
    elems_by_type = defaultdict(set)
    ret['versions']['polytracker'] = '.'.join(map(str, program_trace.polytracker_version))
    # The following code assumes that taint was tracked from a single input file.
    if log.isEnabledFor(logger.STATUS):
        total_bytes = 0
        for function_info in program_trace.functions.values():
            for _, tainted_bytes in function_info.items():
                total_bytes += len(tainted_bytes)
        progress = 0
    for function_name, function_info in program_trace.functions.items():
        if log.isEnabledFor(logger.STATUS):
            function_bytes = sum(len(tainted_bytes) for _, tainted_bytes in function_info.items())#.cmp_bytes.items())
            function_progress = 0
            function_percent = -1
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
                    elem = IDHashable(interval.data)
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
            root.name
            for root in cfg.roots(
                dominator_tree.vertex_induced_subgraph(program_trace.functions[func] for func in func_matches)
            )
        ]
    for elem, functions in matches.items():
        elem.value['functions'] = list(functions)
    return ret


