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
import types
sp = types.SimpleNamespace()
setattr(sp, "_build_dashboard_layout", _app_ui._build_dashboard_layout)
setattr(sp, "view_program_descriptions", _app_prompts.view_program_descriptions)
setattr(sp, "ask_text", _app_prompts.ask_text)
setattr(sp, "_run_processing_pipeline_rich", _app_pipeline._run_processing_pipeline_rich)
setattr(sp, "_run_processing_pipeline_plain", _app_pipeline._run_processing_pipeline_plain)
setattr(sp, "ui_menu", _app_ui.ui_menu)
setattr(sp, "ui_rule", _app_ui.ui_rule)
setattr(sp, "ui_has_rich", _app_ui.ui_has_rich)


def test_build_dashboard_layout_smoke():
    """Smoke test for dashboard layout builder.

    Ensures ``_build_dashboard_layout`` returns a non-empty layout for
    simple input.

    Returns
    -------
    None
    """
    layout = sp._build_dashboard_layout("content")
    assert layout is not None


def test_view_program_descriptions_plain(monkeypatch):
    """Test plain program descriptions view.

    Patches concrete prompt and UI helpers to simulate selecting a
    program and then returning without raising.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to monkeypatch attributes.

    Returns
    -------
    None
    """
    seq = ["1", "0"]
    # Patch the concrete, underlying prompt implementation rather than
    # attempting to monkeypatch a legacy shim module object.
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt, default=None: seq.pop(0))
    monkeypatch.setattr("src.setup.app_ui.ui_menu", lambda items: None)
    monkeypatch.setattr("src.setup.app_ui.ui_rule", lambda t: None)
    monkeypatch.setattr("src.setup.app_ui.ui_has_rich", lambda: False)
    sp.view_program_descriptions()


# Note: interactive TUI variants that rely on Rich/prompt_toolkit are
# exercised indirectly via their lightweight module counterparts in
# tests under `tests/setup/ui/` where we avoid heavy dependencies.


def test_run_processing_pipeline_rich(monkeypatch):
    """Exercise the rich-processing pipeline runner with patched orchestrator helpers.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch orchestrator helpers.

    Returns
    -------
    None
    """
    updates = []

    def updater(x):
        updates.append(x)

    # Patch the orchestrator-level helpers directly to avoid interactive
    # prompts and to control step outcomes.
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(orchestrator, "run_ai_connectivity_check_interactive", lambda: True)
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(orchestrator, "_render_pipeline_table", lambda s1, s2, s3: f"T:{s1},{s2},{s3}")
    monkeypatch.setattr(orchestrator, "_status_label", lambda b: b)

    sp._run_processing_pipeline_rich(content_updater=updater)
    assert len(updates) >= 2


def test_run_processing_pipeline_plain_early(monkeypatch):
    """Exercise the plain-processing pipeline runner when user aborts early.

    Patches orchestrator prompt and pipeline step helpers to avoid
    interactive prompts and heavy processing.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch orchestrator helpers.

    Returns
    -------
    None
    """
    monkeypatch.setattr(orchestrator, "ask_confirm", lambda *a, **k: False)
    monkeypatch.setattr(orchestrator, "_run_pipeline_step", lambda *a, **k: False)
    sp._run_processing_pipeline_plain()
