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


def _ui_items() -> list[tuple[str, str]]:
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
    class _UI:
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
    while True:
        ui_rule(translate("main_menu_title"))
        ui_menu(_ui_items())
        choice = ask_text(translate("enter_choice"))
        if choice == "1":
            _manage_env()
        elif choice == "2":
            view_program_descriptions()
        elif choice == "3":
            run_processing_pipeline()
        elif choice == "4":
            view_logs()
        elif choice == "5":
            reset_project()
        elif choice == "6":
            rprint(translate("exiting"))
            break
        else:
            rprint(translate("invalid_choice"))


def _main_menu_rich_dashboard() -> None:
    """Rich dashboard main menu that renders a live layout."""
    layout = build_dashboard_layout(
        translate,
        Panel(Markdown(translate("welcome")), title="Welcome"),
        VENV_DIR,
        LANG,
    )

    def update_right(renderable: Any) -> None:
        layout["content"].update(renderable)
        if _RICH_CONSOLE is not None:
            _RICH_CONSOLE.print(layout)
        else:
            rprint(renderable)

    # Simple prompt loop
    while True:
        choice = ask_text(translate("enter_choice"))
        if choice == "1":
            _manage_env()
            update_right(
                Panel("Environment managed.", title="Status", border_style="green")
            )
        elif choice == "2":
            view_program_descriptions()
            update_right(Panel("Descriptions viewed.", title="Programs"))
        elif choice == "3":
            run_processing_pipeline(content_updater=update_right)
            update_right(
                Panel(_("pipeline_complete"), title="Pipeline", border_style="green")
            )
        elif choice == "4":
            view_logs()
            update_right(Panel("Logs viewed.", title="Logs"))
        elif choice == "5":
            reset_project()
            update_right(
                Panel(_("reset_complete"), title="Reset", border_style="green")
            )
        elif choice == "6":
            rprint(translate("exiting"))
            break
        else:
            update_right(
                Panel(translate("invalid_choice"), title="Info", border_style="yellow")
            )


def main_menu() -> None:
    """Dispatch to the appropriate main menu based on Rich availability."""
    if ui_has_rich():
        _main_menu_rich_dashboard()
    else:
        _main_menu_plain()


__all__ = ["_main_menu_plain", "_main_menu_rich_dashboard", "main_menu"]
