import sys

"""Tests for `src/setup/ui/prompts.py` (questionary wrappers)."""


import src.setup.ui.prompts as sp
from src.setup import console_helpers as ch


def test_questionary_paths(monkeypatch):
    """Test Questionary paths."""

    class Q:
        """Test Q."""

        @staticmethod
        def text(prompt, default=""):
            """Test Text."""

            class A:
                """Test A."""

                def ask(self):
                    """Test Ask."""
                    return "value"

            return A()

        @staticmethod
        def confirm(prompt, default=True):
            """Test Confirm."""

            class A:
                """Test A."""

                def ask(self):
                    """Test Ask."""
                    return True

            return A()

        @staticmethod
        def select(prompt, choices):
            """Test Select."""

            class A:
                """Test A."""

                def ask(self):
                    """Test Ask."""
                    return choices[-1]

            return A()

    # Ensure any TUI state does not intercept the questionary path
    try:
        from src.setup.pipeline import orchestrator as _orch

        monkeypatch.setattr(_orch, "_TUI_MODE", False, raising=False)
        monkeypatch.setattr(_orch, "_TUI_UPDATER", None, raising=False)
    except Exception:
        pass
    # Ensure Panel is callable for prompt renderers
    monkeypatch.setattr(
        ch,
        "Panel",
        lambda *a, **k: __import__("types").SimpleNamespace(),
        raising=False,
    )
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
