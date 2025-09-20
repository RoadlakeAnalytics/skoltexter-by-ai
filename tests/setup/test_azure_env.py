import sys
from pathlib import Path

"""Tests for `src/setup/azure_env.py`.

Focused tests for environment parsing and interactive Azure connectivity checks.
"""


import src.setup.azure_env as sp


def test_ai_connectivity_unexpected_reply(monkeypatch):
    """Cover the unexpected reply branch (HTTP 200 with non-OK content)."""
    import types

    # Delay importing the orchestrator until after we install the fake
    # `aiohttp` module below so module-level imports that depend on
    # `aiohttp` succeed in environments where the package is absent.

    class FakeCfg:
        """Test FakeCfg."""

        def __init__(self):
            """Test Init."""
            self.gpt4o_endpoint = "https://x"
            self.api_key = "k"
            self.request_timeout = 1

    class FakeResp:
        """Test FakeResp."""

        status = 200

        async def text(self):
            """Test Text."""
            return '{"choices": [{"message": {"content": "Not OK"}}]}'

        async def __aenter__(self):
            """Test Aenter."""
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Test Aexit."""
            return False

    class FakeSess:
        """Test FakeSess."""

        def __init__(self, *a, **k):
            """Test Init."""
            pass

        def post(self, *a, **k):
            """Test Post."""
            return FakeResp()

        async def __aenter__(self):
            """Test Aenter."""
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Test Aexit."""
            return False

    import src.pipeline.ai_processor.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "OpenAIConfig", FakeCfg, raising=True)
    fake_aiohttp = types.SimpleNamespace(
        ClientSession=FakeSess, ClientTimeout=lambda total=None: None
    )
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aiohttp)

    import importlib as _il

    # Import (or reload) the orchestrator module now that a fake aiohttp
    # implementation is available so its imports succeed deterministically.
    sp_local = _il.import_module("src.setup.pipeline.orchestrator")
    _il.reload(sp_local)

    assert sp_local.run_ai_connectivity_check_interactive() is False


def test_parse_env_file_not_exists(tmp_path: Path):
    """Test Parse env file not exists."""
    assert sp.parse_env_file(tmp_path / "missing.env") == {}


def test_prompt_and_update_env_writes(monkeypatch, tmp_path: Path):
    """Test Prompt and update env writes."""
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
    """Test Parse env and find missing."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        'AZURE_API_KEY="abc"\nAZURE_ENDPOINT_BASE="https://x"\n', encoding="utf-8"
    )
    data = sp.parse_env_file(env_path)
    assert data["AZURE_API_KEY"] == "abc"
    missing = sp.find_missing_env_keys(data, sp.REQUIRED_AZURE_KEYS)
    assert "GPT4O_DEPLOYMENT_NAME" in missing and "AZURE_API_VERSION" in missing


def test_ensure_azure_openai_env_triggers_prompt(monkeypatch, tmp_path: Path):
    """Test Ensure azure openai env triggers prompt."""
    envp = tmp_path / ".env"
    envp.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "ENV_PATH", envp)
    called = {"n": 0}

    def fake_prompt(keys, env_path, existing):
        """Test Fake prompt."""
        called["n"] += 1
        for k in keys:
            existing[k] = "x"

    monkeypatch.setattr(sp, "prompt_and_update_env", fake_prompt)
    sp.ensure_azure_openai_env()
    assert called["n"] == 1
