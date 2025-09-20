"""Unit tests for async connectivity checks in :mod:`src.setup.azure_env`.

These tests exercise the silent connectivity helper by installing a
lightweight fake ``aiohttp`` module and a fake OpenAIConfig provider so
the function can be exercised deterministically without network access.

All interactive or network operations are stubbed using ``monkeypatch``.
"""

import json
import types
import sys
from types import SimpleNamespace

import src.setup.azure_env as az


def test_run_ai_connectivity_check_silent_missing_endpoint(monkeypatch):
    """When the OpenAI endpoint is not configured the function reports an error.

    The function should return a tuple ``(False, <detail>)`` when the
    configuration object reports no endpoint.
    """
    dummy_pkg = types.ModuleType("src.pipeline.ai_processor")
    dummy_pkg.OpenAIConfig = lambda: SimpleNamespace(gpt4o_endpoint="", api_key=None)
    monkeypatch.setitem(sys.modules, "src.pipeline.ai_processor", dummy_pkg)

    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is False
    assert "Missing OpenAI endpoint" in detail


def test_run_ai_connectivity_check_silent_success(monkeypatch):
    """Simulate a successful AI connectivity check using a fake aiohttp.

    We install a fake ``aiohttp`` module that yields a crafted JSON
    response containing the exact text ``Status: OK`` so the helper
    returns success.
    """
    # Fake OpenAIConfig that exposes an endpoint and api_key
    dummy_pkg = types.ModuleType("src.pipeline.ai_processor")
    dummy_pkg.OpenAIConfig = lambda: SimpleNamespace(
        gpt4o_endpoint="http://x", api_key="k", request_timeout=1
    )
    monkeypatch.setitem(sys.modules, "src.pipeline.ai_processor", dummy_pkg)

    # Prepare fake aiohttp with async context managers
    class FakeResponse:
        def __init__(self, text_value: str, status: int = 200):
            self.status = status
            self._text = text_value

        async def text(self):
            return self._text

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
            payload = {"choices": [{"message": {"content": "Status: OK"}}]}
            return FakeResponse(json.dumps(payload), status=200)

    fake_aio = types.SimpleNamespace()
    fake_aio.ClientSession = FakeSession
    fake_aio.ClientTimeout = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    ok, detail = az.run_ai_connectivity_check_silent()
    assert ok is True
    assert detail == "Status: OK"

