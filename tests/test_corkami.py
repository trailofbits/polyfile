import zipfile
from functools import partial
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Set
from unittest import TestCase
import urllib.request
from zipfile import ZipFile

from polyfile.magic import MAGIC_DEFS, MagicMatcher

CORKAMI_CORPUS_ZIP = Path(__file__).absolute().parent / "corkami.zip"
CORKAMI_URL = "https://github.com/corkami/pocs/archive/refs/heads/master.zip"


class CorkamiCorpusTest(TestCase):
    default_matcher: MagicMatcher

    @classmethod
    def setUpClass(cls):
        # skip the DER definition because we don't yet support it (and none of the tests actually require it)
        cls.default_matcher = MagicMatcher.parse(*(d for d in MAGIC_DEFS if d.name != "der"))



if not CORKAMI_CORPUS_ZIP.exists():
    with urllib.request.urlopen(CORKAMI_URL) as response, open(CORKAMI_CORPUS_ZIP, "wb") as out_file:
        shutil.copyfileobj(response, out_file)


FILE_MIMETYPE_PATTERN = re.compile(rb"^(.*?:|-)\s*(?P<mime>[^\/\s]+\/[^\/;\s]+)\s*(;.*?$|$)(?P<remainder>.*)",
                                   re.MULTILINE)


def test_file(self: CorkamiCorpusTest, info: zipfile.ZipInfo):
    with TemporaryDirectory() as tmpdir:
        with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
            file_path = z.extract(info, tmpdir)
        orig_file_output = subprocess.check_output(["file", "-I", "--keep-going", str(file_path)])
        file_output = orig_file_output
        file_mimetypes: Set[str] = set()
        while file_output:
            m = FILE_MIMETYPE_PATTERN.match(file_output)
            if not m:
                break
            file_mimetypes.add(m.group("mime").decode("utf-8"))
            file_output = m.group("remainder")
        polyfile_mimetypes = {
            mimetype
            for match in self.default_matcher.match(file_path)
            for mimetype in match.mimetypes
        }
        if len(file_mimetypes & polyfile_mimetypes) != len(file_mimetypes):
            # there are some mimetypes that `file` matched by PolyFile missed
            if "application/octet-stream" in file_mimetypes and "application/octet-stream" not in polyfile_mimetypes:
                # this is just `file`'s default mime type, so take it out
                file_mimetypes -= {"application/octet-stream"}
            if len(file_mimetypes) != len(file_mimetypes & polyfile_mimetypes):
                # PolyFile is more accurate than `file` at detecting PDFs:
                missed_mimetypes = file_mimetypes - polyfile_mimetypes
                if len(missed_mimetypes) == 1 and "text/plain" in missed_mimetypes and "application/pdf" in \
                    polyfile_mimetypes:
                    # PolyFile just detected a PDF that `file` misclassified as text/plain!
                    pass
                else:
                    self.fail(f"`file` matched {file_mimetypes - polyfile_mimetypes!r} but PolyFile matched "
                              f"{polyfile_mimetypes - file_mimetypes}.\nOriginal `file` output was: "
                              f"{orig_file_output!r}")


def _init_tests():
    with ZipFile(CORKAMI_CORPUS_ZIP, "r") as z:
        for info in z.infolist():
            if info.is_dir() or info.file_size <= 0:
                continue
            path = Path(info.filename)
            if path.name.startswith("."):
                continue

            suffix = ""
            func_name = f"test_{path.stem}"
            while hasattr(CorkamiCorpusTest, f"{func_name}{suffix}"):
                if not suffix:
                    suffix = 2
                else:
                    suffix += 1

            def test(self: CorkamiCorpusTest, info=info):
                return test_file(self, info)

            setattr(CorkamiCorpusTest, f"{func_name}{suffix}", test)


_init_tests()
