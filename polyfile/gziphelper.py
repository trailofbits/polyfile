"""Capability-qualified GNU gzip discovery for legacy compression adapters."""

import re
import shutil
from pathlib import Path

from polyfile.compression import DecodeError
from polyfile.external import run_helper
from polyfile.fileutils import FileStream

_GNU_VERSION = re.compile(rb"^gzip (\d+)\.(\d+)(?:\r?\n|$)")


def find_gnu_gzip(*, helper_timeout: float | None = None) -> str:
    """Finds GNU gzip 1.15 or newer among the supported installed executable names.

    Args:
        helper_timeout: Optional timeout for each fixed version-query invocation.

    Returns:
        The absolute path of a supported installed GNU gzip executable.

    Raises:
        DecodeError: If no supported helper is installed or a requested limit is exceeded.
    """
    for name in ("ggzip", "gzip"):
        found = shutil.which(name)
        if found is None:
            continue
        executable = str(Path(found).resolve())
        try:
            with FileStream(b"") as stream:
                version = run_helper(
                    stream,
                    (executable, "--version"),
                    max_output=8192,
                    helper_timeout=helper_timeout,
                )
        except DecodeError as error:
            if error.status == "limited":
                raise
            continue
        matched = _GNU_VERSION.search(version)
        if (
            matched is not None
            and b"Free Software Foundation, Inc." in version
            and tuple(map(int, matched.groups())) >= (1, 15)
        ):
            return executable
    raise DecodeError(
        "decoding legacy compressed streams requires GNU gzip 1.15 or newer; "
        "install ggzip or gzip on PATH",
        status="unsupported",
    )
