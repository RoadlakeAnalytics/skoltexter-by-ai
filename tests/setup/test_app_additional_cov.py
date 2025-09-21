"""Additional tests exercising branches in src.setup.app to improve coverage."""

from types import SimpleNamespace
import subprocess
import importlib
import sys as _sys
import types

import src.setup.app_ui as _app_ui
import src.setup.app_runner as _app_runner
import src.setup.app_venv as _app_venv
import src.setup.app_prompts as _app_prompts

app = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    run=_app_runner.run,
    _sync_console_helpers=_app_ui._sync_console_helpers,
    run_ai_connectivity_check_interactive=_app_runner.run_ai_connectivity_check_interactive,
    run_extreme_quality_suite=_app_runner.run_extreme_quality_suite,
    run_full_quality_suite=_app_runner.run_full_quality_suite,
    entry_point=_app_runner.entry_point,
    main_menu=_app_runner.main_menu,
    set_language=_app_prompts.set_language,
    ensure_azure_openai_env=_app_runner.ensure_azure_openai_env,
    run_ai_connectivity_check_silent=_app_runner.run_ai_connectivity_check_silent,
    ui_success=_app_ui.ui_success,
    ui_error=_app_ui.ui_error,
    get_python_executable=_app_venv.get_python_executable,
)
_sys.modules.setdefault("src.setup.app", app)


def test_parse_cli_args_and_run(monkeypatch):
    ns = app.parse_cli_args(["--lang", "en", "--no-venv", "--ui", "rich"])
    assert ns.lang == "en" and ns.no_venv is True

    called = {}
    # Patch menu.main_menu so run() delegates without error
    import src.setup.ui.menu as menu

    monkeypatch.setattr(menu, "main_menu", lambda: called.setdefault("mm", True))
    args = SimpleNamespace(lang="en")
    app.run(args)
    assert called.get("mm") is True


def test_sync_console_helpers_propagation(monkeypatch):
    # Set module-level toggles and ensure console_helpers picks them up
    import src.setup.console_helpers as ch

    monkeypatch.setattr(app, "_RICH_CONSOLE", object(), raising=False)
    monkeypatch.setattr(app, "_HAS_Q", True, raising=False)
    fake_q = object()
    monkeypatch.setattr(app, "questionary", fake_q, raising=False)
    app._sync_console_helpers()
    assert ch._HAS_Q is True
    assert ch.questionary is fake_q


def test_run_ai_connectivity_interactive_branches(monkeypatch):
    # Success branch
    monkeypatch.setattr(app, "run_ai_connectivity_check_silent", lambda: (True, "ok"))
    called = {}
    monkeypatch.setattr(app, "ui_success", lambda m: called.setdefault("ok", m))
    assert app.run_ai_connectivity_check_interactive() is True
    assert "ok" in called

    # Failure branch
    monkeypatch.setattr(
        app, "run_ai_connectivity_check_silent", lambda: (False, "detail")
    )
    called = {}
    monkeypatch.setattr(app, "ui_error", lambda m: called.setdefault("err", m))
    assert app.run_ai_connectivity_check_interactive() is False
    assert "err" in called


def test_run_quality_suites(monkeypatch):
    # Patch subprocess.run to avoid executing anything
    called = {}

    def fake_run(*a, **k):
        called["args"] = a

    monkeypatch.setattr(app, "get_python_executable", lambda: "/usr/bin/python")
    monkeypatch.setattr(subprocess, "run", fake_run)
    app.run_full_quality_suite()
    app.run_extreme_quality_suite()
    assert "args" in called


def test_entry_point_invokes_main_menu(monkeypatch):
    # Prevent language prompt and venv management, ensure main_menu called
    monkeypatch.setattr(
        app, "parse_cli_args", lambda: SimpleNamespace(lang="en", no_venv=True)
    )
    monkeypatch.setattr(app, "set_language", lambda: None)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None)
    called = {}
    monkeypatch.setattr(app, "main_menu", lambda: called.setdefault("mm", True))
    app.entry_point()
    assert called.get("mm") is True
