from contextlib import contextmanager
import gzip
from pathlib import Path
import pickle
import signal
import struct
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Tuple
from unittest import skipUnless, TestCase
from urllib.error import URLError
import zipfile

from kaitaistruct import KaitaiStructError

from polyfile.kaitai.parser import KaitaiParser, PARSER_DIR, RootNode, Segment
from polyfile.kaitaimatcher import EXTRA_PARSERS, KAITAI_MIME_MAPPING
from polyfile.magic import MagicMatcher
from polyfile.polyfile import Matcher, Submatch

from .corkami_corpus import CorkamiCorpus

DER_CERTIFICATE = Path(__file__).absolute().parent / "msjdbc.cer.gz"
PARSE_TIMEOUT_SECONDS = 20


class TestKaitai(TestCase):
    def test_parser_load(self):
        self.assertIsNotNone(KaitaiParser.load("image/jpeg.ksy"))

    def test_parse_zip(self):
        f = NamedTemporaryFile("wb", delete=False)
        try:
            f.close()
            with zipfile.ZipFile(f.name, "w") as test_zip:
                test_zip.write(__file__)
            for node in KaitaiParser.load("archive/zip.ksy").parse(f.name).ast.dfs():
                with self.subTest(kaitai_node=node.name):
                    if node.parent is None:
                        self.assertIsInstance(node, RootNode)
                    else:
                        self.assertGreaterEqual(node.start, node.parent.start)
                        self.assertLessEqual(node.end, node.parent.end)
                        self.assertLessEqual(len(node.segment), len(node.parent.segment))
        finally:
            path = Path(f.name)
            if path.exists():
                try:
                    path.unlink()
                except PermissionError:
                    # This can sometimes happen on Windows due to a race condition
                    pass

    def test_segments(self):
        s = Segment(0, 10)
        self.assertTrue(s)
        self.assertEqual(s[:5], Segment(0, 5))
        self.assertEqual(s[-1], Segment(9, 10))
        self.assertEqual(s[1:3], Segment(1, 3))
        self.assertRaises(IndexError, s.__getitem__, -len(s) - 1)
        self.assertRaises(IndexError, s.__getitem__, len(s))
        self.assertRaises(ValueError, s.__getitem__, slice(0, 1, 5))
        self.assertFalse(s[20:30])


class TestKaitaiMimeMapping(TestCase):
    """Guards the invariants that make an entry in ``KAITAI_MIME_MAPPING`` do anything at all."""

    def test_mapping_keys_are_reachable(self):
        """Every mapped MIME type must be one that a PolyFile matcher can emit.

        Dispatch in :meth:`polyfile.polyfile.Matcher.handle_mimetype` is an exact lookup on the
        MIME type the magic matcher resolved, so a key that no matcher emits is dead code: the
        parser never runs and nothing reports an error. Eight entries had rotted this way by the
        time this test was written.
        """
        emittable = set(MagicMatcher.DEFAULT_INSTANCE.mimetypes)
        for mimetype in sorted(KAITAI_MIME_MAPPING):
            with self.subTest(mimetype=mimetype):
                self.assertIn(mimetype, emittable)

    def test_mapped_parsers_load(self):
        """Every mapped ``.ksy`` must resolve to an importable parser class."""
        registered = set(KAITAI_MIME_MAPPING.values()) | {ksy_path for _, ksy_path in EXTRA_PARSERS}
        for ksy_path in sorted(registered):
            with self.subTest(ksy_path=ksy_path):
                self.assertIsNotNone(KaitaiParser.load(ksy_path))


class TestGeneratedParsers(TestCase):
    """Guards against mapping a ``.ksy`` whose generated Python cannot even be imported."""

    # kaitai-struct-compiler 0.11 neither escapes Python reserved words used as identifiers nor
    # escapes backslashes in the docstrings it copies from a spec's `doc:` key, so these four
    # generated parsers are not valid Python and cannot be mapped:
    #
    #     wmf.py:32               `not = 6`     (enum member)
    #     sudoers_ts.py:22        `global = 1`  (enum member)
    #     openpgp_message.py:816  `self.class`  (sequence field)
    #     regf.py:14              an unescaped `\N` in a docstring
    KNOWN_UNCOMPILABLE = {
        "openpgp_message.py",
        "regf.py",
        "sudoers_ts.py",
        "wmf.py",
    }

    @staticmethod
    def compiles(path: Path) -> bool:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, ValueError):
            return False
        return True

    def test_generated_parsers_compile(self):
        for path in sorted(PARSER_DIR.glob("*.py")):
            if path.name in self.KNOWN_UNCOMPILABLE:
                continue
            with self.subTest(parser=path.name):
                self.assertTrue(self.compiles(path))

    def test_known_uncompilable_parsers_still_fail(self):
        """Prune ``KNOWN_UNCOMPILABLE`` once upstream fixes a parser, then consider mapping it."""
        for name in sorted(self.KNOWN_UNCOMPILABLE):
            with self.subTest(parser=name):
                self.assertFalse(self.compiles(PARSER_DIR / name))


