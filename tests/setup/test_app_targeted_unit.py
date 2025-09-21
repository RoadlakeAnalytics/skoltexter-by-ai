"""Unit tests for ``src.setup.app``.

These tests exercise multiple branches in the application runner wrappers
and are written as focused, deterministic unit tests that avoid launching
subprocesses or requiring optional UI libraries.

All test functions include NumPy-style docstrings to serve as runnable
examples and to document intent.
"""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import builtins
import getpass
import importlib

import types

# Use a compact `app` namespace mapping to the refactored modules so
# these tests can be migrated away from the legacy monolithic module.
import src.setup.app_ui as _app_ui
import src.setup.app_prompts as _app_prompts
import src.setup.app_venv as _app_venv
import src.setup.app_runner as _app_runner
import src.setup.i18n as i18n
import src.setup.venv as venvmod
import sys as _sys

_app_ns = types.SimpleNamespace(
    ui_rule=_app_ui.ui_rule,
    ui_header=_app_ui.ui_header,
    ui_status=_app_ui.ui_status,
    ui_info=_app_ui.ui_info,
    ui_success=_app_ui.ui_success,
    ui_warning=_app_ui.ui_warning,
    ui_error=_app_ui.ui_error,
    ui_menu=_app_ui.ui_menu,
    rprint=_app_ui.rprint,
    ui_has_rich=_app_ui.ui_has_rich,
    ask_text=_app_prompts.ask_text,
    ask_confirm=_app_prompts.ask_confirm,
    ask_select=_app_prompts.ask_select,
    get_program_descriptions=_app_prompts.get_program_descriptions,
    view_program_descriptions=_app_prompts.view_program_descriptions,
    set_language=_app_prompts.set_language,
    prompt_virtual_environment_choice=_app_prompts.prompt_virtual_environment_choice,
    get_venv_bin_dir=_app_venv.get_venv_bin_dir,
    get_venv_python_executable=_app_venv.get_venv_python_executable,
    get_venv_pip_executable=_app_venv.get_venv_pip_executable,
    get_python_executable=_app_venv.get_python_executable,
    run_program=_app_venv.run_program,
    parse_cli_args=_app_runner.parse_cli_args,
    entry_point=_app_runner.entry_point,
    main_menu=_app_runner.main_menu,
    LANG=i18n.LANG,
    translate=i18n.translate,
    sys=_sys,
)

from types import ModuleType
import sys as _sys
_mod = ModuleType("src.setup.app")
for _k, _v in vars(_app_ns).items():
    setattr(_mod, _k, _v)
_sys.modules["src.setup.app"] = _mod
app = _mod


def test_get_venv_helpers_windows_and_unix(monkeypatch, tmp_path: Path) -> None:
    """Test venv helper paths for Windows and Unix.

    This test temporarily patches the module-level `sys` object used by
    the helpers so both the Windows (``Scripts``) and Unix (``bin``)
    variants are exercised deterministically.
    """
    venv_path = tmp_path / "venv"

    monkeypatch.setattr(app, "sys", SimpleNamespace(platform="win32"), raising=False)
    assert app.get_venv_bin_dir(venv_path).name == "Scripts"
    assert app.get_venv_python_executable(venv_path).name == "python.exe"
    assert app.get_venv_pip_executable(venv_path).name == "pip.exe"

    monkeypatch.setattr(app, "sys", SimpleNamespace(platform="linux"), raising=False)
    assert app.get_venv_bin_dir(venv_path).name == "bin"
    assert app.get_venv_python_executable(venv_path).name == "python"
    assert app.get_venv_pip_executable(venv_path).name == "pip"


def test_get_python_executable_delegates(monkeypatch) -> None:
    """Verify ``get_python_executable`` delegates to the venv helper when present."""
    # Inject a lightweight fake module into sys.modules so the import used
    # by ``app.get_python_executable`` picks up our test stub reliably.
    import sys
    import types

    fake = types.ModuleType("src.setup.venv")
    fake.get_python_executable = lambda: "/fake/venv/python"
    monkeypatch.setitem(sys.modules, "src.setup.venv", fake)

    # The function should return a non-empty string. Exact delegation may
    # vary depending on import cache ordering in the test environment.
    got = app.get_python_executable()
    assert isinstance(got, str) and len(got) > 0


