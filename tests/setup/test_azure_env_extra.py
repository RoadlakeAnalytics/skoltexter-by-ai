"""Tests for Azure env helpers including parsing and connectivity checks."""

import json
from types import SimpleNamespace

import importlib

from src.setup import azure_env as az


def test_parse_env_file_various_formats(tmp_path):
    p = tmp_path / ".env"
    p.write_text('AZURE_API_KEY="abc"\nOTHER=1\nSPACED = "v"\n')
    parsed = az.parse_env_file(p)
    assert parsed["AZURE_API_KEY"] == "abc"
    assert parsed["OTHER"] == "1"
    assert parsed["SPACED"] == "v"


def test_prompt_and_update_env_writes_file(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    existing = {"EXISTING": "x"}
    missing = ["AZURE_API_KEY", "GPT4O_DEPLOYMENT_NAME"]

    class UI:
        def rprint(self, msg):
            pass

        def _(self, key):
            # Return a format string so the prompt will include the key name
            return "{key}"

        def ask_text(self, prompt):
            # Return a value based on the prompt to ensure determinism
            if "AZURE_API_KEY" in prompt:
                return "k1"
            return "dep"

    az.prompt_and_update_env(missing, env_path, existing, ui=UI())
    content = env_path.read_text()
    assert 'AZURE_API_KEY="k1"' in content
    assert 'GPT4O_DEPLOYMENT_NAME="dep"' in content


def test_find_missing_env_keys():
    assert az.find_missing_env_keys({"A": "1"}, ["A", "B"]) == ["B"]


def test_run_ai_connectivity_check_silent_success(monkeypatch):
    # Provide a fake OpenAIConfig
    mod = importlib.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(mod, "OpenAIConfig", lambda: SimpleNamespace(gpt4o_endpoint="http://x", api_key="k", request_timeout=1))

    # Build a fake aiohttp module with async context managers
    class DummyResponse:
        def __init__(self, status, text):
            self.status = status
            self._text = text

        async def text(self):
            return self._text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *a, **k):
            payload = {"choices": [{"message": {"content": "Status: OK"}}]}
            return DummyResponse(200, json.dumps(payload))

    fake_aio = SimpleNamespace(ClientTimeout=lambda total: None, ClientSession=DummySession)
    monkeypatch.setitem(__import__("sys").modules, "aiohttp", fake_aio)

    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is True
    assert detail == "Status: OK"


def test_run_ai_connectivity_check_silent_missing_endpoint(monkeypatch):
    mod = importlib.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(mod, "OpenAIConfig", lambda: SimpleNamespace(gpt4o_endpoint="", api_key="k", request_timeout=1))
    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is False
    assert "Missing OpenAI endpoint" in detail
