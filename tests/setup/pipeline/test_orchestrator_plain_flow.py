"""Tests for the plain (non-Rich) processing pipeline flow in orchestrator.

These tests stub prompts and pipeline steps so the plain flow can be
executed deterministically and we can assert expected side-effects.
"""

import src.setup.pipeline.orchestrator as orch


def test_run_processing_pipeline_plain_success(monkeypatch, tmp_path):
    """When user confirms and steps succeed the pipeline completes.

    We stub confirm and pipeline step execution so that all steps
    report success and then assert that the final success message is shown
    via `ui_success`.
    """
    monkeypatch.setattr(orch, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(orch, "run_ai_connectivity_check_interactive", lambda: True)
    monkeypatch.setattr(orch, "_run_pipeline_step", lambda *a, **k: True)
    called = {}
    monkeypatch.setattr(orch, "ui_success", lambda m: called.setdefault("ok", m))
    orch._run_processing_pipeline_plain()
    assert "ok" in called


def test_run_processing_pipeline_plain_abort_on_confirm_false(monkeypatch):
    """If the user declines the connectivity check the pipeline returns early."""
    monkeypatch.setattr(orch, "ask_confirm", lambda *a, **k: False)
    # Should simply return without raising
    orch._run_processing_pipeline_plain()

