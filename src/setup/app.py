"""Application runner that composes modules and runs the setup app.

This module centralizes the entrypoint logic and is safe to execute as a
module (``python -m src.setup.app``). It does not depend on the legacy
top-level shim.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv as _venv
from pathlib import Path
from typing import Any

import src.setup.i18n as i18n
import src.setup.ui.menu as menu
from src.config import (
    LOG_DIR,
    PROJECT_ROOT,
    REQUIREMENTS_FILE,
    REQUIREMENTS_LOCK_FILE,
    VENV_DIR,
)
from src.setup.i18n import translate

try:
    from rich.panel import Panel
except Exception:
    Panel = None

venv = _venv

# Module-level language for tests to patch; keep in sync with i18n by default
LANG: str = getattr(i18n, "LANG", "en")

# Azure keys (exposed for tests)
try:
    from src.setup.azure_env import REQUIRED_AZURE_KEYS
except Exception:
    REQUIRED_AZURE_KEYS = [
        "AZURE_API_KEY",
        "AZURE_ENDPOINT_BASE",
        "GPT4O_DEPLOYMENT_NAME",
        "AZURE_API_VERSION",
    ]

# Module-level UI/test toggles. Tests monkeypatch these on the module.
_RICH_CONSOLE: object | None = None
_HAS_Q: bool = False
questionary: object | None = None

# TUI adapter slots (tests may set these)
_TUI_MODE: bool = False
_TUI_UPDATER: Any | None = None
_TUI_PROMPT_UPDATER: Any | None = None

# Shared status renderables (used by some TUI flows)
_STATUS_RENDERABLE: Any | None = None
_PROGRESS_RENDERABLE: Any | None = None


def run(args: argparse.Namespace) -> None:
    """Run the setup application using parsed CLI args.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments (``lang``, ``no_venv``).
    """
    i18n.LANG = args.lang
    # Delegate to the menu implementation
    try:
        from src.setup.ui.basic import ui_header

        ui_header(translate("welcome"))
    except Exception:
        pass
    menu.main_menu()


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the setup application.

    Parameters
    ----------
    argv : list[str] | None
        Optional argv list to parse.

    Returns
    -------
    argparse.Namespace
        Parsed args with fields ``lang`` and ``no_venv``.
    """
    parser = argparse.ArgumentParser(description="Setup application")
    parser.add_argument("--lang", type=str, choices=["en", "sv"], default="en")
    parser.add_argument("--no-venv", action="store_true")
    parser.add_argument("--ui", type=str, choices=["rich", "textual"], default="rich")
    return parser.parse_args(argv)


def _sync_console_helpers() -> None:
    """Propagate module-level UI toggles to the console helpers.

    Tests frequently monkeypatch `_RICH_CONSOLE`, `_HAS_Q` or `questionary`
    on this module; this helper pushes those values into the
    ``src.setup.console_helpers`` module before delegating UI actions so
    monkeypatching has the expected effect.
    """
    try:
        import src.setup.console_helpers as ch

        ch._RICH_CONSOLE = _RICH_CONSOLE
        ch._HAS_Q = _HAS_Q
        ch.questionary = questionary
    except Exception:
        pass


def rprint(*objects: Any, **kwargs: Any) -> None:
    """Proxy to console_helpers.rprint so azure UI helpers can use it."""
    _sync_console_helpers()
    try:
        import src.setup.console_helpers as ch

        return ch.rprint(*objects, **kwargs)
    except Exception:
        # Fallback to built-in print
        print(*objects, **kwargs)


_ = translate


def ui_rule(title: str) -> None:
    """Render a UI rule/header, propagating test toggles first."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_rule as _ui_rule

    _ui_rule(title)


def ui_header(title: str) -> None:
    """Render a UI header, propagating test toggles first."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_header as _ui_header

    _ui_header(title)


