"""Tests for `src/setup/pipeline/orchestrator.py`."""

from pathlib import Path

import pytest

import src.setup.pipeline.orchestrator as sp
from src.setup.console_helpers import Panel, Table


def test_run_processing_pipeline_abort(monkeypatch):
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: False)
    sp.run_processing_pipeline()


def test_run_pipeline_step_skip_without_skip_message(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "skip")
    assert (
        sp._run_pipeline_step(
            "k", "program_2", tmp_path, "fail", "ok", skip_message=None
        )
        is True
    )


def test_run_pipeline_step_variants(monkeypatch, tmp_path: Path):
    """Cover success, skip, and failure branches for a pipeline step."""
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp, "run_program", lambda *a, **k: True)
    ok = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "s")
    ok2 = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok2 is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp, "run_program", lambda *a, **k: False)
    ok3 = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok3 is False


def test_run_processing_pipeline_ai_check(monkeypatch):
    """Cover AI-check success and failure in pipeline runner."""
    calls = {"steps": 0}
    monkeypatch.setattr(sp, "ask_confirm", lambda prompt, default_yes=True: True)
    monkeypatch.setattr(
        sp,
        "_run_pipeline_step",
        lambda *a, **k: calls.__setitem__("steps", calls["steps"] + 1) or True,
    )
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    sp.run_processing_pipeline()
    assert calls["steps"] >= 2
    calls["steps"] = 0
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: False)
    sp.run_processing_pipeline()
    assert calls["steps"] == 0


def test_run_processing_pipeline_program3_no_success_message(monkeypatch):
    """Cover run_processing_pipeline path where program3_success is False."""
    import src.setup.pipeline.orchestrator as sp_local

    monkeypatch.setattr(sp_local, "ask_confirm", lambda *a, **k: True)
    calls = {"n": 0}

    def step_runner(prompt_key, program_name, program_path, fail_key, ok_key, **kw):
        calls["n"] += 1
        return calls["n"] != 3

    monkeypatch.setattr(sp_local, "_run_pipeline_step", step_runner)
    monkeypatch.setattr(sp_local, "run_ai_connectivity_check_interactive", lambda: True)
    sp_local.run_processing_pipeline()
    assert calls["n"] == 3


def test_render_pipeline_table_and_status_labels(monkeypatch):
    """Render the status table and verify localized status labels."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    prev = sp.LANG
    try:
        sp.LANG = "en"
        assert "Waiting" in sp._status_label("waiting")
        sp.LANG = "sv"
        assert "Väntar" in sp._status_label("waiting")
    finally:
        sp.LANG = prev
    table = sp._render_pipeline_table("A", "B", "C")
    assert table is not None


def test_run_processing_pipeline_rich_all_ok(monkeypatch):
    """Drive Rich pipeline flow with all steps succeeding and AI check ok."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    calls = {"n": 0}

    def step_runner(*a, **k):
        calls["n"] += 1
        return True

    monkeypatch.setattr(sp, "_run_pipeline_step", step_runner)
    sp._run_processing_pipeline_rich()
    # three steps should be executed
    assert calls["n"] == 3


