"""Thin compatibility shim for the setup application.

This module used to contain a large amount of orchestration logic. To
improve maintainability the implementation has been split into a few
smaller modules under ``src.setup`` (``app_ui``, ``app_prompts``,
``app_venv``, ``app_pipeline``, ``app_runner``). The present module is a
compact compatibility layer that exposes the original public API so
existing callsites and tests continue to work while the real logic lives
in the smaller modules.
"""

from __future__ import annotations

import sys
from typing import Any

from src.config import LOG_DIR, PROJECT_ROOT, REQUIREMENTS_FILE, REQUIREMENTS_LOCK_FILE, VENV_DIR

# Module-level language and toggles (tests may monkeypatch these on the
# shim module before calling into the implementation modules).
LANG: str = "en"
_RICH_CONSOLE: object | None = None
_HAS_Q: bool = False
questionary: object | None = None
_TUI_MODE: bool = False
_TUI_UPDATER: Any | None = None
_TUI_PROMPT_UPDATER: Any | None = None

# Attempt to import `rich.panel` early so tests that inject a stub
# ``rich`` module in ``sys.modules`` are respected before other
# imports. This mirrors the original behaviour of the larger module.
Panel = None
try:
    import importlib

    _rich_mod = sys.modules.get("rich")
    _panel_in_sys = sys.modules.get("rich.panel")
    if _rich_mod is not None and getattr(_rich_mod, "__path__", None) is None:
        if _panel_in_sys is None:
            raise ImportError("rich module stubbed; skip importing rich.panel")
        if getattr(_panel_in_sys, "__spec__", None) is None:
            Panel = getattr(_panel_in_sys, "Panel", None)
        else:
            raise ImportError("rich module stubbed; skip importing rich.panel")
    else:
        _panel_mod = importlib.import_module("rich.panel")
        Panel = getattr(_panel_mod, "Panel", None)
except Exception:
    Panel = None

# Export a stable set of names by importing the smaller modules and
# re-exporting their attributes. The import-time cost is negligible and
# keeps this file tiny while providing the legacy module surface.
from src.setup.app_ui import *  # noqa: F401,F403
from src.setup.app_prompts import *  # noqa: F401,F403
from src.setup.app_venv import *  # noqa: F401,F403
from src.setup.app_pipeline import *  # noqa: F401,F403
from src.setup.app_runner import *  # noqa: F401,F403

__all__ = [
    # state
    "LANG",
    "LOG_DIR",
    "PROJECT_ROOT",
    "REQUIREMENTS_FILE",
    "REQUIREMENTS_LOCK_FILE",
    "VENV_DIR",
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
    # prompts
    "ask_text",
    "ask_confirm",
    "ask_select",
    "get_program_descriptions",
    "view_program_descriptions",
    # venv helpers
    "get_venv_bin_dir",
    "get_venv_python_executable",
    "get_venv_pip_executable",
    "get_python_executable",
    "is_venv_active",
    "run_program",
    "manage_virtual_environment",
    # pipeline wrappers
    "_render_pipeline_table",
    "_run_pipeline_step",
    "_run_processing_pipeline_plain",
    "_run_processing_pipeline_rich",
    "_status_label",
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
]
