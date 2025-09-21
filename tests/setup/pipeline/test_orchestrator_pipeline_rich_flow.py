"""Test the rich/TUI processing pipeline flow in the orchestrator.

This test stubs interactive prompts and step execution so the rich
pipeline runner can be exercised deterministically. It captures the
renderables passed to the content updater to ensure the composition
and update logic is invoked throughout the run.
"""

from types import SimpleNamespace
from pathlib import Path

import src.setup.pipeline.orchestrator as orch


def test_run_processing_pipeline_rich_calls_updater(monkeypatch):
    """Run the rich pipeline with a simple updater and stubbed steps.

    The function should call the provided `content_updater` multiple
    times as the pipeline transitions through states.
    """
    calls = []

    def updater(val):
        # Record that an update was received; the exact type is not
        # important here, only that the call happened.
        calls.append(val)

    # Avoid real connectivity prompts and mark connectivity OK
    monkeypatch.setattr(orch, "ask_confirm", lambda *a, **k: False)
    # Ensure step runner always succeeds without spawning processes
    monkeypatch.setattr(orch, "_run_pipeline_step", lambda *a, **k: True)

    # Run the rich flow with our updater
    orch._run_processing_pipeline_rich(updater)

    # Expect multiple updates (initial + step transitions + final)
    assert len(calls) >= 3
    # At least one received object should expose either .items or be non-empty
    assert any(hasattr(c, "items") or c for c in calls)
