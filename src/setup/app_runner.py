"""Entrypoint and orchestration helpers for setup application.

This module provides top-level orchestration functions for running the interactive
setup, entrypoints, CLI parsing, environment management, Azure/OpenAI configuration
prompting, and invoking UI flows for the application. It composes and delegates to
helpers from the UI, venv, prompt, and Azure environment modules, but contains only
file-local logic and boundaries. It exposes all interactive run methods as patchable
test points for robust CI and user automation.

References
----------
The exported helpers enable patchable orchestration for interactive and CLI-driven
setup within the boundaries of src.setup.app and supporting UI/pipeline modules.

Examples
--------
>>> import src.setup.app_runner as runner
>>> args = runner.parse_cli_args(['--lang', 'en'])
>>> runner.run(args)
>>> runner.entry_point()  # runs entire interactive CLI

"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path
from typing import Any, Optional
from typing import Callable

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
    r"""Run the interactive setup application using parsed CLI arguments.

    Composes UI headers and invokes the main menu entrypoint. Accepts CLI args
    controlling application language and venv activation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments for the application (e.g., ``lang``, ``no_venv``).

    Returns
    -------
    None

    Notes
    -----
    Runs with English fallback if `lang` is invalid. This function delegates UI and
    menu orchestration to `src.setup.app_ui` and `src.setup.ui.menu`.

    Examples
    --------
    >>> import argparse
    >>> from src.setup import app_runner
    >>> ns = argparse.Namespace(lang="en", no_venv=False)
    >>> app_runner.run(ns)  # doctest: +SKIP

    """
    i18n.LANG = args.lang
    try:
        from src.setup.app_ui import ui_header

        ui_header(i18n.translate("welcome"))
    except Exception:
        pass
    try:
        from src.setup.ui import menu

        try:
            menu.main_menu()
        except Exception:
            pass
    except Exception:
        pass


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    r"""Parse command-line arguments for the setup application.

    Creates an argument parser with options for language, venv skipping, and UI type.

    Parameters
    ----------
    argv : list of str or None, optional
        List of argument strings to parse (as from ``sys.argv[1:]``).
        If None, defaults to ``sys.argv``.

    Returns
    -------
    argparse.Namespace
        Namespace containing parsed arguments.

    Examples
    --------
    >>> from src.setup import app_runner
    >>> ns = app_runner.parse_cli_args(['--lang', 'sv', '--no-venv'])
    >>> ns.lang
    'sv'
    >>> ns.no_venv
    True

    """
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
            from src.setup.app_prompts import (
                prompt_virtual_environment_choice as _prompt_choice,
            )
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
        # Prefer the concrete UI package. Tests should patch
        # `src.setup.ui.menu.main_menu` when they need to alter behaviour.
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

        subprocess.run(
            [get_python_executable(), str(helper), "--extreme"], cwd=PROJECT_ROOT
        )
    except Exception:
        pass


def parse_env_file(env_path: Path) -> dict[str, str]:
    from src.setup.azure_env import parse_env_file as _p

    return _p(env_path)


def prompt_and_update_env(
    missing_keys: list[str], env_path: Path, existing: dict[str, str], ui: Any = None
) -> None:
    from src.setup.azure_env import prompt_and_update_env as _p

    # Forward the explicit `ui` when provided; otherwise let the azure
    # helper discover a suitable UI implementation on its own. Avoid
    # reaching into a legacy shim in ``sys.modules``.
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
    # but fall back to the concrete UI helpers so tests can patch the
    # real modules instead of relying on a global shim object.
    # Call the silent connectivity check implementation directly. Tests
    # can patch `run_ai_connectivity_check_silent` on this module when
    # necessary.
    ok, detail = run_ai_connectivity_check_silent()

    # Use the concrete UI helpers; tests should patch these where
    # necessary. This avoids consulting a legacy shim in ``sys.modules``.
    _ui_success_fallback: Optional[Callable[[str], None]] = None
    _ui_error_fallback: Optional[Callable[[str], None]] = None
    try:
        from src.setup.app_ui import (
            ui_success as _ui_success_fallback,
            ui_error as _ui_error_fallback,
        )
    except Exception:
        _ui_success_fallback = None
        _ui_error_fallback = None

    if ok:
        if _ui_success_fallback is not None:
            try:
                _ui_success_fallback(i18n.translate("ai_check_ok"))
            except Exception:
                pass
        return True
    if _ui_error_fallback is not None:
        try:
            _ui_error_fallback(i18n.translate("ai_check_fail"))
            _ui_error_fallback(str(detail))
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
