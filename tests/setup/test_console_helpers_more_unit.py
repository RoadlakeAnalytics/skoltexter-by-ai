"""Tests for `src.setup.console_helpers` covering dynamic import branches.

These tests exercise the runtime checks that determine whether Rich is
available and that `rprint` prefers Rich's print when possible.
"""

import types
import sys

import src.setup.console_helpers as ch


def test_ui_has_rich_respects_internal_flag(monkeypatch):
    """ui_has_rich should return True when the internal console exists."""
    # Force the internal console to a truthy object
    monkeypatch.setattr(ch, "_RICH_CONSOLE", object(), raising=False)
    assert ch.ui_has_rich() is True

    # When internal console is None but rich import fails, return False
    monkeypatch.setattr(ch, "_RICH_CONSOLE", None, raising=False)
    monkeypatch.setitem(sys.modules, "rich", None)
    assert ch.ui_has_rich() is False


def test_rprint_prefers_rich_and_falls_back(monkeypatch, capsys):
    """rprint should call Rich's print when available and fallback to print.

    We stub a minimal `rich.print` callable in sys.modules to verify the
    preferred path and ensure the fallback prints to stdout when Rich fails.
    """
    # Create a fake rich module with a print function
    fake_rich = types.ModuleType("rich")

    called = {}

    def fake_print(*args, **kwargs):
        called['ok'] = True

    fake_rich.print = fake_print
    monkeypatch.setitem(sys.modules, "rich", fake_rich)

    # When console reports available, rprint tries rich.print
    monkeypatch.setattr(ch, "ui_has_rich", lambda: True, raising=False)
    ch.rprint("hello")
    assert called.get('ok') is True

    # Force rich_path to fail and ensure fallback prints to stdout
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False, raising=False)
    ch.rprint("fallback")
    out = capsys.readouterr().out
    assert "fallback" in out

