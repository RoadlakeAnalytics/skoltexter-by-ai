"""Tests for AIAPIClient network response parsing and error handling.

These tests provide lightweight async test doubles for `aiohttp` session
behavior so the coroutine can be exercised deterministically.
"""

import json
import asyncio
from types import SimpleNamespace

import pytest

from src.pipeline.ai_processor.client import AIAPIClient


@pytest.mark.asyncio
async def test_no_endpoint_returns_config_error():
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="")
    client = AIAPIClient(cfg)
    res = await client.process_content(None, {})
    assert res[0] is False and res[2].get("error_type") == "ConfigurationError"


class DummyResp:
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
    def __init__(self, response):
        self._response = response

    def post(self, *a, **k):
        return self._response


@pytest.mark.asyncio
async def test_http_200_invalid_json_returns_raw_text():
    cfg = SimpleNamespace(
        api_key="k", gpt4o_endpoint="http://x", request_timeout=1, max_retries=0
    )
    client = AIAPIClient(cfg)
    resp = DummyResp(200, "not-json")
    session = DummySession(resp)
    ok, content, raw = await client.process_content(session, {"x": 1})
    assert ok is False and raw.get("raw_response_text") == "not-json"


@pytest.mark.asyncio
async def test_http_200_with_fenced_content_is_cleaned():
    cfg = SimpleNamespace(api_key="k", gpt4o_endpoint="http://x", request_timeout=1)
    client = AIAPIClient(cfg)
    fenced = json.dumps({"choices": [{"message": {"content": "```\nHello\n```"}}]})
    resp = DummyResp(200, fenced)
    session = DummySession(resp)
    ok, content, raw = await client.process_content(session, {"x": 1})
    assert ok is True and "Hello" in content


@pytest.mark.asyncio
async def test_clienterror_returns_clienterror_type():
    class BadSession:
        def post(self, *a, **k):
            raise Exception("client error")

    cfg = SimpleNamespace(
        api_key="k", gpt4o_endpoint="http://x", request_timeout=1, max_retries=0
    )
    client = AIAPIClient(cfg)
    ok, content, raw = await client.process_content(BadSession(), {"x": 1})
    assert ok is False and raw.get("error_type") in ("ClientError", "Exception")
