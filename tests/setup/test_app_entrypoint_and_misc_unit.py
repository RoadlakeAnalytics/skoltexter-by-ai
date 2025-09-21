"""Tests for entrypoint and small interactive helpers in :mod:`src.setup.app`.

These tests exercise control-flow in the top-level entrypoint and a few
small helpers that previously had interactive behaviour. They avoid
spawning subprocesses or requiring a TTY by monkeypatching the interactive
bits so the tests are deterministic.
"""

from types import SimpleNamespace
from pathlib import Path
import importlib

import types
import sys as _sys

import src.setup.app_prompts as _app_prompts
import src.setup.app_runner as _app_runner
import src.setup.app_ui as _app_ui
import src.setup.app_venv as _app_venv

app = types.SimpleNamespace()
setattr(app, "parse_cli_args", _app_runner.parse_cli_args)
setattr(app, "set_language", _app_prompts.set_language)
setattr(app, "entry_point", _app_runner.entry_point)
setattr(app, "main_menu", _app_runner.main_menu)
setattr(app, "prompt_virtual_environment_choice", _app_prompts.prompt_virtual_environment_choice)
setattr(app, "LANG", _app_prompts.__dict__.get("LANG", None))
setattr(app, "ask_text", _app_prompts.ask_text)
setattr(app, "ui_info", _app_ui.ui_info)
setattr(app, "is_venv_active", _app_venv.is_venv_active)
setattr(app, "manage_virtual_environment", _app_venv.manage_virtual_environment)
setattr(app, "ensure_azure_openai_env", _app_runner.ensure_azure_openai_env)
_sys.modules["src.setup.app"] = app


def test_set_language_sets_module_lang(monkeypatch):
    """Ensure `set_language` updates both the i18n module and module state.

    The function prompts the user; here we patch `ask_text` to return a
    controlled choice and verify `i18n.LANG` and `app.LANG` are updated.

    """
    # Choice '1' -> English
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    app.set_language()
    assert importlib.import_module("src.setup.i18n").LANG == "en"
    assert app.LANG == "en"

    # Choice '2' -> Swedish
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    app.set_language()
    assert importlib.import_module("src.setup.i18n").LANG == "sv"
    assert app.LANG == "sv"


def test_set_language_keyboardinterrupt_raises_systemexit(monkeypatch):
    """If the prompt raises KeyboardInterrupt `set_language` should exit.

    This verifies the code path that converts a KeyboardInterrupt into a
    controlled SystemExit (to make CLI behaviour deterministic).
    """
    def _kb(_=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.setup.app_prompts.ask_text", _kb)
    try:
        # Expect SystemExit to be raised when user interrupts
        app.set_language()
        raised = False
    except SystemExit:
        raised = True
    assert raised is True


def test_prompt_virtual_environment_choice_branches(monkeypatch):
    """Test both choices for `prompt_virtual_environment_choice`.

    The function loops until a valid option is given; we provide direct
    returns via monkeypatching `ask_text` to exercise both branches.
    """
    # Choose '1' -> True
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    assert app.prompt_virtual_environment_choice() is True

    # Choose '2' -> False, and ensure ui_info is called
    called = {}
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    monkeypatch.setattr("src.setup.app_ui.ui_info", lambda m: called.setdefault("info", m))
    assert app.prompt_virtual_environment_choice() is False
    assert "info" in called


# Tests for src.setup.app_runner were moved to
# `tests/setup/test_app_runner_unit.py` to establish a 1:1 mapping between
# production modules and their canonical test files as part of the shim
# migration effort.


# Tests for src.setup.app_runner were moved to
# `tests/setup/test_app_runner_unit.py` to establish a 1:1 mapping between
# production modules and their canonical test files as part of the shim
# migration effort.
