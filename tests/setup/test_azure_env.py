"""Tests for `src/setup/azure_env.py`.

Focused tests for environment parsing and interactive Azure connectivity checks.
"""

import sys
from pathlib import Path

import src.setup.azure_env as sp


def test_ai_connectivity_unexpected_reply(monkeypatch):
    """Cover the unexpected reply branch (HTTP 200 with non-OK content)."""
    import types

    import src.setup.pipeline.orchestrator as sp_local

    class FakeCfg:
        def __init__(self):
            self.gpt4o_endpoint = "https://x"
            self.api_key = "k"
            self.request_timeout = 1

    class FakeResp:
        status = 200

        async def text(self):
            return '{"choices": [{"message": {"content": "Not OK"}}]}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSess:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            return FakeResp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_mod = types.SimpleNamespace(OpenAIConfig=FakeCfg)
    monkeypatch.setitem(sys.modules, "src.program2_ai_processor", fake_mod)
    fake_aiohttp = types.SimpleNamespace(
        ClientSession=FakeSess, ClientTimeout=lambda total=None: None
    )
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aiohttp)

    assert sp_local.run_ai_connectivity_check_interactive() is False


def test_parse_env_file_not_exists(tmp_path: Path):
    assert sp.parse_env_file(tmp_path / "missing.env") == {}


def test_prompt_and_update_env_writes(monkeypatch, tmp_path: Path):
    envp = tmp_path / ".env"
    existing = {"EXTRA": "keep"}
    missing = list(sp.REQUIRED_AZURE_KEYS)
    seq_vals = iter(["k1", "k2", "k3", "k4"])  # for required keys
    import src.setup.ui.prompts as pr

    monkeypatch.setattr(pr, "ask_text", lambda prompt: next(seq_vals))
    sp.prompt_and_update_env(missing, envp, existing)
    text = envp.read_text(encoding="utf-8")
    for k in sp.REQUIRED_AZURE_KEYS:
        assert k in text
    assert 'EXTRA="keep"' in text


def test_parse_env_and_find_missing(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        'AZURE_API_KEY="abc"\nAZURE_ENDPOINT_BASE="https://x"\n', encoding="utf-8"
    )
    data = sp.parse_env_file(env_path)
    assert data["AZURE_API_KEY"] == "abc"
    missing = sp.find_missing_env_keys(data, sp.REQUIRED_AZURE_KEYS)
    assert "GPT4O_DEPLOYMENT_NAME" in missing and "AZURE_API_VERSION" in missing


def test_ensure_azure_openai_env_triggers_prompt(monkeypatch, tmp_path: Path):
    envp = tmp_path / ".env"
    envp.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "ENV_PATH", envp)
    called = {"n": 0}

    def fake_prompt(keys, env_path, existing):
        called["n"] += 1
        for k in keys:
            existing[k] = "x"

    monkeypatch.setattr(sp, "prompt_and_update_env", fake_prompt)
    sp.ensure_azure_openai_env()
    assert called["n"] == 1
