"""Dependency-safe Textual dashboard integration for setup UI.

Single Responsibility Principle:
    Exposes the dashboard application classes as safe imports from the Textual UI layer,
    ensuring all logic outside dashboard UI remains importable even if the optional
    `textual` dependency is missing.

Architectural Role:
    - This file only supplies a wrapper/sentinel contract for Textual-optional imports.
    - Fully decoupled from pipeline/frontend logic, allows safe runtime and type-checking of all `ui` modules.
    - All business logic is absent; uses error signaling to guide developers/admins to install Textual as needed.

"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .textual_app import DashboardContext, SetupDashboardApp
else:  # pragma: no cover - runtime dependency guard
    class _MissingTextualApp:
        r"""Sentinel class for missing Textual dependency.

        Short summary:
            - Instantiation always raises RuntimeError describing how to install the missing optional dependency.

        Parameters
        ----------
        *a : Any
            All positional arguments (ignored).
        **k : Any
            All keyword arguments (ignored).

        Raises
        ------
        RuntimeError
            Always raised to indicate that Textual is required.

        Notes
        -----
        AGENTS.md compliant: this module only signals dependency issues,
        does not block import of any other package logic.

        Examples
        --------
        >>> obj = SetupDashboardApp()
        Traceback (most recent call last):
            ...
        RuntimeError: Textual is not installed; install it with ...
        """
        def __init__(self, *a: Any, **k: Any) -> None:
            r"""Always raises RuntimeError, never constructs.

            Parameters
            ----------
            *a : Any
                Positional arguments (unused).
            **k : Any
                Keyword arguments (unused).

            Raises
            ------
            RuntimeError
                Always thrown to trigger missing dependency message.

            Examples
            --------
            >>> SetupDashboardApp()
            Traceback (most recent call last):
                ...
            RuntimeError: Textual is not installed; install it ...
            """
            raise RuntimeError(
                "Textual is not installed; install it with `pip install textual` "
                "to use SetupDashboardApp (the dashboard UI)."
            )

    SetupDashboardApp = _MissingTextualApp
    DashboardContext: Any = object

__all__ = ["DashboardContext", "SetupDashboardApp"]
