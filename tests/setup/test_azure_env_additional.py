"""Unit tests for ``src.setup.azure_env`` helpers.

These tests cover parsing of .env files, prompting updates and a mocked
AI connectivity check that exercises the aiohttp-dependent code path.
"""

from pathlib import Path
import sys

import src.setup.azure_env as az


def test_parse_env_file_and_missing_keys(tmp_path: Path) -> None:
    """Parsing `.env` files yields the correct key/value mapping.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory for test files.

    Returns
    -------
    None
    """
    env = tmp_path / ".envtest"
    env.write_text('AZURE_API_KEY="abc"\nOTHER=1\n')
    parsed = az.parse_env_file(env)
    assert parsed.get("AZURE_API_KEY") == "abc"
    assert parsed.get("OTHER") == "1"
    # find_missing_env_keys
    missing = az.find_missing_env_keys(parsed, ["AZURE_API_KEY", "MISSING_KEY"])
    assert missing == ["MISSING_KEY"]


def test_prompt_and_update_env_writes_file(monkeypatch, tmp_path: Path) -> None:
    """Prompting for missing keys writes an updated .env file.

    We provide a minimal UI shim to avoid interactive input.
    """
    env_path = tmp_path / ".env"
    existing = {"AZURE_API_KEY": "k"}
    missing = ["AZURE_ENDPOINT_BASE", "AZURE_API_VERSION"]

    class UI:
        @staticmethod
        def rprint(msg):
            pass

        @staticmethod
        def _(k):
            # Return a template containing the {key} placeholder so the
            # caller's .format(key=...) invocation produces a prompt with
            # the actual key name included.
            return "Enter value for {key}: "

        @staticmethod
        def ask_text(prompt):
            # return a deterministic value for each missing key
            if "AZURE_ENDPOINT_BASE" in prompt:
                return "http://x"
            return "v1"

    az.prompt_and_update_env(missing, env_path, existing, ui=UI)
    text = env_path.read_text(encoding="utf-8")
    assert 'AZURE_ENDPOINT_BASE="http://x"' in text
    assert 'AZURE_API_VERSION="v1"' in text


def test_run_ai_connectivity_check_silent(monkeypatch) -> None:
    """Mock aiohttp and OpenAIConfig to simulate a successful reply.

    The test injects a fake module into sys.modules for aiohttp and the
    pipeline OpenAIConfig so the async helper runs deterministically.
    """

    class FakeResp:
        status = 200

        async def text(self):
            return '{"choices": [{"message": {"content": "Status: OK"}}]}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *a, **k):
            return FakeResp()

    class FakeAiohttp:
        ClientSession = FakeSession
        ClientTimeout = lambda **k: None

    # Fake OpenAIConfig class
    class FakeOpenAIConfig:
        def __init__(self):
            self.gpt4o_endpoint = "http://x"
            self.api_key = "k"
            self.request_timeout = 5

    # Inject fake modules
    monkeypatch.setitem(sys.modules, "aiohttp", FakeAiohttp)
    fake_mod = type(sys)("src.pipeline.ai_processor")
    fake_mod.OpenAIConfig = FakeOpenAIConfig
    monkeypatch.setitem(sys.modules, "src.pipeline.ai_processor", fake_mod)

    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is True and detail == "Status: OK"


def test_run_ai_connectivity_check_missing_endpoint(monkeypatch) -> None:
    """If OpenAIConfig has no endpoint the function returns False."""

    class FakeOpenAIConfig2:
        def __init__(self):
            self.gpt4o_endpoint = ""
            self.api_key = "k"
            self.request_timeout = 5

    fake_mod2 = type(sys)("src.pipeline.ai_processor")
    fake_mod2.OpenAIConfig = FakeOpenAIConfig2
    monkeypatch.setitem(sys.modules, "src.pipeline.ai_processor", fake_mod2)
    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is False and "Missing OpenAI endpoint" in detail
