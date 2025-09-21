"""Test helper shim mapping refactored modules into an `app` namespace.

This module is intended for test use only. Tests that previously
imported the legacy `src.setup.app` compatibility shim can instead
import `from tests._app_shim import app` which exposes the same
attributes but delegates them to the concrete, refactored modules
under `src.setup.*`.

The mappings are defensive: we use ``getattr`` with sensible fallbacks
so tests remain robust even if a concrete helper is missing.
"""

from __future__ import annotations

from types import SimpleNamespace
import subprocess as _subproc
import os as _os
import venv as _venv_mod

from src.setup import app_ui, app_prompts, app_venv, app_pipeline, app_runner
import src.setup.i18n as i18n
import src.setup.azure_env as azure_env
from src import config as cfg


# Build a SimpleNamespace that mirrors the legacy `src.setup.app` API but
# delegates behavior to the refactored modules. Tests may import `app`
# from this module and then monkeypatch attributes on it when needed.
_ns = SimpleNamespace(
    # UI helpers
    _sync_console_helpers=getattr(app_ui, "_sync_console_helpers", lambda: None),
    rprint=getattr(app_ui, "rprint", lambda *a, **k: None),
    ui_rule=getattr(app_ui, "ui_rule", lambda *a, **k: None),
    ui_header=getattr(app_ui, "ui_header", lambda *a, **k: None),
    ui_status=getattr(app_ui, "ui_status", lambda *a, **k: None),
    ui_info=getattr(app_ui, "ui_info", lambda *a, **k: None),
    ui_success=getattr(app_ui, "ui_success", lambda *a, **k: None),
    ui_warning=getattr(app_ui, "ui_warning", lambda *a, **k: None),
    ui_error=getattr(app_ui, "ui_error", lambda *a, **k: None),
    ui_menu=getattr(app_ui, "ui_menu", lambda *a, **k: None),
    _build_dashboard_layout=getattr(app_ui, "_build_dashboard_layout", lambda *a, **k: None),
    ui_has_rich=getattr(app_ui, "ui_has_rich", lambda: False),
    Panel=getattr(app_ui, "Panel", None),
    # Prompts
    ask_text=getattr(app_prompts, "ask_text", lambda *a, **k: ""),
    ask_confirm=getattr(app_prompts, "ask_confirm", lambda *a, **k: False),
    ask_select=getattr(app_prompts, "ask_select", lambda *a, **k: None),
    get_program_descriptions=getattr(app_prompts, "get_program_descriptions", lambda: {}),
    view_program_descriptions=getattr(app_prompts, "view_program_descriptions", lambda *a, **k: None),
    set_language=getattr(app_prompts, "set_language", lambda: None),
    prompt_virtual_environment_choice=getattr(app_prompts, "prompt_virtual_environment_choice", lambda: False),
    # Venv helpers
    get_venv_bin_dir=getattr(app_venv, "get_venv_bin_dir", lambda p: p / "bin"),
    get_venv_python_executable=getattr(app_venv, "get_venv_python_executable", lambda p: p / "python"),
    get_venv_pip_executable=getattr(app_venv, "get_venv_pip_executable", lambda p: p / "pip"),
    get_python_executable=getattr(app_venv, "get_python_executable", lambda: getattr(_os, "executable", "/usr/bin/python")),
    is_venv_active=getattr(app_venv, "is_venv_active", lambda: False),
    run_program=getattr(app_venv, "run_program", lambda *a, **k: True),
    manage_virtual_environment=getattr(app_venv, "manage_virtual_environment", lambda *a, **k: None),
    venv=_venv_mod,
    subprocess=_subproc,
    os=_os,
    # Pipeline
    _run_pipeline_step=getattr(app_pipeline, "_run_pipeline_step", lambda *a, **k: None),
    _render_pipeline_table=getattr(app_pipeline, "_render_pipeline_table", lambda *a, **k: None),
    _status_label=getattr(app_pipeline, "_status_label", lambda *a, **k: ""),
    _run_processing_pipeline_plain=getattr(app_pipeline, "_run_processing_pipeline_plain", lambda *a, **k: None),
    _run_processing_pipeline_rich=getattr(app_pipeline, "_run_processing_pipeline_rich", lambda *a, **k: None),
    # Runner/entry
    run=getattr(app_runner, "run", lambda *a, **k: None),
    parse_cli_args=getattr(app_runner, "parse_cli_args", lambda *a, **k: None),
    entry_point=getattr(app_runner, "entry_point", lambda *a, **k: None),
    main_menu=getattr(app_runner, "main_menu", lambda *a, **k: None),
    run_full_quality_suite=getattr(app_runner, "run_full_quality_suite", lambda: None),
    run_extreme_quality_suite=getattr(app_runner, "run_extreme_quality_suite", lambda: None),
    parse_env_file=getattr(app_runner, "parse_env_file", lambda *a, **k: {}),
    prompt_and_update_env=getattr(app_runner, "prompt_and_update_env", lambda *a, **k: None),
    find_missing_env_keys=getattr(app_runner, "find_missing_env_keys", lambda *a, **k: []),
    ensure_azure_openai_env=getattr(app_runner, "ensure_azure_openai_env", lambda *a, **k: None),
    run_ai_connectivity_check_silent=getattr(app_runner, "run_ai_connectivity_check_silent", lambda *a, **k: (False, "")),
    run_ai_connectivity_check_interactive=getattr(app_runner, "run_ai_connectivity_check_interactive", lambda *a, **k: False),
    # i18n + config
    translate=getattr(i18n, "translate", lambda k: k),
    LANG=getattr(i18n, "LANG", "en"),
    _=getattr(i18n, "_", lambda k: k),
    REQUIRED_AZURE_KEYS=getattr(azure_env, "REQUIRED_AZURE_KEYS", []),
    LOG_DIR=getattr(cfg, "LOG_DIR", None),
    PROJECT_ROOT=getattr(cfg, "PROJECT_ROOT", None),
    REQUIREMENTS_FILE=getattr(cfg, "REQUIREMENTS_FILE", None),
    REQUIREMENTS_LOCK_FILE=getattr(cfg, "REQUIREMENTS_LOCK_FILE", None),
    VENV_DIR=getattr(cfg, "VENV_DIR", None),
)

# Create a real module object and populate it with the attributes from the
# namespace. This ensures `import src.setup.app as app` continues to return a
# module object that tests can monkeypatch and that runtime code that reads
# `sys.modules['src.setup.app']` will find.
from types import ModuleType
import sys as _sys

_mod = ModuleType("src.setup.app")
for _k, _v in vars(_ns).items():
    setattr(_mod, _k, _v)

# Register module in sys.modules so importers and runtime code see it.
# Overwrite any existing entry so runtime lookups (e.g. in
# src.setup.app_runner.entry_point) observe the test shim during tests.
_sys.modules["src.setup.app"] = _mod

# Export the module as `app` for tests that do `from tests._app_shim import app`.
app = _mod
