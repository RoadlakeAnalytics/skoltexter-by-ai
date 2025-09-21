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

    This helper imports the concrete ``src.setup.console_helpers`` module
    and attempts to read toggle values from the legacy ``src.setup.app``
    module if it is importable. The function uses an explicit, lazy
    import of the legacy module instead of reading ``sys.modules`` to
    make the dependency explicit and easier to reason about during the
    shim removal migration.

    Returns
    -------
    None
        No value is returned. The function modifies the state of the
        imported ``src.setup.console_helpers`` module in-place when
        toggle values are available.
    """
    try:
        import src.setup.console_helpers as ch
    except ImportError:
        # Console helpers are optional; nothing to propagate.
        return

    # Do not rely on the legacy shim module for runtime toggles. Tests
    # should patch the concrete `src.setup.console_helpers` module when
    # they need to control these values. Preserve any explicit, pre-
    # existing Console object and only fill missing toggle values from
    # the concrete module itself.
    if not hasattr(ch, "_RICH_CONSOLE"):
        ch._RICH_CONSOLE = None
    # Respect any explicit setting on the concrete console_helpers module.
    ch._HAS_Q = getattr(ch, "_HAS_Q", False)
    ch.questionary = getattr(ch, "questionary", None)


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
    """Return True when Rich console is available or when patched on the concrete module.

    This adapter prefers the concrete `src.setup.console_helpers.ui_has_rich`
    function. If the concrete helper cannot be used (for example because it
    raises an exception under test conditions), the function falls back to the
    concrete module's internal `_RICH_CONSOLE` flag. Avoiding a dynamic
    lookup of the legacy shim keeps behaviour deterministic when other tests
    manipulate ``sys.modules``.
    """
    try:
        import src.setup.console_helpers as ch

        _sync_console_helpers()
        return ch.ui_has_rich()
    except Exception:
        # If the concrete console helpers cannot be used for any reason,
        # fall back to the concrete module's internal flag rather than
        # performing a dynamic lookup of the legacy shim. This keeps the
        # behaviour deterministic and prevents accidental coupling to a
        # mutated `sys.modules['src.setup.app']` introduced by other
        # tests.
        try:
            import src.setup.console_helpers as ch2

            return bool(getattr(ch2, "_RICH_CONSOLE", None))
        except Exception:
            return False


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
