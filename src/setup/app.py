"""Application runner that composes modules and runs the setup app.

This module centralizes the entrypoint logic and is safe to execute as a
module (``python -m src.setup.app``). It does not depend on the legacy
top-level shim.
"""

from __future__ import annotations

import src.setup.i18n as i18n
import src.setup.ui.menu as menu
from src.setup.i18n import translate
from src.setup.ui.basic import ui_header


def run(args) -> None:
    """Run the setup application using parsed CLI args."""
    i18n.LANG = args.lang
    ui_header(translate("welcome"))
    menu.main_menu()


__all__ = ["run"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup application")
    parser.add_argument("--no-venv", action="store_true")
    parser.add_argument("--lang", choices=["en", "sv"], default="en")
    run(parser.parse_args())
