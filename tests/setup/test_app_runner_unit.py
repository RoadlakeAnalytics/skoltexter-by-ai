"""Unit tests for :mod:`src.setup.app_runner` helpers.

These tests verify delegation into the azure_env helpers and that missing
keys cause the expected prompt/update flow to be invoked.
"""

from pathlib import Path

import src.setup.app_runner as ar


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
