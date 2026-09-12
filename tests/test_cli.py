import contextlib
import io
import re
import shlex
from unittest import TestCase
from zipfile import ZipFile

from polyfile.__main__ import FormatOutput, main
from polyfile.fileutils import Tempfile

USAGE_CHOICES = re.compile(r"--format \{([^}]*)}")
HELP_EXAMPLE = re.compile(r"^\s*polyfile INPUT_FILE (-\S+ \S+(?: -\S+ \S+)*)$", re.MULTILINE)


def run_cli(*argv: str) -> str:
    """Runs PolyFile's command line with the given arguments and returns what it wrote to STDOUT."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(["polyfile", "--quiet", *argv])
    return output.getvalue()


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
        contents = io.BytesIO()
        with ZipFile(contents, "w") as zf:
            zf.writestr("hello.txt", "hello, PolyFile\n")
        cls.zip_file = contents.getvalue()

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
