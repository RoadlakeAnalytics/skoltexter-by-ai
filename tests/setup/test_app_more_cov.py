"""Additional tests for src.setup.app to exercise entrypoint and helpers.

These tests stub heavy interactions (venv manager, main menu, env prompting)
so the functions execute their control flow without side effects.
"""

from types import SimpleNamespace
import types
import sys as _sys

import src.setup.app_runner as _app_runner
import src.setup.app_prompts as _app_prompts
import src.setup.app_venv as _app_venv
import src.setup.i18n as i18n

_app_ns = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    set_language=_app_prompts.set_language,
    ensure_azure_openai_env=_app_runner.ensure_azure_openai_env,
    entry_point=_app_runner.entry_point,
    main_menu=_app_runner.main_menu,
    is_venv_active=_app_venv.is_venv_active,
    prompt_virtual_environment_choice=_app_prompts.prompt_virtual_environment_choice,
    manage_virtual_environment=_app_venv.manage_virtual_environment,
    ask_text=_app_prompts.ask_text,
    prompt_and_update_env=_app_runner.prompt_and_update_env,
    run_ai_connectivity_check_silent=_app_runner.run_ai_connectivity_check_silent,
)

app = _app_ns
_sys.modules["src.setup.app"] = app


def test_entry_point_minimal(monkeypatch):
    monkeypatch.setattr("src.setup.app_runner.parse_cli_args", lambda: SimpleNamespace(lang="en", no_venv=True, ui="rich"))
    monkeypatch.setattr("src.setup.app_prompts.set_language", lambda: None)
    monkeypatch.setattr("src.setup.app_runner.ensure_azure_openai_env", lambda: None)
    called = {}
    monkeypatch.setattr("src.setup.app_runner.main_menu", lambda: called.setdefault("main", True))
    app.entry_point()
    assert called.get("main") is True


def test_entry_point_with_venv(monkeypatch):
    monkeypatch.setattr("src.setup.app_runner.parse_cli_args", lambda: SimpleNamespace(lang="en", no_venv=False, ui="rich"))
    monkeypatch.setattr("src.setup.app_prompts.set_language", lambda: None)
    monkeypatch.setattr("src.setup.app_venv.is_venv_active", lambda: False)
    monkeypatch.setattr("src.setup.app_prompts.prompt_virtual_environment_choice", lambda: True)
    called = {}
    monkeypatch.setattr(
        "src.setup.app_venv.manage_virtual_environment", lambda: called.setdefault("vm", True)
    )
    monkeypatch.setattr("src.setup.app_runner.ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr("src.setup.app_runner.main_menu", lambda: None)
    app.entry_point()
    assert called.get("vm") is True


