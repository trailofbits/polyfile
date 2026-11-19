"""Verify fresh and cached differential corpora against the same pinned archive."""

import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests import corkami_corpus as corpus


@pytest.fixture
def archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    upstream = tmp_path / "upstream.zip"
    with ZipFile(upstream, "w") as files:
        for folder in ("a", "b"):
            files.writestr(f"pocs-{corpus.CORKAMI_COMMIT}/{folder}/sample.txt", folder)
    monkeypatch.setattr(corpus, "CORKAMI_URL", upstream.as_uri())
    monkeypatch.setattr(corpus, "CORKAMI_CORPUS_ZIP", tmp_path / "cache.zip")
    monkeypatch.setattr(corpus, "CORKAMI_SHA256", hashlib.sha256(upstream.read_bytes()).hexdigest())
    return upstream


def test_clean_stale_and_offline_caches_select_the_same_members(archive: Path) -> None:
    def contents() -> dict[str, bytes]:
        result = {}
        for member in corpus.CorkamiCorpus.files():
            with member as extracted:
                result[member.path_in_zip.parent.name] = extracted.read_bytes()
        return result

    assert contents() == {"a": b"a", "b": b"b"}
    corpus.CORKAMI_CORPUS_ZIP.write_bytes(b"old corpus")
    assert contents() == {"a": b"a", "b": b"b"}
    archive.unlink()
    assert corpus.CorkamiCorpus.read("b/sample.txt") == b"b"


def test_invalid_download_preserves_existing_cache(archive: Path) -> None:
    corpus.CORKAMI_CORPUS_ZIP.write_bytes(b"old corpus")
    archive.write_bytes(b"unverified download")
    with pytest.raises(ValueError, match="expected SHA-256"):
        list(corpus.CorkamiCorpus.files())
    assert corpus.CORKAMI_CORPUS_ZIP.read_bytes() == b"old corpus"
