"""Tests for TUI-specific branches in `src/setup/ui/prompts.py`.

These tests simulate the orchestrator TUI being active and exercise the
branches that render prompts into the TUI area and then read input via
`input()` or `getpass.getpass()` depending on environment.
"""

import builtins
import getpass
import os
import sys

from src.setup.ui import prompts as prom
from src.setup.pipeline import orchestrator as orch


def test_ask_text_tui_uses_input(monkeypatch):
    called = {}
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: called.setdefault("upd", v))
    monkeypatch.setattr(
        orch, "_TUI_PROMPT_UPDATER", lambda v: called.setdefault("pupd", v)
    )
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "typed")

    res = prom.ask_text("Prompt: ", default="def")
    assert res == "typed"
    assert "pupd" in called


def test_ask_text_tui_input_eof_returns_default(monkeypatch):
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: None)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", lambda v: None)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    def _bad(*a, **k):
        raise EOFError()

    monkeypatch.setattr(builtins, "input", _bad)
    assert prom.ask_text("p", default="D") == "D"


def test_ask_text_tui_getpass_path(monkeypatch):
    # Remove pytest env to exercise getpass branch
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: None)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", lambda v: None)
    # Make stdin appear to be a TTY
    monkeypatch.setattr(sys, "stdin", sys.__stdin__)
    monkeypatch.setattr(sys.__stdin__, "isatty", lambda: True)
    # Ensure Panel is callable so prompt delivery does not error
    import src.setup.console_helpers as ch

    monkeypatch.setattr(
        ch,
        "Panel",
        lambda *a, **k: __import__("types").SimpleNamespace(),
        raising=False,
    )
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "gpval")

    assert prom.ask_text("p") == "gpval"


def test_ask_confirm_tui_variants(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: None)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", lambda v: None)

    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    assert prom.ask_confirm("?", default_yes=True) is True
    monkeypatch.setattr(builtins, "input", lambda prompt="": "n")
    assert prom.ask_confirm("?", default_yes=True) is False
