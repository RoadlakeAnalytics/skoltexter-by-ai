"""Tests for `src/setup/ui/prompts.py` (questionary wrappers)."""

import sys

import src.setup.ui.prompts as sp
from src.setup import console_helpers as ch


def test_questionary_paths(monkeypatch):
    class Q:
        @staticmethod
        def text(prompt, default=""):
            class A:
                def ask(self):
                    return "value"

            return A()

        @staticmethod
        def confirm(prompt, default=True):
            class A:
                def ask(self):
                    return True

            return A()

        @staticmethod
        def select(prompt, choices):
            class A:
                def ask(self):
                    return choices[-1]

            return A()

    monkeypatch.setattr(ch, "_HAS_Q", True)
    monkeypatch.setattr(ch, "questionary", Q)
    assert sp.ask_text("?") == "value"
    assert sp.ask_confirm("?") is True
    assert sp.ask_select("?", ["a", "b"]) == "b"


def test_ask_text_confirm_and_select(monkeypatch):
    """Exercise input helpers via fallback paths."""
    monkeypatch.setattr(ch, "_HAS_Q", False)
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "hello")
    assert sp.ask_text("Your name: ") == "hello"
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "")
    assert sp.ask_confirm("Continue?") is True
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "n")
    assert sp.ask_confirm("Continue?") is False
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "2")
    assert sp.ask_select("Pick one", ["A", "B", "C"]) == "B"
