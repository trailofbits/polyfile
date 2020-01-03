from graphviz import Digraph
import networkx as nx

from . import polymerge
from .polytracker import ProgramTrace


class CFG(nx.DiGraph):
    def __init__(self, trace: ProgramTrace):
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
