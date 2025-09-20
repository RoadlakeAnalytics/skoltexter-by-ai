"""Unit tests for console helpers (rich/questionary integration)."""

import importlib
import sys

from src.setup import console_helpers as ch


def test_ui_has_rich_false_when_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "rich", None)
    # If rich module is not importable, ui_has_rich should be False
    assert ch.ui_has_rich() is False


def test_ui_has_rich_true_when_console_available(monkeypatch):
    # Ensure a fake rich module and set _RICH_CONSOLE non-None
    fake = importlib.util.module_from_spec(importlib.machinery.ModuleSpec("rich", None))
    monkeypatch.setitem(sys.modules, "rich", fake)
    monkeypatch.setattr(ch, "_RICH_CONSOLE", object())
    assert ch.ui_has_rich() is True


def test_rprint_falls_back_to_print(monkeypatch, capsys):
    # Ensure no rich available
    monkeypatch.setitem(sys.modules, "rich", None)
    ch.rprint("hello", "world")
    out = capsys.readouterr().out
    assert "hello world" in out
