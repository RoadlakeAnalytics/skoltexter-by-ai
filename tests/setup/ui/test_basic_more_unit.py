"""Tests for the basic UI primitives under different Rich availability."""

import importlib
import sys

from src.setup.ui import basic as basic
from src.setup import console_helpers as ch


def test_ui_rule_and_header_fallback(monkeypatch, capsys):
    # Force non-rich path
    monkeypatch.setattr(ch, "_RICH_CONSOLE", None)
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False)
    basic.ui_rule("Title")
    basic.ui_header("Header")
    out = capsys.readouterr().out
    assert "Title" in out or "Header" in out


def test_ui_status_context_manager(monkeypatch, capsys):
    monkeypatch.setattr(ch, "_RICH_CONSOLE", None)
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False)
    with basic.ui_status("Working..."):
        pass
    out = capsys.readouterr().out
    assert "Working" in out

