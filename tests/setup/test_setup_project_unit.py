"""Unit tests for top-level `setup_project.py` helpers.

These tests exercise many branches of the setup script by monkeypatching
external dependencies and user input functions. They avoid performing
destructive operations by stubbing subprocess and filesystem calls.
"""

import builtins
import sys
from types import SimpleNamespace
from pathlib import Path

import setup_project as sp


def test_ui_helpers_fallback(capsys, monkeypatch):
    # Force non-rich code path
    monkeypatch.setattr(sp, "_RICH_CONSOLE", None)
    sp.ui_rule("Title")
    sp.ui_header("Header")
    with sp.ui_status("Working..."):
        pass
    sp.ui_info("info")
    sp.ui_success("ok")
    sp.ui_warning("warn")
    sp.ui_error("err")
    sp.ui_menu([("1", "A"), ("2", "B")])
    out = capsys.readouterr().out
    assert "Title" in out or "Header" in out


def test_ask_helpers_branches(monkeypatch):
    # Fallback input
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")
    monkeypatch.setattr(sp, "_TUI_MODE", False)
    monkeypatch.setattr(sp, "_HAS_Q", False)
    assert sp.ask_text("prompt:") == "hello"

    # Questionary path
    monkeypatch.setattr(sp, "_HAS_Q", True)
    class Q:
        @staticmethod
        def text(prompt, default=""):
            return SimpleNamespace(ask=lambda: "qval")

    monkeypatch.setattr(sp, "questionary", Q)
    assert sp.ask_text("p") == "qval"

    # TUI path - prefer getpass
    monkeypatch.setattr(sp, "_TUI_MODE", True)
    monkeypatch.setattr(sp, "_TUI_UPDATER", lambda x: None)
    monkeypatch.setattr(sp, "_TUI_PROMPT_UPDATER", None)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "gval")
    assert sp.ask_text("p") == "gval"
    # reset TUI mode
    monkeypatch.setattr(sp, "_TUI_MODE", False)
    monkeypatch.setattr(sp, "_HAS_Q", False)


def test_venv_path_helpers(monkeypatch, tmp_path: Path):
    v = tmp_path / "venv"
    # Non-windows
    monkeypatch.setattr(sp, "sys", SimpleNamespace(platform="linux"), raising=False)
    assert sp.get_venv_bin_dir(v).name in ("bin", "Scripts")
    # Windows
    monkeypatch.setattr(sp, "sys", SimpleNamespace(platform="win32"), raising=False)
    assert sp.get_venv_bin_dir(v).name == "Scripts"


def test_translate_and_alias(monkeypatch):
    monkeypatch.setattr(sp, "LANG", "en")
    assert isinstance(sp.translate("welcome"), str)
    # Unknown key returns key
    assert sp.translate("no_such_key") == "no_such_key"


def test_set_language_and_exit(monkeypatch):
    # Select sv
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "2")
    sp.set_language()
    assert sp.LANG == "sv"

    # KeyboardInterrupt triggers sys.exit
    def bad(_=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr(sp, "ask_text", bad)
    try:
        sp.set_language()
    except SystemExit:
        pass


def test_parse_cli_and_prompt_venv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup_project.py", "--lang", "en", "--no-venv", "--ui", "rich"], raising=False)
    ns = sp.parse_cli_args()
    assert ns.lang == "en" and ns.no_venv is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "1")
    monkeypatch.setattr(sp, "ui_menu", lambda items: None)
    monkeypatch.setattr(sp, "ui_rule", lambda title: None)
    assert sp.prompt_virtual_environment_choice() is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "2")
    assert sp.prompt_virtual_environment_choice() is False


def test_parse_env_and_find_missing(tmp_path: Path):
    env = tmp_path / ".envtest"
    env.write_text('AZURE_API_KEY="abc"\nOTHER=1\n')
    parsed = sp.parse_env_file(env)
    assert parsed.get("AZURE_API_KEY") == "abc"
    missing = sp.find_missing_env_keys(parsed, ["AZURE_API_KEY", "GPT4O_DEPLOYMENT_NAME"])
    assert "GPT4O_DEPLOYMENT_NAME" in missing


def test_prompt_and_update_env(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    existing = {}
    # Supply a value per required Azure key
    vals = [f"v{i}" for i in range(1, len(sp.REQUIRED_AZURE_KEYS) + 1)]
    seq = iter(vals)
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.prompt_and_update_env(sp.REQUIRED_AZURE_KEYS, env, existing)
    content = env.read_text()
    for k in sp.REQUIRED_AZURE_KEYS:
        assert k in content


def test_ensure_azure_openai_env_calls_prompt(monkeypatch, tmp_path: Path):
    # Create an empty .env and ensure prompt_and_update_env is invoked
    monkeypatch.setattr(sp, "parse_env_file", lambda p: {})
    called = {}

    def fake_prompt(missing, path, existing):
        called['ok'] = True

    monkeypatch.setattr(sp, "prompt_and_update_env", fake_prompt)
    sp.ensure_azure_openai_env()
    assert called.get('ok') is True


def test_run_ai_connectivity_check_silent_no_endpoint(monkeypatch):
    # Patch OpenAIConfig to have no endpoint
    import src.pipeline.ai_processor as aipkg

    monkeypatch.setattr(aipkg, "OpenAIConfig", lambda: SimpleNamespace(gpt4o_endpoint="", api_key="k", request_timeout=1))
    ok, detail = sp.run_ai_connectivity_check_silent()
    assert ok is False and "Missing OpenAI endpoint" in detail


def test_entry_point_minimal(monkeypatch):
    # Provide minimal CLI args and stub out heavy functions
    monkeypatch.setattr(sp, "parse_cli_args", lambda: SimpleNamespace(lang='en', no_venv=True, ui='rich'))
    monkeypatch.setattr(sp, "set_language", lambda: None)
    monkeypatch.setattr(sp, "ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr(sp, "main_menu", lambda: None)
    try:
        sp.entry_point()
    except SystemExit:
        pass
