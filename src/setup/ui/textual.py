"""Textual UI integration exported from the ui package.

This module exposes the Textual application classes moved into the
package as `textual_app.py`. Import is performed lazily and falls back to
clear placeholders when the optional `textual` dependency is missing so
the rest of the package can be imported in minimal environments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .textual_app import DashboardContext, SetupDashboardApp
else:  # pragma: no cover - optional dependency at runtime

    class _MissingTextualApp:  # sentinel placeholder
        """Placeholder raised when Textual dependency is not available.

        Instantiating this class will raise a RuntimeError explaining how to
        install the optional dependency.
        """

        def __init__(self, *a, **k):  # pragma: no cover - runtime guard
            """Inform the caller that the Textual dependency is missing.

            Raises
            ------
            RuntimeError
                Always raised to indicate the missing optional dependency.
            """
            raise RuntimeError(
                "Textual is not installed; install it with `pip install textual` "
                "to use the Textual dashboard (SetupDashboardApp)."
            )

    SetupDashboardApp = _MissingTextualApp
    DashboardContext: Any = object

__all__ = ["DashboardContext", "SetupDashboardApp"]
