import sys
from types import SimpleNamespace

"""Tests for `src/setup/app.py` runner."""


import src.setup.app_runner as app
import src.setup.i18n as i18n
import src.setup.ui.menu as menu

import importlib
import builtins
from types import SimpleNamespace

import src.setup.app_ui as app_ui
import src.setup.app_prompts as app_prompts
import src.setup.app_venv as app_venv


def test_ui_helpers_fallback(capsys, monkeypatch):
    """Exercise UI fallback helpers when rich console is not available.

    This test patches the concrete console helpers to force the non-rich
    code path and then exercises the UI adapter functions to ensure they
    do not raise and produce output.

    Parameters
    ----------
    capsys : pytest.CaptureFixture
        Fixture to capture stdout/stderr.
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Force non-rich code path by clearing any concrete console helper
    monkeypatch.setattr("src.setup.console_helpers._RICH_CONSOLE", None, raising=False)

    app_ui.ui_rule("Title")
    app_ui.ui_header("Header")
    with app_ui.ui_status("Working..."):
        pass
    app_ui.ui_info("info")
    app_ui.ui_success("ok")
    app_ui.ui_warning("warn")
    app_ui.ui_error("err")
    app_ui.ui_menu([("1", "A"), ("2", "B")])
    out = capsys.readouterr().out
    assert "Title" in out or "Header" in out


def test_ask_helpers_branches(monkeypatch):
    """Verify the ask_text wrapper forwards to the prompts adapter or input.

    This test patches the concrete prompt implementation and the local
    TUI flags so the wrapper exercises both the input fallback and the
    prompts-adapter code path.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Fallback input path
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")
    monkeypatch.setattr(
        app_prompts, "_get_tui_flags", lambda: (False, None, None), raising=False
    )
    assert app_prompts.ask_text("prompt:") == "hello"

    # Prompts adapter path
    _prom = importlib.import_module("src.setup.ui.prompts")
    monkeypatch.setattr(
        _prom, "ask_text", lambda p, default=None: "qval", raising=False
    )
    assert app_prompts.ask_text("p") == "qval"


def test_venv_path_helpers(monkeypatch, tmp_path: "pathlib.Path"):
    """Verify virtualenv bin directory selection for different platforms.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level attributes.
    tmp_path : pathlib.Path
        Temporary path used as the virtualenv root.

    Returns
    -------
    None
    """
    v = tmp_path / "venv"
    monkeypatch.setattr(
        "src.setup.app_venv.sys", SimpleNamespace(platform="linux"), raising=False
    )
    assert app_venv.get_venv_bin_dir(v).name in ("bin", "Scripts")
    monkeypatch.setattr(
        "src.setup.app_venv.sys", SimpleNamespace(platform="win32"), raising=False
    )
    assert app_venv.get_venv_bin_dir(v).name == "Scripts"


def test_entry_point_basic(monkeypatch):
    """Test Entry point basic."""
    # Run entry_point with --lang en and --no-venv to cover the flow
    # Avoid interactive pauses and ensure the app runner receives CLI args.
    monkeypatch.setattr(
        sys, "argv", ["setup_project.py", "--lang", "en", "--no-venv"], raising=False
    )
    # Prevent side-effects from interactive helpers
    monkeypatch.setattr(i18n, "set_language", lambda: None, raising=False)
    monkeypatch.setattr(menu, "main_menu", lambda: None, raising=False)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None, raising=False)
    # Avoid exiting the test process
    monkeypatch.setattr(sys, "exit", lambda code=0: None, raising=False)
    # Run the app entry with a SimpleNamespace simulating parsed args
    app.run(SimpleNamespace(lang="en", no_venv=True))
