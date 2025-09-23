"""Re-exports Rich-based UI components for the orchestrator.

This module exposes UI factories implemented in the ``src.setup.ui``
package such as dashboard layout and main menu factories. It does not
implement UI logic itself.

Examples
--------
>>> from src.setup.ui.rich import build_dashboard_layout, _main_menu_rich_dashboard
>>> layout = build_dashboard_layout()
>>> menu_panel = _main_menu_rich_dashboard()
>>> assert layout is not None
>>> assert menu_panel is not None

"""

from __future__ import annotations

from src.setup.ui.layout import build_dashboard_layout
from src.setup.ui.menu import _main_menu_rich_dashboard

__all__ = [
    "_main_menu_rich_dashboard",
    "build_dashboard_layout",
]
