"""Extra unit tests for AIAPIClient to cover error and retry branches.

These tests exercise HTTP 200 responses with empty choices/content, non-200
errors, and various exceptions raised by the session to ensure robust
error-path behaviour.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from src.pipeline.ai_processor.client import AIAPIClient


class DummyResponse:
    def __init__(self, status: int, text_value: str):
        self.status = status
        self._text = text_value

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, resp):
        self.resp = resp

    def post(self, *a, **k):
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


@pytest.mark.asyncio
async def test_http_200_empty_choices_returns_data():
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", max_retries=0)
    client = AIAPIClient(cfg)
    payload = {"choices": []}
    resp = DummyResponse(200, json.dumps(payload))
    session = DummySession(resp)
    ok, content, data = await client.process_content(session, {})
    assert ok is False and content is None and isinstance(data, dict)


@pytest.mark.asyncio
async def test_http_200_empty_message_content_returns_data():
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", max_retries=0)
    client = AIAPIClient(cfg)
    payload = {"choices": [{"message": {"content": ""}}]}
    resp = DummyResponse(200, json.dumps(payload))
    session = DummySession(resp)
    ok, content, data = await client.process_content(session, {})
    assert ok is False and content is None and isinstance(data, dict)


@pytest.mark.asyncio
async def test_http_500_returns_status_error():
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", max_retries=0)
    client = AIAPIClient(cfg)
    resp = DummyResponse(500, "server error")
    session = DummySession(resp)
    ok, content, data = await client.process_content(session, {})
    assert ok is False and content is None and isinstance(data, dict)
    assert data.get("status_code") == 500


@pytest.mark.asyncio
async def test_timeout_error_returns_timeout_type(monkeypatch):
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", max_retries=0)
    client = AIAPIClient(cfg)

    class BadSession:
        def post(self, *a, **k):
            raise TimeoutError("to")

    session = BadSession()
    # Patch asyncio.sleep to avoid delays in retries
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)
    ok, content, data = await client.process_content(session, {})
    assert ok is False and content is None and data.get("error_type") == "TimeoutError"


@pytest.mark.asyncio
async def test_generic_exception_returns_exception_type(monkeypatch):
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", max_retries=0)
    client = AIAPIClient(cfg)

    class BadSession:
        def post(self, *a, **k):
            raise Exception("boom")

    session = BadSession()
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)
    ok, content, data = await client.process_content(session, {})
    assert ok is False and content is None and data.get("error_type") == "Exception"

