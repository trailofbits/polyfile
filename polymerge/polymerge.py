import copy
from collections import defaultdict

from intervaltree import IntervalTree


class Hashable(dict):
    def __init__(self, value):
        self.value = value

    @staticmethod
    def deephash(obj):
        if isinstance(obj, dict):
            return hash(tuple(Hashable.deephash(o) for o in sorted(obj.items())))
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return hash(tuple(Hashable.deephash(o) for o in obj))
        else:
            return hash(obj)

    def __hash__(self):
        return Hashable.deephash(self.value)


def build_intervals(elem: dict, tree: IntervalTree=None):
    if tree is None:
        tree = IntervalTree()
    if 'size' in elem:
        tree[elem['offset']:elem['offset']+elem['size']] = elem
    if 'subEls' in elem:
        for child in elem['subEls']:
            build_intervals(child, tree)
    return tree


def merge(polyfile_json_obj, polytracker_json_obj):
    ret = copy.deepcopy(polyfile_json_obj)
    for match in ret['struc']:
        intervals = build_intervals(match)
    matches = defaultdict(set)
    for function, offsets in polytracker_json_obj.items():
        for offset in offsets:
            for interval in intervals[offset]:
                matches[Hashable(interval.data)].add(function)
    for elem, functions in matches.items():
        elem.value['functions'] = list(functions)
    return ret
