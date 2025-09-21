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

app = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    set_language=_app_prompts.set_language,
    entry_point=_app_runner.entry_point,
    main_menu=_app_runner.main_menu,
    prompt_virtual_environment_choice=_app_prompts.prompt_virtual_environment_choice,
    LANG=_app_prompts.__dict__.get('LANG', None),
    ask_text=_app_prompts.ask_text,
    ui_info=_app_ui.ui_info,
    is_venv_active=_app_venv.is_venv_active,
    manage_virtual_environment=_app_venv.manage_virtual_environment,
    ensure_azure_openai_env=_app_runner.ensure_azure_openai_env,
)
_sys.modules.setdefault("src.setup.app", app)


def test_set_language_sets_module_lang(monkeypatch):
    """Ensure `set_language` updates both the i18n module and module state.

    The function prompts the user; here we patch `ask_text` to return a
    controlled choice and verify `i18n.LANG` and `app.LANG` are updated.

    Examples
    --------
    >>> import src.setup.app as app
    >>> # monkeypatch ask_text to return '1' or '2' in tests
    """
    # Choice '1' -> English
    monkeypatch.setattr(app, "ask_text", lambda prompt: "1")
    app.set_language()
    assert importlib.import_module("src.setup.i18n").LANG == "en"
    assert app.LANG == "en"

    # Choice '2' -> Swedish
    monkeypatch.setattr(app, "ask_text", lambda prompt: "2")
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

    monkeypatch.setattr(app, "ask_text", _kb)
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
    monkeypatch.setattr(app, "ask_text", lambda prompt: "1")
    assert app.prompt_virtual_environment_choice() is True

    # Choose '2' -> False, and ensure ui_info is called
    called = {}
    monkeypatch.setattr(app, "ask_text", lambda prompt: "2")
    monkeypatch.setattr(app, "ui_info", lambda m: called.setdefault("info", m))
    assert app.prompt_virtual_environment_choice() is False
    assert "info" in called


def test_entry_point_triggers_manage_virtualenv_when_needed(monkeypatch):
    """`entry_point` should call `manage_virtual_environment` when appropriate.

    We monkeypatch `parse_cli_args`, `is_venv_active` and
    `prompt_virtual_environment_choice` to simulate the branch where a
    venv must be created/managed.
    """
    # Simulate CLI args that do not set a language and request venv handling
    monkeypatch.setattr(app, "parse_cli_args", lambda: SimpleNamespace(lang=None, no_venv=False, ui="rich"))
    monkeypatch.setattr(app, "set_language", lambda: None)
    monkeypatch.setattr(app, "is_venv_active", lambda: False)

    called = {}

    def fake_prompt():
        return True

    def fake_manage():
        called["managed"] = True

    monkeypatch.setattr(app, "prompt_virtual_environment_choice", lambda: True)
    monkeypatch.setattr(app, "manage_virtual_environment", fake_manage)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr(app, "main_menu", lambda: None)

    # Clear any env var that would skip language prompt
    monkeypatch.delenv("SETUP_SKIP_LANGUAGE_PROMPT", raising=False)

    # Call entry_point; should call manage_virtual_environment
    app.entry_point()
    assert called.get("managed") is True


def test_main_menu_swallows_exceptions(monkeypatch):
    """`main_menu` wrapper should swallow exceptions from the UI module.

    We set `menu` to a fake module where `main_menu` raises and ensure the
    wrapper does not propagate the exception.
    """
    fake_menu = SimpleNamespace()

    def _boom():
        raise RuntimeError("boom")

    fake_menu.main_menu = _boom
    monkeypatch.setattr(app, "menu", fake_menu, raising=False)
    # Should not raise
    app.main_menu()