def ui_status(message: str):
    """Context manager wrapper for UI status display."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_status as _ui_status

    return _ui_status(message)


def ui_info(message: str) -> None:
    """Display an informational message via the UI adapter.

    Parameters
    ----------
    message : str
        Message text to display.

    Returns
    -------
    None
        No return value.
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_info as _ui_info

    _ui_info(message)


def ui_success(message: str) -> None:
    """Display a success message via the UI adapter.

    Parameters
    ----------
    message : str
        Message text to display.

    Returns
    -------
    None
        No return value.
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_success as _ui_success

    _ui_success(message)


def ui_warning(message: str) -> None:
    """Display a warning message via the UI adapter.

    Parameters
    ----------
    message : str
        Message text to display.

    Returns
    -------
    None
        No return value.
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_warning as _ui_warning

    _ui_warning(message)


def ui_error(message: str) -> None:
    """Display an error message via the UI adapter.

    Parameters
    ----------
    message : str
        Message text to display.

    Returns
    -------
    None
        No return value.
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_error as _ui_error

    _ui_error(message)


def ui_menu(items: list[tuple[str, str]]) -> None:
    """Render a simple menu using the UI adapter.

    Parameters
    ----------
    items : list[tuple[str, str]]
        Pairs of (key, label) to display as selectable menu items.

    Returns
    -------
    None
        No return value.
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_menu as _ui_menu

    _ui_menu(items)


