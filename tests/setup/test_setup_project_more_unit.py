"""Additional unit tests for functions in setup_project.py."""

import src.setup.app as sp


def test_build_dashboard_layout_smoke():
    # Use a simple string as content to ensure layout builds without error
    layout = sp._build_dashboard_layout("content")
    assert layout is not None


def test_view_program_descriptions_plain(monkeypatch):
    seq = ["1", "0"]
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default=None: seq.pop(0))
    monkeypatch.setattr(sp, "ui_menu", lambda items: None)
    monkeypatch.setattr(sp, "ui_rule", lambda t: None)
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    sp.view_program_descriptions()


# Note: interactive TUI variants that rely on Rich/prompt_toolkit are
# exercised indirectly via their lightweight module counterparts in
# tests under `tests/setup/ui/` where we avoid heavy dependencies.


def test_run_processing_pipeline_rich(monkeypatch):
    updates = []

    def updater(x):
        updates.append(x)

    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(
        sp, "_render_pipeline_table", lambda s1, s2, s3: f"T:{s1},{s2},{s3}"
    )
    monkeypatch.setattr(sp, "_status_label", lambda b: b)

    sp._run_processing_pipeline_rich(content_updater=updater)
    assert len(updates) >= 2


def test_run_processing_pipeline_plain_early(monkeypatch):
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)
    # Avoid interactive _run_pipeline_step by stubbing it to fail early
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: False)
    sp._run_processing_pipeline_plain()
