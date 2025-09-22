"""Rich-specific dashboard configuration and menu exports for the terminal UI layer.

Single Responsibility Principle (SRP)
------------------------------------
This module exposes core dashboard configuration and menu components for the Rich-backed terminal UI.
Its sole responsibility is exporting orchestrator-facing UI layouts and menu factories, strictly delimiting
the boundary between UI composition (Rich interface) and business/data logic. No logic, state, or exception
handling is defined here; only symbol re-exports for downstream use.

Role in Architecture
--------------------
As part of the UI Orchestration Layer (`src/setup/ui/`), this module enables the Orchestrator (`src/setup/pipeline/orchestrator.py`)
to present interactive dashboards and menus via Rich TUI elements. All logic and layout details reside in
`src/setup/ui/layout.py` and `src/setup/ui/menu.py`—this module guarantees their interface for downstream consumer modules,
strictly enforcing clean separation (see AGENTS.md §3/4/5).

Portfolio/CI/Test Boundary
--------------------------
- This module shall always contain only explicit exports, no logic or side effects.
- Its boundary is verifiable via mutation (mutmut), coverage (pytest), and audit (interrogate, bandit, pip-audit).
- Canonical and corner CI/test cases are handled upstream in lower-level UI modules and in integration tests (see
  `tests/setup/ui/test_layout_unit.py`, `tests/setup/ui/test_menu_ui_unit.py`).
- Exception boundaries are empty; all exceptions are handled at the implementation and orchestrator boundaries.

Exports/API Guarantees
----------------------
__all__ = ["_main_menu_rich_dashboard", "build_dashboard_layout"]

    - `_main_menu_rich_dashboard : Callable[[], rich.panel.Panel]`
      Factory for constructing the main dashboard menu, implemented in `src/setup/ui/menu.py`.
      See `src/setup/ui/menu.py` for complete docstring, robust parameter/returns/test/audit coverage.

    - `build_dashboard_layout : Callable[[], rich.layout.Layout]`
      Factory for assembling the Rich dashboard layout, implemented in `src/setup/ui/layout.py`.
      See `src/setup/ui/layout.py` for comprehensive docstring, rationale, mutation/test/CI edge cases.

Module Notes
------------
- Imports are documented below for trace/audit purposes.
- No local implementation, only re-exports per explicit UI boundary policy.
- Linkage to AGENTS.md §4 (Documentation), §5 (Robustness/Testing/CI guards), CI gates, and corner/canonical/mutation/
  integration policies is provided by downstream modules.

References
----------
AGENTS.md §3 (Architecture), §4 (Documentation), §5 (Robustness), CI gates (ruff, black, mypy, pytest, mutmut, interrogate, bandit, pip-audit).

Examples
--------
The following canonical/corner/CI portfolio usage patterns are covered in test suites:
    >>> from src.setup.ui.rich import build_dashboard_layout, _main_menu_rich_dashboard
    >>> layout = build_dashboard_layout()
    >>> menu_panel = _main_menu_rich_dashboard()
    >>> assert layout is not None
    >>> assert menu_panel is not None

See also
--------
src/setup/ui/layout.py         -- dashboard layout composition, robust docstring and CI coverage.
src/setup/ui/menu.py           -- dashboard menu factory, full docstring and audit/test coverage.
tests/setup/ui/test_layout_unit.py
tests/setup/ui/test_menu_ui_unit.py

Raises
------
None. All exceptions handled in lower layers or orchestrator.

"""

from __future__ import annotations

from src.setup.ui.layout import build_dashboard_layout
from src.setup.ui.menu import _main_menu_rich_dashboard

__all__ = [
    "_main_menu_rich_dashboard",
    "build_dashboard_layout"
]