class TestKaitaiParsing(TestCase):
    """Checks that each mapped specification extracts real structure from a real file.

    A specification that parses without error but yields nothing but a root node is not worth
    mapping, so every case asserts more than one AST node. ``StructNode.explore`` walks only
    ``SEQ_FIELDS`` and never ``instances:``, so specs that keep their content in ``instances:``
    (iso9660, id3v1_1, ext2 among them) fail that bar and are deliberately unmapped.
    """

    # Files from the Corkami "pocs" corpus, which is downloaded on demand.
    CORKAMI_SAMPLES: Tuple[Tuple[str, str], ...] = (
        ("image/gif.ksy", "mini/gif89.gif"),
        ("image/png.ksy", "mini/png.png"),
        ("image/jpeg.ksy", "mini/jpg.jpg"),
        ("image/bmp.ksy", "mini/bmp.bmp"),
        ("image/ico.ksy", "mini/ico.ico"),
        ("image/webp.ksy", "mini/webp.webp"),
        ("image/dicom.ksy", "mini/dicom.dcm"),
        ("media/avi.ksy", "mini/avi.avi"),
        ("media/wav.ksy", "mini/riff.wav"),
        ("media/ogg.ksy", "mini/vorbis.ogg"),
        ("media/quicktime_mov.ksy", "mini/qt.mov"),
        ("media/quicktime_mov.ksy", "mini/mp4.mp4"),
        ("executable/elf.ksy", "mini/mini.elf"),
        ("executable/mach_o.ksy", "mini/mini.macho"),
        ("executable/microsoft_pe.ksy", "mini/pe32.exe"),
        ("executable/java_class.ksy", "mini/java.class"),
        ("executable/swf.ksy", "mini/mini.swf"),
        ("archive/gzip.ksy", "mini/gzip.gz"),
        ("archive/cpio_old_le.ksy", "mini/binary.cpio"),
        ("game/doom_wad.ksy", "mini/wad.wad"),
    )

    @staticmethod
    def node_count(ksy_path: str, data: bytes) -> int:
        return len(list(KaitaiParser.load(ksy_path).parse(data).ast.dfs()))

    def test_corkami_samples(self):
        try:
            CorkamiCorpus.ensure_downloaded()
        except URLError as e:
            self.skipTest(f"could not download the Corkami corpus: {e}")
        for ksy_path, sample in self.CORKAMI_SAMPLES:
            with self.subTest(ksy_path=ksy_path, sample=sample):
                data = CorkamiCorpus.read(f"pocs-master/{sample}")
                self.assertGreater(self.node_count(ksy_path, data), 1)

    def test_synthesized_samples(self):
        """Covers mapped specs with no sample in the Corkami corpus."""
        samples = {
            "media/au.ksy": b".snd" + struct.pack(">IIIII", 24, 8, 1, 8000, 1) + bytes(8),
            "image/tga.ksy": (
                bytes([0, 0, 2, 0, 0, 0, 0, 0]) + struct.pack("<HHHHBB", 0, 0, 2, 2, 24, 0) + bytes(12)
            ),
            "media/creative_voice_file.ksy": (
                b"Creative Voice File\x1a" + struct.pack("<HHH", 26, 0x010A, 0x1129) + b"\x00"
            ),
            "serialization/python_pickle.ksy": pickle.dumps({"polyfile": [1, 2, 3]}),
            "serialization/asn1/asn1_der.ksy": gzip.decompress(DER_CERTIFICATE.read_bytes()),
        }
        for ksy_path, data in sorted(samples.items()):
            with self.subTest(ksy_path=ksy_path):
                self.assertGreater(self.node_count(ksy_path, data), 1)

    @skipUnless(hasattr(signal, "SIGALRM"), "bounding a runaway parse needs SIGALRM")
    def test_truncated_input_does_not_hang(self):
        """A truncated file must fail fast rather than loop forever.

        `archive/rar.ksy` is unmapped because it does loop forever on RAR5: its `blocks` field is
        `repeat: eos` over a switch whose v5 case consumes no bytes. This guards the mapped specs
        against the same shape of bug, which a plain parse test would hang on rather than fail.
        """
        try:
            CorkamiCorpus.ensure_downloaded()
        except URLError as e:
            self.skipTest(f"could not download the Corkami corpus: {e}")
        for ksy_path, sample in self.CORKAMI_SAMPLES:
            data = CorkamiCorpus.read(f"pocs-master/{sample}")
            for fraction in (10, 50, 90):
                truncated = data[:max(1, len(data) * fraction // 100)]
                with self.subTest(ksy_path=ksy_path, sample=sample, percent=fraction):
                    with self.assertCompletesQuickly(ksy_path):
                        try:
                            self.node_count(ksy_path, truncated)
                        except KaitaiStructError:
                            pass

    @contextmanager
    def assertCompletesQuickly(self, ksy_path: str, seconds: int = PARSE_TIMEOUT_SECONDS):
        def on_alarm(signum, frame):
            raise TimeoutError(f"{ksy_path} did not finish parsing within {seconds}s")

        previous = signal.signal(signal.SIGALRM, on_alarm)
        signal.alarm(seconds)
        try:
            yield
        except TimeoutError as e:
            self.fail(str(e))
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)


class TestKaitaiRegistration(TestCase):
    def test_parser_runs_end_to_end(self):
        """A mapped MIME type must actually dispatch its parser through `Matcher.match`."""
        try:
            CorkamiCorpus.ensure_downloaded()
        except URLError as e:
            self.skipTest(f"could not download the Corkami corpus: {e}")
        with TemporaryDirectory() as tmpdir:
            webp = Path(tmpdir) / "sample.webp"
            webp.write_bytes(CorkamiCorpus.read("pocs-master/mini/webp.webp"))
            matches = list(Matcher().match(webp))
        self.assertTrue(any(m.name == "image/webp" for m in matches))
        submatches = [m for m in matches if isinstance(m, Submatch)]
        self.assertGreater(len(submatches), 1)
