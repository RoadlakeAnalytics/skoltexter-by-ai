"""UI helpers extracted from src.setup.app.

This module contains thin UI adapters that delegate to the project's
UI helpers while reading module-level test toggles from the main
``src.setup.app`` module at runtime. Using ``sys.modules`` for lookup
avoids circular imports while giving tests a stable patch point.
"""

from __future__ import annotations

import sys
from typing import Any


def _sync_console_helpers() -> None:
    """Propagate module-level UI toggles into the console helpers.

    The real toggle state is stored on the main ``src.setup.app`` module
    so tests can monkeypatch there. This helper looks up the values at
    runtime and copies them into ``src.setup.console_helpers``.
    """
    try:
        import src.setup.console_helpers as ch

        app_mod = sys.modules.get("src.setup.app")
        ch._RICH_CONSOLE = getattr(app_mod, "_RICH_CONSOLE", None)
        ch._HAS_Q = getattr(app_mod, "_HAS_Q", False)
        ch.questionary = getattr(app_mod, "questionary", None)
    except Exception:
        # Intentionally swallow errors: UI helpers should remain best-effort
        # and not break tests when optional deps are absent.
        pass


def rprint(*objects: Any, **kwargs: Any) -> None:
    """Proxy to ``src.setup.console_helpers.rprint`` with a fallback.

    Parameters
    ----------
    *objects : Any
        Objects to print.
    **kwargs : Any
        Keyword arguments forwarded to the underlying printer.
    """
    _sync_console_helpers()
    try:
        import src.setup.console_helpers as ch

        return ch.rprint(*objects, **kwargs)
    except Exception:
        # Fallback to built-in print when console helpers are unavailable.
        print(*objects, **kwargs)


def ui_rule(title: str) -> None:
    """Render a UI rule/header using the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_rule as _ui_rule

    _ui_rule(title)


def ui_header(title: str) -> None:
    """Render a UI header using the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_header as _ui_header

    _ui_header(title)


def ui_status(message: str):
    """Context manager wrapper for UI status display."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_status as _ui_status

    return _ui_status(message)


def ui_info(message: str) -> None:
    """Display an informational message via the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_info as _ui_info

    _ui_info(message)


def ui_success(message: str) -> None:
    """Display a success message via the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_success as _ui_success

    _ui_success(message)


def ui_warning(message: str) -> None:
    """Display a warning message via the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_warning as _ui_warning

    _ui_warning(message)


def ui_error(message: str) -> None:
    """Display an error message via the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_error as _ui_error

    _ui_error(message)


def ui_menu(items: list[tuple[str, str]]) -> None:
    """Render a simple menu using the UI adapter."""
    _sync_console_helpers()
    from src.setup.ui.basic import ui_menu as _ui_menu

    _ui_menu(items)


def _build_dashboard_layout(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Build a dashboard layout by delegating to the UI layout helper."""
    _sync_console_helpers()
    from src.setup.ui import _build_dashboard_layout as _impl

    return _impl(*args, **kwargs)


def ui_has_rich() -> bool:
    """Return True when Rich console is available or when patched on app module."""
    try:
        import src.setup.console_helpers as ch

        _sync_console_helpers()
        return ch.ui_has_rich()
    except Exception:
        app_mod = sys.modules.get("src.setup.app")
        return bool(getattr(app_mod, "_RICH_CONSOLE", None))


__all__ = [
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
]

