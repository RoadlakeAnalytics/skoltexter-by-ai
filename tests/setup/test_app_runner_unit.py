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

    def fake_prompt(missing, path, existing):
        called['ok'] = True

    monkeypatch.setattr(ar, 'prompt_and_update_env', fake_prompt)
    ar.ensure_azure_openai_env()
    assert called.get('ok') is True

