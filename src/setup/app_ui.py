"""User Interface Adapter Module for School Data Pipeline.

This module (`app_ui.py`) implements the strict adapter pattern for all UI-related routines
in the School Data Pipeline project. It exposes wrapper functions for console output, status
indicators, error signaling, and menu rendering. Its sole responsibility is to decouple
orchestrator logic from concrete UI implementations, patch legacy toggles for test isolation, and
provide a deterministic integration layer for all terminal-based interactions.

All UI actions (info, error, warning, menu, dashboard) are routed through this module, which
propagates runtime toggles and avoids circular imports to other UI modules. It is designed to
permit robust patching (for test or deployment), reliable fallback logic, and maintain compliance
with portfolio documentation standards.

Parameters
----------
None

Returns
-------
None

See Also
--------
`src/setup/console_helpers.py`, `src/setup/ui/basic.py`

References
----------
School Data Pipeline AGENTS.md documentation standards.

Examples
--------
>>> from src.setup import app_ui
>>> app_ui.rprint("Hello pipeline!")
Hello pipeline!
>>> app_ui.ui_info("Processing started")
Processing started

Notes
-----
All functions in this module avoid direct dependencies on concrete UI modules except via runtime
import and toggling. Docstrings strictly follow AGENTS.md/NumPy standards for maximal clarity.

"""

from __future__ import annotations

import sys
from typing import Any
from contextlib.abc import AbstractContextManager

def _sync_console_helpers() -> None:
    r"""Synchronize legacy UI toggles into the console helpers module.

    Imports `src.setup.console_helpers` and propagates legacy toggle values
    (`_RICH_CONSOLE`, `_HAS_Q`, `questionary`) for deterministic UI patching.
    Designed to avoid circular imports, support test patching of UI behavior, and
    guarantee adapter separation from implementation. Idempotent and safe to call
    from all adapter routines; recommended as a portfolio guardrail.

    Parameters
    ----------
    None

    Returns
    -------
    None
        No value is returned. The imported module's internal state may be modified.

    Raises
    ------
    ImportError
        If `src.setup.console_helpers` cannot be imported.
    AttributeError
        If a required toggle attribute does not exist in the imported module.

    See Also
    --------
    rprint : UI print adapter.
    ui_rule, ui_header, ui_status : UI rendering adapters.

    Examples
    --------
    >>> _sync_console_helpers()
    # After call, src.setup.console_helpers._RICH_CONSOLE is safely patched.

    Notes
    -----
    Enables deterministic patching and adapter-compliant UI testing.
    """

def rprint(*objects: Any, **kwargs: Any) -> None:
    r"""Print objects to the Rich terminal, falling back to built-in print if unavailable.

    Delegates to the console_helpers.rprint adapter (if available), ensuring robust
    output in all environments.

    Parameters
    ----------
    *objects : Any
        Objects to print to the terminal.
    **kwargs : Any
        Keyword arguments for the printing routine.

    Returns
    -------
    None
        No value is returned. Output is produced on the terminal.

    Notes
    -----
    Falls back to builtin print if console helpers are unavailable.

    Examples
    --------
    >>> rprint("Hello", "world", sep=", ")
    Hello, world
    """
    _sync_console_helpers()
    try:
        import src.setup.console_helpers as ch

        return ch.rprint(*objects, **kwargs)
    except Exception:
        print(*objects, **kwargs)

def ui_rule(title: str) -> None:
    r"""Render a horizontal UI rule/header using the UI adapter.

    Parameters
    ----------
    title : str
        The title text to display.

    Returns
    -------
    None
        No value is returned. Output is rendered to the terminal.

    Examples
    --------
    >>> ui_rule("School Dashboard")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_rule as _ui_rule

    _ui_rule(title)

def ui_header(title: str) -> None:
    r"""Render a header in the UI using the adapter.

    Parameters
    ----------
    title : str
        The title to display.

    Returns
    -------
    None
        No value is returned. Output appears in the terminal.

    Examples
    --------
    >>> ui_header("Pipeline Step 1")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_header as _ui_header

    _ui_header(title)

