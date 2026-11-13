"""Behavioral checks for stderr diagnostics and live work tracking."""

import io
import logging
from contextlib import redirect_stderr, redirect_stdout

import pytest
from rich.console import Console

from polyfile import logger
from polyfile.iterators import LazyIterableSet
from polyfile.magic import MagicMatcher, Match, MatchContext


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def frame(session: logger.TerminalSession) -> str:
    output = io.StringIO()
    Console(file=output, width=100).print(session.render())
    return output.getvalue()


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("CI", raising=False)
    return Terminal()


def test_redirected_stderr_keeps_only_diagnostics():
    output, errors = io.StringIO(), io.StringIO()
    log = logger.getStatusLogger("polyfile.child")
    with redirect_stdout(output), redirect_stderr(errors), logger.logging_context():
        log.status("working")
        log.info("discovery")
        log.warning("warning [red] \x1b[2J")
        log.error("failure")
    assert output.getvalue() == ""
    assert "working" not in errors.getvalue()
    assert "discovery" not in errors.getvalue()
    assert errors.getvalue().count("warning [red]") == 1
    assert "failure" in errors.getvalue()
    assert "\\x1b[2J" in errors.getvalue()
    assert "\x1b" not in errors.getvalue()


@pytest.mark.parametrize("level", [logging.DEBUG, logger.TRACE])
def test_explicit_verbose_logs_survive_redirection(level):
    errors = io.StringIO()
    with logger.logging_context(level, stream=errors):
        log = logger.getStatusLogger("polyfile")
        log.debug("details")
        log.trace("trace details")
        log.status("working")
    assert "details" in errors.getvalue()
    assert ("trace details" in errors.getvalue()) == (level == logger.TRACE)
    assert "working" not in errors.getvalue()


def test_quiet_suppresses_even_critical_logs(terminal):
    with logger.logging_context(logger.TRACE, quiet=True, stream=terminal):
        log = logger.getStatusLogger("polyfile")
        log.status("working")
        log.critical("failure")
        assert list(log.range([1, 2])) == [1, 2]
    assert terminal.getvalue() == ""


def test_context_restores_host_logging_after_failure(terminal):
    root = logging.getLogger()
    handlers, level, factory = root.handlers[:], root.level, logging.getLoggerClass()
    for _ in range(2):
        with pytest.raises(ValueError), logger.logging_context(stream=terminal):
            logger.getStatusLogger("polyfile.child").warning("one message")
            raise ValueError("failed")
        assert root.handlers == handlers
        assert root.level == level
        assert logging.getLoggerClass() is factory
    assert terminal.getvalue().count("one message") == 2


def test_progress_counts_processed_items_and_cleans_up(terminal):
    with logger.logging_context(stream=terminal) as session:
        work = logger.getStatusLogger("polyfile").range(
            [1, 2], "Checking", " tests", update_interval=0
        )
        assert next(work) == 1
        assert "0/2 tests" in frame(session)
        assert next(work) == 2
        assert "1/2 tests" in frame(session)
        work.close()
        assert "Checking" not in frame(session)
    assert "\x1b[?25h" in terminal.getvalue()


def test_nested_progress_restores_parent(terminal):
    with logger.logging_context(stream=terminal) as session:
        log = logger.getStatusLogger("polyfile")
        parent = log.range([1, 2], "Parent", update_interval=0)
        next(parent)
        child = log.range([3], "Child", update_interval=0)
        next(child)
        assert "Child" in frame(session)
        assert "Parent" not in frame(session)
        child.close()
        assert "Parent" in frame(session)
        assert "Child" not in frame(session)
        parent.close()


def test_empty_work_and_delayed_work_do_not_animate(terminal):
    with logger.logging_context(stream=terminal) as session:
        log = logger.getStatusLogger("polyfile")
        assert list(log.range([], "Empty")) == []
        assert list(log.range([1], "Delayed", delay=60)) == [1]
        assert not session.live.is_started
    assert terminal.getvalue() == ""


def test_suspension_does_not_redirect_streams(terminal):
    output = io.StringIO()
    with redirect_stdout(output), logger.logging_context(stream=terminal) as session:
        logger.getStatusLogger("polyfile").status("Working")
        with session.suspend():
            assert not session.live.is_started
            print("result")
        assert session.live.is_started
    assert output.getvalue() == "result\n"
    assert "result" not in terminal.getvalue()


def test_force_color_does_not_enable_redirected_status(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    errors = io.StringIO()
    with logger.logging_context(stream=errors):
        log = logger.getStatusLogger("polyfile")
        log.status("working")
        log.warning("diagnostic")
    assert "\x1b" not in errors.getvalue()
    assert "working" not in errors.getvalue()


def test_no_color_removes_severity_colors(terminal, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    with logger.logging_context(stream=terminal):
        logger.getStatusLogger("polyfile").warning("diagnostic")
    assert "diagnostic" in terminal.getvalue()
    assert "\x1b[33m" not in terminal.getvalue()


def test_delayed_progress_appears_after_delay(terminal, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(logger, "monotonic", lambda: now[0])
    with logger.logging_context(stream=terminal) as session:
        work = logger.getStatusLogger("polyfile").range(
            [1, 2], "Checking", delay=1, update_interval=0
        )
        next(work)
        assert not session.live.is_started
        now[0] = 2
        next(work)
        assert session.live.is_started
        assert "1/2" in frame(session)
        work.close()


def test_abandoned_nested_work_cannot_restart_a_closed_session(terminal):
    with logger.logging_context(stream=terminal):
        log = logger.getStatusLogger("polyfile")
        parent = log.range([1], "Parent")
        child = log.range([2], "Child")
        next(parent)
        next(child)
    completed_output = terminal.getvalue()
    child.close()
    parent.close()
    assert terminal.getvalue() == completed_output


def test_file_display_does_not_evaluate_unused_match_details(terminal):
    class RenderedMatch(Match):
        @property
        def mimetypes(self) -> LazyIterableSet[str]:
            raise AssertionError("display resolved an unused MIME label")

        def __str__(self) -> str:
            raise AssertionError("display rendered the description again")

    match = RenderedMatch(MagicMatcher(), MatchContext(b"input"), ())
    with logger.logging_context(stream=terminal) as session:
        session.start_scan("input", recursive=False)
        logger.report_file_identification(match, "Existing identification description")
        assert len(session.tree) == 1
        assert "Existing identification description" in frame(session)
