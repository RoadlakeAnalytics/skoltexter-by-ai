"""Unit tests for :mod:`src.setup.azure_env`.

Focuses on parsing simple `.env` files and the helper that determines
missing keys and invokes the prompt updater when required.
"""

from pathlib import Path

import src.setup.azure_env as az


def test_parse_env_file_and_find_missing(tmp_path: Path) -> None:
    """Parse a simple .env file and detect missing keys.

    This ensures the parser recognises quoted values and returns the
    expected mapping.
    """
    p = tmp_path / ".envtest"
    p.write_text('AZURE_API_KEY="abc"\nOTHER=1\n')
    d = az.parse_env_file(p)
    assert d.get("AZURE_API_KEY") == "abc"
    missing = az.find_missing_env_keys(d, ["AZURE_API_KEY", "MISSING_KEY"])
    assert missing == ["MISSING_KEY"]


def test_ensure_azure_openai_env_prompts_when_missing(
    monkeypatch, tmp_path: Path
) -> None:
    """When required keys are missing, ``prompt_and_update_env`` is invoked."""
    fake_env = {}
    monkeypatch.setattr(az, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(az, "parse_env_file", lambda p: fake_env)
    called = {}

    def fake_prompt(missing, env_path, existing, ui=None):
        called["args"] = (missing, env_path, existing)

    monkeypatch.setattr(az, "prompt_and_update_env", fake_prompt)
    # Trigger
    az.ensure_azure_openai_env()
    assert "args" in called
