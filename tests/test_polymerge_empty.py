import pytest

from polyfile import __version__
from polymerge.polymerge import merge
from polymerge.polytracker import FunctionInfo, ProgramTrace


@pytest.mark.parametrize("offsets", [[], [0], [0, 1, 2]])
def test_empty_structure_has_no_function_associations(offsets: list[int]) -> None:
    trace = ProgramTrace((0, 0, 1), [FunctionInfo("reader", {None: offsets})])

    merged = merge({"versions": {"polyfile": __version__}, "struc": []}, trace)

    assert merged == {
        "versions": {
            "polyfile": __version__,
            "polymerge": __version__,
            "polytracker": "0.0.1",
        },
        "struc": [],
        "best_function_matches": {},
    }


def test_nonempty_structure_retains_its_function_associations() -> None:
    trace = ProgramTrace(
        (0, 0, 1), [FunctionInfo("reader", {None: [0, 1]}, called_from=("caller",))]
    )

    merged = merge(
        {"struc": [{"type": "header", "offset": 0, "size": 2, "subEls": []}]}, trace
    )

    assert merged["struc"][0]["functions"] == ["reader"]
