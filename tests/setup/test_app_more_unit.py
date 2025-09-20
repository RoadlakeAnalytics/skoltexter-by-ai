"""More tests for the lightweight app wrappers in ``src.setup.app``.

These tests exercise virtual-environment prompting and the entry point
flow under controlled conditions.
"""

from types import SimpleNamespace

import src.setup.app as app


def test_prompt_virtual_environment_choice_true(monkeypatch):
    monkeypatch.setattr(app, "ask_text", lambda prompt: "1")
    assert app.prompt_virtual_environment_choice() is True


def test_prompt_virtual_environment_choice_false(monkeypatch):
    monkeypatch.setattr(app, "ask_text", lambda prompt: "2")
    assert app.prompt_virtual_environment_choice() is False


def test_entry_point_minimal_flow(monkeypatch):
    # Provide minimal CLI args and stub out heavy functions
    monkeypatch.setattr(app, "parse_cli_args", lambda: SimpleNamespace(lang="en", no_venv=True, ui="rich"))
    monkeypatch.setattr(app, "set_language", lambda: None)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr(app, "main_menu", lambda: None)
    # Should not raise
    app.entry_point()

