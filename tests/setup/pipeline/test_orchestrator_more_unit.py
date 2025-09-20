"""Additional tests for orchestrator pipeline step logic."""

from types import SimpleNamespace

import src.setup.pipeline.orchestrator as orch


def test_run_pipeline_step_yes_ok(monkeypatch):
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: True)
    ok = orch._run_pipeline_step("prompt", "program_1", SimpleNamespace(), "fail", "ok")
    assert ok is True


def test_run_pipeline_step_yes_fail(monkeypatch):
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "y")
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: False)
    ok = orch._run_pipeline_step("prompt", "program_1", SimpleNamespace(), "fail", "ok")
    assert ok is False


def test_run_pipeline_step_skip_and_invalid(monkeypatch):
    # Skip with message
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "s")
    ok = orch._run_pipeline_step(
        "prompt", "program_1", SimpleNamespace(), "fail", "ok", skip_message="skip_msg"
    )
    assert ok is True
    # Invalid choice
    monkeypatch.setattr(orch, "ask_text", lambda p, default="y": "x")
    ok2 = orch._run_pipeline_step(
        "prompt", "program_1", SimpleNamespace(), "fail", "ok"
    )
    assert ok2 is False


def test_run_pipeline_by_name_mapping(monkeypatch):
    # program_1 maps to run_markdown
    monkeypatch.setattr(orch, "run_markdown", lambda: True)
    assert orch.run_pipeline_by_name("program_1") is True
    # program_2 calls ai_processor_main and returns True
    monkeypatch.setattr(orch, "ai_processor_main", lambda: None)
    assert orch.run_pipeline_by_name("program_2") is True
    # unknown falls back to run_program
    monkeypatch.setattr(orch, "run_program", lambda *a, **k: True)
    assert orch.run_pipeline_by_name("unknown_prog") is True