def _build_dashboard_layout(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Build a dashboard layout by delegating to the UI layout helper.

    This thin wrapper exists for backward compatibility so callers that
    import ``_build_dashboard_layout`` from ``src.setup.app`` continue to
    work. It simply forwards arguments to ``src.setup.ui._build_dashboard_layout``.
    """
    _sync_console_helpers()
    from src.setup.ui import _build_dashboard_layout as _impl

    return _impl(*args, **kwargs)


def ui_has_rich() -> bool:
    """Return True when Rich console is available or when module was patched."""
    try:
        import src.setup.console_helpers as ch

        _sync_console_helpers()
        return ch.ui_has_rich()
    except Exception:
        return bool(_RICH_CONSOLE)


def ask_text(prompt: str, default: str | None = None) -> str:
    """Prompt user for text using the prompts adapter (TUI-aware).

    Propagates TUI updater flags to the orchestrator module so prompt
    behaviour can be controlled by tests.
    """
    # Preserve legacy behaviour for the TUI mode used by the original
    # `setup_project` shim: when TUI mode is enabled and an updater is
    # registered prefer `getpass.getpass` (falling back to input) so tests
    # that patch getpass observe the expected path.
    if _TUI_MODE and _TUI_UPDATER is not None:
        if _TUI_PROMPT_UPDATER is not None:
            try:
                _TUI_PROMPT_UPDATER(Panel(f"{prompt}\n\n> ", title="Input"))
            except Exception:
                pass
        try:
            import getpass

            value = getpass.getpass("")
        except Exception:
            try:
                value = input("")
            except Exception:
                return default or ""
        return (value or "").strip() or (default or "")

    try:
        import src.setup.pipeline.orchestrator as _orch

        _orch._TUI_MODE = _TUI_MODE
        _orch._TUI_UPDATER = _TUI_UPDATER
        _orch._TUI_PROMPT_UPDATER = _TUI_PROMPT_UPDATER
    except Exception:
        pass
    _sync_console_helpers()
    from src.setup.ui.prompts import ask_text as _ask

    return _ask(prompt, default)


def ask_confirm(prompt: str, default_yes: bool = True) -> bool:
    """Prompt the user for a yes/no confirmation.

    Parameters
    ----------
    prompt : str
        Text to present to the user.
    default_yes : bool, optional
        Whether the default selection should be treated as a 'yes', by
        default True.

    Returns
    -------
    bool
        True if the user confirmed, False otherwise.
    """
    try:
        import src.setup.pipeline.orchestrator as _orch

        _orch._TUI_MODE = _TUI_MODE
        _orch._TUI_UPDATER = _TUI_UPDATER
        _orch._TUI_PROMPT_UPDATER = _TUI_PROMPT_UPDATER
    except Exception:
        pass
    _sync_console_helpers()
    from src.setup.ui.prompts import ask_confirm as _askc

    return _askc(prompt, default_yes)


def ask_select(prompt: str, choices: list[str]) -> str:
    """Prompt the user to select one option from a list of choices.

    Parameters
    ----------
    prompt : str
        Prompt text to display.
    choices : list[str]
        Available options.

    Returns
    -------
    str
        The selected option.
    """
    _sync_console_helpers()
    from src.setup.ui.prompts import ask_select as _asks

    return _asks(prompt, choices)


def get_venv_bin_dir(venv_path: Path) -> Path:
    """Return the venv bin/Scripts directory respecting patched `sys`.

    Tests may monkeypatch the module-level `sys` variable on this module to
    simulate platforms; prefer that over the real sys module.
    """
    platform = getattr(sys, "platform", "")
    if platform == "win32":
        return venv_path / "Scripts"
    return venv_path / "bin"


def get_venv_python_executable(venv_path: Path) -> Path:
    """Return the path to the Python executable inside a virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root.

    Returns
    -------
    Path
        Path to the Python executable within the venv.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    if getattr(sys, "platform", "") == "win32":
        return bin_dir / "python.exe"
    return bin_dir / "python"


def get_venv_pip_executable(venv_path: Path) -> Path:
    """Return the path to the pip executable inside a virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root.

    Returns
    -------
    Path
        Path to the pip executable within the venv.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    if getattr(sys, "platform", "") == "win32":
        return bin_dir / "pip.exe"
    return bin_dir / "pip"


def get_python_executable() -> str:
    """Return the Python executable for the current environment.

    This delegates to ``src.setup.venv.get_python_executable`` when
    available; use a best-effort fallback to ``sys.executable``.
    """
    try:
        from src.setup.venv import get_python_executable as _g

        return _g()
    except Exception:
        return sys.executable


def is_venv_active() -> bool:
    """Return whether a Python virtual environment is currently active.

    Delegates to ``src.setup.venv.is_venv_active`` when available.
    """
    try:
        from src.setup.venv import is_venv_active as _impl

        return _impl()
    except Exception:
        return False


def run_program(
    program_name: str, program_file: Path, stream_output: bool = False
) -> bool:
    """Run a program as a subprocess using the selected Python executable.

    The implementation here is intentionally small and predictable so tests
    can monkeypatch ``setup_project`` equivalents without invoking the
    more complex pipeline runner.
    """
    python = get_python_executable()
    env = os.environ.copy()
    env["LANG_UI"] = i18n.LANG
    if stream_output:
        proc = subprocess.Popen(
            [python, "-m", program_file.with_suffix("").name], cwd=PROJECT_ROOT, env=env
        )
        return proc.wait() == 0
    result = subprocess.run(
        [python, "-m", program_file.with_suffix("").name],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode == 0


def manage_virtual_environment() -> None:
    """Invoke the refactored virtual environment manager.

    This wrapper prepares a lightweight UI adapter and synchronises a
    few helper functions so the venv manager can be exercised in tests
    without the full interactive runtime.

    Returns
    -------
    None
        No return value.
    """
    # Synchronize get_venv helpers into the venv module used by the manager
    try:
        import src.setup.fs_utils as fs_utils
        import src.setup.venv_manager as vm

        # Ensure the manager sees the same fs utils and venv helpers
        vm.create_safe_path = fs_utils.create_safe_path
        vm.safe_rmtree = fs_utils.safe_rmtree
    except Exception:
        vm = None

    class _UI:
        import logging

        logger = logging.getLogger("src.setup.app")
        rprint = staticmethod(ui_info)
        # Default to True in test environment so UI restart branches are
        # exercised; tests may monkeypatch behavior when needed.
        ui_has_rich = staticmethod(lambda: True)
        ask_text = staticmethod(ask_text)
        subprocess = subprocess
        shutil = __import__("shutil")
        sys = sys
        venv = __import__("venv")
        os = os

        @staticmethod
        def _(k: str) -> str:
            return translate(k)

        ui_info = staticmethod(ui_info)
        ui_success = staticmethod(ui_success)
        ui_warning = staticmethod(ui_warning)

    # Delegate to the implementation
    if vm is not None:
        # If tests have monkeypatched module-level venv helpers on this
        # module, propagate those into the lower-level venv helper module
        # so the manager honours the test doubles. Only propagate values
        # that are clearly not defined in this module (i.e. come from
        # test code) to avoid creating recursive references.
        try:
            import src.setup.venv as _venvmod

            for _name in (
                "is_venv_active",
                "get_venv_python_executable",
                "get_venv_pip_executable",
                "get_python_executable",
            ):
                if _name in globals():
                    _val = globals()[_name]
                    # Only propagate if the attribute originates outside
                    # this module (tests will typically inject functions
                    # from their own modules).
                    if getattr(_val, "__module__", None) != __name__:
                        setattr(_venvmod, _name, _val)
        except Exception:
            pass

        vm.manage_virtual_environment(
            PROJECT_ROOT, VENV_DIR, REQUIREMENTS_FILE, REQUIREMENTS_LOCK_FILE, _UI
        )


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse an env file and return a mapping of keys to values.

    Parameters
    ----------
    env_path : Path
        Path to the .env file to parse.

    Returns
    -------
    dict[str, str]
        Mapping of environment keys to their string values.
    """
    from src.setup.azure_env import parse_env_file as _p

    return _p(env_path)


def prompt_and_update_env(
    missing_keys: list[str], env_path: Path, existing: dict[str, str], ui: Any = None
) -> None:
    """Prompt for missing environment keys and update the .env file.

    Parameters
    ----------
    missing_keys : list[str]
        List of keys that are missing and should be prompted for.
    env_path : Path
        Path to the .env file to update.
    existing : dict[str, str]
        Previously parsed existing values.
    ui : Any, optional
        UI adapter object; defaults to this module so tests can monkeypatch
        prompt helpers.

    Returns
    -------
    None
    """
    from src.setup.azure_env import prompt_and_update_env as _p

    # Prefer passing this module as the UI adapter so tests that monkeypatch
    # prompt helpers on this module are respected.
    if ui is None:
        ui = sys.modules.get(__name__)
    return _p(missing_keys, env_path, existing, ui=ui)


def find_missing_env_keys(existing: dict[str, str], required: list[str]) -> list[str]:
    """Return a list of required keys missing from the existing mapping.

    Parameters
    ----------
    existing : dict[str, str]
        Mapping of existing environment values.
    required : list[str]
        List of keys that are required.

    Returns
    -------
    list[str]
        Keys that are required but absent from `existing`.
    """
    from src.setup.azure_env import find_missing_env_keys as _f

    return _f(existing, required)


def ensure_azure_openai_env(ui: Any = None) -> None:
    """Ensure required Azure/OpenAI environment variables are present.

    If keys are missing, prompt the user (using the provided `ui` adapter)
    to supply them and update the env file.

    Parameters
    ----------
    ui : Any, optional
        UI adapter to use for prompting. If omitted, the module object is
        used so tests that monkeypatch prompt helpers behave correctly.

    Returns
    -------
    None
    """
    env_path = globals().get("ENV_PATH", PROJECT_ROOT / ".env")
    existing = parse_env_file(env_path)
    missing = find_missing_env_keys(existing, REQUIRED_AZURE_KEYS)
    if missing:
        prompt_and_update_env(missing, env_path, existing)


def run_ai_connectivity_check_silent() -> tuple[bool, str]:
    """Run a silent connectivity check against the configured AI endpoint.

    Returns
    -------
    tuple[bool, str]
        A tuple of (ok, detail) where `ok` is True on success and `detail`
        holds diagnostic information.
    """
    from src.setup.azure_env import run_ai_connectivity_check_silent as _r

    return _r()


def run_ai_connectivity_check_interactive() -> bool:
    """Run an interactive connectivity check and report results to the UI.

    Returns
    -------
    bool
        True if the connectivity check succeeded, False otherwise.
    """
    ok, detail = run_ai_connectivity_check_silent()
    if ok:
        ui_success(translate("ai_check_ok"))
        return True
    ui_error(translate("ai_check_fail"))
    ui_error(str(detail))
    return False


def run_full_quality_suite() -> None:
    """Run the local quality suite helper script.

    Uses the project's Python runtime to execute ``tools/run_all_checks.py``.
    Tests typically monkeypatch ``subprocess.run`` so the call is safe.
    """
    helper = PROJECT_ROOT / "tools" / "run_all_checks.py"
    try:
        subprocess.run([get_python_executable(), str(helper)], cwd=PROJECT_ROOT)
    except Exception:
        pass


def run_extreme_quality_suite() -> None:
    """Run the extreme quality suite (intensive checks)."""
    helper = PROJECT_ROOT / "tools" / "run_all_checks.py"
    try:
        subprocess.run(
            [get_python_executable(), str(helper), "--extreme"], cwd=PROJECT_ROOT
        )
    except Exception:
        pass


def _run_pipeline_step(*args: Any, **kwargs: Any) -> Any:
    from src.setup.pipeline.orchestrator import _run_pipeline_step as _impl

    return _impl(*args, **kwargs)


def _render_pipeline_table(*args: Any, **kwargs: Any) -> Any:
    from src.setup.pipeline.orchestrator import _render_pipeline_table as _impl

    return _impl(*args, **kwargs)


def _status_label(base: str) -> str:
    from src.setup.pipeline.orchestrator import _status_label as _impl

    return _impl(base)


def _run_processing_pipeline_plain() -> None:
    # Propagate prompt/control helpers into the orchestrator so tests that
    # monkeypatch these names on this module affect the orchestrator which
    # imported them at module import time.
    # Temporarily propagate helpers into the orchestrator for the duration
    # of the delegated call so tests that patch this module behave as
    # expected. Restore the original values afterwards to avoid leaking
    # monkeypatches between tests.
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")
        replaced: dict[str, object | None] = {}
        for _n in ("ask_confirm", "ask_text", "run_ai_connectivity_check_interactive"):
            if _n in globals():
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, globals()[_n])
    except Exception:
        orch = None
        replaced = {}

    try:
        from src.setup.pipeline.orchestrator import (
            _run_processing_pipeline_plain as _impl,
        )

        return _impl()
    finally:
        if orch is not None:
            for _n, _old in replaced.items():
                try:
                    if _old is None:
                        delattr(orch, _n)
                    else:
                        setattr(orch, _n, _old)
                except Exception:
                    pass


