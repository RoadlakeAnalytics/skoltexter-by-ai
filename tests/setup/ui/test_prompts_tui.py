import builtins
import sys

"""Tests for TUI-specific branches in `src/setup/ui/prompts.py`.

These tests simulate the orchestrator TUI being active and exercise the
branches that render prompts into the TUI area and then read input via
`input()` or `getpass.getpass()` depending on environment.
"""

import getpass

from src.setup.pipeline import orchestrator as orch
from src.setup.ui import prompts as prom


def test_ask_text_tui_uses_input(monkeypatch):
    called = {}
    # Install a fake orchestrator so the prompts adapter will observe the
    # TUI updater callbacks deterministically.
    import importlib as _il
    import types as _types

    orch_fake = _types.ModuleType("src.setup.pipeline.orchestrator")
    orch_fake._TUI_MODE = True
    orch_fake._TUI_UPDATER = lambda v: called.setdefault("upd", v)
    orch_fake._TUI_PROMPT_UPDATER = lambda v: called.setdefault("pupd", v)
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch_fake)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch_fake)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "typed")

    res = prom.ask_text("Prompt: ", default="def")
    assert res == "typed"
    assert "pupd" in called


def test_ask_text_tui_input_eof_returns_default(monkeypatch):
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: None)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", lambda v: None)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    def _bad(*a, **k):
        raise EOFError()

    monkeypatch.setattr(builtins, "input", _bad)
    assert prom.ask_text("p", default="D") == "D"


def test_ask_text_tui_getpass_path(monkeypatch):
    # Remove pytest env to exercise getpass branch
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    # Install a fake orchestrator to guarantee the TUI flags are present
    import importlib as _il
    import types as _types

    orch_fake = _types.ModuleType("src.setup.pipeline.orchestrator")
    orch_fake._TUI_MODE = True
    orch_fake._TUI_UPDATER = lambda v: None
    orch_fake._TUI_PROMPT_UPDATER = lambda v: None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch_fake)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch_fake)
    # Make stdin appear to be a TTY
    monkeypatch.setattr(sys, "stdin", sys.__stdin__)
    monkeypatch.setattr(sys.__stdin__, "isatty", lambda: True)
    # Ensure Panel is callable so prompt delivery does not error
    import src.setup.console_helpers as ch

    monkeypatch.setattr(
        ch,
        "Panel",
        lambda *a, **k: __import__("types").SimpleNamespace(),
        raising=False,
    )
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "gpval")

    assert prom.ask_text("p") == "gpval"


def test_ask_confirm_tui_variants(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    # Ensure the orchestrator module used by the prompts adapter is our
    # test-time module object so TUI flags are observed deterministically.
    import importlib as _il

    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", orch)
    pkg = _il.import_module("src.setup.pipeline")
    setattr(pkg, "orchestrator", orch)
    monkeypatch.setattr(orch, "_TUI_MODE", True)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda v: None)
    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", lambda v: None)

    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    assert prom.ask_confirm("?", default_yes=True) is True
    monkeypatch.setattr(builtins, "input", lambda prompt="": "n")
    assert prom.ask_confirm("?", default_yes=True) is False
