import sys

"""Tests for `src/setup/ui/prompts.py` (questionary wrappers)."""


import src.setup.ui.prompts as sp
from src.setup import console_helpers as ch
from types import SimpleNamespace
import builtins


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


def test_ask_text_questionary_success(monkeypatch) -> None:
    """Return text provided by the questionary adapter.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module state.

    Returns
    -------
    None
    """
    import src.setup.pipeline.orchestrator as orch

    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)
    # Ensure the orchestrator TUI path is disabled so the questionary
    # adapter branch is exercised deterministically in tests.
    monkeypatch.setattr(orch, "_TUI_MODE", False, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", None, raising=False)

    class FakeText:
        def __init__(self, prompt, default=""):
            self.prompt = prompt

        def ask(self):
            return "  qval  "

    monkeypatch.setattr(
        ch,
        "questionary",
        SimpleNamespace(text=lambda p, default="": FakeText(p, default)),
        raising=False,
    )
    assert sp.ask_text("Q") == "qval"


def test_ask_text_questionary_raises_fallback_to_input(monkeypatch) -> None:
    """If the questionary adapter raises, fall back to standard input.

    The adapter's `.text()` is made to raise and the builtin `input` is
    stubbed to provide the fallback value.
    """
    import src.setup.pipeline.orchestrator as orch

    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)
    # Ensure orchestrator TUI path is disabled so we hit the questionary
    # adapter and then the standard input fallback when it raises.
    monkeypatch.setattr(orch, "_TUI_MODE", False, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", None, raising=False)

    class Q:
        @staticmethod
        def text(prompt, default=""):
            return SimpleNamespace(
                ask=lambda prompt=prompt: (_ for _ in ()).throw(Exception("boom"))
            )

    monkeypatch.setattr(ch, "questionary", Q, raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": " fallback ")
    assert sp.ask_text("Q", default="def") == "fallback"


def test_ask_text_tui_prompt_updater_invoked(monkeypatch) -> None:
    """TUI path invokes the prompt updater and reads from `input` in tests.

    We enable the orchestrator TUI flags and install a small prompt
    updater that captures the passed Panel's title.
    """
    import src.setup.pipeline.orchestrator as orch

    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda *a, **k: None, raising=False)
    captured = {}

    def _pu(panel):
        captured["title"] = getattr(panel, "title", None)

    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", _pu, raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "  ans  ")

    val = sp.ask_text("Prompt?")
    assert val == "ans"
    assert captured.get("title") == "Input"