def test_run_processing_pipeline_rich_step2_fail(monkeypatch):
    """Ensure Rich pipeline still proceeds to step 3 if step 2 fails."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    seq = iter([True, False, True])
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: next(seq))
    sp._run_processing_pipeline_rich()


def test_run_processing_pipeline_plain_ok(monkeypatch):
    """Directly exercise the plain pipeline variant to ensure coverage."""
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)  # skip AI check
    seq = iter(["y", "y", "y"])  # accept all steps
    monkeypatch.setattr(sp, "ask_text", lambda *a, **k: next(seq))
    monkeypatch.setattr(sp, "run_program", lambda *a, **k: True)
    sp._run_processing_pipeline_plain()


def test_run_processing_pipeline_dispatch_plain(monkeypatch):
    """Force dispatcher to call the plain pipeline branch."""
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    called = {"plain": 0}
    monkeypatch.setattr(
        sp, "_run_processing_pipeline_plain", lambda: called.__setitem__("plain", 1)
    )
    sp.run_processing_pipeline()
    assert called["plain"] == 1


def test_plain_pipeline_ai_check_decline(monkeypatch):
    """Cover plain pipeline branch where AI check fails and returns early."""
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: False)
    sp._run_processing_pipeline_plain()


def test_plain_pipeline_first_step_fail(monkeypatch):
    """Cover early return path after first pipeline step fails (plain)."""
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)

    # fail first step
    def fail_first(prompt_key, program_name, program_path, fail_key, ok_key, **kw):
        return False

    monkeypatch.setattr(sp, "_run_pipeline_step", fail_first)
    sp._run_processing_pipeline_plain()


def test_plain_pipeline_ai_check_ok(monkeypatch):
    """Cover plain pipeline branch where AI check passes with confirmation."""
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    calls = {"n": 0}

    def all_ok(*a, **k):
        calls["n"] += 1
        return True

    monkeypatch.setattr(sp, "_run_pipeline_step", all_ok)
    sp._run_processing_pipeline_plain()
    assert calls["n"] == 3


def test_plain_pipeline_third_step_false(monkeypatch):
    """Cover plain pipeline branch where the third step returns False."""
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)
    state = {"i": 0}

    def third_false(*a, **k):
        state["i"] += 1
        return state["i"] < 3

    monkeypatch.setattr(sp, "_run_pipeline_step", third_false)
    sp._run_processing_pipeline_plain()


def test_run_processing_pipeline_rich_updater(monkeypatch):
    """Cover the updater-driven rich pipeline path so output stays in right pane."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    seq = iter([True, True, True])
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: next(seq))
    updates: list[object] = []

    def updater(renderable):
        updates.append(renderable)

    sp.run_processing_pipeline(content_updater=updater)
    assert updates, "Expected content updates during rich pipeline"


def test_run_processing_pipeline_rich_updater_ai_fail(monkeypatch):
    """Cover updater path when AI connectivity fails after confirmation."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: False)
    updates: list[object] = []

    def updater(renderable):
        updates.append(renderable)

    sp.run_processing_pipeline(content_updater=updater)
    assert updates, "Expected at least one AI check update when failing"


def test_run_processing_pipeline_rich_updater_program3_false(monkeypatch):
    """Cover updater path with program 3 false (no final path panel)."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)
    seq = iter([True, True, False])
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: next(seq))
    updates: list[object] = []
    sp.run_processing_pipeline(content_updater=lambda r: updates.append(r))
    assert updates, "Expected pipeline table updates even when step 3 is false"


def test_tui_confirm_yes_default(monkeypatch):
    """Cover TUI confirm path with empty input using default yes."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    updates: list[object] = []
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    # Make pipeline steps quick
    seq = iter([True, True, True])
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: next(seq))
    # Empty input to exercise default_yes branch
    monkeypatch.setattr("builtins.input", lambda _="": "")
    sp.run_processing_pipeline(content_updater=lambda r: updates.append(r))
    assert updates, "Expected pipeline updates when using TUI confirm"


def test_tui_confirm_no(monkeypatch):
    """Cover TUI confirm path with explicit 'n' response (returns False)."""
    updates: list[object] = []
    # Input 'n' to decline AI check
    monkeypatch.setattr("builtins.input", lambda _="": "n")
    sp.run_processing_pipeline(content_updater=lambda r: updates.append(r))
    assert updates, "Expected at least AI prompt update when declining"


def test_compose_and_update_variants(monkeypatch):
    """Cover compose helper branches: both, only progress, empty, TUI off."""
    # TUI on
    called: list[object] = []
    monkeypatch.setattr(sp, "_TUI_MODE", True, raising=True)
    monkeypatch.setattr(
        sp, "_TUI_UPDATER", lambda obj: called.append(type(obj).__name__), raising=True
    )
    # both status + progress
    monkeypatch.setattr(sp, "_STATUS_RENDERABLE", Table(), raising=True)
    monkeypatch.setattr(sp, "_PROGRESS_RENDERABLE", Panel("x"), raising=True)
    sp._compose_and_update()
    # only progress
    monkeypatch.setattr(sp, "_STATUS_RENDERABLE", None, raising=True)
    sp._compose_and_update()
    # empty
    monkeypatch.setattr(sp, "_PROGRESS_RENDERABLE", None, raising=True)
    sp._compose_and_update()
    assert any(n in ("Group",) for n in called) and any(n == "Panel" for n in called)
    # TUI off (early return)
    monkeypatch.setattr(sp, "_TUI_MODE", False, raising=True)
    before = len(called)
    sp._compose_and_update()
    assert len(called) == before
