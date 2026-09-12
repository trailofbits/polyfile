import base64
import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterator, List, Tuple
from unittest import TestCase
from zipfile import ZipFile

from polyfile.__main__ import FormatOutput, main
from polyfile.fileutils import Tempfile

from .test_pdf import WELL_FORMED_PDF
from .test_zipmatcher import MEMBERS, PNG, build_zip

USAGE_CHOICES = re.compile(r"--format \{([^}]*)}")
HELP_EXAMPLE = re.compile(r"^\s*polyfile INPUT_FILE (-\S+ \S+(?: -\S+ \S+)*)$", re.MULTILINE)
OBJECT_REPR = re.compile(r"<[\w.]+ object at 0x[0-9a-f]+>")


def zip_file() -> bytes:
    """Builds the small ZIP archive that these tests hand to the command line."""
    contents = io.BytesIO()
    with ZipFile(contents, "w") as zf:
        zf.writestr("hello.txt", "hello, PolyFile\n")
    return contents.getvalue()


def run_cli(*argv: str) -> str:
    """Runs PolyFile's command line with the given arguments and returns what it wrote to STDOUT."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "--quiet", *argv])
    return output.getvalue()


def run_cli_until_exit(*argv: str) -> Tuple[int, str]:
    """Runs PolyFile's command line and returns its exit code and what it wrote to STDERR."""
    errors = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
        try:
            main(["polyfile", "--quiet", *argv])
        except SystemExit as exiting:
            return exiting.code, errors.getvalue()
    return 0, errors.getvalue()


def cli_help() -> str:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        with contextlib.suppress(SystemExit):
            main(["polyfile", "--help"])
    return output.getvalue()


class FormatArgumentTests(TestCase):
    """Tests that every output format the `--format` help advertises is one `--format` accepts.

    These tests prevent a regression to the behavior reported in
    https://github.com/trailofbits/polyfile/issues/3497, where `--format file` was the documented
    default and had an implemented output branch, but was missing from the argparse choices and so
    was rejected as an invalid choice; `json` was listed twice in the choices; and the example in
    the help text passed the formats to `--filetype` instead of `--format`.
    """

    zip_file: bytes

    @classmethod
    def setUpClass(cls):
        cls.zip_file = zip_file()

    def test_default_format_is_valid(self):
        self.assertIn(FormatOutput.default_format, FormatOutput.valid_formats)

    def test_every_format_is_accepted(self):
        with Tempfile(self.zip_file, suffix=".zip") as path:
            for output_format in FormatOutput.valid_formats:
                with self.subTest(output_format=output_format):
                    self.assertNotEqual(run_cli("--format", output_format, path), "")

    def test_no_duplicate_choices(self):
        choices = USAGE_CHOICES.search(cli_help())
        self.assertIsNotNone(choices, "the usage line does not list the `--format` choices")
        listed = choices.group(1).split(",")
        self.assertEqual(sorted(listed), sorted(set(listed)))
        self.assertEqual(sorted(listed), sorted(FormatOutput.valid_formats))

    def test_omitted_format_matches_the_default(self):
        with Tempfile(self.zip_file, suffix=".zip") as path:
            self.assertEqual(run_cli(path), run_cli("--format", FormatOutput.default_format, path))

    def test_help_example_runs(self):
        example = HELP_EXAMPLE.search(cli_help())
        self.assertIsNotNone(example, "the `--format` help no longer contains a runnable example")
        with Tempfile(self.zip_file, suffix=".zip") as path:
            output = run_cli(*shlex.split(example.group(1)), path)
        self.assertIn("application/zip", output)
        self.assertIn("\"b64contents\"", output)


