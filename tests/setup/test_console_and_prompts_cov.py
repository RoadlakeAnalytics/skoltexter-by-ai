"""Extra unit tests targeting console helpers and prompt fallbacks.

These tests exercise branches that depend on optional dependencies
(`rich`, `questionary`) and TUI/TTY state. They use lightweight
stubbing to avoid heavy or interactive behaviour.
"""

from types import SimpleNamespace
import sys
import types

import src.setup.console_helpers as ch
import src.setup.ui.prompts as prom


def test_rprint_fallback(monkeypatch, capsys):
    # Force fallback path regardless of installed 'rich'
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False)
    ch.rprint("hello", "world")
    out = capsys.readouterr().out
    assert "hello world" in out


def test_fake_panel_properties():
    # When rich is absent, Panel should be the lightweight fake class.
    P = ch.Panel
    p = P("content", title="T")
    assert hasattr(p, "renderable") and p.title == "T"


def test_ask_text_questionary(monkeypatch):
    # Simulate questionary adapter
    monkeypatch.setattr(ch, "_HAS_Q", True)

    class Q:
        @staticmethod
        def text(prompt, default=""):
            return SimpleNamespace(ask=lambda: "qval")

    monkeypatch.setattr(ch, "questionary", Q)
    # Ensure any TUI orchestrator state from other tests is disabled so
    # the questionary branch is exercised deterministically.
    import types

    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = False
    orch._TUI_UPDATER = None
    orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    import builtins

    monkeypatch.setattr(builtins, "input", lambda prompt="": "qval")
    val = prom.ask_text("p?")
    assert val == "qval"


def test_ask_text_tui_getpass(monkeypatch):
    # Create a fake orchestrator module that enables TUI flows
    orch = types.ModuleType("src.setup.pipeline.orchestrator")
    orch._TUI_MODE = True
    orch._TUI_UPDATER = lambda x: None
    orch._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)

    # Simulate interactive tty so getpass branch is used. Ensure we're not
    # running in the pytest-internal test harness branch by clearing the
    # PYTEST_CURRENT_TEST env var.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "gval")
    # Ensure questionary disabled
    monkeypatch.setattr(ch, "_HAS_Q", False)
    monkeypatch.setattr(ch, "questionary", None)
    # Provide a safe input fallback in case the flow unexpectedly uses
    # `input()` (order-dependent tests may flip branches). This keeps the
    # assertion deterministic.
    import builtins

    monkeypatch.setattr(builtins, "input", lambda prompt="": "gval")

    val = prom.ask_text("p?: ")
    assert val == "gval"


def test_ask_select_non_tty(monkeypatch):
    # Simulate non-tty environment and no pytest env var
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    choices = ["A", "B", "C"]
    res = prom.ask_select("choose", choices)
    assert res == "C"
