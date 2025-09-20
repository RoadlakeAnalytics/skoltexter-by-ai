"""Tests to exercise the full pipeline flows in the orchestrator.

These tests stub out the prompts and step execution functions so the
rich/plain pipeline runners can be exercised deterministically and in
isolation.
"""

from types import SimpleNamespace

import importlib

import src.setup.pipeline.orchestrator as orch


def test_run_processing_pipeline_rich_updates_and_completes(monkeypatch):
    """The rich pipeline runner should invoke the provided updater repeatedly."""
    updates = []

    def update_right(obj):
        updates.append(obj)

    # Ensure AI check passes and each pipeline step reports success
    monkeypatch.setattr(orch, "ask_confirm", lambda p, default_yes=True: True)
    monkeypatch.setattr(orch, "run_ai_connectivity_check_interactive", lambda: True)
    monkeypatch.setattr(orch, "_run_pipeline_step", lambda *a, **k: True)

    orch._run_processing_pipeline_rich(update_right)
    assert updates, "Updater was not called during rich pipeline"


def test_run_processing_pipeline_plain_flow_runs_all_steps(monkeypatch):
    """The plain pipeline runner executes steps and prints success without error."""
    monkeypatch.setattr(orch, "ask_confirm", lambda p, default_yes=True: True)
    monkeypatch.setattr(orch, "run_ai_connectivity_check_interactive", lambda: True)
    # Make steps succeed
    monkeypatch.setattr(orch, "_run_pipeline_step", lambda *a, **k: True)

    # Should not raise
    orch._run_processing_pipeline_plain()
