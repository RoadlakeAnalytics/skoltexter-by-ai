"""Additional unit tests for functions in setup_project.py."""

import types
import sys as _sys

import src.setup.app_ui as _app_ui
import src.setup.app_pipeline as _app_pipeline
import src.setup.app_prompts as _app_prompts
import src.setup.pipeline.orchestrator as orchestrator

# Expose a compact `sp` module mapping the small set of helpers used
# by this test file. We register a real module object in
# ``sys.modules['src.setup.app']`` so code that expects a module (and
# uses importlib.reload) behaves deterministically.
_mod = types.ModuleType("src.setup.app")
setattr(_mod, "_build_dashboard_layout", _app_ui._build_dashboard_layout)
setattr(_mod, "view_program_descriptions", _app_prompts.view_program_descriptions)
setattr(_mod, "ask_text", _app_prompts.ask_text)
setattr(_mod, "_run_processing_pipeline_rich", _app_pipeline._run_processing_pipeline_rich)
setattr(_mod, "_run_processing_pipeline_plain", _app_pipeline._run_processing_pipeline_plain)
setattr(_mod, "ui_menu", _app_ui.ui_menu)
setattr(_mod, "ui_rule", _app_ui.ui_rule)
setattr(_mod, "ui_has_rich", _app_ui.ui_has_rich)
_sys.modules["src.setup.app"] = _mod
sp = _mod


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

    # Patch the orchestrator-level helpers directly to avoid interactive
    # prompts and to control step outcomes.
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(
        orchestrator, "run_ai_connectivity_check_interactive", lambda: True
    )
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(
        orchestrator, "_render_pipeline_table", lambda s1, s2, s3: f"T:{s1},{s2},{s3}"
    )
    monkeypatch.setattr(orchestrator, "_status_label", lambda b: b)

    sp._run_processing_pipeline_rich(content_updater=updater)
    assert len(updates) >= 2


def test_run_processing_pipeline_plain_early(monkeypatch):
    # Patch orchestrator-level prompt and pipeline step helpers to avoid
    # interactive prompts and heavy processing.
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: False)
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: False)
    sp._run_processing_pipeline_plain()
