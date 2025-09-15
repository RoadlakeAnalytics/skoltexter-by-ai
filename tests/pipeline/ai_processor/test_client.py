"""Client-related tests for program2 AI processor.

This file contains tests that exercise the HTTP client interactions,
rate limiting and error handling branches of the SchoolDescriptionProcessor
by injecting fake sessions/responses and controlling sleeps/retries.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.program2_ai_processor as p2
from src.program2_ai_processor import SchoolDescriptionProcessor


class FakeLimiter:
    async def __aenter__(self):
        """Enter async context (test stub)."""
        return None

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context (test stub)."""
        return False


class FakeResponse:
    def __init__(self, status: int, text: str):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, responses):
        self._responses = iter(responses)

    def post(self, *args, **kwargs):
        try:
            return next(self._responses)
        except StopIteration:
            return FakeResponse(500, "{}")


def make_processor(tmp_path: Path) -> SchoolDescriptionProcessor:
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://example.invalid/endpoint",
        api_key="test",
        request_timeout=5,
        max_retries=1,
        backoff_factor=2.0,
        retry_sleep_on_429=1,
        temperature=0.0,
    )
    return SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)


@pytest.mark.asyncio
async def test_api_rate_limit_429(monkeypatch, tmp_path: Path):
    """Simulate 429 rate-limit, verify retry with sleep then success."""
    proc = make_processor(tmp_path)
    import json

    good = json.dumps({"choices": [{"message": {"content": "OK"}}]})
    session = FakeSession([FakeResponse(429, "Too many"), FakeResponse(200, good)])
    slept = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, raw_response = await proc.call_openai_api(
        session, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is True and content == "OK" and slept[0] == 1
    assert isinstance(raw_response, dict)
    assert (
        raw_response.get("choices", [{}])[0].get("message", {}).get("content") == "OK"
    )


@pytest.mark.asyncio
async def test_api_server_error_500_retries_then_fail(monkeypatch, tmp_path: Path):
    """Simulate 500 server errors and verify backoff then failure."""
    proc = make_processor(tmp_path)
    session = FakeSession([FakeResponse(500, "ERR"), FakeResponse(500, "ERR")])
    slept = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, err = await proc.call_openai_api(
        session, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and isinstance(err, dict) and 1 in slept


@pytest.mark.asyncio
async def test_client_error(monkeypatch, tmp_path: Path):
    """Simulate aiohttp.ClientError and verify error mapping."""
    import aiohttp

    proc = make_processor(tmp_path)

    class ErrorSession:
        def post(self, *args, **kwargs):
            raise aiohttp.ClientError("network down")

    slept = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, err = await proc.call_openai_api(
        ErrorSession(), {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and err.get("error_type") == "ClientError"


@pytest.mark.asyncio
async def test_timeout_error(monkeypatch, tmp_path: Path):
    """Simulate asyncio.TimeoutError and verify error mapping."""
    proc = make_processor(tmp_path)

    class TimeoutSession:
        def post(self, *args, **kwargs):
            class Ctx:
                async def __aenter__(self_inner):
                    raise TimeoutError()

                async def __aexit__(self_inner, exc_type, exc, tb):
                    return False

            return Ctx()

    slept = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, err = await proc.call_openai_api(
        TimeoutSession(), {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and err.get("error_type") == "TimeoutError"


@pytest.mark.asyncio
async def test_invalid_json_response(tmp_path: Path):
    """Return non-JSON 200 body and ensure JSONDecode path is covered."""
    proc = make_processor(tmp_path)
    session = FakeSession([FakeResponse(200, "not-json")])
    ok, content, err = await proc.call_openai_api(
        session, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and "raw_response_text" in err


@pytest.mark.asyncio
async def test_empty_choices_and_content(monkeypatch, tmp_path: Path):
    """Cover empty choices and empty content branches under 200 OK."""
    proc = make_processor(tmp_path)
    import json

    session1 = FakeSession([FakeResponse(200, json.dumps({"choices": []}))])
    proc.config.max_retries = 0
    ok, content, err = await proc.call_openai_api(
        session1, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None
    assert isinstance(err, dict) and err.get("choices") == []
    bad = json.dumps({"choices": [{"message": {"content": ""}}]})
    session2 = FakeSession([FakeResponse(200, bad)])
    monkeypatch.setattr(proc.config, "max_retries", 0)
    ok2, content2, err2 = await proc.call_openai_api(
        session2, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok2 is False and content2 is None
    assert isinstance(err2, dict)
    assert err2.get("choices", [{}])[0].get("message", {}).get("content", "") == ""


@pytest.mark.asyncio
async def test_api_empty_choices_retry_then_success(monkeypatch, tmp_path: Path):
    """Simulate empty 'choices' on first 200 response, then success on retry."""
    proc = make_processor(tmp_path)
    import json

    first = json.dumps({"choices": []})
    second = json.dumps({"choices": [{"message": {"content": "OK"}}]})
    session = FakeSession([FakeResponse(200, first), FakeResponse(200, second)])
    slept: list[float] = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, raw = await proc.call_openai_api(
        session, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is True and content == "OK"
    assert slept and slept[0] == 1
    assert isinstance(raw, dict)
    assert raw.get("choices", [{}])[0].get("message", {}).get("content") == "OK"

