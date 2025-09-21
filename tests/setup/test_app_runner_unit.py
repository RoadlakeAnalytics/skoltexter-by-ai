"""Unit tests for :mod:`src.setup.app_runner` helpers.

These tests verify delegation into the azure_env helpers and that missing
keys cause the expected prompt/update flow to be invoked.
"""

from pathlib import Path

import src.setup.app_runner as ar
import src.setup.app_ui as _app_ui
import src.setup.app_venv as _app_venv
import src.setup.app_prompts as _app_prompts
import subprocess
from types import SimpleNamespace


def test_parse_env_file_delegates(monkeypatch, tmp_path: Path) -> None:
    """parse_env_file should delegate to the azure_env parser.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module state.
    tmp_path : Path
        Temporary path used as env file.

    Returns
    -------
    None
    """
    called = {}

    def fake_parse(p):
        called['p'] = str(p)
        return {'AZURE_API_KEY': 'k'}

    monkeypatch.setattr('src.setup.azure_env.parse_env_file', fake_parse, raising=False)
    res = ar.parse_env_file(tmp_path / '.env')
    assert res.get('AZURE_API_KEY') == 'k'
    assert 'p' in called


def test_prompt_and_update_env_passes_ui(monkeypatch, tmp_path: Path) -> None:
    """prompt_and_update_env should delegate and accept an explicit UI.

    This test ensures the function calls into the azure_env helper and that
    when `ui` is omitted the app module object may be provided implicitly.
    """
    called = {}

    def fake_prompt(missing, path, existing, ui=None):
        called['args'] = (tuple(missing), str(path), dict(existing), getattr(ui, '__name__', None))

    monkeypatch.setattr('src.setup.azure_env.prompt_and_update_env', fake_prompt, raising=False)
    ar.prompt_and_update_env(['K'], tmp_path / '.env', {})
    assert 'args' in called


def test_ensure_azure_openai_env_calls_prompt_when_missing(monkeypatch, tmp_path: Path) -> None:
    """When required keys are missing ensure_azure_openai_env invokes the prompt.

    We patch the parsing and missing-key detection to force the prompt path.
    """
    monkeypatch.setattr(ar, 'parse_env_file', lambda p: {})
    monkeypatch.setattr(ar, 'find_missing_env_keys', lambda existing, req: ['K'])
    called = {}

    def fake_prompt(missing, path, existing, ui=None):
        called['ok'] = True

    monkeypatch.setattr(ar, 'prompt_and_update_env', fake_prompt)
    ar.ensure_azure_openai_env()
    assert called.get('ok') is True


def test_parse_cli_and_prompt_venv(monkeypatch) -> None:
    """Verify CLI parsing and the virtualenv prompt helper behaviour.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching argv and prompt functions.

    Returns
    -------
    None
    """
    import src.setup.app_prompts as _prom

    ns = ar.parse_cli_args(["--lang", "en", "--no-venv", "--ui", "rich"])
    assert ns.lang == "en" and ns.no_venv is True
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    monkeypatch.setattr("src.setup.app_ui.ui_menu", lambda items: None, raising=False)
    monkeypatch.setattr("src.setup.app_ui.ui_rule", lambda title: None, raising=False)
    assert _prom.prompt_virtual_environment_choice() is True
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    assert _prom.prompt_virtual_environment_choice() is False


def test_parse_env_and_find_missing(tmp_path: Path) -> None:
    """Parse a `.env` file and detect missing required keys.

    Parameters
    ----------
    tmp_path : Path
        Temporary filesystem location used for the env file.

    Returns
    -------
    None
    """
    env = tmp_path / ".envtest"
    env.write_text('AZURE_API_KEY="abc"\nOTHER=1\n')
    parsed = ar.parse_env_file(env)
    assert parsed.get("AZURE_API_KEY") == "abc"
    missing = ar.find_missing_env_keys(parsed, ["AZURE_API_KEY", "GPT4O_DEPLOYMENT_NAME"]) 
    assert "GPT4O_DEPLOYMENT_NAME" in missing


def test_run_ai_connectivity_check_silent_no_endpoint(monkeypatch) -> None:
    """When no endpoint is configured the connectivity check should fail.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to override the OpenAI configuration object.

    Returns
    -------
    None
    """
    from types import SimpleNamespace
    import src.pipeline.ai_processor as aipkg

    monkeypatch.setattr(
        aipkg,
        "OpenAIConfig",
        lambda: SimpleNamespace(gpt4o_endpoint="", api_key="k", request_timeout=1),
    )
    ok, detail = ar.run_ai_connectivity_check_silent()
    assert ok is False and "Missing OpenAI endpoint" in detail


def test_entry_point_minimal(monkeypatch) -> None:
    """Run the entry point with minimal CLI args and stubbed heavy helpers.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to stub heavy or interactive helpers.

    Returns
    -------
    None
    """
    from types import SimpleNamespace

    monkeypatch.setattr(
        'src.setup.app_runner.parse_cli_args',
        lambda: SimpleNamespace(lang="en", no_venv=True, ui="rich"),
        raising=False,
    )
    monkeypatch.setattr('src.setup.app_prompts.set_language', lambda: None, raising=False)
    monkeypatch.setattr('src.setup.app_runner.ensure_azure_openai_env', lambda: None, raising=False)
    monkeypatch.setattr('src.setup.app_runner.main_menu', lambda: None, raising=False)
    try:
        ar.entry_point()
    except SystemExit:
        pass


