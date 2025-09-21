"""Canonical tests for ``src.setup.app_prompts``.

These tests exercise the interactive prompt helpers by patching the
concrete prompt implementation rather than relying on legacy shim
modules in ``sys.modules``. They follow the project's NumPy-style
docstring conventions for test functions.
"""

import importlib

import pytest

from src.exceptions import UserInputError
import src.setup.app_prompts as app_prompts


def test_set_language_sets_module_lang(monkeypatch):
    """Ensure selecting a language updates the i18n module language.

    Patch the concrete prompt helper to return a controlled choice and
    verify that the central ``src.setup.i18n`` state is updated
    accordingly.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Choice '1' -> English
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    app_prompts.set_language()
    assert importlib.import_module("src.setup.i18n").LANG == "en"

    # Choice '2' -> Swedish
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    app_prompts.set_language()
    assert importlib.import_module("src.setup.i18n").LANG == "sv"


def test_set_language_keyboardinterrupt_raises_userinputerror(monkeypatch):
    """A KeyboardInterrupt during language selection raises UserInputError.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching input behaviour.

    Returns
    -------
    None
    """

    def _kb(_=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.setup.app_prompts.ask_text", _kb)
    with pytest.raises(UserInputError):
        app_prompts.set_language()


def test_prompt_virtual_environment_choice_branches(monkeypatch):
    """Test both choices for ``prompt_virtual_environment_choice``.

    The function loops until a valid option is given; here we patch the
    concrete prompt helper to exercise both branches and assert the UI
    notification is invoked when the user skips venv creation.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level attributes.

    Returns
    -------
    None
    """
    # Choose '1' -> True
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    assert app_prompts.prompt_virtual_environment_choice() is True

    # Choose '2' -> False, and ensure ui_info is called
    called = {}
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    monkeypatch.setattr(
        "src.setup.app_ui.ui_info", lambda m: called.setdefault("info", m)
    )
    assert app_prompts.prompt_virtual_environment_choice() is False
    assert "info" in called


def test_ask_text_tui_branch(monkeypatch) -> None:
    """Test the TUI-specific branch of ``ask_text`` that uses getpass/input.

    The test stubs out the prompt-updater and the Panel class so the
    function can be exercised deterministically in the pytest environment.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Ensure TUI mode is active on the canonical orchestrator and provide prompt updaters
    monkeypatch.setattr(
        "src.setup.pipeline.orchestrator._TUI_MODE", True, raising=False
    )
    monkeypatch.setattr(
        "src.setup.pipeline.orchestrator._TUI_UPDATER",
        lambda *a, **k: None,
        raising=False,
    )

    captured = {}

    def _prompt_updater(panel):
        # record that updater was called and the provided title
        captured["title"] = getattr(panel, "title", None)

    monkeypatch.setattr(
        "src.setup.pipeline.orchestrator._TUI_PROMPT_UPDATER",
        _prompt_updater,
        raising=False,
    )

    class _Panel:
        def __init__(self, renderable, title=""):
            self.renderable = renderable
            self.title = title

    # Ensure a `rich.panel` stub is present so the prompt-updater branch
    # that constructs a Panel instance is exercised deterministically.
    import types, sys as _sys

    panel_mod = types.ModuleType("rich.panel")
    panel_mod.Panel = _Panel
    monkeypatch.setitem(_sys.modules, "rich.panel", panel_mod)

    # Force getpass to raise so the code falls back to input; then stub input
    import getpass, builtins

    def _raise_getpass(prompt=""):
        raise RuntimeError("no tty")

    monkeypatch.setattr(getpass, "getpass", _raise_getpass, raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")

    val = app_prompts.ask_text("Prompt?", default="def")
    assert val == "hello"
    assert captured.get("title") == "Input"

    # If input yields empty string the default should be returned
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    val2 = app_prompts.ask_text("Prompt?", default="fallback")
    assert val2 == "fallback"


def test_ask_text_delegates_to_prompts(monkeypatch) -> None:
    """When not in TUI mode ``ask_text`` should delegate to the prompts adapter.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """

    monkeypatch.setattr(
        "src.setup.pipeline.orchestrator._TUI_MODE", False, raising=False
    )
    monkeypatch.setattr(
        "src.setup.ui.prompts.ask_text", lambda p, d=None: "delegated", raising=False
    )

    assert app_prompts.ask_text("Q", default=None) == "delegated"


def test_prompt_virtual_environment_choice_and_view_programs(monkeypatch) -> None:
    """Test the venv prompt helper and program description viewer.

    The test uses the concrete modules and patches their real attributes
    so behaviour is local to this test and does not depend on any legacy shim.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level attributes.

    Returns
    -------
    None
    """
    # prompt_virtual_environment_choice: '1' -> True, '2' -> False
    monkeypatch.setattr("src.setup.app_ui.ui_menu", lambda items: None, raising=False)
    monkeypatch.setattr(
        "src.setup.app_prompts.ask_text", lambda prompt="": "1", raising=False
    )
    assert app_prompts.prompt_virtual_environment_choice() is True

    monkeypatch.setattr(
        "src.setup.app_prompts.ask_text", lambda prompt="": "2", raising=False
    )
    assert app_prompts.prompt_virtual_environment_choice() is False

    # view_program_descriptions: exercise printing of a program body
    monkeypatch.setattr(
        "src.setup.app_prompts.get_program_descriptions",
        lambda: {"1": ("T", "BODY")},
        raising=False,
    )
    monkeypatch.setattr("src.setup.app_ui.ui_has_rich", lambda: False, raising=False)
    printed = []
    monkeypatch.setattr(
        "src.setup.app_ui.rprint",
        lambda *a, **k: printed.append(" ".join(map(str, a))),
        raising=False,
    )

    seq = ["1", "0"]

    def _ask(prompt=""):
        return seq.pop(0)

    monkeypatch.setattr("src.setup.app_prompts.ask_text", _ask, raising=False)
    app_prompts.view_program_descriptions()
    assert any("BODY" in p for p in printed)
