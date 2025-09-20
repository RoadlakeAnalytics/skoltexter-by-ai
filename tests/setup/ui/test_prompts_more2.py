"""Additional real tests covering questionary and TTY branches in prompts.

These tests avoid artificial coverage tricks and exercise the actual
adapter branches by installing lightweight stubs for optional
dependencies and manipulating TTY/environment state.
"""

import sys
import types
import builtins

from src.setup import console_helpers as ch
import src.setup.ui.prompts as prom


def test_questionary_text_branch(monkeypatch):
    # Ensure orchestrator TUI path is disabled so questionary branch is used
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = False
    orch._TUI_UPDATER = None
    orch._TUI_PROMPT_UPDATER = None
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    # Ensure pytest internal env var is present to avoid early non-tty returns
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)

    # Enable questionary adapter and return a value from .ask()
    monkeypatch.setattr(ch, "_HAS_Q", True)

    class Q:
        @staticmethod
        def text(prompt, default=""):
            return types.SimpleNamespace(ask=lambda: "qval")

    monkeypatch.setattr(ch, "questionary", Q)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert prom.ask_text("p") == "qval"


def test_questionary_text_falls_back_on_exception(monkeypatch):
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = False
    orch._TUI_UPDATER = None
    orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)

    monkeypatch.setattr(ch, "_HAS_Q", True)

    class Q:
        @staticmethod
        def text(prompt, default=""):
            return types.SimpleNamespace(
                ask=lambda: (_ for _ in ()).throw(RuntimeError())
            )

    monkeypatch.setattr(ch, "questionary", Q)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "fb")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert prom.ask_text("p") == "fb"


def test_questionary_confirm_and_select_variants(monkeypatch):
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = False
    orch._TUI_UPDATER = None
    orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)

    # confirm path
    monkeypatch.setattr(ch, "_HAS_Q", True)

    class QC:
        @staticmethod
        def confirm(prompt, default=True):
            return types.SimpleNamespace(ask=lambda: False)

        @staticmethod
        def select(prompt, choices=None):
            return types.SimpleNamespace(ask=lambda: choices[0])

    monkeypatch.setattr(ch, "questionary", QC)
    # Ensure the package attribute for src.setup.pipeline points to our stub
    import importlib as _il

    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert prom.ask_confirm("?", default_yes=True) is False
    assert prom.ask_select("choose", ["A", "B"]) == "A"


def test_ask_select_questionary_present_but_has_q_false(monkeypatch):
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = False
    orch._TUI_UPDATER = None
    orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)

    # questionary present but _HAS_Q False triggers alternate branch
    monkeypatch.setattr(ch, "_HAS_Q", False)

    class Q2:
        @staticmethod
        def select(prompt, choices=None):
            return types.SimpleNamespace(ask=lambda: choices[1])

    monkeypatch.setattr(ch, "questionary", Q2)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert prom.ask_select("choose", ["A", "B"]) == "B"


def test_non_tty_default_behavior(monkeypatch):
    # Non-tty and not in pytest env -> returns default
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert prom.ask_text("p", default="DFT") == "DFT"
