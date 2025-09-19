"""Additional unit tests for the pipeline orchestrator."""

from types import SimpleNamespace
from src.setup.pipeline import orchestrator
from src.setup import console_helpers as ch


def test_compose_and_update_with_fallback_group(monkeypatch):
    # Ensure TUI is enabled and updater captures the content
    captured = {}
    monkeypatch.setattr(orchestrator, "_TUI_MODE", True)
    monkeypatch.setattr(
        orchestrator, "_TUI_UPDATER", lambda c: captured.setdefault("c", c)
    )
    # Set status and progress renderables
    orchestrator._STATUS_RENDERABLE = "S"
    orchestrator._PROGRESS_RENDERABLE = "P"

    # Make the console_helpers.Group callable raise so the fallback is used
    monkeypatch.setattr(
        ch, "Group", lambda a, b: (_ for _ in ()).throw(RuntimeError("nope"))
    )

    orchestrator._compose_and_update()
    assert "c" in captured
    # Fallback Group stores items attribute
    assert hasattr(captured["c"], "items")
    assert captured["c"].items == ("S", "P")


def test_compose_and_update_status_only(monkeypatch):
    captured = {}
    monkeypatch.setattr(orchestrator, "_TUI_MODE", True)
    monkeypatch.setattr(
        orchestrator, "_TUI_UPDATER", lambda c: captured.setdefault("c", c)
    )
    orchestrator._STATUS_RENDERABLE = "ONLY"
    orchestrator._PROGRESS_RENDERABLE = None
    orchestrator._compose_and_update()
    assert captured["c"] == "ONLY"


def test_run_processing_pipeline_rich_full_flow(monkeypatch):
    updates = []

    def updater(x):
        updates.append(x)

    # Make confirmations and checks succeed and pipeline steps return True
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(
        orchestrator, "run_ai_connectivity_check_interactive", lambda: True
    )
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: True)
    # Ensure render table and status label use simple defaults
    monkeypatch.setattr(
        orchestrator, "_render_pipeline_table", lambda s1, s2, s3: f"T:{s1},{s2},{s3}"
    )
    monkeypatch.setattr(orchestrator, "_status_label", lambda base: base)

    orchestrator._run_processing_pipeline_rich(content_updater=updater)
    # Expect multiple updates (at least initial AI check panel + status changes)
    assert len(updates) >= 3


def test_run_processing_pipeline_rich_no_updater(monkeypatch):
    # No updater provided: exercise non-updater branch
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(
        orchestrator, "run_ai_connectivity_check_interactive", lambda: True
    )
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(orchestrator, "_render_pipeline_table", lambda s1, s2, s3: "T")
    orchestrator._run_processing_pipeline_rich(content_updater=None)


def test_run_processing_pipeline_rich_step_failures(monkeypatch):
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(
        orchestrator, "run_ai_connectivity_check_interactive", lambda: True
    )
    # First step succeeds, second fails, third succeeds
    seq = iter([True, False, True])
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: next(seq))
    monkeypatch.setattr(orchestrator, "_render_pipeline_table", lambda s1, s2, s3: "T")
    orchestrator._run_processing_pipeline_rich(content_updater=lambda x: None)
