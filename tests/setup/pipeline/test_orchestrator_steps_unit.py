"""Unit tests for various branches of the orchestrator step runner.
"""

import importlib

import src.setup.pipeline.orchestrator as orch


def test_compose_and_update_no_render(monkeypatch):
    called = {}

    def upd(content):
        called["c"] = content

    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", upd)
    orch._STATUS_RENDERABLE = None
    orch._PROGRESS_RENDERABLE = None
    orch._compose_and_update()
    assert "c" in called


def test_run_pipeline_step_yes_ok(monkeypatch):
    # choose 'y', run_program returns True
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: True
    )
    monkeypatch.setattr(orch, "ui_success", lambda m: None)
    res = orch._run_pipeline_step("p", "program_1", None, "fail", "ok")
    assert res is True


def test_run_pipeline_step_yes_fail(monkeypatch):
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(
        orch, "run_program", lambda name, path, stream_output=False: False
    )
    called = {}
    monkeypatch.setattr(orch, "ui_warning", lambda m: called.setdefault("w", m))
    res = orch._run_pipeline_step("p", "program_1", None, "fail", "ok")
    assert res is False
    assert "w" in called


def test_run_pipeline_step_skip_and_invalid(monkeypatch):
    # Skip
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "s")
    called = {}
    monkeypatch.setattr(orch, "ui_info", lambda m: called.setdefault("i", m))
    res = orch._run_pipeline_step(
        "p", "program_2", None, "fail", "ok", skip_message="skipped"
    )
    assert res is True or res is None

    # Invalid
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "x")
    called = {}
    monkeypatch.setattr(orch, "ui_warning", lambda m: called.setdefault("w", m))
    res2 = orch._run_pipeline_step("p", "program_1", None, "fail", "ok")
    assert res2 is False
    assert "w" in called
