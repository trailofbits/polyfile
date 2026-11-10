"""Real-process tests for bounded external decoder transport and cleanup."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

from polyfile.compression import DecodeError
from polyfile.external import DIAGNOSTIC_BYTES, run_helper
from polyfile.fileutils import FileStream


def python_helper(code: str) -> tuple[str, ...]:
    return (sys.executable, "-I", "-c", code)


def test_all_pipes_are_drained_concurrently() -> None:
    data = b"input" * 100000
    code = (
        "import sys; sys.stderr.buffer.write(b'e'*262144); sys.stderr.flush(); "
        "sys.stdout.buffer.write(b'p'*262144); sys.stdout.flush(); "
        "sys.stdout.buffer.write(sys.stdin.buffer.read())"
    )
    with FileStream(data) as stream:
        result = run_helper(stream, python_helper(code), helper_timeout=10)
    assert result == b"p" * 262144 + data


def test_output_limit_is_checked_before_accepting_bytes() -> None:
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(
            stream,
            python_helper("import sys; sys.stdout.buffer.write(b'x'*1000000)"),
            max_output=15,
            helper_timeout=5,
        )
    assert error.value.status == "limited"
    assert "15-byte" in str(error.value)


def test_exact_output_boundary_and_zero_output() -> None:
    with FileStream(b"bytes") as stream:
        assert (
            run_helper(
                stream,
                python_helper("import sys; print(sys.stdin.read(),end='')"),
                max_output=5,
            )
            == b"bytes"
        )
    with FileStream(b"") as stream:
        assert run_helper(stream, python_helper("pass"), max_output=0) == b""


def test_failure_retains_bounded_diagnostics() -> None:
    code = "import sys; sys.stderr.buffer.write(b'E'*1000000); sys.exit(2)"
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(stream, python_helper(code), helper_timeout=5)
    assert error.value.status == "invalid"
    assert "E" * DIAGNOSTIC_BYTES in str(error.value)
    assert len(str(error.value)) < DIAGNOSTIC_BYTES + 100


def test_failed_helper_does_not_publish_partial_output() -> None:
    code = "import sys; print('partial'); print('corrupt data',file=sys.stderr); sys.exit(1)"
    with FileStream(b"") as stream, pytest.raises(DecodeError, match="corrupt data"):
        run_helper(stream, python_helper(code))


def test_missing_helper_is_an_explicit_unsupported_result(tmp_path: Path) -> None:
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(stream, (str(tmp_path / "missing-decoder"),))
    assert error.value.status == "unsupported"
    assert "cannot start" in str(error.value)


def test_relative_helper_command_is_rejected() -> None:
    with FileStream(b"") as stream, pytest.raises(ValueError, match="absolute"):
        run_helper(stream, ("gzip", "-d", "-c"))


def test_backend_environment_and_temporary_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GZIP", "untrusted inherited options")
    monkeypatch.setenv("PYTHONPATH", "untrusted module directory")
    code = (
        "import json,os; print(json.dumps({'cwd':os.getcwd(), 'tmp':os.environ['TMPDIR'], "
        "'gzip':os.environ.get('GZIP'),'pythonpath':os.environ.get('PYTHONPATH'),"
        "'lrzip':os.environ.get('LRZIP')}))"
    )
    with FileStream(b"") as stream:
        result = json.loads(
            run_helper(stream, python_helper(code), environment={"LRZIP": "NOCONFIG"})
        )
    assert result["gzip"] is None and result["pythonpath"] is None
    assert result["lrzip"] == "NOCONFIG"
    assert Path(result["cwd"]).resolve() == Path(result["tmp"]).resolve()
    assert not Path(result["cwd"]).exists()


@pytest.mark.skipif(os.name != "posix", reason="uses the POSIX process existence probe")
def test_timeout_kills_and_reaps_the_helper(tmp_path: Path) -> None:
    marker = tmp_path / "pid"
    code = (
        "import os,time; from pathlib import Path; "
        "Path(os.environ['POLYFILE_TEST_PID']).write_text(str(os.getpid())); time.sleep(30)"
    )
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(
            stream,
            python_helper(code),
            helper_timeout=0.5,
            environment={"POLYFILE_TEST_PID": str(marker)},
        )
    assert error.value.status == "limited"
    pid = int(marker.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_premature_input_close_is_reported() -> None:
    code = "import sys; sys.stdin.close(); print('partial')"
    with (
        FileStream(b"input" * 100000) as stream,
        pytest.raises(DecodeError, match="prematurely"),
    ):
        run_helper(stream, python_helper(code), helper_timeout=5)


@pytest.mark.parametrize("timeout", (0, -1, float("inf"), float("nan")))
def test_invalid_timeout_is_rejected(timeout: float) -> None:
    with FileStream(b"") as stream, pytest.raises(ValueError, match="helper_timeout"):
        run_helper(stream, python_helper("pass"), helper_timeout=timeout)


def test_requested_memory_limit_is_unsupported_off_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("polyfile.external.sys.platform", "darwin")
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(stream, python_helper("pass"), max_memory=100000000)
    assert error.value.status == "unsupported"
    assert "only on Linux" in str(error.value)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux hard-memory launcher")
def test_linux_memory_limit_is_applied_before_helper_execution() -> None:
    code = "import resource; print(resource.getrlimit(resource.RLIMIT_AS)[0])"
    with FileStream(b"") as stream:
        result = run_helper(stream, python_helper(code), max_memory=256 * 1024 * 1024)
    assert int(result) == 256 * 1024 * 1024


@pytest.mark.skipif(sys.platform != "linux", reason="Linux hard-memory launcher")
def test_linux_allocation_over_limit_is_reported() -> None:
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(
            stream,
            python_helper("value=bytearray(512*1024*1024)"),
            max_memory=128 * 1024 * 1024,
        )
    assert error.value.status == "limited"


def test_missing_child_module_path_is_not_resolved_from_working_directory() -> None:
    code = "import sys; print(sys.flags.isolated)"
    with FileStream(b"") as stream:
        assert run_helper(stream, python_helper(code)).strip() == b"1"


@pytest.mark.skipif(os.name != "posix", reason="POSIX group-signal fallback")
def test_group_signal_denial_still_kills_and_reaps_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(pid: int, signal: int) -> None:
        raise PermissionError("group signal unavailable")

    monkeypatch.setattr("polyfile.external.os.killpg", denied)
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(stream, python_helper("import time; time.sleep(30)"), helper_timeout=0.2)
    assert error.value.status == "limited"


def test_input_read_failure_is_reported_and_helper_is_reaped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_read(size: int) -> bytes:
        raise OSError("unreadable input")

    with FileStream(b"input") as stream, pytest.raises(DecodeError, match="unreadable input"):
        monkeypatch.setattr(stream, "read", failed_read)
        run_helper(stream, python_helper("import sys; sys.stdout.write(sys.stdin.read())"))


@pytest.mark.parametrize("timeout", (1e20, 1e308))
def test_large_finite_timeout_is_supported(timeout: float) -> None:
    with FileStream(b"") as stream:
        assert run_helper(stream, python_helper("pass"), helper_timeout=timeout) == b""


def test_unrepresentable_integer_timeout_is_rejected() -> None:
    with FileStream(b"") as stream, pytest.raises(ValueError, match="helper_timeout"):
        run_helper(stream, python_helper("pass"), helper_timeout=10**10000)


@pytest.mark.skipif(os.name != "posix", reason="POSIX decoder process group")
def test_timeout_closes_pipes_inherited_by_a_descendant_after_leader_exit() -> None:
    code = (
        "import subprocess,sys; subprocess.Popen([sys.executable,'-I','-c',"
        "'import time; time.sleep(2)'])"
    )
    started = time.monotonic()
    with FileStream(b"") as stream, pytest.raises(DecodeError) as error:
        run_helper(stream, python_helper(code), helper_timeout=0.2)
    assert error.value.status == "limited"
    assert time.monotonic() - started < 1.5