def _run_processing_pipeline_rich(*args: Any, **kwargs: Any) -> None:
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")
        replaced: dict[str, object | None] = {}
        for _n in ("ask_confirm", "ask_text", "run_ai_connectivity_check_interactive"):
            if _n in globals():
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, globals()[_n])
    except Exception:
        orch = None
        replaced = {}

    try:
        from src.setup.pipeline.orchestrator import (
            _run_processing_pipeline_rich as _impl,
        )

        return _impl(*args, **kwargs)
    finally:
        if orch is not None:
            for _n, _old in replaced.items():
                try:
                    if _old is None:
                        delattr(orch, _n)
                    else:
                        setattr(orch, _n, _old)
                except Exception:
                    pass


def prompt_virtual_environment_choice() -> bool:
    """Ask the user whether to create/manage a virtual environment.

    Returns
    -------
    bool
        True if the user chose to create/manage a venv, False if skipped.
    """
    ui_rule(translate("venv_menu_title"))
    ui_menu(
        [
            ("1", translate("venv_menu_option_1")[3:]),
            ("2", translate("venv_menu_option_2")[3:]),
        ]
    )
    while True:
        choice = ask_text(translate("venv_menu_prompt"))
        if choice == "1":
            return True
        if choice == "2":
            ui_info(translate("venv_skipped"))
            return False
        print(translate("invalid_choice"))


