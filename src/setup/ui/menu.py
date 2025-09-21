"""Main menu implementations (plain + rich dashboard).

Shim-free implementations wired to the src.setup modules.
"""

from __future__ import annotations

from typing import Any

from src.config import PROJECT_ROOT, VENV_DIR
from src.setup.console_helpers import (
    _RICH_CONSOLE,
    Markdown,
    Panel,
    rprint,
    ui_has_rich,
)
from src.setup.i18n import LANG, translate
from src.setup.i18n import _ as _
from src.setup.pipeline.orchestrator import run_processing_pipeline
from src.setup.reset import reset_project
from src.setup.ui.basic import ui_menu, ui_rule
from src.setup.ui.layout import build_dashboard_layout
from src.setup.ui.programs import view_logs, view_program_descriptions
from src.setup.ui.prompts import ask_text
from src.setup.venv_manager import manage_virtual_environment
import sys as _sys
from src.config import INTERACTIVE_MAX_INVALID_ATTEMPTS


def _ui_items() -> list[tuple[str, str]]:
    """Return the list of main menu items as (key, label) pairs.

    The labels are extracted from the translation table and trimmed to be
    suitable for display in compact menus.
    """
    return [
        (
            "1",
            (
                translate("menu_option_1").split(" ", 1)[1]
                if ": " not in translate("menu_option_1")
                else translate("menu_option_1")[3:]
            ),
        ),
        (
            "2",
            (
                translate("menu_option_2").split(" ", 1)[1]
                if ": " not in translate("menu_option_2")
                else translate("menu_option_2")[3:]
            ),
        ),
        (
            "3",
            (
                translate("menu_option_3").split(" ", 1)[1]
                if ": " not in translate("menu_option_3")
                else translate("menu_option_3")[3:]
            ),
        ),
        (
            "4",
            (
                translate("menu_option_4").split(" ", 1)[1]
                if ": " not in translate("menu_option_4")
                else translate("menu_option_4")[3:]
            ),
        ),
        (
            "5",
            (
                translate("menu_option_5").split(" ", 1)[1]
                if ": " not in translate("menu_option_5")
                else translate("menu_option_5")[3:]
            ),
        ),
        (
            "6",
            (
                translate("menu_option_6").split(" ", 1)[1]
                if ": " not in translate("menu_option_6")
                else translate("menu_option_6")[3:]
            ),
        ),
    ]


def _manage_env() -> None:
    """Expose a minimal UI surface for venv management.

    This function constructs a lightweight ``_UI`` object that mimics the
    attributes used by the venv manager so it can be invoked in isolation
    from the rest of the interactive setup flow.
    """

    class _UI:
        """Small adapter exposing console utilities and process helpers.

        The class provides the functions and attributes expected by the
        ``manage_virtual_environment`` helper.
        """

        import logging
        import os as os_mod
        import shutil as shutil_mod
        import subprocess as subprocess_mod
        import sys as sys_mod
        import venv as venv_mod

        logger = logging.getLogger("src.setup.ui.menu")
        rprint = staticmethod(rprint)
        ui_has_rich = staticmethod(ui_has_rich)
        ask_text = staticmethod(ask_text)
        subprocess = subprocess_mod
        shutil = shutil_mod
        sys = sys_mod
        venv = venv_mod
        os = os_mod

        @staticmethod
        def _(k: str) -> str:
            """Translate a key using the global translation function.

            Parameters
            ----------
            k : str
                i18n key to translate.

            Returns
            -------
            str
                Translated string.
            """
            return translate(k)

    manage_virtual_environment(
        PROJECT_ROOT,
        VENV_DIR,
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "requirements.lock",
        _UI,
    )


