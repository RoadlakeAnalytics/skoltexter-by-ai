"""Processor-related tests for program2 AI pipeline.

This file contains tests that exercise the higher-level processing logic,
payload creation, CLI invocation paths and various I/O success/failure
behaviours of SchoolDescriptionProcessor and the program entrypoint.
"""

import asyncio
import sys
from builtins import FakeLimiter
from pathlib import Path
from types import SimpleNamespace

import pytest
import logging

import src.pipeline.ai_processor as p2
from src.pipeline.ai_processor import SchoolDescriptionProcessor


def make_proc(tmp_path: Path) -> SchoolDescriptionProcessor:
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


def test_create_ai_payload_with_template(tmp_path: Path):
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
        asyncio,
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


def test_configure_logging_filehandler_error(monkeypatch):
    class BadFH:
        def __init__(self, *a, **k):
            raise RuntimeError("no file handler")

    monkeypatch.setattr(logging, "FileHandler", BadFH)
    p2.configure_logging("INFO", enable_file=True)


def test_openai_config_missing_api_key(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    import types, sys as _sys

    monkeypatch.setitem(_sys.modules, "src.program2_ai_processor", types.SimpleNamespace(PROJECT_ROOT=tmp_path))
    with pytest.raises(ValueError):
        p2.OpenAIConfig()


def test_openai_config_azure_missing_endpoint(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AZURE_API_KEY", "k")
    monkeypatch.delenv("AZURE_ENDPOINT_BASE", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    import types, sys as _sys

    monkeypatch.setitem(_sys.modules, "src.program2_ai_processor", types.SimpleNamespace(PROJECT_ROOT=tmp_path))
    with pytest.raises(ValueError):
        p2.OpenAIConfig()


def test_openai_config_non_azure_no_endpoint_warning(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.delenv("AZURE_ENDPOINT_BASE", raising=False)
    import types, sys as _sys

    monkeypatch.setitem(_sys.modules, "src.program2_ai_processor", types.SimpleNamespace(PROJECT_ROOT=tmp_path))
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
    s = "```markdown\nHello"
    out = SchoolDescriptionProcessor._clean_ai_response(s)
    assert out.startswith("Hello")
    s2 = "```\nBye"
    out2 = SchoolDescriptionProcessor._clean_ai_response(s2)
    assert out2.startswith("Bye")
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
            return self

        async def __aexit__(self, et, e, tb):
            return False

    class S:
        def post(self, *a, **k):
            return R()

    class Limiter:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *a, **k):
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
            return self

        async def __aexit__(self, et, e, tb):
            return False

    class R2:
        status = 200

        async def text(self):
            return json.dumps({"choices": [{"message": {"content": "OK"}}]})

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, e, tb):
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
            return None

        async def __aexit__(self, *a, **k):
            return False

    ok, content, raw_response = await proc.call_openai_api(
        S(), {"x": 1}, "S1", Limiter2()
    )
    assert ok is True and content == "OK"
    assert isinstance(raw_response, dict)
    assert (
        raw_response.get("choices", [{}])[0].get("message", {}).get("content") == "OK"
    )


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
                    raise RuntimeError("boom")

                async def __aexit__(self_inner, et, e, tb):
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
                    return self_inner

                async def __aexit__(self_inner, et, e, tb):
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
            return None

        async def __aexit__(self, *a, **k):
            return False

    ok, content, raw_response = await proc.call_openai_api(
        S(), {"x": 1}, "S1", Limiter4()
    )
    assert ok is True and content == "OK"
    assert isinstance(raw_response, dict)
    assert (
        raw_response.get("choices", [{}])[0].get("message", {}).get("content") == "OK"
    )


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


def test_program2_main_generic_exception(monkeypatch, tmp_path: Path, capsys):
    class BadConfig2:
        def __init__(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(p2, "OpenAIConfig", BadConfig2)
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
    with pytest.raises(RuntimeError):
        p2.main()


def test_program2_main_keyboard_interrupt(monkeypatch, tmp_path: Path, capsys):
    class CtrlConfig:
        def __init__(self):
            raise KeyboardInterrupt()

    monkeypatch.setattr(p2, "OpenAIConfig", CtrlConfig)
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


def test_log_processing_summary(tmp_path: Path, caplog):
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
    with caplog.at_level(logging.INFO):
        p2.log_processing_summary(stats, md_dir, json_dir)


@pytest.mark.asyncio
async def test_call_openai_api_all_retries_failed(tmp_path: Path, monkeypatch):
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


@pytest.mark.asyncio
async def test_openai_config_env_paths(monkeypatch, tmp_path: Path):
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
    ok, _, err = await proc.call_openai_api(object(), {"x": 1}, "S1", FakeLimiter())
    assert ok is False and err.get("error_type") == "ConfigurationError"


def test_openai_config_loads_dotenv(monkeypatch, tmp_path: Path):
    import types, sys as _sys

    monkeypatch.setitem(_sys.modules, "src.program2_ai_processor", types.SimpleNamespace(PROJECT_ROOT=tmp_path))
    env_text = (
        "AZURE_API_KEY=kkk\n"
        "AZURE_ENDPOINT_BASE=https://example.test\n"
        "GPT4O_DEPLOYMENT_NAME=gpt-4o\n"
        "AZURE_API_VERSION=2024-05-01-preview\n"
    )
    (tmp_path / ".env").write_text(env_text, encoding="utf-8")
    cfg = p2.OpenAIConfig()
    assert cfg.gpt4o_endpoint.startswith("https://example.test")
    for key in [
        "AZURE_API_KEY",
        "AZURE_ENDPOINT_BASE",
        "GPT4O_DEPLOYMENT_NAME",
        "AZURE_API_VERSION",
    ]:
        monkeypatch.delenv(key, raising=False)


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


@pytest.mark.asyncio
async def test_process_school_file_success_without_raw_json(
    tmp_path: Path, monkeypatch
):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    f = input_dir / "Z.md"
    f.write_text("Z", encoding="utf-8")
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
        return True, "OK", None

    monkeypatch.setattr(
        SchoolDescriptionProcessor, "call_openai_api", fake_call, raising=True
    )
    import aiohttp

    async with aiohttp.ClientSession() as session:
        ok = await proc.process_school_file(
            session, f, FakeLimiter(), asyncio.Semaphore(1)
        )
        assert ok is True
    raw_path = proc.json_output_dir / "Z_gpt4o_raw_response.json"
    assert not raw_path.exists()


@pytest.mark.asyncio
async def test_process_school_file_failure_without_raw_json(
    tmp_path: Path, monkeypatch
):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    f = input_dir / "W.md"
    f.write_text("W", encoding="utf-8")
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
        return False, None, None

    monkeypatch.setattr(
        SchoolDescriptionProcessor, "call_openai_api", fake_call, raising=True
    )
    import aiohttp

    async with aiohttp.ClientSession() as session:
        ok = await proc.process_school_file(
            session, f, FakeLimiter(), asyncio.Semaphore(1)
        )
        assert ok is False
    failed = proc.json_output_dir / "W_gpt4o_FAILED_response.json"
    assert not failed.exists()
