"""Tests for Program 2: AI processor of school descriptions.

Exercises payload construction, fenced-code cleanup, API call logic with
retries and error branches, concurrency and gather handling, CLI entry flow,
and I/O success/failure paths. NumPy-style docstrings are used for clarity.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.program2_ai_processor as p2
from src.program2_ai_processor import SchoolDescriptionProcessor


# --- From test_program2.py ---
@pytest.mark.asyncio
async def test_program2_process_one_file_with_mock(tmp_path: Path, monkeypatch):
    """Process a single file with a mocked AI call.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.
    monkeypatch : MonkeyPatch
        Fixture used to replace the AI call with a deterministic implementation.

    Returns
    -------
    None
        Asserts that one AI output file is written and success is recorded.
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "X001.md").write_text("# X School\nData...", encoding="utf-8")
    fake_config = SimpleNamespace(
        api_key="test",
        gpt4o_endpoint="https://example.invalid/endpoint",
        temperature=0.0,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        request_timeout=5,
        target_rpm=1000,
        max_concurrent_requests=2,
    )
    processor = SchoolDescriptionProcessor(fake_config, input_dir, tmp_path)

    async def fake_call_openai_api(self, session, payload, school_id, rate_limiter):
        return True, "AI CONTENT", {"choices": [{"message": {"content": "AI CONTENT"}}]}

    monkeypatch.setattr(
        SchoolDescriptionProcessor,
        "call_openai_api",
        fake_call_openai_api,
        raising=True,
    )
    stats = await processor.process_all_files(limit=1)
    assert stats["successful_ai_processing"] == 1
    out_md = processor.markdown_output_dir / "X001_ai_description.md"
    assert (
        out_md.exists() and out_md.read_text(encoding="utf-8").strip() == "AI CONTENT"
    )


# --- From test_program2_api_errors.py ---
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
        """Enter async context (test stub)."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context (test stub)."""
        return False


class FakeSession:
    def __init__(self, responses):
        self._responses = iter(responses)

    def post(self, *args, **kwargs):
        try:
            return next(self._responses)
        except StopIteration:
            return FakeResponse(500, "{}")


def make_processor(tmp_path):
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
async def test_api_rate_limit_429(monkeypatch, tmp_path):
    """Simulate 429 rate-limit, verify retry with sleep then success.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        Fixture to monkeypatch asyncio.sleep and session.
    tmp_path : Path
        Temporary path for processor dirs.
    """
    proc = make_processor(tmp_path)
    import json

    good = json.dumps({"choices": [{"message": {"content": "OK"}}]})
    session = FakeSession([FakeResponse(429, "Too many"), FakeResponse(200, good)])
    slept = []

    async def fake_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    ok, content, _ = await proc.call_openai_api(session, {"x": 1}, "S1", FakeLimiter())
    assert ok is True and content == "OK" and slept[0] == 1


