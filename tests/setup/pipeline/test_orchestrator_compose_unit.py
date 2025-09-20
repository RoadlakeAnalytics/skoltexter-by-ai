"""Tests for orchestrator compose/update and TUI mode helpers.

These tests exercise the in-memory update flow and ensure the TUI updaters
are called with appropriate renderables in both the Rich and fallback
paths.
"""

import types

import src.setup.pipeline.orchestrator as orch
from src.setup import console_helpers as ch


def test_compose_and_update_with_fallback_group(monkeypatch):
    # Force fallback Group by ensuring rich is absent
    monkeypatch.setattr(ch, "_RICH_CONSOLE", None)
    monkeypatch.setattr(ch, "Group", ch.Group)
    called = []

    def updater(content):
        called.append(content)

    orch._TUI_MODE = True
    orch._TUI_UPDATER = updater
    # Provide both status and progress renderables
    orch._STATUS_RENDERABLE = "S"
    orch._PROGRESS_RENDERABLE = "P"
    orch._compose_and_update()
    assert called, "Updater was not called"
    first = called[0]
    # Fallback Group exposes `.items` attribute
    assert hasattr(first, "items")


def test_compose_and_update_status_only(monkeypatch):
    called = []

    def updater(content):
        called.append(content)

    orch._TUI_MODE = True
    orch._TUI_UPDATER = updater
    orch._STATUS_RENDERABLE = "ONLY"
    orch._PROGRESS_RENDERABLE = None
    orch._compose_and_update()
    assert called and called[0] == "ONLY"


def test_set_tui_mode_and_restore(monkeypatch):
    # Ensure set_tui_mode registers and restores previous state
    updates = []

    def upd(x):
        updates.append(x)

    prev = (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER)
    restore = orch.set_tui_mode(upd)
    assert orch._TUI_MODE is True and orch._TUI_UPDATER is upd
    restore()
    assert (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER) == prev
