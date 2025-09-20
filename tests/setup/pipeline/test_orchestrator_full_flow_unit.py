"""Integration-like unit tests for orchestrator full pipeline flows.

These tests stub external side-effects but execute the high-level flow so
we cover branches that announce pipeline completion and present the
output file path.
"""

from pathlib import Path

import src.setup.pipeline.orchestrator as orch


def test_run_processing_pipeline_plain_full(monkeypatch, tmp_path: Path):
    # Directly set module-level roots so the display message uses tmp_path
    monkeypatch.setattr(orch, "PROJECT_ROOT", tmp_path, raising=False)
    # Ensure index.html path exists to be realistic
    out = tmp_path / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text("<html></html>")
    # Force English messages for deterministic assertions
    monkeypatch.setattr(orch, "LANG", "en", raising=False)

    # Control interactive prompts and step execution
    monkeypatch.setattr(orch, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(orch, "run_ai_connectivity_check_interactive", lambda: True)
    monkeypatch.setattr(orch, "_run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(orch, "_render_pipeline_table", lambda s1, s2, s3: "TBL")
    monkeypatch.setattr(orch, "_status_label", lambda b: b)

    captured = {}

    def fake_rprint(msg):
        captured["msg"] = msg

    monkeypatch.setattr(orch, "rprint", fake_rprint)

    orch._run_processing_pipeline_plain()

    # Ensure completion message was emitted
    assert "pipeline_complete" in str(
        captured.get("msg", "")
    ) or "Open the file" in str(captured.get("msg", ""))
