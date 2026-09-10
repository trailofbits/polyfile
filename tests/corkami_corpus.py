"""Access to the Corkami "pocs" corpus of polyglot and edge-case files.

The corpus is downloaded on demand rather than vendored (``tests/.gitignore`` excludes it), so
importing this module is cheap and has no side effects.
"""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Iterator
import urllib.request
from zipfile import ZipFile, ZipInfo

CORKAMI_CORPUS_ZIP = Path(__file__).absolute().parent / "corkami.zip"
CORKAMI_URL = "https://github.com/corkami/pocs/archive/refs/heads/master.zip"


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
        with urllib.request.urlopen(CORKAMI_URL) as response, open(CORKAMI_CORPUS_ZIP, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

    @classmethod
    def ensure_downloaded(cls):
        if not CORKAMI_CORPUS_ZIP.exists():
            cls.download()

    @classmethod
    def read(cls, path_in_zip: str) -> bytes:
        """Returns the contents of one file in the corpus, downloading the corpus if necessary."""
        cls.ensure_downloaded()
        with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
            return z.read(path_in_zip)

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
