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
    monkeypatch.setattr("src.setup.app_ui.ui_info", lambda m: called.setdefault("info", m))
    assert app_prompts.prompt_virtual_environment_choice() is False
    assert "info" in called