def test_parse_cli_args_and_run_added(monkeypatch):
    """Parse CLI args and ensure `run` delegates to the concrete UI menu.

    This test was migrated from the legacy shim-based test suite and now
    patches the concrete UI menu implementation directly.
    """
    ns = ar.parse_cli_args(["--lang", "en", "--no-venv", "--ui", "rich"])
    assert ns.lang == "en" and ns.no_venv is True

    called = {}
    import src.setup.ui.menu as menu

    monkeypatch.setattr(menu, "main_menu", lambda: called.setdefault("mm", True))
    args = SimpleNamespace(lang="en")
    ar.run(args)
    assert called.get("mm") is True


def test_run_ai_connectivity_interactive_branches_added(monkeypatch):
    """Verify interactive AI connectivity check success and failure flows.

    The test patches the concrete runner and UI helpers so it does not
    rely on a global shim object.
    """
    monkeypatch.setattr("src.setup.app_runner.run_ai_connectivity_check_silent", lambda: (True, "ok"))
    called = {}
    monkeypatch.setattr("src.setup.app_ui.ui_success", lambda m: called.setdefault("ok", m), raising=False)
    assert ar.run_ai_connectivity_check_interactive() is True
    assert "ok" in called

    monkeypatch.setattr("src.setup.app_runner.run_ai_connectivity_check_silent", lambda: (False, "detail"))
    called = {}
    monkeypatch.setattr("src.setup.app_ui.ui_error", lambda m: called.setdefault("err", m), raising=False)
    assert ar.run_ai_connectivity_check_interactive() is False
    assert "err" in called


def test_run_quality_suites_added(monkeypatch):
    """Ensure the quality-suite helpers invoke subprocess with the runtime.

    This test patches the runtime detection and subprocess runner so no
    external commands are executed during the test.
    """
    called = {}

    def fake_run(*a, **k):
        called["args"] = a

    monkeypatch.setattr("src.setup.app_runner.get_python_executable", lambda: "/usr/bin/python")
    monkeypatch.setattr(subprocess, "run", fake_run)
    ar.run_full_quality_suite()
    ar.run_extreme_quality_suite()
    assert "args" in called


def test_entry_point_invokes_main_menu_added(monkeypatch):
    """Entry point should invoke main menu when CLI args indicate so.

    The test patches parsing, prompts and environment helpers so the
    entry point proceeds directly to the main menu.
    """
    monkeypatch.setattr("src.setup.app_runner.parse_cli_args", lambda: SimpleNamespace(lang="en", no_venv=True))
    monkeypatch.setattr("src.setup.app_prompts.set_language", lambda: None)
    monkeypatch.setattr("src.setup.app_runner.ensure_azure_openai_env", lambda: None)
    called = {}
    monkeypatch.setattr("src.setup.app_runner.main_menu", lambda: called.setdefault("mm", True))
    ar.entry_point()
    assert called.get("mm") is True


def test_entry_point_triggers_manage_virtualenv_when_needed(monkeypatch):
    """`entry_point` should call `manage_virtual_environment` when appropriate.

    We monkeypatch `parse_cli_args`, `is_venv_active` and
    `prompt_virtual_environment_choice` to simulate the branch where a
    venv must be created/managed.
    """
    # Simulate CLI args that do not set a language and request venv handling
    monkeypatch.setattr("src.setup.app_runner.parse_cli_args", lambda: SimpleNamespace(lang=None, no_venv=False, ui="rich"))
    monkeypatch.setattr("src.setup.app_prompts.set_language", lambda: None)
    monkeypatch.setattr("src.setup.app_venv.is_venv_active", lambda: False)

    called = {}

    def fake_prompt():
        return True

    def fake_manage():
        called["managed"] = True

    monkeypatch.setattr("src.setup.app_prompts.prompt_virtual_environment_choice", lambda: True)
    monkeypatch.setattr("src.setup.app_venv.manage_virtual_environment", fake_manage)
    monkeypatch.setattr("src.setup.app_runner.ensure_azure_openai_env", lambda: None)
    # Patch the concrete runner main_menu so the interactive menu does not run
    monkeypatch.setattr("src.setup.app_runner.main_menu", lambda: None)

    # Clear any env var that would skip language prompt
    monkeypatch.delenv("SETUP_SKIP_LANGUAGE_PROMPT", raising=False)

    # Prevent interactive language prompt from blocking the test
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1", raising=False)
    # Call entry_point; should call manage_virtual_environment
    ar.entry_point()
    assert called.get("managed") is True


def test_main_menu_swallows_exceptions(monkeypatch):
    """`main_menu` wrapper should swallow exceptions from the UI module.

    We patch the concrete UI module's `main_menu` to raise and ensure the
    wrapper in :mod:`src.setup.app_runner` does not propagate the exception.
    """
    def _boom():
        raise RuntimeError("boom")

    import importlib

    menu = importlib.import_module("src.setup.ui.menu")
    monkeypatch.setattr(menu, "main_menu", _boom)
    # Should not raise when the app_runner wrapper swallows UI exceptions
    ar.main_menu()
