from typing import Dict, Iterable, List, Set

from .cfg import CFG


class FunctionInfo:
    def __init__(self, name: str, cmp_bytes: Dict[str, List[int]], input_bytes: Dict[str, List[int]] = None, called_from: Iterable[str] = ()):
        self.name = name
        self.called_from = frozenset(called_from)
        self.cmp_bytes = cmp_bytes
        if input_bytes is None:
            self.input_bytes = cmp_bytes
        else:
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, cmp_bytes={self.cmp_bytes!r}, input_bytes={self.input_bytes!r}, called_from={self.called_from!r})"


class ProgramTrace:
    def __init__(self, polytracker_version: tuple, function_data: Iterable[FunctionInfo]):
        self.polytracker_version = polytracker_version
        self.functions: Dict[str, FunctionInfo] = {f.name: f for f in function_data}
        self._cfg = None

    @property
    def cfg(self) -> CFG:
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
    function_data = []
    for function_name, data in polytracker_json_obj.items():
        if 'input_bytes' not in data:
            if 'cmp_bytes' in data:
                input_bytes = data['cmp_bytes']
            else:
                input_bytes = {}
        else:
            input_bytes = data['input_bytes']
        if 'cmp_bytes' in data:
            cmp_bytes = data['cmp_bytes']
        else:
            cmp_bytes = input_bytes
        if 'called_from' in data:
            called_from = data['called_from']
        else:
            called_from = ()
        function_data.append(FunctionInfo(
            name=function_name,
            cmp_bytes=cmp_bytes,
            input_bytes=input_bytes,
            called_from=called_from
        ))
    return ProgramTrace(
        polytracker_version=(0, 0, 1, 'alpha2.1'),
        function_data=function_data
    )
