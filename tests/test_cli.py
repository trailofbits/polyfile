import base64
import contextlib
import io
import json
import re
import shlex
from typing import Tuple
from unittest import TestCase
from zipfile import ZipFile

from polyfile.__main__ import FormatOutput, main
from polyfile.fileutils import Tempfile

USAGE_CHOICES = re.compile(r"--format \{([^}]*)}")
HELP_EXAMPLE = re.compile(r"^\s*polyfile INPUT_FILE (-\S+ \S+(?: -\S+ \S+)*)$", re.MULTILINE)
# some `struc` values are the `repr` of a matcher object, whose address differs between runs
OBJECT_ADDRESS = re.compile(r"0x[0-9a-f]+")


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
            with_contents = json.loads(OBJECT_ADDRESS.sub("0x0", run_cli("--format", "json", path)))
            without = json.loads(OBJECT_ADDRESS.sub("0x0", run_cli("--format", "json", "--no-contents", path)))
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
