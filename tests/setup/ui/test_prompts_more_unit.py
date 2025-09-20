"""Additional unit tests for prompt fallbacks and TUI branches.

These exercises target the TUI-specific branches and adapter error
fallbacks in ``src.setup.ui.prompts``. They intentionally inject a
lightweight fake orchestrator module into ``sys.modules`` to control
the TUI flags without mutating the real orchestrator object.
"""

import sys
import types
import builtins

import src.setup.ui.prompts as prom
from src.setup import console_helpers as ch


def make_orch(tui_mode=True, updater=lambda x: None, prompt_updater=None):
    m = types.ModuleType("src.setup.pipeline.orchestrator")
    m._TUI_MODE = tui_mode
    m._TUI_UPDATER = updater
    m._TUI_PROMPT_UPDATER = prompt_updater
    return m


def test_ask_text_tui_uses_input_when_pytest_env(monkeypatch):
    orch = make_orch(tui_mode=True, updater=lambda x: None)
    # Ensure the package attribute and sys.modules entry are set so
    # ``from src.setup.pipeline import orchestrator`` resolves to our fake
    # module during the prompt call.
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)
    # Simulate pytest env so the code uses input() even when TTY
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "typed")
    res = prom.ask_text("p?")
    assert res == "typed"


def test_ask_text_tui_getpass_and_fallback(monkeypatch):
    orch = make_orch(tui_mode=True, updater=lambda x: None)
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)
    # Simulate a real TTY so getpass branch is chosen
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    import getpass

    # Normal getpass behaviour
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "secret")
    assert prom.ask_text("p:") == "secret"

    # If getpass raises, fallback to input()
    def boom(prompt=""):
        raise RuntimeError()

    monkeypatch.setattr(getpass, "getpass", boom)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "fallback")
    assert prom.ask_text("p:") == "fallback"


def test_ask_text_questionary_error_fallback(monkeypatch):
    # Enable questionary but have its adapter raise on ask()
    monkeypatch.setattr(ch, "_HAS_Q", True)

    class Q:
        @staticmethod
        def text(prompt, default=""):
            return types.SimpleNamespace(ask=lambda: (_ for _ in ()).throw(RuntimeError()))

    monkeypatch.setattr(ch, "questionary", Q)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "qfallback")
    # Ensure TTY state allows input fallback
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert prom.ask_text("p") == "qfallback"


def test_ask_text_non_tty_returns_default(monkeypatch):
    # Non-tty + not in pytest env -> default returned
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert prom.ask_text("p", default="DFT") == "DFT"


def test_ask_confirm_tui_and_questionary(monkeypatch):
    # TUI non-tty path using input
    orch = make_orch(tui_mode=True, updater=lambda x: None)
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "y")
    assert prom.ask_confirm("sure?") is True

    # Questionary confirm path: ensure a non-TUI orchestrator stub is
    # present so the questionary branch (non-TUI) is exercised
    # deterministically.
    orch2 = make_orch(tui_mode=False, updater=None)
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch2)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch2)
    monkeypatch.setattr(ch, "_HAS_Q", True)

    class QC:
        @staticmethod
        def confirm(prompt, default=True):
            return types.SimpleNamespace(ask=lambda: False)

    monkeypatch.setattr(ch, "questionary", QC)
    assert prom.ask_confirm("sure?", default_yes=True) is False


def test_ask_select_numeric_choice(monkeypatch):
    # Simulate numeric selection via input
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    # Ensure questionary adapter is not used in this test so we exercise
    # the input-based selection fallback.
    monkeypatch.setattr(ch, "questionary", None)
    monkeypatch.setattr(ch, "_HAS_Q", False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")
    assert prom.ask_select("pick", ["A", "B"]) == "B"
