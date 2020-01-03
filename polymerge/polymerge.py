import copy
from collections import defaultdict

from intervaltree import IntervalTree

from polyfile import logger

from . import polytracker

log = logger.getStatusLogger("PolyMerge")


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


def merge(polyfile_json_obj: dict, polytracker_json_obj: dict, simplify=False) -> dict:
    ret = copy.deepcopy(polyfile_json_obj)
    for match in ret['struc']:
        intervals = build_intervals(match)
    matches = defaultdict(set)
    elems_by_function = defaultdict(set)
    program_trace: polytracker.ProgramTrace = polytracker.parse(polytracker_json_obj)
    # The following code assumes that taint was tracked from a single input file.
    if log.isEnabledFor(logger.STATUS):
        total_bytes = 0
        for function_info in program_trace.functions.values():
            for _, tainted_bytes in function_info.items():
                total_bytes += len(tainted_bytes)
        progress = 0
    for function_name, function_info in program_trace.functions.items():
        if log.isEnabledFor(logger.STATUS):
            function_bytes = sum(len(tainted_bytes) for _, tainted_bytes in function_info.items())
            function_progress = 0
            function_percent = -1
        for input_source, tainted_bytes in function_info.items():
            for offset in tainted_bytes:
                if log.isEnabledFor(logger.STATUS):
                    progress += 1
                    function_progress += 1
                    last_percent = function_percent
                    function_percent = int((function_progress / function_bytes) * 100.0)
                    if function_percent > last_percent:
                        log.status(f"{(progress / total_bytes) * 100.0:.2f}%\tprocessing function {function_name}... ({function_percent}%)")
                for interval in intervals[offset]:
                    elem = IDHashable(interval.data)
                    if simplify:
                        elems_by_function[function_name].add(elem)
                    matches[elem].add(function_name)
    log.clear_status()
    if simplify:
        # only choose the elements with the fewest number of functions
        num_functions = {elem: len(functions) for elem, functions in matches.items()}
        for function, elems in elems_by_function.items():
            min_value = min(num_functions[elem] for elem in elems)
            for elem in elems:
                if num_functions[elem] == min_value:
                    if 'functions' in elem.value:
                        elem.value['functions'].append(function)
                    else:
                        elem.value['functions'] = [function]
    else:
        for elem, functions in matches.items():
            elem.value['functions'] = list(functions)
    return ret