def _main_menu_plain() -> None:
    """Plain (non-rich) main menu loop displayed in the terminal."""
    _app_mod = _sys.modules.get("src.setup.app")
    try:
        import importlib

        _cfg = importlib.import_module("src.config")
        max_attempts = getattr(_cfg, "INTERACTIVE_MAX_INVALID_ATTEMPTS", INTERACTIVE_MAX_INVALID_ATTEMPTS)
    except Exception:
        max_attempts = INTERACTIVE_MAX_INVALID_ATTEMPTS
    if _app_mod is not None:
        max_attempts = getattr(_app_mod, "INTERACTIVE_MAX_INVALID_ATTEMPTS", max_attempts)

    attempts = 0
    while True:
        ui_rule(translate("main_menu_title"))
        ui_menu(_ui_items())
        choice = ask_text(translate("enter_choice"))
        if choice == "1":
            attempts = 0
            _manage_env()
        elif choice == "2":
            attempts = 0
            view_program_descriptions()
        elif choice == "3":
            attempts = 0
            run_processing_pipeline()
        elif choice == "4":
            attempts = 0
            view_logs()
        elif choice == "5":
            attempts = 0
            reset_project()
        elif choice == "6":
            rprint(translate("exiting"))
            break
        else:
            attempts += 1
            rprint(translate("invalid_choice"))
            if attempts >= max_attempts:
                rprint(translate("exiting"))
                raise SystemExit("Exceeded maximum invalid selections in main menu")


def _main_menu_rich_dashboard() -> None:
    """Rich dashboard main menu that renders a live layout."""
    layout = build_dashboard_layout(
        translate,
        Panel(Markdown(translate("welcome")), title="Welcome"),
        VENV_DIR,
        LANG,
    )

    def update_right(renderable: Any) -> None:
        """Update the right-hand content area of the rich dashboard.

        Parameters
        ----------
        renderable : Any
            Renderable object to place in the content slot of the layout.
        """
        layout["content"].update(renderable)
        if _RICH_CONSOLE is not None:
            _RICH_CONSOLE.print(layout)
        else:
            rprint(renderable)

    # Simple prompt loop with attempts limiting
    _app_mod = _sys.modules.get("src.setup.app")
    try:
        import importlib

        _cfg = importlib.import_module("src.config")
        max_attempts = getattr(_cfg, "INTERACTIVE_MAX_INVALID_ATTEMPTS", INTERACTIVE_MAX_INVALID_ATTEMPTS)
    except Exception:
        max_attempts = INTERACTIVE_MAX_INVALID_ATTEMPTS
    if _app_mod is not None:
        max_attempts = getattr(_app_mod, "INTERACTIVE_MAX_INVALID_ATTEMPTS", max_attempts)

    attempts = 0
    while True:
        choice = ask_text(translate("enter_choice"))
        if choice == "1":
            attempts = 0
            _manage_env()
            update_right(
                Panel("Environment managed.", title="Status", border_style="green")
            )
        elif choice == "2":
            attempts = 0
            view_program_descriptions()
            update_right(Panel("Descriptions viewed.", title="Programs"))
        elif choice == "3":
            attempts = 0
            run_processing_pipeline(content_updater=update_right)
            update_right(
                Panel(_("pipeline_complete"), title="Pipeline", border_style="green")
            )
        elif choice == "4":
            attempts = 0
            view_logs()
            update_right(Panel("Logs viewed.", title="Logs"))
        elif choice == "5":
            attempts = 0
            reset_project()
            update_right(
                Panel(_("reset_complete"), title="Reset", border_style="green")
            )
        elif choice == "6":
            rprint(translate("exiting"))
            break
        else:
            attempts += 1
            update_right(
                Panel(translate("invalid_choice"), title="Info", border_style="yellow")
            )
            if attempts >= max_attempts:
                update_right(Panel(translate("exiting"), title="Info", border_style="red"))
                raise SystemExit("Exceeded maximum invalid selections in main dashboard menu")


def main_menu() -> None:
    """Dispatch to the appropriate main menu based on Rich availability."""
    if ui_has_rich():
        _main_menu_rich_dashboard()
    else:
        _main_menu_plain()


__all__ = ["_main_menu_plain", "_main_menu_rich_dashboard", "main_menu"]