def ui_status(message: str) -> AbstractContextManager[None]:
    r"""Provide a context manager for UI status display.

    Wraps status signals in the UI, enabling resource usage indicators or spinner formatting.

    Parameters
    ----------
    message : str
        The status message to display.

    Returns
    -------
    AbstractContextManager[None]
        A context manager which shows/hides the status indicator.

    Examples
    --------
    >>> with ui_status("Processing..."):
    ...     # Do work here
    ...     pass
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_status as _ui_status

    return _ui_status(message)

def ui_info(message: str) -> None:
    r"""Display an informational message via the UI adapter.

    Parameters
    ----------
    message : str
        Informational message content.

    Returns
    -------
    None
        No value is returned. Message appears in terminal UI.

    Examples
    --------
    >>> ui_info("File loaded successfully.")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_info as _ui_info

    _ui_info(message)

def ui_success(message: str) -> None:
    r"""Display a success message using the UI adapter.

    Parameters
    ----------
    message : str
        Message reporting a successful operation.

    Returns
    -------
    None
        No value is returned. Output sent to UI.

    Examples
    --------
    >>> ui_success("All records processed.")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_success as _ui_success

    _ui_success(message)

def ui_warning(message: str) -> None:
    r"""Display a warning message using the UI adapter.

    Parameters
    ----------
    message : str
        Warning message explaining non-critical issues.

    Returns
    -------
    None
        No value is returned. Message appears in terminal UI.

    Examples
    --------
    >>> ui_warning("Some files were skipped.")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_warning as _ui_warning

    _ui_warning(message)

def ui_error(message: str) -> None:
    r"""Display an error message using the UI adapter.

    Parameters
    ----------
    message : str
        Message reporting a failed or exceptional operation.

    Returns
    -------
    None
        No value is returned. The message is printed as an error.

    Examples
    --------
    >>> ui_error("Failed to connect to server.")
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_error as _ui_error

    _ui_error(message)

def ui_menu(items: list[tuple[str, str]]) -> None:
    r"""Render a simple UI menu from a list of item tuples.

    Parameters
    ----------
    items : list of tuple[str, str]
        Menu entries as a list of (label, description) tuples.

    Returns
    -------
    None
        No value is returned. Menu appears in terminal UI.

    Examples
    --------
    >>> ui_menu([("1", "Start pipeline"), ("2", "Exit")])
    """
    _sync_console_helpers()
    from src.setup.ui.basic import ui_menu as _ui_menu

    _ui_menu(items)

def _build_dashboard_layout(*args: Any, **kwargs: Any) -> dict[str, Any]:
    r"""Build and return the dashboard layout via UI layout helper.

    Parameters
    ----------
    *args : Any
        Positional arguments to pass to the dashboard layout routine.
    **kwargs : Any
        Keyword arguments for the dashboard layout routine.

    Returns
    -------
    dict[str, Any]
        Dictionary describing the dashboard layout data structure.

    Examples
    --------
    >>> layout = _build_dashboard_layout()
    >>> 'header' in layout
    True
    """
    _sync_console_helpers()
    from src.setup.ui import _build_dashboard_layout as _impl

    return _impl(*args, **kwargs)

def ui_has_rich() -> bool:
    r"""Return True if a Rich console is available, else False.

    Attempts to query the concrete `src.setup.console_helpers.ui_has_rich`
    function, propagating environment toggles. On exception, falls back to the
    module's internal `_RICH_CONSOLE` flag for deterministic behavior in tests.

    Parameters
    ----------
    None

    Returns
    -------
    bool
        True if Rich console is available; otherwise False.

    Notes
    -----
    This design improves reproducibility during test patching and avoids legacy module lookup.

    Examples
    --------
    >>> isinstance(ui_has_rich(), bool)
    True
    """
    try:
        import src.setup.console_helpers as ch

        _sync_console_helpers()
        return ch.ui_has_rich()
    except Exception:
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
