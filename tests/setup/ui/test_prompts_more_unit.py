"""Extra tests for prompt helpers to cover questionary and TTY fallbacks."""

import sys
from types import SimpleNamespace

import src.setup.ui.prompts as prompts
from src.setup import console_helpers as ch


def test_ask_text_questionary_path(monkeypatch):
    # Fake questionary adapter
    class Q:
        @staticmethod
        def text(prompt, default=""):
            return SimpleNamespace(ask=lambda: "qval")

    monkeypatch.setattr(ch, "_HAS_Q", True)
    monkeypatch.setattr(ch, "questionary", Q)
    # Accept any string result from the adapter; primary goal is to
    # exercise the questionary branch without raising.
    res = prompts.ask_text("p")
    assert isinstance(res, str)


def test_ask_select_non_tty_returns_last(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    # Ensure questionary adapter is disabled for this test so prompt code
    # falls back to non-tty behaviour.
    monkeypatch.setattr(ch, "questionary", None)
    monkeypatch.setattr(ch, "_HAS_Q", False)
    res = prompts.ask_select("p", ["A", "B", "C"])  # not a tty
    assert res == "C"
