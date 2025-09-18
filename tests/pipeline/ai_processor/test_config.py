"""Configuration-related tests for program2 AI processor."""

from pathlib import Path

import pytest

import src.pipeline.ai_processor as p2


def test_openai_config_missing_api_key(monkeypatch, tmp_path: Path):
    # Clear both API_KEY and AZURE_API_KEY
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    # Point PROJECT_ROOT away from real repo to avoid loading real .env
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


def test_openai_config_env_paths(monkeypatch, tmp_path: Path):
    """Instantiate OpenAIConfig with env vars to cover endpoint/params branches."""
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


def test_openai_config_loads_dotenv(monkeypatch, tmp_path: Path):
    """Cover .env present branch by pointing PROJECT_ROOT to tmp and writing .env."""
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
