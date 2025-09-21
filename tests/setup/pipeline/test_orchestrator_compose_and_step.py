"""Unit tests for orchestrator compose/update and pipeline steps.

These tests exercise the TUI update composition logic and the
``_run_pipeline_step`` decision branches (yes, skip, invalid). The tests
avoid spawning subprocesses by monkeypatching the underlying
``run_program`` helper.
"""

from types import SimpleNamespace
from pathlib import Path

import src.setup.pipeline.orchestrator as orch


def test_set_tui_mode_and_compose_update(monkeypatch):
    """Test that setting TUI mode registers an updater and composes content.

    We register a simple updater that captures the last value passed to
    it and ensure ``_compose_and_update`` calls it with a container that
    exposes an ``items`` attribute.
    """
    captured = {}

    def updater(val):
        captured["val"] = val

    restore = orch.set_tui_mode(updater, None)
    try:
        # Set status and progress renderables and invoke compose
        orch._STATUS_RENDERABLE = "STATUS"
        orch._PROGRESS_RENDERABLE = "PROGRESS"
        orch._compose_and_update()
        assert "val" in captured
        # The updater should receive an object with `.items` containing our values
        got = captured["val"]
        assert hasattr(got, "items")
        assert got.items[0] == "STATUS"
        assert got.items[1] == "PROGRESS"
    finally:
        restore()


def test_run_pipeline_step_yes_and_failure(monkeypatch, tmp_path: Path):
    """When user confirms, run_program is invoked; failures show warning.

    We simulate user input 'y' and make ``run_program`` return False to
    exercise the failure branch which should return False.
    """
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default=None: "y")
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: False)
    # Should return False when program fails
    ok = orch._run_pipeline_step(
        "prompt_key",
        "program_x",
        Path("/tmp/prog.py"),
        "fail_key",
        "confirm_key",
    )
    assert ok is False


def test_run_pipeline_step_skip_and_invalid(monkeypatch, tmp_path: Path):
    """Test skip choice and invalid input branches for pipeline step."""
    # skip
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default=None: "s")
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: True)
    ok = orch._run_pipeline_step(
        "prompt_key",
        "program_x",
        Path("/tmp/prog.py"),
        "fail_key",
        "confirm_key",
        skip_message="skip_msg",
    )
    assert ok is True

    # invalid
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default=None: "nope")
    ok2 = orch._run_pipeline_step(
        "prompt_key",
        "program_x",
        Path("/tmp/prog.py"),
        "fail_key",
        "confirm_key",
    )
    assert ok2 is False
