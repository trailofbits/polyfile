"""Apply a requested Linux address-space ceiling before replacing this process."""

import os
import resource
import sys


def main(arguments: list[str]) -> None:
    """Sets the configured ceiling and executes the fixed decoder argument vector."""
    try:
        ceiling = int(arguments[0])
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
        os.execve(arguments[1], arguments[1:], os.environ)
    except (OSError, ValueError, OverflowError) as error:
        sys.stderr.write(f"cannot apply external decoder memory limit: {error}\n")
        raise SystemExit(125) from error


if __name__ == "__main__":
    main(sys.argv[1:])
