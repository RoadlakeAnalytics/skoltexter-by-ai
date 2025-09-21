"""Wrapper tests for :mod:`src.setup.pipeline.orchestrator`.

Cover the high-level wrapper functions that choose between Rich and
plain flows and map program names to runners.
"""

import src.setup.pipeline.orchestrator as orch


def test_run_processing_pipeline_chooses_plain_or_rich(monkeypatch):
    """`run_processing_pipeline` should call rich runner when `ui_has_rich` True.

    We stub the concrete implementations and assert the correct branch
    is selected.
    """
    called = {}
    monkeypatch.setattr(
        orch, "_run_processing_pipeline_plain", lambda: called.setdefault("plain", True)
    )
    monkeypatch.setattr(
        orch,
        "_run_processing_pipeline_rich",
        lambda *a, **k: called.setdefault("rich", True),
    )

    # Force plain path
    monkeypatch.setattr(orch, "ui_has_rich", lambda: False)
    orch.run_processing_pipeline(None)
    assert "plain" in called

    called.clear()
    # Force rich path
    monkeypatch.setattr(orch, "ui_has_rich", lambda: True)
    orch.run_processing_pipeline(None)
    assert "rich" in called


def test_run_pipeline_by_name_maps_to_runners(monkeypatch):
    """Verify program name mapping for known program identifiers."""
    called = {}
    monkeypatch.setattr(orch, "run_markdown", lambda: called.setdefault("m", True))
    monkeypatch.setattr(orch, "ai_processor_main", lambda: called.setdefault("a", True))
    monkeypatch.setattr(orch, "run_website", lambda: called.setdefault("w", True))

    assert orch.run_pipeline_by_name("program_1") is True
    assert "m" in called
    called.clear()
    assert orch.run_pipeline_by_name("program_2") is True
    assert "a" in called
    called.clear()
    assert orch.run_pipeline_by_name("program_3") is True
    assert "w" in called
