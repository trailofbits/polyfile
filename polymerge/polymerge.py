import copy
from collections import defaultdict

from intervaltree import IntervalTree


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
    for function, offsets in polytracker_json_obj.items():
        for offset in offsets:
            for interval in intervals[offset]:
                elem = IDHashable(interval.data)
                if simplify:
                    elems_by_function[function].add(elem)
                matches[elem].add(function)
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
