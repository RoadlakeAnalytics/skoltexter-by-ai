"""Additional tests for menu flows to increase branch coverage (UI).

These tests exercise the plain and rich menu loops with controlled
input sequences and stubbed side-effects so no real environment changes
are performed.
"""

import sys
from types import SimpleNamespace

import src.setup.ui.menu as menu


def test_ui_items_has_six_items():
    items = menu._ui_items()
    assert len(items) == 6


def test_manage_env_delegates(monkeypatch):
    called = {}

    def fake_manage(*a, **k):
        called["ok"] = True

    monkeypatch.setattr(menu, "manage_virtual_environment", fake_manage)
    menu._manage_env()
    assert called.get("ok") is True


def test_main_menu_plain_exits_quick(monkeypatch):
    # Provide a sequence of answers: choose '2' then '6' to exit.
    seq = iter(["2", "6"])
    monkeypatch.setattr(menu, "ask_text", lambda prompt: next(seq))
    # Stub heavy calls
    monkeypatch.setattr(menu, "view_program_descriptions", lambda: None)
    monkeypatch.setattr(menu, "run_processing_pipeline", lambda *a, **k: None)
    monkeypatch.setattr(menu, "view_logs", lambda: None)
    monkeypatch.setattr(menu, "reset_project", lambda: None)
    # Should exit cleanly
    menu._main_menu_plain()


def test_main_menu_rich_dashboard_simple(monkeypatch):
    # Simulate rich console absent so rprint path is used
    monkeypatch.setattr(menu, "_RICH_CONSOLE", None)
    seq = iter(["1", "6"])  # manage env then exit
    monkeypatch.setattr(menu, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(menu, "manage_virtual_environment", lambda *a, **k: None)
    menu._main_menu_rich_dashboard()
