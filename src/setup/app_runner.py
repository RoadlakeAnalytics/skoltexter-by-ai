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
    # Delegate to the UI menu implementation. Tests should patch the
    # concrete UI module (``src.setup.ui.menu``) when needed rather than
    # injecting a module into ``sys.modules``.
    try:
        from src.setup.ui import menu

        try:
            menu.main_menu()
        except Exception:
            pass
    except Exception:
        # No UI available in this environment; continue silently.
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
    # Parse CLI args. Tests can monkeypatch this module's ``parse_cli_args``
    # if they need to alter parsing behaviour.
    args = parse_cli_args()

    if getattr(args, "lang", None):
        i18n.LANG = args.lang if args.lang in i18n.TEXTS else "en"
    if not os.environ.get("SETUP_SKIP_LANGUAGE_PROMPT"):
        # Call the canonical set_language implementation; tests should
        # patch ``src.setup.app_prompts.set_language`` when needed.
        try:
            from src.setup.app_prompts import set_language as _set

            _set()
        except Exception:
            pass
    if not getattr(args, "no_venv", False):
        # Determine if a venv is active and optionally manage it. Tests
        # should patch the concrete helpers in ``src.setup.app_venv`` and
        # ``src.setup.app_prompts`` when necessary.
        try:
            from src.setup.app_venv import is_venv_active as _is_venv_active
            from src.setup.app_prompts import prompt_virtual_environment_choice as _prompt_choice
            from src.setup.app_venv import manage_virtual_environment as _manage

            if not _is_venv_active():
                try:
                    if _prompt_choice():
                        _manage()
                except Exception:
                    pass
        except Exception:
            pass

    try:
        ensure_azure_openai_env()
    except Exception:
        pass

    try:
        # Call local main_menu implementation; tests may patch
        # ``src.setup.ui.menu.main_menu`` as needed.
        main_menu()
    except Exception:
        return


def main_menu() -> None:
    """Delegate to the UI package main menu.

    Exposed so tests can monkeypatch the entry point behaviour.
    """
    try:
        app_mod = sys.modules.get("src.setup.app")
        menu = getattr(app_mod, "menu", None)
        if menu is None:
            import src.setup.ui.menu as menu
        try:
            menu.main_menu()
        except Exception:
            return
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
        ui = sys.modules.get("src.setup.app")
    return _p(missing_keys, env_path, existing, ui=ui)


def find_missing_env_keys(existing: dict[str, str], required: list[str]) -> list[str]:
    from src.setup.azure_env import find_missing_env_keys as _f

    return _f(existing, required)


def ensure_azure_openai_env(ui: Any = None) -> None:
    """Ensure required Azure/OpenAI environment variables exist.

    This helper reads the configured `.env` file (via the canonical
    ``ENV_PATH`` defined in :mod:`src.setup.azure_env`), determines which
    keys are missing and, if any are absent, prompts the user (using
    :func:`prompt_and_update_env`) to collect them and write an updated
    `.env` file.

    Parameters
    ----------
    ui : optional
        Optional UI object providing ``rprint``, ``_`` and ``ask_text``.
        If not provided the implementation will allow the underlying
        helpers to decide the appropriate UI fallback.

    Returns
    -------
    None
    """
    # Prefer an explicit import of the concrete azure helpers so this
    # module no longer depends on an external shim object in
    # ``sys.modules``. Tests should patch the concrete functions on this
    # module (for example ``src.setup.app_runner.parse_env_file``) when
    # necessary.
    from src.setup import azure_env as _azure_env

    env_path = getattr(_azure_env, "ENV_PATH", PROJECT_ROOT / ".env")

    existing = parse_env_file(env_path)
    required = getattr(_azure_env, "REQUIRED_AZURE_KEYS", [])
    missing = find_missing_env_keys(existing, required)
    if missing:
        # Forward the optional UI through to the prompt helper.
        prompt_and_update_env(missing, env_path, existing, ui=ui)


def run_ai_connectivity_check_silent() -> tuple[bool, str]:
    from src.setup.azure_env import run_ai_connectivity_check_silent as _r

    return _r()


def run_ai_connectivity_check_interactive() -> bool:
    # Prefer a possibly patched implementation on the central shim module
    app_mod = sys.modules.get("src.setup.app")
    _r = getattr(app_mod, "run_ai_connectivity_check_silent", run_ai_connectivity_check_silent)
    ok, detail = _r()
    # Call the UI helpers via the central app module so tests can override
    # them by monkeypatching attributes on ``src.setup.app``.
    app_mod = sys.modules.get("src.setup.app")
    if ok:
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
