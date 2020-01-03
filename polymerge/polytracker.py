from typing import Dict, Iterable, List, Set

import networkx as nx
from graphviz import Digraph

from . import polymerge


class FunctionInfo:
    def __init__(self, name: str, input_bytes: Dict[str, List[int]], called_from: Iterable[str] = ()):
        self.name = name
        self.called_from = frozenset(called_from)
        self.input_bytes = input_bytes

    @property
    def taint_sources(self) -> Set[str]:
        return self.input_bytes.keys()

    def __getitem__(self, input_source_name):
        return self.input_bytes[input_source_name]

    def __iter__(self):
        return self.taint_sources

    def items(self):
        return self.input_bytes.items()

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, input_bytes={self.input_bytes!r}, called_from={self.called_from!r})"


class CFG(nx.DiGraph):
    def __init__(self, trace):
        super().__init__()
        self.trace: ProgramTrace = trace

    def to_dot(self, merged_json_obj=None, only_labeled_functions=False) -> Digraph:
        dot = Digraph(comment='PolyTracker Program Trace')
        function_ids = {node.name: i for i, node in enumerate(self.nodes)}
        if merged_json_obj is not None:
            function_labels = {
                func_name: ', '.join(['::'.join(label) for label in labels])
                for func_name, labels in polymerge.function_labels(merged_json_obj).items()
            }
        else:
            function_labels = {}
        for f in self.nodes:
            if f.name in function_labels:
                label = f"{f.name} ({function_labels[f.name]})"
            else:
                label = f.name
            dot.node(f'func{function_ids[f.name]}', label=label)
        for caller, callee in self.edges:
            dot.edge(f'func{function_ids[caller.name]}', f'func{function_ids[callee.name]}')
        return dot


class ProgramTrace:
    def __init__(self, polytracker_version: tuple, function_data: Iterable[FunctionInfo]):
        self.polytracker_version = polytracker_version
        self.functions: Dict[str, FunctionInfo] = {f.name: f for f in function_data}
        self._cfg = None

    @property
    def cfg(self):
        if self._cfg is not None:
            return self._cfg
        self._cfg = CFG(self)
        self._cfg.add_nodes_from(self.functions.values())
        for f in list(self.functions.values()):
            for caller in f.called_from:
                if caller not in self.functions:
                    info = FunctionInfo(caller, {})
                    self.functions[caller] = info
                    self._cfg.add_node(info)
                    self._cfg.add_edge(info, f)
                else:
                    self._cfg.add_edge(self.functions[caller], f)
        return self._cfg

    def __repr__(self):
        return f"{self.__class__.__name__}(polytracker_version={self.polytracker_version!r}, function_data={list(self.functions.values())!r})"


def parse(polytracker_json_obj: dict) -> ProgramTrace:
    # TODO: Once https://github.com/trailofbits/polytracker/issues/39 is implemented, add logic here for versioning

    for function_name, function_data in polytracker_json_obj.items():
        if isinstance(function_data, dict) and 'called_from' in function_data:
            # this is the second version of the output format
            return parse_format_v2(polytracker_json_obj)
        else:
            return parse_format_v1(polytracker_json_obj)


def parse_format_v1(polytracker_json_obj: dict) -> ProgramTrace:
    return ProgramTrace(
        polytracker_version=(0, 0, 1),
        function_data=[FunctionInfo(
            function_name,
            {None: taint_bytes}
        ) for function_name, taint_bytes in polytracker_json_obj.items()
        ]
    )


def parse_format_v2(polytracker_json_obj: dict) -> ProgramTrace:
    return ProgramTrace(
        polytracker_version=(0, 0, 1, 'alpha2.1'),
        function_data=[FunctionInfo(
            name=function_name,
            input_bytes=function_data['input_bytes'],
            called_from=function_data['called_from']
        ) for function_name, function_data in polytracker_json_obj.items()
        ]
    )