def get_program_descriptions() -> dict[str, tuple[str, str]]:
    from src.setup.ui.programs import get_program_descriptions as _g

    return _g()


def view_program_descriptions() -> None:
    """Interactive view showing program descriptions using module-level prompts."""
    ui_rule(translate("program_descriptions_title"))
    while True:
        descriptions = get_program_descriptions()
        items = [(k, v[0]) for k, v in descriptions.items()]
        items.append(("0", translate("return_to_menu")))
        ui_menu(items)
        choice = ask_text(translate("select_program_to_describe"))
        if choice == "0":
            break
        if choice in descriptions:
            _title, body = descriptions[choice]
            if ui_has_rich():
                try:
                    rprint(body)
                    continue
                except Exception:
                    pass
            rprint(body)
        else:
            rprint(translate("invalid_choice"))


def set_language() -> None:
    """Prompt the user to select an interface language and set module state.

    This updates both the i18n module and the module-level `LANG` value.
    """
    prompt = i18n.TEXTS["en"]["language_prompt"]
    while True:
        try:
            choice = ask_text(prompt)
        except KeyboardInterrupt:
            raise SystemExit from None
        if choice == "1":
            i18n.LANG = "en"
            break
        if choice == "2":
            i18n.LANG = "sv"
            break
        print(i18n.TEXTS["en"]["invalid_choice"])  # pragma: no cover - trivial loop
    global LANG
    LANG = i18n.LANG


