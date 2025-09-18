"""Textual UI integration exported from the ui package.

This module exposes the Textual application classes moved into the
package as `textual_app.py`. Import is performed lazily and falls back to
clear placeholders when the optional `textual` dependency is missing so
the rest of the package can be imported in minimal environments.
"""

from __future__ import annotations

try:  # Lazy import so package import doesn't require Textual to be installed
    from .textual_app import DashboardContext, SetupDashboardApp
except Exception:  # pragma: no cover - optional dependency
    # Provide lightweight placeholders with helpful error messages so that
    # callers that actually want to run the Textual app get a clear error
    # while other parts of the codebase can import this package safely.

    class _MissingTextualApp:  # sentinel placeholder
        def __init__(self, *a, **k):  # pragma: no cover - runtime guard
            raise RuntimeError(
                "Textual is not installed; install it with `pip install textual` "
                "to use the Textual dashboard (SetupDashboardApp)."
            )

    SetupDashboardApp = _MissingTextualApp  # type: ignore
    DashboardContext = object

__all__ = ["SetupDashboardApp", "DashboardContext"]