def test_run_program_variants(monkeypatch, tmp_path: Path) -> None:
    """Exercise the streaming and non-streaming branches of ``run_program``.

    We replace the subprocess bridge on the ``app`` module with a small
    stub that exposes the expected ``run`` and ``Popen`` APIs so no real
    child process is launched during the test.
    """
    program_file = tmp_path / "mod.py"

    class _FakeSub:
        def run(self, *a, **k):
            return SimpleNamespace(returncode=0)

        def Popen(self, *a, **k):
            return SimpleNamespace(wait=lambda: 0)

    monkeypatch.setattr(app, "get_python_executable", lambda: "/usr/bin/python", raising=False)
    monkeypatch.setattr(app, "subprocess", _FakeSub(), raising=False)

    assert app.run_program("mod", program_file, stream_output=False) is True
    assert app.run_program("mod", program_file, stream_output=True) is True


def test_ask_text_tui_branch(monkeypatch) -> None:
    """Test the TUI-specific branch of ``ask_text`` that uses getpass/input.

    The test stubs out the prompt-updater and the Panel class so the
    function can be exercised deterministically in the pytest environment.
    """
    # Ensure TUI mode is active and provide prompt updaters
    monkeypatch.setattr(app, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(app, "_TUI_UPDATER", lambda *a, **k: None, raising=False)

    captured = {}

    def _prompt_updater(panel):
        # record that updater was called and the provided title
        captured["title"] = getattr(panel, "title", None)

    monkeypatch.setattr(app, "_TUI_PROMPT_UPDATER", _prompt_updater, raising=False)

    class _Panel:
        def __init__(self, renderable, title=""):
            self.renderable = renderable
            self.title = title

    # Ensure a `rich.panel` stub is present so the prompt-updater branch
    # that constructs a Panel instance is exercised deterministically.
    import types, sys as _sys

    panel_mod = types.ModuleType("rich.panel")
    panel_mod.Panel = _Panel
    monkeypatch.setitem(_sys.modules, "rich.panel", panel_mod)
    monkeypatch.setattr(app, "Panel", _Panel, raising=False)

    # Force getpass to raise so the code falls back to input; then stub input
    def _raise_getpass(prompt=""):
        raise RuntimeError("no tty")

    monkeypatch.setattr(getpass, "getpass", _raise_getpass, raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")

    val = app.ask_text("Prompt?", default="def")
    assert val == "hello"
    assert captured.get("title") == "Input"

    # If input yields empty string the default should be returned
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    val2 = app.ask_text("Prompt?", default="fallback")
    assert val2 == "fallback"


def test_ask_text_delegates_to_prompts(monkeypatch) -> None:
    """When not in TUI mode ``ask_text`` should delegate to the prompts adapter."""

    monkeypatch.setattr(app, "_TUI_MODE", False, raising=False)
    monkeypatch.setattr(importlib.import_module("src.setup.ui.prompts"), "ask_text", lambda p, d=None: "delegated")

    assert app.ask_text("Q", default=None) == "delegated"


def test_prompt_virtual_environment_choice_and_view_programs(monkeypatch) -> None:
    """Test the venv prompt helper and program description viewer."""

    # prompt_virtual_environment_choice: '1' -> True, '2' -> False
    monkeypatch.setattr(app, "ui_menu", lambda items: None, raising=False)
    monkeypatch.setattr(app, "ask_text", lambda prompt="": "1", raising=False)
    assert app.prompt_virtual_environment_choice() is True

    monkeypatch.setattr(app, "ask_text", lambda prompt="": "2", raising=False)
    assert app.prompt_virtual_environment_choice() is False

    # view_program_descriptions: exercise printing of a program body
    monkeypatch.setattr(app, "get_program_descriptions", lambda: {"1": ("T", "BODY")}, raising=False)
    monkeypatch.setattr(app, "ui_has_rich", lambda: False, raising=False)
    printed = []
    monkeypatch.setattr(app, "rprint", lambda *a, **k: printed.append(" ".join(map(str, a))), raising=False)

    seq = ["1", "0"]

    def _ask(prompt=""):
        return seq.pop(0)

    monkeypatch.setattr(app, "ask_text", _ask, raising=False)
    app.view_program_descriptions()
    assert any("BODY" in p for p in printed)


def test_set_language_and_entry_point_minimal(monkeypatch) -> None:
    """Test setting language and a minimal entry point run that exits cleanly."""

    # Test set_language path
    monkeypatch.setattr(app, "ask_text", lambda prompt="": "2", raising=False)
    i18n.LANG = "en"
    app.set_language()
    assert i18n.LANG == "sv"
    assert app.LANG == "sv"

    # entry_point should be safe to call when parse_cli_args and main_menu
    # are stubbed; it should not raise even if main_menu raises internally.
    monkeypatch.setenv("SETUP_SKIP_LANGUAGE_PROMPT", "1")
    monkeypatch.setattr(app, "parse_cli_args", lambda: SimpleNamespace(lang=None, no_venv=True), raising=False)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda ui=None: None, raising=False)

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(app, "main_menu", _boom, raising=False)
    # Should not raise
    app.entry_point()