class NoContentsTests(TestCase):
    """Tests for `--no-contents`, which drops the base64 encoding of the input from SBuD output.

    These tests cover the request in https://github.com/trailofbits/polyfile/issues/3399. The
    `b64contents` key scales with the size of the input, so it dominates the JSON output, and a
    consumer that does not need the contents has no way to ask PolyFile not to produce them.
    """

    zip_file: bytes

    @classmethod
    def setUpClass(cls):
        cls.zip_file = zip_file()

    def analyze(self, *argv: str) -> dict:
        with Tempfile(self.zip_file, suffix=".zip") as path:
            return json.loads(run_cli(*argv, path))

    def test_the_default_output_still_carries_the_contents(self):
        self.assertEqual(base64.b64encode(self.zip_file).decode("utf-8"),
                         self.analyze("--format", "json")["b64contents"])

    def test_the_key_is_omitted_rather_than_emptied(self):
        self.assertNotIn("b64contents", self.analyze("--format", "json", "--no-contents"))

    def test_the_sbud_format_honors_the_flag(self):
        self.assertNotIn("b64contents", self.analyze("--format", "sbud", "--no-contents"))

    def test_nothing_else_about_the_output_changes(self):
        with Tempfile(self.zip_file, suffix=".zip") as path:
            with_contents = json.loads(run_cli("--format", "json", path))
            without = json.loads(run_cli("--format", "json", "--no-contents", path))
        del with_contents["b64contents"]
        self.assertEqual(with_contents, without)

    def test_html_output_refuses_the_flag(self):
        """`polyfile/html.py` builds the hex viewer out of `b64contents`.

        Without this check the run reached `html.generate` and failed there, so the message the
        user saw depended on which output format happened to come first.
        """
        for argv in (("--format", "html"), ("--html", "-")):
            with self.subTest(argv=argv):
                with Tempfile(self.zip_file, suffix=".zip") as path:
                    code, errors = run_cli_until_exit(*argv, "--no-contents", path)
                self.assertEqual(1, code)
                self.assertIn("`--no-contents` cannot be combined with HTML output", errors)

    def test_html_output_is_refused_even_alongside_a_format_that_allows_it(self):
        with Tempfile(self.zip_file, suffix=".zip") as path:
            code, errors = run_cli_until_exit("--format", "json", "--format", "html", "--no-contents", path)
        self.assertEqual(1, code)
        self.assertIn("`--no-contents` cannot be combined with HTML output", errors)

    def test_formats_that_carry_no_contents_are_unaffected(self):
        with Tempfile(self.zip_file, suffix=".zip") as path:
            for output_format in ("file", "mime", "explain"):
                with self.subTest(output_format=output_format):
                    self.assertEqual(run_cli("--format", output_format, path),
                                     run_cli("--format", output_format, "--no-contents", path))


REPRODUCIBILITY_SCRIPT: str = """
import contextlib
import hashlib
import io
import sys
from polyfile.__main__ import main

RENDERINGS = (
    ["--format", "json", "--format", "sbud", "--format", "html"],
    ["--format", "json", "--no-contents"],
)

for path in sys.argv[1:]:
    for rendering in RENDERINGS:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["polyfile", "--quiet", *rendering, path])
        digest = hashlib.sha256(output.getvalue().encode("utf-8")).hexdigest()
        print(path, " ".join(rendering), digest)
"""
"""Renders each input every way that carries the match tree, and prints a digest of the result.

`--no-contents` is a second rendering rather than another `--format`, because it cannot be
combined with HTML output. The digest keeps a failure message short; what matters is that it
covers the bytes a consumer receives.
"""

SAMPLES: Dict[str, bytes] = {
    "sample.zip": build_zip(),
    "sample.png": PNG,
    "sample.pdf": WELL_FORMED_PDF,
}
"""One input for each kind of match tree PolyFile builds: ZIP records come from a struct
matcher, the PNG from a compiled Kaitai Struct parser, and the PDF from a hand-written one."""

HASH_SEEDS: Tuple[str, ...] = ("0", "1", "12345")
"""Values of `PYTHONHASHSEED`, so this also guards the match order that issue #3509 settled."""

RENDER_TIMEOUT_SECONDS: int = 300

