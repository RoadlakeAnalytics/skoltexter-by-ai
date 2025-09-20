"""Extra unit tests for the pipeline orchestrator.

These tests exercise TUI composition, mode toggling and the prompt-driven
step runner. They use lightweight monkeypatching to avoid spawning
subprocesses or requiring Rich to be installed.
"""

from pathlib import Path
from types import SimpleNamespace

import src.setup.pipeline.orchestrator as orch


def test_compose_and_update_group_fallback(monkeypatch):
    """When both status and progress renderables are set the updater receives
    a container with an ``items`` attribute holding the two objects.
    """
    captured = {}

    def updater(content):
        captured["content"] = content

    # Enable TUI mode and register our capturing updater
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", updater)
    # Provide simple renderables
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "STATUS")
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "PROG")

    # Run the compose/update flow
    orch._compose_and_update()

    assert "content" in captured
    got = captured["content"]
    # The fallback Group stores items in `.items`
    assert hasattr(got, "items")
    assert tuple(got.items) == ("STATUS", "PROG")


def test_set_tui_mode_restore(monkeypatch):
    """set_tui_mode returns a restore function that reverts module globals."""
    # Record previous state
    prev_mode = orch._TUI_MODE
    prev_updater = orch._TUI_UPDATER

    def dummy(u):
        pass

    restore = orch.set_tui_mode(dummy, None)
    try:
        assert orch._TUI_MODE is True
        assert orch._TUI_UPDATER is dummy
    finally:
        restore()

    assert orch._TUI_MODE == prev_mode
    assert orch._TUI_UPDATER == prev_updater


def test_run_pipeline_step_branches(monkeypatch):
    """Exercise yes/skip/invalid choices for the interactive step runner."""
    # Make translations identity to simplify assertions
    monkeypatch.setattr(orch, "_", lambda k: k)

    calls = {"success": [], "warn": [], "info": []}
    monkeypatch.setattr(orch, "ui_success", lambda msg: calls["success"].append(msg))
    monkeypatch.setattr(orch, "ui_warning", lambda msg: calls["warn"].append(msg))
    monkeypatch.setattr(orch, "ui_info", lambda msg: calls["info"].append(msg))

    # 1) Yes and program succeeds
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: True
    )
    ok = orch._run_pipeline_step("p", "program_1", Path("x"), "fail", "confirm")
    assert ok is True
    assert calls["success"] and calls["success"][-1] == "confirm"

    # 2) Yes but program fails
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: False)
    calls["warn"].clear()
    ok = orch._run_pipeline_step("p", "program_1", Path("x"), "fail_key", "confirm")
    assert ok is False
    assert any("fail_key" in str(w) for w in calls["warn"])

    # 3) Skip with skip_message
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "s")
    calls["info"].clear()
    ok = orch._run_pipeline_step(
        "p", "program_2", Path("x"), "fail_key", "confirmed", skip_message="skipped"
    )
    assert ok is True
    assert calls["info"] and calls["info"][-1] == "skipped"

    # 4) Invalid choice
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "x")
    calls["warn"].clear()
    ok = orch._run_pipeline_step("p", "program_2", Path("x"), "fail_key", "confirmed")
    assert ok is False
    assert calls["warn"]


def test_run_pipeline_by_name_maps(monkeypatch):
    """Ensure canonical program names map to the correct runners."""
    # program_1 -> run_markdown
    monkeypatch.setattr(orch, "run_markdown", lambda: True)
    assert orch.run_pipeline_by_name("program_1") is True

    # program_2 -> ai_processor_main (calls and returns True)
    called = {}

    def fake_ai_main():
        called["ai"] = True

    monkeypatch.setattr(orch, "ai_processor_main", fake_ai_main)
    assert orch.run_pipeline_by_name("program_2") is True
    assert called.get("ai") is True

    # program_3 -> run_website
    monkeypatch.setattr(orch, "run_website", lambda: True)
    assert orch.run_pipeline_by_name("program_3") is True

    # unknown -> falls back to run_program
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: True
    )
    assert orch.run_pipeline_by_name("program_x", stream_output=True) is True
