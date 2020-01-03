from typing import Dict, Iterable, List, Set

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

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, input_bytes={self.input_bytes!r}, called_from={self.called_from!r})"


class ProgramTrace:
    def __init__(self, polytracker_version: tuple, function_data: Iterable[FunctionInfo]):
        self.polytracker_version = polytracker_version
        self.functions: Dict[str, FunctionInfo] = {f.name: f for f in function_data}

    def build_cfg(self, merged_json_obj=None, only_labeled_functions=False) -> Digraph:
        dot = Digraph(comment='PolyTracker Program Trace')
        function_ids = {name: i for i, name in enumerate(self.functions)}
        if merged_json_obj is not None:
            function_labels = {
                func_name: ', '.join(['::'.join(label) for label in labels])
                for func_name, labels in polymerge.function_labels(merged_json_obj).items()
            }
        else:
            function_labels = {}
        for f in self.functions.values():
            if f.name in function_labels:
                label = f"{f.name} ({function_labels[f.name]})"
            else:
                label = f.name
            dot.node(f'func{function_ids[f.name]}', label=label)
        for f in self.functions.values():
            for caller in f.called_from:
                if caller not in function_ids:
                    caller_id = len(function_ids)
                    function_ids[caller] = caller_id
                    dot.node(f'func{ caller_id }', label=caller)
                dot.edge(f'func{function_ids[caller]}', f'func{function_ids[f.name]}')
        return dot

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
