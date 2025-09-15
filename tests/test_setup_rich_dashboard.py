"""Additional tests for Rich dashboard and bootstrap modes in setup_project.

These tests aim to cover Rich-specific rendering helpers and flows to
avoid unnecessary no-cover pragmas, while keeping side effects contained.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import setup_project as sp

def test_main_menu_rich_dashboard_routes(monkeypatch):
    """Exercise Rich dashboard menu choices and ensure handlers are called."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    calls = {"env": 0, "desc": 0, "pipe": 0, "logs": 0, "reset": 0, "q": 0, "qq": 0}
    monkeypatch.setattr(
        sp,
        "manage_virtual_environment",
        lambda: calls.__setitem__("env", calls["env"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "view_program_descriptions",
        lambda: calls.__setitem__("desc", calls["desc"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "run_processing_pipeline",
        lambda: calls.__setitem__("pipe", calls["pipe"] + 1),
    )
    monkeypatch.setattr(
        sp, "view_logs", lambda: calls.__setitem__("logs", calls["logs"] + 1)
    )
    monkeypatch.setattr(
        sp, "reset_project", lambda: calls.__setitem__("reset", calls["reset"] + 1)
    )
    monkeypatch.setattr(
        sp, "run_full_quality_suite", lambda: calls.__setitem__("q", calls["q"] + 1)
    )
    monkeypatch.setattr(
        sp,
        "run_extreme_quality_suite",
        lambda: calls.__setitem__("qq", calls["qq"] + 1),
    )

    seq = iter(["1", "2", "3", "4", "5", "q", "qq", "6"])  # then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()
    assert calls == {
        "env": 1,
        "desc": 1,
        "pipe": 1,
        "logs": 1,
        "reset": 1,
        "q": 1,
        "qq": 1,
    }

def test_view_logs_rich_prints_syntax(monkeypatch, tmp_path: Path):
    """Verify that rich Syntax is used when viewing logs under rich UI."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    logf = tmp_path / "t.log"
    logf.write_text("hello syntax", encoding="utf-8")
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    seq = iter(["1", "0"])  # open first log, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))

    captured = {"types": []}

    def cap_print(obj, *a, **k):
        captured["types"].append(type(obj).__name__)

    # Replace rprint to capture first argument type
    monkeypatch.setattr(sp, "rprint", cap_print)
    sp.view_logs()
    assert "Syntax" in captured["types"]

def test_entry_point_bootstrap_mode(monkeypatch):
    """Trigger bootstrap mode: no rich, no questionary, no --no-venv flag."""
    # Force parse_cli_args to return no-venv=False and no lang
    monkeypatch.setattr(
        sp, "parse_cli_args", lambda: SimpleNamespace(lang=None, no_venv=False)
    )
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    monkeypatch.setattr(sp, "_HAS_Q", False, raising=False)
    called = {"venv": 0}
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr(
        sp, "manage_virtual_environment", lambda: called.__setitem__("venv", 1)
    )

    def _exit(_code=0):
        raise SystemExit

    monkeypatch.setattr(sp.sys, "exit", _exit)
    with pytest.raises(SystemExit):
        sp.entry_point()
    assert called["venv"] == 1

def test_main_menu_plain_flow(monkeypatch):
    """Exercise the plain main menu including invalid input then exit."""
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    # No-op handlers
    monkeypatch.setattr(sp, "manage_virtual_environment", lambda: None)
    monkeypatch.setattr(sp, "view_program_descriptions", lambda: None)
    monkeypatch.setattr(sp, "run_processing_pipeline", lambda: None)
    monkeypatch.setattr(sp, "view_logs", lambda: None)
    monkeypatch.setattr(sp, "reset_project", lambda: None)
    monkeypatch.setattr(sp, "run_full_quality_suite", lambda: None)
    monkeypatch.setattr(sp, "run_extreme_quality_suite", lambda: None)
    seq = iter(
        ["x", "1", "2", "3", "4", "5", "q", "qq", "6"]
    )  # invalid then all then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_plain()

def test_view_logs_plain_print(monkeypatch, tmp_path: Path, capsys):
    """Cover non-rich branch in log viewing by forcing plain output path."""
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    logf = tmp_path / "t2.log"
    logf.write_text("plain content", encoding="utf-8")
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    seq = iter(["1", "0"])  # open first log then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_logs()
    out = capsys.readouterr().out
    assert "plain content" in out

def test_main_menu_dispatch_plain(monkeypatch):
    """Ensure dispatcher main_menu calls plain branch when rich is unavailable."""
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    # Plain menu will read once and exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "6")
    # No-op handlers to avoid side-effects
    monkeypatch.setattr(sp, "_main_menu_plain", lambda: None)
    sp.main_menu()

def test_view_program_descriptions_non_rich(monkeypatch, capsys):
    """Exercise non-rich path of program descriptions viewer."""
    monkeypatch.setattr(sp, "ui_has_rich", lambda: False)
    seq = iter(["1", "0"])  # view first, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_program_descriptions()
    out = capsys.readouterr().out
    assert "Program 1" in out or "Generera" in out

def test_main_menu_rich_only_descriptions(monkeypatch):
    """Ensure rich dashboard follows '2' branch without hitting '1' first."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    calls = {"desc": 0}
    monkeypatch.setattr(
        sp,
        "view_program_descriptions",
        lambda: calls.__setitem__("desc", calls["desc"] + 1),
    )
    seq = iter(["2", "6"])  # go to descriptions, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()
    assert calls["desc"] == 1

def test_main_menu_rich_exit_immediately(monkeypatch):
    """Exercise rich dashboard exit path without touching choice '1'."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    seq = iter(["6"])  # Exit directly
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()

def test_main_menu_rich_console_none_branch(monkeypatch):
    """Force the `_RICH_CONSOLE` False branch inside the rich dashboard loop."""
    # We don't skip on rich here; instead force console to None
    monkeypatch.setattr(sp, "_RICH_CONSOLE", None, raising=True)
    seq = iter(["6"])  # Exit directly
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()

def test_main_menu_rich_typeerror_fallback(monkeypatch):
    """Ensure TypeError fallback path is covered for monkeypatched run_processing_pipeline."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    # Monkeypatch run_processing_pipeline to a no-arg lambda to trigger TypeError when called with kwarg
    monkeypatch.setattr(sp, "run_processing_pipeline", lambda: None)
    seq = iter(["3", "6"])  # choose pipeline then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()

def test_main_menu_rich_pipeline_updates_content(monkeypatch):
    """Ensure set_content branch executes with _RICH_CONSOLE True (update right pane)."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")

    def fake_pipeline(**kwargs):
        updater = kwargs.get("content_updater")
        if updater:
            updater(sp.Table())

    monkeypatch.setattr(sp, "run_processing_pipeline", fake_pipeline)
    seq = iter(["3", "6"])  # run pipeline then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()

def test_main_menu_rich_pipeline_updates_content_console_none(monkeypatch):
    """Cover set_content branch when _RICH_CONSOLE is None (no clear/print)."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    # Force console None path
    monkeypatch.setattr(sp, "_RICH_CONSOLE", None, raising=True)

    def fake_pipeline(**kwargs):
        updater = kwargs.get("content_updater")
        if updater:
            updater(sp.Table())

    monkeypatch.setattr(sp, "run_processing_pipeline", fake_pipeline)
    seq = iter(["3", "6"])  # run pipeline then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp._main_menu_rich_dashboard()

def test_dashboard_tui_menu_input(monkeypatch):
    """Ensure dashboard uses TUI input in right panel for menu selection."""
    if not sp.ui_has_rich():
        pytest.skip("Rich not available in this environment")
    # Input '6' to exit via TUI prompt path
    monkeypatch.setattr("builtins.input", lambda _="": "6")
    sp._main_menu_rich_dashboard()

def test_dashboard_tui_menu_input_console_none(monkeypatch):
    """Exercise update_right when _RICH_CONSOLE is None during TUI menu prompt."""
    monkeypatch.setattr(sp, "_RICH_CONSOLE", None, raising=True)
    # Input '6' to exit; should invoke update_right without console
    monkeypatch.setattr("builtins.input", lambda _="": "6")
    sp._main_menu_rich_dashboard()