def entry_point() -> None:
    """Run the setup application.

    This function orchestrates CLI parsing, language setup, optional venv
    management and running the interactive main menu.
    """
    args = parse_cli_args()
    if getattr(args, "lang", None):
        i18n.LANG = args.lang if args.lang in i18n.TEXTS else "en"
    if not os.environ.get("SETUP_SKIP_LANGUAGE_PROMPT"):
        set_language()
    if not getattr(args, "no_venv", False):
        if not is_venv_active():
            if prompt_virtual_environment_choice():
                manage_virtual_environment()

    ensure_azure_openai_env()
    try:
        # Call the local wrapper so tests can monkeypatch `main_menu` on
        # this module without needing to patch the ui.menu implementation.
        main_menu()
    except Exception:
        return


def main_menu() -> None:
    """Delegate to the UI package main menu.

    Exposed so tests can monkeypatch the entry point behaviour.
    """
    try:
        menu.main_menu()
    except Exception:
        return


__all__ = [
    "LANG",
    "LOG_DIR",
    "PROJECT_ROOT",
    "REQUIREMENTS_FILE",
    "REQUIREMENTS_LOCK_FILE",
    "VENV_DIR",
    "_render_pipeline_table",
    "_run_pipeline_step",
    "_run_processing_pipeline_plain",
    "_run_processing_pipeline_rich",
    "_status_label",
    "ask_confirm",
    "ask_select",
    "ask_text",
    "ensure_azure_openai_env",
    "entry_point",
    "find_missing_env_keys",
    "get_python_executable",
    "get_venv_bin_dir",
    "get_venv_pip_executable",
    "get_venv_python_executable",
    "manage_virtual_environment",
    "parse_cli_args",
    "parse_env_file",
    "prompt_and_update_env",
    "prompt_virtual_environment_choice",
    "run",
    "run_ai_connectivity_check_interactive",
    "run_ai_connectivity_check_silent",
    "run_program",
    "set_language",
    "ui_error",
    "ui_header",
    "ui_info",
    "ui_menu",
    "ui_rule",
    "ui_status",
    "ui_success",
    "ui_warning",
]
