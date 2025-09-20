"""Additional tests exercising questionary and non‑TTY branches in prompts."""

import sys
import importlib
from types import SimpleNamespace

import src.setup.ui.prompts as prom
from src.setup import console_helpers as ch


def test_ask_text_uses_questionary(monkeypatch):
    """When questionary is enabled, ask_text should use it and return the answer."""
    fake = SimpleNamespace(text=lambda prompt, default=None: SimpleNamespace(ask=lambda: "qval"))
    monkeypatch.setattr(ch, "_HAS_Q", True)
    monkeypatch.setattr(ch, "questionary", fake)
    # Ensure TUI mode is not active so questionary branch is used.
    try:
        import src.setup.pipeline.orchestrator as orch

        monkeypatch.setattr(orch, "_TUI_MODE", False, raising=False)
        monkeypatch.setattr(orch, "_TUI_UPDATER", None, raising=False)
    except Exception:
        pass
    val = prom.ask_text("Prompt:", default="def")
    assert val == "qval"


def test_ask_text_questionary_exception_falls_back(monkeypatch):
    """If questionary raises the code should fall back to input behaviour."""
    class Bad:
        def text(self, *a, **k):
            return SimpleNamespace(ask=lambda: (_ for _ in ()).throw(Exception("boom")))

    monkeypatch.setattr(ch, "_HAS_Q", True)
    monkeypatch.setattr(ch, "questionary", Bad())
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda prompt="": "typed")
    val = prom.ask_text("p", default="d")
    assert val == "typed"


def test_ask_text_non_tty_returns_default(monkeypatch):
    """When stdin is not a TTY and not running under pytest the default is returned."""
    # Simulate non-tty
    monkeypatch.setattr(sys, "stdin", sys.__stdin__)
    monkeypatch.setattr(sys.__stdin__, "isatty", lambda: False)
    # Ensure we're not in a pytest env
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert prom.ask_text("p", default="D") == "D"


def test_ask_confirm_questionary_branch(monkeypatch):
    """Test confirm branch that routes through questionary when present."""
    fake = SimpleNamespace(confirm=lambda prompt, default=True: SimpleNamespace(ask=lambda: True))
    monkeypatch.setattr(ch, "_HAS_Q", False)
    monkeypatch.setattr(ch, "questionary", fake)
    assert prom.ask_confirm("p", default_yes=True) is True


def test_ask_select_non_tty_returns_last(monkeypatch):
    monkeypatch.setattr(sys, "stdin", sys.__stdin__)
    monkeypatch.setattr(sys.__stdin__, "isatty", lambda: False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    choices = ["A", "B", "C"]
    assert prom.ask_select("p", choices) == "C"
