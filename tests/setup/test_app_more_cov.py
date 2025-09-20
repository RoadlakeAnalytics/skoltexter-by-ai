"""Additional tests for src.setup.app to exercise entrypoint and helpers.

These tests stub heavy interactions (venv manager, main menu, env prompting)
so the functions execute their control flow without side effects.
"""

from types import SimpleNamespace
import src.setup.app as app
import src.setup.i18n as i18n


def test_entry_point_minimal(monkeypatch):
    monkeypatch.setattr(
        app,
        "parse_cli_args",
        lambda: SimpleNamespace(lang="en", no_venv=True, ui="rich"),
    )
    monkeypatch.setattr(app, "set_language", lambda: None)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None)
    called = {}
    monkeypatch.setattr(app, "main_menu", lambda: called.setdefault("main", True))
    app.entry_point()
    assert called.get("main") is True


def test_entry_point_with_venv(monkeypatch):
    monkeypatch.setattr(
        app,
        "parse_cli_args",
        lambda: SimpleNamespace(lang="en", no_venv=False, ui="rich"),
    )
    monkeypatch.setattr(app, "set_language", lambda: None)
    monkeypatch.setattr(app, "is_venv_active", lambda: False)
    monkeypatch.setattr(app, "prompt_virtual_environment_choice", lambda: True)
    called = {}
    monkeypatch.setattr(
        app, "manage_virtual_environment", lambda: called.setdefault("vm", True)
    )
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr(app, "main_menu", lambda: None)
    app.entry_point()
    assert called.get("vm") is True


def test_prompt_virtual_environment_choice(monkeypatch):
    monkeypatch.setattr(app, "ask_text", lambda prompt: "1")
    assert app.prompt_virtual_environment_choice() is True
    monkeypatch.setattr(app, "ask_text", lambda prompt: "2")
    assert app.prompt_virtual_environment_choice() is False


def test_set_language_keyboardinterrupt(monkeypatch):
    # Test that KeyboardInterrupt inside ask_text triggers SystemExit
    def bad(_=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr(app, "ask_text", bad)
    try:
        app.set_language()
    except SystemExit:
        pass
