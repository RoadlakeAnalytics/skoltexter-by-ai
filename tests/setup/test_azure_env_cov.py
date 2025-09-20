"""Unit tests for Azure env helpers with injected aiohttp stub.

These tests avoid network I/O by providing a lightweight fake aiohttp
module in ``sys.modules`` before invoking the connectivity check.
"""

import json
from types import SimpleNamespace
import sys
import types

from src.setup import azure_env as ae


def test_parse_env_file_and_find_missing(tmp_path: str | None):
    p = tmp_path / ".envtest"
    p.write_text('AZURE_API_KEY="abc"\nOTHER=1\n')
    parsed = ae.parse_env_file(p)
    assert parsed.get("AZURE_API_KEY") == "abc"
    missing = ae.find_missing_env_keys(
        parsed, ["AZURE_API_KEY", "GPT4O_DEPLOYMENT_NAME"]
    )
    assert "GPT4O_DEPLOYMENT_NAME" in missing


def test_prompt_and_update_env_writes_file(tmp_path: str | None, monkeypatch):
    env_path = tmp_path / ".env"
    existing = {}
    missing = ["AZURE_API_KEY", "GPT4O_DEPLOYMENT_NAME"]
    # Provide a minimal UI shim with ask_text that returns values in order
    seq = iter(["keyval", "depval"])

    class UI:
        @staticmethod
        def rprint(msg):
            pass

        @staticmethod
        def _(k):
            return k

        @staticmethod
        def ask_text(prompt):
            return next(seq)

    ae.prompt_and_update_env(missing, env_path, existing, ui=UI())
    content = env_path.read_text()
    assert 'AZURE_API_KEY="keyval"' in content
    assert 'GPT4O_DEPLOYMENT_NAME="depval"' in content


def test_run_ai_connectivity_check_silent_success(monkeypatch):
    # Stub OpenAIConfig
    class Cfg:
        def __init__(self):
            self.gpt4o_endpoint = "http://x"
            self.api_key = "k"
            self.request_timeout = 1

    monkeypatch.setattr(
        sys.modules.setdefault(
            "src.pipeline.ai_processor", types.ModuleType("src.pipeline.ai_processor")
        ),
        "OpenAIConfig",
        Cfg,
        raising=False,
    )

    # Build a fake aiohttp module
    fake_aio = types.ModuleType("aiohttp")

    class FakePost:
        def __init__(self, text_val):
            self.status = 200
            self._text = text_val

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return self._text

    class FakeSession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *a, **k):
            # Return an async context manager
            body = json.dumps({"choices": [{"message": {"content": "Status: OK"}}]})
            return FakePost(body)

    class FakeClientTimeout:
        def __init__(self, **k):
            pass

    fake_aio.ClientSession = FakeSession
    fake_aio.ClientTimeout = FakeClientTimeout

    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    ok, detail = ae.run_ai_connectivity_check_silent()
    assert ok is True and "Status: OK" in detail