ZIP_RECORDS: Tuple[str, ...] = ("LocalFileHeader", "CentralDirectory", "EndOfCentralDirectory")


def elements(sbud: Dict) -> Iterator[Dict]:
    """Yields every element of an SBuD document, parents before children."""
    stack: List[Dict] = list(reversed(sbud["struc"]))
    while stack:
        element = stack.pop()
        yield element
        stack.extend(reversed(element["subEls"]))


class ReproducibleOutputTests(TestCase):
    """Tests that PolyFile's structured output is a function of its input alone.

    These prevent a regression to the behavior reported in
    https://github.com/trailofbits/polyfile/issues/3581, where the `value` of a ZIP record's
    element came from `str()` on the `polyfile.structmatcher.PolyFileStruct` that produced it.
    That class defines no `__str__`, so the element carried the default `object.__str__`, which
    embeds the object's address. Address space layout randomization moves that address, so two
    runs over one file produced different JSON.
    """

    paths: Dict[str, str]

    @classmethod
    def setUpClass(cls):
        directory = TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.paths = {}
        for name, content in SAMPLES.items():
            path = Path(directory.name) / name
            path.write_bytes(content)
            cls.paths[name] = str(path)

    def test_output_is_identical_between_runs(self):
        """Tests that separate processes render one file's JSON, SBuD, and HTML identically.

        Separate processes are what makes this meaningful: the addresses a `repr` embeds are
        stable within one process, and Python randomizes the hash seed per process as well.
        """
        command = [sys.executable, "-c", REPRODUCIBILITY_SCRIPT, *self.paths.values()]
        reported: Dict[str, str] = {}
        for seed in HASH_SEEDS:
            result = subprocess.run(command, capture_output=True,
                                    env=dict(os.environ, PYTHONHASHSEED=seed),
                                    timeout=RENDER_TIMEOUT_SECONDS)
            self.assertEqual(0, result.returncode,
                             f"PYTHONHASHSEED={seed} failed: "
                             f"{result.stderr.decode('utf-8', 'replace')}")
            reported[seed] = result.stdout.decode("utf-8")
        detail = "".join(f"PYTHONHASHSEED={seed}:\n{output}" for seed, output in reported.items())
        self.assertEqual(1, len(set(reported.values())),
                         f"the output differs between runs:\n{detail}")

    def test_no_element_value_holds_an_object_repr(self):
        """Tests that no element reports a Python object instead of the content it describes."""
        for name, path in self.paths.items():
            with self.subTest(sample=name):
                self.assertNotRegex(run_cli("--format", "json", path), OBJECT_REPR)

    def test_zip_records_omit_the_value_their_fields_carry(self):
        """Tests the format `docs/json_format.md` documents for an element with no content.

        A ZIP record spans its fields and nothing else, so it reports no `value` of its own.
        Its fields still report theirs; stripping those too would lose the archive's contents.
        """
        sbud = json.loads(run_cli("--format", "json", self.paths["sample.zip"]))
        records = [element for element in elements(sbud) if element["type"] in ZIP_RECORDS]
        self.assertEqual(2 * len(MEMBERS) + 1, len(records))
        for record in records:
            self.assertNotIn("value", record)
            self.assertTrue(all("value" in field for field in record["subEls"]),
                            f"a field of {record['type']} lost its value")

    def test_omitting_the_contents_omits_nothing_else(self):
        """Tests that the two independent omissions do not interact.

        `--no-contents` drops `b64contents` from the top of the SBuD object, and an element with
        no content of its own drops `value`. Nothing else may go missing when both apply.
        """
        path = self.paths["sample.zip"]
        without = json.loads(run_cli("--format", "json", "--no-contents", path))
        self.assertNotIn("b64contents", without)
        records = [element for element in elements(without) if element["type"] in ZIP_RECORDS]
        self.assertEqual(2 * len(MEMBERS) + 1, len(records))
        for record in records:
            self.assertTrue(all("value" in field for field in record["subEls"]),
                            f"a field of {record['type']} lost its value")
