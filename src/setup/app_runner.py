"""Entrypoint and orchestration helpers extracted from src.setup.app.

This module contains the high-level run/entrypoint logic that composes the
smaller helpers (UI, prompts, venv and pipeline) to implement the CLI and
interactive flows. It reads and writes module-level config/state on the
``src.setup.app`` module so tests can patch expected global state.
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path
from typing import Any

import importlib

import src.setup.i18n as i18n

from src.config import (
    LOG_DIR,
    PROJECT_ROOT,
    REQUIREMENTS_FILE,
    REQUIREMENTS_LOCK_FILE,
    VENV_DIR,
)


def run(args: argparse.Namespace) -> None:
    """Run the setup application using parsed CLI args.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments (``lang``, ``no_venv``).
    """
    i18n.LANG = args.lang
    try:
        from src.setup.app_ui import ui_header

        ui_header(i18n.translate("welcome"))
    except Exception:
        pass
    # Delegate to the menu implementation. Allow tests to inject a fake
    # module onto the app module for deterministic behaviour.
    app_mod = sys.modules.get("src.setup.app")
    menu = getattr(app_mod, "menu", None)
    if menu is None:
        try:
            menu = importlib.import_module("src.setup.ui.menu")
        except Exception:
            menu = None
    if menu is not None:
        try:
            menu.main_menu()
        except Exception:
            pass


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the setup application."""
    parser = argparse.ArgumentParser(description="Setup application")
    parser.add_argument("--lang", type=str, choices=["en", "sv"], default="en")
    parser.add_argument("--no-venv", action="store_true")
    parser.add_argument("--ui", type=str, choices=["rich", "textual"], default="rich")
    return parser.parse_args(argv)


def entry_point() -> None:
    """Run the setup application from the command-line.

    This orchestrates parsing, optional venv management and launching the
    interactive menu.
    """
    # Allow tests to override the CLI parsing routine by patching the
    # attribute on the app shim module; fall back to the local parser
    # when not present.
    app_mod = sys.modules.get("src.setup.app")
    _parse = getattr(app_mod, "parse_cli_args", None)
    if _parse is None:
        args = parse_cli_args()
    else:
        args = _parse()

    if getattr(args, "lang", None):
        i18n.LANG = args.lang if args.lang in i18n.TEXTS else "en"
    if not os.environ.get("SETUP_SKIP_LANGUAGE_PROMPT"):
        # Prefer a patched implementation on the app shim module so tests
        # that monkeypatch ``app.set_language`` work deterministically.
        app_mod = sys.modules.get("src.setup.app")
        set_lang = getattr(app_mod, "set_language", None)
        if set_lang is None:
            try:
                from src.setup.app_prompts import set_language as _set

                _set()
            except Exception:
                pass
        else:
            try:
                set_lang()
            except Exception:
                pass
    if not getattr(args, "no_venv", False):
        from src.setup.app_venv import is_venv_active

        if not is_venv_active():
            try:
                from src.setup.app_prompts import prompt_virtual_environment_choice

                if prompt_virtual_environment_choice():
                    from src.setup.app_venv import manage_virtual_environment

                    manage_virtual_environment()
            except Exception:
                pass

    try:
        from src.setup.app_runner import ensure_azure_openai_env as _ensure

        _ensure()
    except Exception:
        # The real function may prompt; ignore in a minimal CLI run.
        pass

    try:
        from src.setup.app import main_menu

        main_menu()
    except Exception:
        return


def main_menu() -> None:
    """Delegate to the UI package main menu.

    Exposed so tests can monkeypatch the entry point behaviour.
    """
    try:
        import src.setup.ui.menu as menu

        menu.main_menu()
    except Exception:
        return


def run_full_quality_suite() -> None:
    """Run the local quality suite helper script.

    Uses the project's Python runtime to execute ``tools/run_all_checks.py``.
    Tests typically monkeypatch ``subprocess.run`` so the call is safe.
    """
    helper = PROJECT_ROOT / "tools" / "run_all_checks.py"
    try:
        import subprocess

        subprocess.run([get_python_executable(), str(helper)], cwd=PROJECT_ROOT)
    except Exception:
        pass


def run_extreme_quality_suite() -> None:
    """Run the extreme quality suite (intensive checks)."""
    helper = PROJECT_ROOT / "tools" / "run_all_checks.py"
    try:
        import subprocess

        subprocess.run([get_python_executable(), str(helper), "--extreme"], cwd=PROJECT_ROOT)
    except Exception:
        pass


def parse_env_file(env_path: Path) -> dict[str, str]:
    from src.setup.azure_env import parse_env_file as _p

    return _p(env_path)


def prompt_and_update_env(missing_keys: list[str], env_path: Path, existing: dict[str, str], ui: Any = None) -> None:
    from src.setup.azure_env import prompt_and_update_env as _p

    if ui is None:
        ui = sys.modules.get(__name__)
    return _p(missing_keys, env_path, existing, ui=ui)


def find_missing_env_keys(existing: dict[str, str], required: list[str]) -> list[str]:
    from src.setup.azure_env import find_missing_env_keys as _f

    return _f(existing, required)


def ensure_azure_openai_env(ui: Any = None) -> None:
    env_path = getattr(sys.modules.get("src.setup.app"), "ENV_PATH", PROJECT_ROOT / ".env")
    existing = parse_env_file(env_path)
    missing = find_missing_env_keys(existing, [])
    if missing:
        prompt_and_update_env(missing, env_path, existing)


def run_ai_connectivity_check_silent() -> tuple[bool, str]:
    from src.setup.azure_env import run_ai_connectivity_check_silent as _r

    return _r()


def run_ai_connectivity_check_interactive() -> bool:
    ok, detail = run_ai_connectivity_check_silent()
    if ok:
        # Call the UI helpers via the central app module so tests can override
        # them by monkeypatching attributes on ``src.setup.app``.
        app_mod = sys.modules.get("src.setup.app")
        ui_success = getattr(app_mod, "ui_success", None)
        if ui_success is not None:
            try:
                ui_success(i18n.translate("ai_check_ok"))
            except Exception:
                pass
        return True
    ui_error = getattr(app_mod, "ui_error", None)
    if ui_error is not None:
        try:
            ui_error(i18n.translate("ai_check_fail"))
            ui_error(str(detail))
        except Exception:
            pass
    return False


def get_python_executable() -> str:
    try:
        from src.setup.venv import get_python_executable as _g

        return _g()
    except Exception:
        return getattr(sys, "executable", "/usr/bin/python")


__all__ = [
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
    "get_python_executable",
]
