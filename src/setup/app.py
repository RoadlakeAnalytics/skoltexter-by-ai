"""Compatibility adapter for legacy tests.

This module intentionally provides a narrow compatibility layer that
re-exports functions from the refactored modules under ``src.setup`` so
existing tests keep working while we migrate them to import concrete
modules. This file is a temporary, well-documented adapter and should
be removed once tests have been updated to reference the new modules
directly.
"""

from __future__ import annotations

from src.setup import app_ui, app_prompts, app_venv, app_pipeline, app_runner
from src.setup import i18n, azure_env
from src import config as _config
import subprocess
import sys
import venv as _venv_module
import os as _os_module

# Backwards-compatible module-level toggles used by tests. Tests often
# monkeypatch these on the legacy top-level module; provide sane defaults
# here so the compatibility adapter behaves like the original module.
_RICH_CONSOLE = None
_HAS_Q = False
questionary = None
_TUI_MODE = False
_TUI_UPDATER = None
_TUI_PROMPT_UPDATER = None
venv = _venv_module
os = _os_module

# Optional rich Panel import: if the optional rich package is available at
# import-time, expose the Panel symbol to preserve legacy import-time
# behaviour relied upon by tests that reload this module under stubbed
# import conditions.
try:  # pragma: no cover - exercised by tests when rich is stubbed
    from importlib import import_module

    _panel_mod = import_module("rich.panel")
    Panel = getattr(_panel_mod, "Panel", None)
except Exception:
    Panel = None

# UI
_sync_console_helpers = app_ui._sync_console_helpers
rprint = app_ui.rprint
ui_rule = app_ui.ui_rule
ui_header = app_ui.ui_header
ui_status = app_ui.ui_status
ui_info = app_ui.ui_info
ui_success = app_ui.ui_success
ui_warning = app_ui.ui_warning
ui_error = app_ui.ui_error
ui_menu = app_ui.ui_menu
_build_dashboard_layout = app_ui._build_dashboard_layout


def ui_has_rich() -> bool:
    """Return whether the rich console/UI is available.

    This wrapper delegates to the refactored UI helper and falls back to
    the module-level `_RICH_CONSOLE` flag when the helper raises or is
    unavailable. Tests may monkeypatch `_RICH_CONSOLE` on this module to
    influence the behaviour.
    """
    try:
        return bool(app_ui.ui_has_rich())
    except Exception:
        return bool(_RICH_CONSOLE)

# Prompts
ask_text = app_prompts.ask_text
ask_confirm = app_prompts.ask_confirm
ask_select = app_prompts.ask_select
get_program_descriptions = app_prompts.get_program_descriptions
view_program_descriptions = app_prompts.view_program_descriptions
set_language = app_prompts.set_language
prompt_virtual_environment_choice = app_prompts.prompt_virtual_environment_choice

# Venv
get_venv_bin_dir = app_venv.get_venv_bin_dir
get_venv_python_executable = app_venv.get_venv_python_executable
get_venv_pip_executable = app_venv.get_venv_pip_executable
get_python_executable = app_venv.get_python_executable
is_venv_active = app_venv.is_venv_active
run_program = app_venv.run_program
manage_virtual_environment = app_venv.manage_virtual_environment

# Pipeline wrappers
_run_pipeline_step = app_pipeline._run_pipeline_step
_render_pipeline_table = app_pipeline._render_pipeline_table
_status_label = app_pipeline._status_label
_run_processing_pipeline_plain = app_pipeline._run_processing_pipeline_plain
_run_processing_pipeline_rich = app_pipeline._run_processing_pipeline_rich

# Runner/entry
run = app_runner.run
parse_cli_args = app_runner.parse_cli_args
entry_point = app_runner.entry_point
main_menu = app_runner.main_menu
run_full_quality_suite = app_runner.run_full_quality_suite
run_extreme_quality_suite = app_runner.run_extreme_quality_suite
parse_env_file = app_runner.parse_env_file
prompt_and_update_env = app_runner.prompt_and_update_env
find_missing_env_keys = app_runner.find_missing_env_keys
ensure_azure_openai_env = app_runner.ensure_azure_openai_env
run_ai_connectivity_check_silent = app_runner.run_ai_connectivity_check_silent
run_ai_connectivity_check_interactive = app_runner.run_ai_connectivity_check_interactive

# i18n helpers and constants
translate = i18n.translate
LANG = i18n.LANG
_ = i18n._

# Azure keys
REQUIRED_AZURE_KEYS = azure_env.REQUIRED_AZURE_KEYS

# Config constants
LOG_DIR = _config.LOG_DIR
PROJECT_ROOT = _config.PROJECT_ROOT
REQUIREMENTS_FILE = _config.REQUIREMENTS_FILE
REQUIREMENTS_LOCK_FILE = _config.REQUIREMENTS_LOCK_FILE
VENV_DIR = _config.VENV_DIR

__all__ = [
    # UI
    "_sync_console_helpers",
    "rprint",
    "ui_rule",
    "ui_header",
    "ui_status",
    "ui_info",
    "ui_success",
    "ui_warning",
    "ui_error",
    "ui_menu",
    "_build_dashboard_layout",
    "ui_has_rich",
    "Panel",
    # Prompts
    "ask_text",
    "ask_confirm",
    "ask_select",
    "get_program_descriptions",
    "view_program_descriptions",
    "set_language",
    "prompt_virtual_environment_choice",
    # venv
    "get_venv_bin_dir",
    "get_venv_python_executable",
    "get_venv_pip_executable",
    "get_python_executable",
    "is_venv_active",
    "run_program",
    "manage_virtual_environment",
    # pipeline
    "_run_pipeline_step",
    "_render_pipeline_table",
    "_status_label",
    "_run_processing_pipeline_plain",
    "_run_processing_pipeline_rich",
    # runner
    "run",
    "parse_cli_args",
    "entry_point",
    "main_menu",
    "run_full_quality_suite",
    "run_extreme_quality_suite",
    "parse_env_file",
    "prompt_and_update_env",
    "find_missing_env_keys",
    "ensure_azure_openai_env",
    "run_ai_connectivity_check_silent",
    "run_ai_connectivity_check_interactive",
    # i18n
    "translate",
    "LANG",
    "_",
    # azure keys
    "REQUIRED_AZURE_KEYS",
    # config
    "LOG_DIR",
    "PROJECT_ROOT",
    "REQUIREMENTS_FILE",
    "REQUIREMENTS_LOCK_FILE",
    "VENV_DIR",
    "sys",
    "venv",
    "os",
    # legacy subprocess module (tests may monkeypatch this)
    "subprocess",
]
