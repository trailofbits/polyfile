"""Loading serialized search roots returns to the caller without terminal output."""

from io import BytesIO

import pytest

from polyfile import serialization
from polyfile.search import ACNode, MultiSequenceSearch


def test_load_returns_an_acyclic_search_without_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with BytesIO() as stream:
        serialization.dump(ACNode(), stream)
        stream.seek(0)
        search = MultiSequenceSearch.load(stream)
    assert isinstance(search, MultiSequenceSearch)
    assert isinstance(search.trie, ACNode)
    assert list(search.search(b"example")) == []
    assert capsys.readouterr() == ("", "")


def test_load_rejects_a_serialized_value_that_is_not_a_search_root() -> None:
    with BytesIO() as stream:
        serialization.dump(42, stream)
        stream.seek(0)
        with pytest.raises(ValueError, match="search root.*ACNode"):
            MultiSequenceSearch.load(stream)
