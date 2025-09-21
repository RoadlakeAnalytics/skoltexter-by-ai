"""Tests for prompt fallbacks covering questionary and TUI branches.

These tests monkeypatch the console helpers to provide deterministic
questionary shims and exercise the TUI prompt updater behaviour.
"""

import builtins
import os
import sys

from types import SimpleNamespace

import src.setup.ui.prompts as prom
from src.setup import console_helpers as ch
import src.setup.pipeline.orchestrator as orch


def test_ask_text_questionary(monkeypatch):
    """When questionary is enabled the adapter should be used."""
    class FakeAns:
        def __init__(self, val):
            self._v = val

        def ask(self):
            return self._v

    class FakeQuestionary:
        @staticmethod
        def text(prompt, default=None):
            return FakeAns("val_from_q")

    # Ensure orchestrator TUI branch is disabled for deterministic behavior
    import sys as _sys
    import types as _types
    import importlib as _il

    orch_stub = _types.ModuleType("src.setup.pipeline.orchestrator")
    orch_stub._TUI_MODE = False
    orch_stub._TUI_UPDATER = None
    orch_stub._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(_sys.modules, "src.setup.pipeline.orchestrator", orch_stub)
    pkg = _il.import_module("src.setup.pipeline")
    monkeypatch.setattr(pkg, "orchestrator", orch_stub, raising=False)
    _il.reload(prom)
    monkeypatch.setattr(ch, "_HAS_Q", True)
    monkeypatch.setattr(ch, "questionary", FakeQuestionary)
    val = prom.ask_text("p?")
    assert val == "val_from_q"


def test_ask_text_tui_uses_input(monkeypatch):
    """When TUI mode is active the prompt updater should be invoked.

    We simulate being inside pytest by setting the env var and providing a
    simple input replacement.
    """
    # Install a fresh orchestrator stub that enables TUI mode and a prompt updater
    import sys as _sys
    import types as _types
    import importlib as _il

    calls = {}

    def prompt_updater(val):
        calls["last"] = val

    orch_stub = _types.ModuleType("src.setup.pipeline.orchestrator")
    orch_stub._TUI_MODE = True
    orch_stub._TUI_UPDATER = lambda v: None
    orch_stub._TUI_PROMPT_UPDATER = prompt_updater
    monkeypatch.setitem(_sys.modules, "src.setup.pipeline.orchestrator", orch_stub)
    pkg = _il.import_module("src.setup.pipeline")
    monkeypatch.setattr(pkg, "orchestrator", orch_stub, raising=False)
    _il.reload(prom)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "tty-answer")
    res = prom.ask_text("Prompt?", default="x")
    assert res == "tty-answer"
    assert "last" in calls
