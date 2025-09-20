"""Unit tests for the pipeline orchestrator helper functions.

These tests exercise TUI updater composition, pipeline step branching and
the mapping between canonical program names and runner functions.
"""

import types
from types import SimpleNamespace
import sys

import src.setup.pipeline.orchestrator as orch


def test_set_tui_mode_and_restore():
    called = {}

    def updater(x):
        called["x"] = x

    def prompt_updater(x):
        called["p"] = x

    prev = (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER)
    restore = orch.set_tui_mode(updater, prompt_updater)
    assert orch._TUI_MODE is True and orch._TUI_UPDATER is updater
    restore()
    assert (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER) == prev


def test_compose_and_update_with_group(monkeypatch):
    # Ensure updater receives a composite object with `.items`
    received = {}

    def updater(content):
        received["content"] = content

    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", updater)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", None)
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "S")
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "P")
    try:
        orch._compose_and_update()
        assert "content" in received
        # The content should expose an .items attribute containing our two items
        assert hasattr(received["content"], "items")
        assert received["content"].items[0] == "S"
        assert received["content"].items[1] == "P"
    finally:
        monkeypatch.setattr(orch, "_TUI_MODE", False)
        monkeypatch.setattr(orch, "_TUI_UPDATER", None)
        monkeypatch.setattr(orch, "_STATUS_RENDERABLE", None)
        monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None)


def test_run_ai_connectivity_check_interactive(monkeypatch):
    # Success
    monkeypatch.setattr(orch, "run_ai_connectivity_check_silent", lambda: (True, "OK"))
    assert orch.run_ai_connectivity_check_interactive() is True
    # Failure
    monkeypatch.setattr(
        orch, "run_ai_connectivity_check_silent", lambda: (False, "ERR")
    )
    assert orch.run_ai_connectivity_check_interactive() is False


def test_run_pipeline_by_name_and_unknown(monkeypatch):
    # Known program 1
    monkeypatch.setattr(orch, "run_markdown", lambda: True)
    assert orch.run_pipeline_by_name("program_1") is True
    # Program 2 (ai main)
    called = {}

    def fake_ai():
        called["ai"] = True

    monkeypatch.setattr(orch, "ai_processor_main", fake_ai)
    assert orch.run_pipeline_by_name("program_2") is True
    assert called.get("ai") is True
    # Unknown falls back to run_program
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: True
    )
    assert orch.run_pipeline_by_name("unknown_prog") is True


def test_run_pipeline_step_branches(monkeypatch):
    # y + success
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: True
    )
    calls = {}
    monkeypatch.setattr(
        orch, "ui_success", lambda msg: calls.setdefault("success", msg)
    )
    ok = orch._run_pipeline_step(
        "run_program_1_prompt",
        "program_1",
        Path := types.SimpleNamespace(),
        "fail",
        "ok",
    )
    assert ok is True
    # y + fail
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: False
    )
    calls.clear()
    monkeypatch.setattr(orch, "ui_warning", lambda msg: calls.setdefault("warn", msg))
    ok2 = orch._run_pipeline_step(
        "run_program_1_prompt", "program_1", Path, "fail", "ok"
    )
    assert ok2 is False
    # skip
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "s")
    calls.clear()
    monkeypatch.setattr(orch, "ui_info", lambda msg: calls.setdefault("info", msg))
    ok3 = orch._run_pipeline_step(
        "run_program_1_prompt",
        "program_1",
        Path,
        "fail",
        "ok",
        skip_message="program_2_skipped",
    )
    assert ok3 is True
    # invalid
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "x")
    calls.clear()
    ok4 = orch._run_pipeline_step(
        "run_program_1_prompt", "program_1", Path, "fail", "ok"
    )
    assert ok4 is False
