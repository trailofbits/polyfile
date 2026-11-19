"""Access to the Corkami "pocs" corpus of polyglot and edge-case files.

The corpus is downloaded on demand rather than vendored (``tests/.gitignore`` excludes it), so
importing this module is cheap and has no side effects.
"""

import hashlib
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from collections.abc import Iterator
import urllib.request
from zipfile import ZipFile, ZipInfo

CORKAMI_CORPUS_ZIP = Path(__file__).absolute().parent / "corkami.zip"
CORKAMI_COMMIT = "6d277c83efdceb6916ee8c6efe6ff0639cc6193f"
CORKAMI_URL = f"https://codeload.github.com/corkami/pocs/zip/{CORKAMI_COMMIT}"
CORKAMI_SHA256 = "b76fbb4c371586fdec9e6850b9b266a41768a7ffa6ececd00aa6a96b6e18aa63"


def _checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class CorkamiFile:
    def __init__(self, path_in_zip: Path, info: ZipInfo):
        self.path_in_zip: Path = path_in_zip
        self.info: ZipInfo = info
        self._tmpdir: TemporaryDirectory = None  # type: ignore

    def __enter__(self) -> Path:
        self._tmpdir = TemporaryDirectory()
        self._tmpdir.__enter__()
        with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
            return Path(z.extract(self.info, self._tmpdir.name))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._tmpdir.__exit__(exc_type, exc_val, exc_tb)


class CorkamiCorpus:
    @classmethod
    def download(cls):
        with TemporaryDirectory(dir=CORKAMI_CORPUS_ZIP.parent) as directory:
            archive = Path(directory) / "corpus.zip"
            with urllib.request.urlopen(CORKAMI_URL) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
            actual = _checksum(archive)
            if actual != CORKAMI_SHA256:
                raise ValueError(
                    f"Corkami archive {CORKAMI_COMMIT}: expected SHA-256 {CORKAMI_SHA256}, "
                    f"received {actual}"
                )
            archive.replace(CORKAMI_CORPUS_ZIP)

    @classmethod
    def ensure_downloaded(cls):
        if not CORKAMI_CORPUS_ZIP.exists() or _checksum(CORKAMI_CORPUS_ZIP) != CORKAMI_SHA256:
            cls.download()

    @classmethod
    def read(cls, path_in_zip: str) -> bytes:
        """Returns the contents of one file in the corpus, downloading the corpus if necessary."""
        cls.ensure_downloaded()
        with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
            return z.read(f"pocs-{CORKAMI_COMMIT}/{path_in_zip}")

    @classmethod
    def files(cls) -> Iterator[CorkamiFile]:
        cls.ensure_downloaded()
        with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
            for info in z.infolist():
                if info.is_dir() or info.file_size <= 0:
                    continue
                path = Path(info.filename)
                if not path.name.startswith("."):
                    yield CorkamiFile(path_in_zip=path, info=info)
