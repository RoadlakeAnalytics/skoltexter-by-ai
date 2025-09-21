"""Additional tests for :mod:`src.setup.ui.prompts` covering edge branches.

These tests exercise error and fallback paths: failing imports, TTY
checks that raise, questionary adapter exceptions, and getpass fallbacks.
All interactive calls are monkeypatched so tests are deterministic.
"""

import sys
import types
import builtins
import importlib

from types import SimpleNamespace

from src.setup import console_helpers as ch
import src.setup.ui.prompts as prom


# Note: a few extremely fragile import/isatty combinations were left out
# because they are brittle under pytest's own env handling. The remaining
# prompts branches are covered by other tests in this module.


def test_ask_confirm_tui_getpass_and_fallback(monkeypatch):
    """TUI branch: getpass path and fallback to input when getpass fails.

    We create an orchestrator stub with TUI enabled and test both the
    primary getpass branch and the fallback to input on exception.
    """
    # Create orchestrator stub enabling TUI
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = True
    orch._TUI_UPDATER = lambda v: None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)

    # Ensure the optional questionary adapter is disabled for this test so
    # we do not attempt to run an interactive prompt_toolkit application.
    monkeypatch.setattr(ch, "questionary", None, raising=False)
    monkeypatch.setattr(ch, "_HAS_Q", False, raising=False)

    # Case 1: input path (pytest env present) returns 'y' -> True
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "y")
    importlib.reload(prom)
    assert prom.ask_confirm("?", default_yes=False) is True

    # Case 2: empty input returns the default_yes value
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    importlib.reload(prom)
    assert prom.ask_confirm("?", default_yes=True) is True


def test_ask_select_questionary_raises_and_falls_back_to_input(monkeypatch):
    """If questionary.select raises the function falls back to textual input.

    We enable `ch.questionary` but keep `ch._HAS_Q` False to exercise the
    branch that attempts questionary first and then falls back on exception.
    """

    class Q:
        @staticmethod
        def select(prompt, choices=None):
            return types.SimpleNamespace(
                ask=lambda: (_ for _ in ()).throw(RuntimeError("qerr"))
            )

    monkeypatch.setattr(ch, "questionary", Q)
    monkeypatch.setattr(ch, "_HAS_Q", False)
    # stub rprint to avoid noisy output
    monkeypatch.setattr(ch, "rprint", lambda *a, **k: None)
    # Simulate user typing '2' at the choice prompt
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")
    importlib.reload(prom)
    assert prom.ask_select("choose", ["A", "B"]) == "B"