@pytest.mark.asyncio
async def test_api_server_error_500_retries_then_fail(monkeypatch, tmp_path):
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
async def test_client_error(monkeypatch, tmp_path):
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
async def test_timeout_error(monkeypatch, tmp_path):
    """Simulate asyncio.TimeoutError and verify error mapping."""
    proc = make_processor(tmp_path)

    class TimeoutSession:
        def post(self, *args, **kwargs):
            class Ctx:
                async def __aenter__(self_inner):
                    """Enter async context (test stub)."""
                    raise TimeoutError()

                async def __aexit__(self_inner, exc_type, exc, tb):
                    """Exit async context (test stub)."""
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
async def test_invalid_json_response(tmp_path):
    """Return non-JSON 200 body and ensure JSONDecode path is covered."""
    proc = make_processor(tmp_path)
    session = FakeSession([FakeResponse(200, "not-json")])
    ok, content, err = await proc.call_openai_api(
        session, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and "raw_response_text" in err


@pytest.mark.asyncio
async def test_empty_choices_and_content(monkeypatch, tmp_path):
    """Cover empty choices and empty content branches under 200 OK."""
    proc = make_processor(tmp_path)
    import json

    session1 = FakeSession([FakeResponse(200, json.dumps({"choices": []}))])
    ok, content, err = await proc.call_openai_api(
        session1, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None
    bad = json.dumps({"choices": [{"message": {"content": ""}}]})
    session2 = FakeSession([FakeResponse(200, bad)])
    monkeypatch.setattr(proc.config, "max_retries", 0)
    ok2, content2, err2 = await proc.call_openai_api(
        session2, {"x": 1}, "S1", FakeLimiter()
    )
    assert ok2 is False and content2 is None


# --- From payload/clean tests ---
def make_proc(tmp_path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=5,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.3,
    )
    p = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)
    return p


def test_create_ai_payload_with_template(tmp_path):
    """Create payload with a minimal SYSTEM/USER template and verify fields."""
    proc = make_proc(tmp_path)
    proc.prompt_template = "SYSTEM: sys\nUSER: Hello {school_data}\n"
    payload = proc.create_ai_payload("X")
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert "Hello X" in payload["messages"][1]["content"]
    assert payload["temperature"] == proc.config.temperature


def test_clean_ai_response_variants():
    """Cover fenced-code variants for response cleanup."""
    assert SchoolDescriptionProcessor._clean_ai_response("```code```") == "code"
    out = SchoolDescriptionProcessor._clean_ai_response("```\ncode\n```")
    assert out.strip() == "code"
    assert (
        SchoolDescriptionProcessor._clean_ai_response("```python\ncode\n```") == "code"
    )


def test_program2_main_invocation(monkeypatch, tmp_path: Path):
    """Invoke program2 main with patched classes to cover CLI flow."""
    called = {}

    class FakeConfig:
        def __init__(self):
            self.api_key = "x"
            self.gpt4o_endpoint = "https://x"
            self.temperature = 0.0
            self.request_timeout = 5
            self.max_retries = 0
            self.backoff_factor = 1.0
            self.retry_sleep_on_429 = 0
            self.max_concurrent_requests = 2
            self.target_rpm = 100

    class FakeProcessor:
        def __init__(self, config, input_dir, output_dir_base):
            called["init"] = (str(input_dir), str(output_dir_base))
            self.markdown_output_dir = tmp_path / "md"
            self.json_output_dir = tmp_path / "json"

    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(p2, "OpenAIConfig", FakeConfig)
    monkeypatch.setattr(p2, "SchoolDescriptionProcessor", FakeProcessor)
    monkeypatch.setattr(
        p2.asyncio,
        "run",
        lambda coro: {
            "total_files_in_input_dir": 0,
            "skipped_already_processed": 0,
            "attempted_to_process": 0,
            "successful_ai_processing": 0,
            "failed_ai_processing": 0,
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program2_ai_processor.py",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path),
            "--limit",
            "5",
        ],
    )
    p2.main()
    assert called["init"][0] == str(tmp_path)


# ---- Extra paths consolidated from test_program2_extra_paths.py ----


def test_configure_logging_filehandler_error(monkeypatch):
    class BadFH:
        def __init__(self, *a, **k):
            raise RuntimeError("no file handler")

    monkeypatch.setattr(p2.logging, "FileHandler", BadFH)
    # Should not raise
    p2.configure_logging("INFO", enable_file=True)


def test_openai_config_missing_api_key(monkeypatch, tmp_path: Path):
    # Clear both API_KEY and AZURE_API_KEY
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    # Point PROJECT_ROOT away from real repo to avoid loading real .env
    monkeypatch.setattr(p2, "PROJECT_ROOT", tmp_path)
    with pytest.raises(ValueError):
        p2.OpenAIConfig()


def test_openai_config_azure_missing_endpoint(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AZURE_API_KEY", "k")
    monkeypatch.delenv("AZURE_ENDPOINT_BASE", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setattr(p2, "PROJECT_ROOT", tmp_path)
    with pytest.raises(ValueError):
        p2.OpenAIConfig()


def test_openai_config_non_azure_no_endpoint_warning(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.delenv("AZURE_ENDPOINT_BASE", raising=False)
    monkeypatch.setattr(p2, "PROJECT_ROOT", tmp_path)
    cfg = p2.OpenAIConfig()
    assert cfg.gpt4o_endpoint == ""


def test_parse_prompt_template_missing_markers(tmp_path: Path):
    cfg = SimpleNamespace(
        api_key="k",
        gpt4o_endpoint="https://x",
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)
    proc.prompt_template = "Only user no markers"
    with pytest.raises(ValueError):
        proc.create_ai_payload("S")


def test_clean_ai_response_partial_fences():
    # Start with ```markdown but not a full code fence pair
    s = "```markdown\nHello"
    out = SchoolDescriptionProcessor._clean_ai_response(s)
    assert out.startswith("Hello")
    # Start with ``` without matching end
    s2 = "```\nBye"
    out2 = SchoolDescriptionProcessor._clean_ai_response(s2)
    assert out2.startswith("Bye")
    # End with ``` trimming
    s3 = "Hello```"
    out3 = SchoolDescriptionProcessor._clean_ai_response(s3)
    assert out3 == "Hello"


@pytest.mark.asyncio
async def test_call_openai_api_empty_choices_no_retry(tmp_path: Path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)

    import json

    class R:
        status = 200

        async def text(self):
            return json.dumps({"choices": []})

        async def __aenter__(self):
            """Enter async context (test stub)."""
            return self

        async def __aexit__(self, et, e, tb):
            """Exit async context (test stub)."""
            return False

    class S:
        def post(self, *a, **k):
            return R()

    class Limiter:
        async def __aenter__(self):
            """Enter async context (test stub)."""
            return None

        async def __aexit__(self, *a, **k):
            """Exit async context (test stub)."""
            return False

    ok, content, err = await proc.call_openai_api(S(), {"x": 1}, "S1", Limiter())
    assert ok is False and content is None and isinstance(err, dict)


@pytest.mark.asyncio
async def test_call_openai_api_empty_content_then_success(monkeypatch, tmp_path: Path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=1,
        max_retries=1,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)

    import json

    class R1:
        status = 200

        async def text(self):
            return json.dumps({"choices": [{"message": {"content": ""}}]})

        async def __aenter__(self):
            """Enter async context (test stub)."""
            return self

        async def __aexit__(self, et, e, tb):
            """Exit async context (test stub)."""
            return False

    class R2:
        status = 200

        async def text(self):
            return json.dumps({"choices": [{"message": {"content": "OK"}}]})

        async def __aenter__(self):
            """Enter async context (test stub)."""
            return self

        async def __aexit__(self, et, e, tb):
            """Exit async context (test stub)."""
            return False

    class S:
        def __init__(self):
            self._calls = 0

        def post(self, *a, **k):
            self._calls += 1
            return R1() if self._calls == 1 else R2()

    async def _noop_sleep(*a, **k):
        return None

    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    class Limiter2:
        async def __aenter__(self):
            """Enter async context (test stub)."""
            return None

        async def __aexit__(self, *a, **k):
            """Exit async context (test stub)."""
            return False

    ok, content, err = await proc.call_openai_api(S(), {"x": 1}, "S1", Limiter2())
    assert ok is True and content == "OK"


@pytest.mark.asyncio
async def test_call_openai_api_exception_then_success(monkeypatch, tmp_path: Path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=1,
        max_retries=1,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)

    class Bad:
        def post(self, *a, **k):
            class Ctx:
                async def __aenter__(self_inner):
                    """Enter async context (test stub)."""
                    raise RuntimeError("boom")

                async def __aexit__(self_inner, et, e, tb):
                    """Exit async context (test stub)."""
                    return False

            return Ctx()

    import json

    class Good:
        def post(self, *a, **k):
            class Ctx:
                status = 200

                async def text(self):
                    return json.dumps({"choices": [{"message": {"content": "OK"}}]})

                async def __aenter__(self_inner):
                    """Enter async context (test stub)."""
                    return self_inner

                async def __aexit__(self_inner, et, e, tb):
                    """Exit async context (test stub)."""
                    return False

            return Ctx()

    class S:
        def __init__(self):
            self._calls = 0

        def post(self, *a, **k):
            self._calls += 1
            return Bad().post() if self._calls == 1 else Good().post()

    async def _noop_sleep2(*a, **k):
        return None

    monkeypatch.setattr(asyncio, "sleep", _noop_sleep2)

    class Limiter4:
        async def __aenter__(self):
            """Enter async context (test stub)."""
            return None

        async def __aexit__(self, *a, **k):
            """Exit async context (test stub)."""
            return False

    ok, content, err = await proc.call_openai_api(S(), {"x": 1}, "S1", Limiter4())
    assert ok is True and content == "OK"


@pytest.mark.asyncio
async def test_process_school_file_skip_if_output_exists(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "A.md").write_text("A", encoding="utf-8")
    cfg = SimpleNamespace(
        api_key="x",
        gpt4o_endpoint="https://x",
        temperature=0.0,
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        max_concurrent_requests=1,
        target_rpm=10,
    )
    proc = SchoolDescriptionProcessor(cfg, input_dir, tmp_path)
    out_md = proc.markdown_output_dir / "A_ai_description.md"
    out_md.write_text("done", encoding="utf-8")
    import aiohttp

    async with aiohttp.ClientSession() as session:

        class Limiter3:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *a, **k):
                return False

        ok = await proc.process_school_file(
            session, input_dir / "A.md", Limiter3(), asyncio.Semaphore(1)
        )
        assert ok is True


@pytest.mark.asyncio
async def test_process_all_files_gather_exception(monkeypatch, tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "A.md").write_text("A", encoding="utf-8")
    cfg = SimpleNamespace(
        api_key="x",
        gpt4o_endpoint="https://x",
        temperature=0.0,
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        max_concurrent_requests=1,
        target_rpm=10,
    )
    proc = SchoolDescriptionProcessor(cfg, input_dir, tmp_path)

    # Ensure tasks are awaited to avoid un-awaited coroutine warning
    async def fake_proc(*args, **kwargs):
        return True

    monkeypatch.setattr(
        p2.SchoolDescriptionProcessor, "process_school_file", fake_proc, raising=True
    )

    async def boom(*tasks, **kwargs):
        for t in tasks:
            try:
                await t
            except Exception:
                pass
        raise RuntimeError("gather error")

    monkeypatch.setattr(p2.tqdm_asyncio, "gather", boom)
    import aiohttp

    with pytest.raises(RuntimeError):
        async with aiohttp.ClientSession():
            await proc.process_all_files(limit=None)


def test_program2_main_valueerror(monkeypatch, tmp_path: Path, capsys):
    """Force OpenAIConfig to raise ValueError and cover main's handler."""

    class BadConfig:
        def __init__(self):
            raise ValueError("bad env")

    monkeypatch.setattr(p2, "OpenAIConfig", BadConfig)
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program2_ai_processor.py",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    p2.main()
    capsys.readouterr()
    # We don't assert exact message, just that no crash occurred


def test_program2_main_generic_exception(monkeypatch, tmp_path: Path, capsys):
    class BadProc:
        def __init__(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        p2,
        "OpenAIConfig",
        lambda: SimpleNamespace(
            api_key="x",
            gpt4o_endpoint="https://x",
            temperature=0.0,
            request_timeout=1,
            max_retries=0,
            backoff_factor=1.0,
            retry_sleep_on_429=0,
        ),
    )
    monkeypatch.setattr(p2, "SchoolDescriptionProcessor", BadProc)
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program2_ai_processor.py",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    p2.main()
    capsys.readouterr()


def test_program2_main_keyboard_interrupt(monkeypatch, tmp_path: Path, capsys):
    """KeyboardInterrupt in main triggers graceful warning logging.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        Fixture to patch OpenAIConfig and argv.
    tmp_path : Path
        Temporary directory for input/output args.
    capsys : CaptureFixture
        Captures logs/stdout (smoke only).
    """

    class KI:
        def __init__(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(p2, "OpenAIConfig", KI)
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program2_ai_processor.py",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    p2.main()
    capsys.readouterr()


def test_log_processing_summary(tmp_path: Path, caplog):
    """Directly call log_processing_summary to cover its log output lines.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory used to create output dirs.
    caplog : pytest.LogCaptureFixture
        Pytest logging capture utility.
    """
    stats = {
        "total_files_in_input_dir": 3,
        "skipped_already_processed": 1,
        "attempted_to_process": 2,
        "successful_ai_processing": 1,
        "failed_ai_processing": 1,
    }
    md_dir = tmp_path / "md"
    json_dir = tmp_path / "json"
    md_dir.mkdir()
    json_dir.mkdir()
    with caplog.at_level(p2.logging.INFO):
        p2.log_processing_summary(stats, md_dir, json_dir)


@pytest.mark.asyncio
async def test_call_openai_api_all_retries_failed(tmp_path: Path, monkeypatch):
    """Simulate only 429 responses with max_retries=0 -> final None error object."""
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)

    class R:
        status = 429

        async def text(self):
            return "rate"

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, e, tb):
            return False

    class S:
        def post(self, *a, **k):
            return R()

    ok, content, err = await proc.call_openai_api(S(), {"x": 1}, "SCH", FakeLimiter())
    assert ok is False and content is None and err is None


def test_openai_config_env_paths(monkeypatch, tmp_path: Path):
    """Instantiate OpenAIConfig with env vars to cover endpoint/params branches."""
    # Ensure .env does not exist so the warning branch is covered
    monkeypatch.setenv("AZURE_API_KEY", "k")
    monkeypatch.setenv("AZURE_ENDPOINT_BASE", "https://api.example.com")
    monkeypatch.setenv("GPT4O_DEPLOYMENT_NAME", "gpt-4o")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-05-01-preview")
    monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "2")
    monkeypatch.setenv("TARGET_RPM", "100")
    monkeypatch.setenv("MAX_RETRIES", "0")
    monkeypatch.setenv("BACKOFF_FACTOR", "1.0")
    monkeypatch.setenv("RETRY_SLEEP_ON_429", "0")
    monkeypatch.setenv("TEMPERATURE", "0.0")
    monkeypatch.setenv("REQUEST_TIMEOUT", "5")
    cfg = p2.OpenAIConfig()
    assert cfg.gpt4o_endpoint.endswith(
        "chat/completions?api-version=2024-05-01-preview"
    )


@pytest.mark.asyncio
async def test_call_openai_api_unexpected_exception(tmp_path: Path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="https://x",
        api_key="k",
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)

    class BadSession:
        def post(self, *a, **k):
            class Ctx:
                async def __aenter__(self_inner):
                    raise RuntimeError("boom")

                async def __aexit__(self_inner, et, e, tb):
                    return False

            return Ctx()

    ok, content, err = await proc.call_openai_api(
        BadSession(), {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and content is None and err.get("error_type") == "Exception"


@pytest.mark.asyncio
async def test_call_openai_api_no_endpoint(tmp_path: Path):
    cfg = SimpleNamespace(
        gpt4o_endpoint="",
        api_key="k",
        request_timeout=1,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        temperature=0.0,
    )
    proc = SchoolDescriptionProcessor(cfg, tmp_path, tmp_path)
    ok, content, err = await proc.call_openai_api(
        object(), {"x": 1}, "S1", FakeLimiter()
    )
    assert ok is False and err.get("error_type") == "ConfigurationError"


def test_parse_arguments_all_flags(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LANG_UI", "sv")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program2_ai_processor.py",
            "--limit",
            "5",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path),
            "--log-level",
            "INFO",
            "--lang",
            "en",
        ],
    )
    args = p2.parse_arguments()
    assert args.limit == 5 and args.input == str(tmp_path)


@pytest.mark.asyncio
async def test_process_school_file_io_error(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    f = input_dir / "S.md"
    f.write_text("X", encoding="utf-8")
    cfg = SimpleNamespace(
        api_key="x",
        gpt4o_endpoint="https://x",
        temperature=0.0,
        request_timeout=5,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        max_concurrent_requests=2,
        target_rpm=100,
    )
    proc = SchoolDescriptionProcessor(cfg, input_dir, tmp_path)
    # Force open() to raise
    orig_open = Path.open

    def bad_open(self, mode="r", *a, **k):
        if self == f:
            raise OSError("io")
        return orig_open(self, mode, *a, **k)

    monkeypatch.setattr(Path, "open", bad_open)
    import aiohttp

    async with aiohttp.ClientSession() as session:
        ok = await proc.process_school_file(
            session, f, FakeLimiter(), asyncio.Semaphore(1)
        )
        assert ok is False


# --- From process_limits tests ---
@pytest.mark.asyncio
async def test_process_all_files_limit_and_skips(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for name in ["A.md", "B.md", "C.md"]:
        (input_dir / name).write_text(name, encoding="utf-8")
    out_dir = tmp_path / "ai_processed_markdown"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "A_ai_description.md").write_text("done", encoding="utf-8")
    cfg = SimpleNamespace(
        api_key="x",
        gpt4o_endpoint="https://x",
        temperature=0.0,
        request_timeout=5,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        max_concurrent_requests=2,
        target_rpm=100,
    )
    proc = SchoolDescriptionProcessor(cfg, input_dir, tmp_path)

    async def fake_call(session, payload, school_id, limiter):
        return True, f"DESC {school_id}", {"choices": [{"message": {"content": "x"}}]}

    monkeypatch.setattr(
        SchoolDescriptionProcessor, "call_openai_api", fake_call, raising=True
    )
    stats = await proc.process_all_files(limit=1)
    assert (
        stats["skipped_already_processed"] == 1 and stats["attempted_to_process"] == 1
    )


# --- Additional IO failure path ---
@pytest.mark.asyncio
async def test_process_school_file_failure_saves_failed_json(
    tmp_path: Path, monkeypatch
):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "Y.md").write_text("Y", encoding="utf-8")
    cfg = SimpleNamespace(
        api_key="x",
        gpt4o_endpoint="https://x",
        temperature=0.0,
        request_timeout=5,
        max_retries=0,
        backoff_factor=1.0,
        retry_sleep_on_429=0,
        max_concurrent_requests=2,
        target_rpm=100,
    )
    proc = SchoolDescriptionProcessor(cfg, input_dir, tmp_path)

    async def fake_call(self, session, payload, school_id, limiter):
        return False, None, {"error": "bad"}

    monkeypatch.setattr(
        SchoolDescriptionProcessor, "call_openai_api", fake_call, raising=True
    )
    import aiohttp

    async with aiohttp.ClientSession() as session:
        ok = await proc.process_school_file(
            session, input_dir / "Y.md", FakeLimiter(), asyncio.Semaphore(1)
        )
        assert ok is False
    failed = proc.json_output_dir / "Y_gpt4o_FAILED_response.json"
    assert failed.exists()
