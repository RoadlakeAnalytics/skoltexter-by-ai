"""Isolated tests for prompts that avoid global state interference.

We dynamically load `src/setup/ui/prompts.py` with a controlled
``src.setup`` package and a mock `console_helpers` module so the various
branches (questionary, TUI, non-tty) can be exercised deterministically.
"""

import importlib.util
import types
import sys
from pathlib import Path


def _load_prompts_with_console(monkeypatch, console_mod, orchestrator_mod=None):
    """Dynamically load the prompts module with given console_helpers.

    This installs a temporary `src.setup` package in `sys.modules` that
    exposes our `console_helpers` stub and optionally a pipeline
    `orchestrator` module. The prompts module is then executed from file
    so its imports resolve to the injected modules.
    """
    pkg = types.ModuleType("src.setup")
    pkg.console_helpers = console_mod
    monkeypatch.setitem(sys.modules, "src.setup", pkg)
    monkeypatch.setitem(sys.modules, "src.setup.console_helpers", console_mod)

    if orchestrator_mod is not None:
        pipkg = types.ModuleType("src.setup.pipeline")
        pipkg.orchestrator = orchestrator_mod
        monkeypatch.setitem(sys.modules, "src.setup.pipeline", pipkg)
        monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orchestrator_mod)

    src = Path("src/setup/ui/prompts.py").resolve()
    spec = importlib.util.spec_from_file_location("tmp_prompts", str(src))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_isolated_ask_text_uses_questionary(monkeypatch):
    ch = types.ModuleType("console_helpers")

    class Q:
        @staticmethod
        def text(prompt, default=None):
            return types.SimpleNamespace(ask=lambda: "qtext")

    ch.questionary = Q
    ch._HAS_Q = True

    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = False
    fake_orch._TUI_UPDATER = None
    fake_orch._TUI_PROMPT_UPDATER = None
    prompts = _load_prompts_with_console(monkeypatch, ch, orchestrator_mod=fake_orch)
    assert prompts.ask_text("Prompt", default="d") == "qtext"


def test_isolated_ask_confirm_uses_questionary(monkeypatch):
    ch = types.ModuleType("console_helpers")

    class Q:
        @staticmethod
        def confirm(prompt, default=True):
            return types.SimpleNamespace(ask=lambda: True)

    ch.questionary = Q
    ch._HAS_Q = True

    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = False
    fake_orch._TUI_UPDATER = None
    fake_orch._TUI_PROMPT_UPDATER = None
    prompts = _load_prompts_with_console(monkeypatch, ch, orchestrator_mod=fake_orch)
    assert prompts.ask_confirm("Proceed?", default_yes=False) is True


def test_isolated_ask_select_uses_questionary(monkeypatch):
    ch = types.ModuleType("console_helpers")

    class Q:
        @staticmethod
        def select(prompt, choices=None):
            return types.SimpleNamespace(ask=lambda: "chosen")

    ch.questionary = Q
    ch._HAS_Q = True

    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = False
    fake_orch._TUI_UPDATER = None
    fake_orch._TUI_PROMPT_UPDATER = None
    prompts = _load_prompts_with_console(monkeypatch, ch, orchestrator_mod=fake_orch)
    assert prompts.ask_select("Pick", ["A", "B"]) == "chosen"


def test_isolated_tui_updater_calls_panel(monkeypatch):
    """When TUI is active the prompt updater should be invoked with a Panel."""
    ch = types.ModuleType("console_helpers")

    class Panel:
        def __init__(self, renderable, title=""):
            self.renderable = renderable
            self.title = title

    ch.Panel = Panel
    ch._HAS_Q = False

    # Captured argument
    captured = {}

    def prompt_updater(obj):
        captured['obj'] = obj

    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = True
    fake_orch._TUI_UPDATER = lambda v: None
    fake_orch._TUI_PROMPT_UPDATER = prompt_updater

    # Ensure getpass is used (simulate TTY) and returns a value
    import getpass as _gp

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(_gp, "getpass", lambda prompt="": "got", raising=False)

    prompts = _load_prompts_with_console(monkeypatch, ch, orchestrator_mod=fake_orch)
    val = prompts.ask_text("Q?", default="d")
    assert val == "got"
    assert 'obj' in captured
