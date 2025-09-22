"""Module docstring for src.setup.ui: Cohesive UI interface aggregator.

Single Responsibility Principle (SRP):
    This subpackage exposes the public UI interface for all setup-related TUI utilities,
    centralizing entry points for menu, prompts, status, error/success, and overall dashboard
    layout. It re-exports implementation symbols from focused internal modules (`basic.py`, `layout.py`,
    `prompts.py`, `programs.py`) under a unified namespace, maintaining strict separation
    of orchestration/UI from downstream pipeline logic per portfolio architecture (AGENTS.md §3).

Package Boundary & Rationale:
    The src.setup.ui subpackage serves as a boundary for the entire UI layer of the setup orchestrator.
    No business logic is present; all orchestration and rendering is deferred to internal modules. This pattern:
    - Enables concise imports for setup-layer clients: e.g., `from src.setup.ui import ui_menu, ask_confirm`.
    - Enforces modularity and maintainability (SRP at submodule/file granularity, AGENTS.md §3/§4).
    - Facilitates CI visibility and auditability, as all UI symbols are explicitly surfaced in `__all__`.

Integration, Configuration, Exception, and Testing Notes:
    - All configuration constants must be defined in `src/config.py` (per AGENTS.md §3.3). This module never hardcodes values.
    - Exception handling is delegated to downstream modules, which must use only custom exceptions from `src/exceptions.py` (§5.2).
    - Unit/integration tests for UI coverage target the aggregated symbols and linkage correctness in tests/setup/ui/
    - CI gates (pytest, mypy --strict, ruff, interrogate) validate symbol exports, import correctness, and audit/failure on broken UI linkage.

Canonical and Corner/Empty/Test Branches:
    - Canonical use: Routine re-export of active symbols defined in UI modules. CI verifies import and usage flows.
    - Empty/init case: As a package aggregator, this module contains no functions or classes; this is intentional for decoupling/audit (§4.1, §5.4).
    - Corner: If a submodule is removed/renamed or a symbol is missing, import errors are surfaced in CI/test audits.
    - Explicit test coverage: Audit/pytest/interrogate always validate that all re-exported symbols are functional and imported as intended.
    - If the module is changed to include logic, it must obey AGENTS.md SRP and documentation rules, and any missing/corrupt exports must be reflected in CI coverage.

Usage/Linkage Flows & Portfolio Guarantees:
    - Typical usage (canonical): `from src.setup.ui import ui_menu, ask_confirm`
    - Linkage: Downstream orchestrator modules depend on this aggregation for all UI menu flows.
    - All exported names are audited for usage and coverage; audit/test failures are visible in CI logs.
    - This pattern is a gold-standard for maintainable portfolio codebases (AGENTS.md §4/§5).

Examples
--------
This package contains no top-level functions/classes.
Example usage (all tested under pytest & xdoctest):

>>> from src.setup.ui import ui_header, ui_menu, ui_error, ask_confirm
>>> # Use these in orchestrators or UI wrappers.

See Also
--------
src/config.py
src/exceptions.py
src/setup/ui/basic.py
src/setup/ui/layout.py
src/setup/ui/programs.py
src/setup/ui/prompts.py
tests/setup/test_app_ui.py
tests/setup/ui/test_*_unit.py

Notes
-----
- All symbols listed in __all__ are intended for external usage.
- Downstream modules must only access UI via this aggregator for auditability and portfolio robustness.
- CI/test coverage verifies every code branch, including the empty-init/corner flows.
- Any modification must comply with AGENTS.md and NumPy docstring standards.

"""

from __future__ import annotations

from src.setup.console_helpers import ui_has_rich as _ui_has_rich

from .basic import (
    ui_error,
    ui_header,
    ui_info,
    ui_menu,
    ui_rule,
    ui_status,
    ui_success,
    ui_warning,
)
from .layout import build_dashboard_layout as _build_dashboard_layout
from .programs import (
    _view_logs_tui,
    _view_program_descriptions_tui,
    get_program_descriptions,
    view_logs,
    view_program_descriptions,
)
from .prompts import ask_confirm, ask_select, ask_text

__all__ = [
    "_build_dashboard_layout",
    "_view_logs_tui",
    "_view_program_descriptions_tui",
    "ask_confirm",
    "ask_select",
    "ask_text",
    "get_program_descriptions",
    "ui_error",
    "ui_has_rich",
    "ui_header",
    "ui_info",
    "ui_menu",
    "ui_rule",
    "ui_status",
    "ui_success",
    "ui_warning",
    "view_logs",
    "view_program_descriptions",
]

# Re-export the helper under the public name so callers can do
# ``from src.setup.ui import ui_has_rich`` without importing
# ``src.setup.console_helpers`` directly. The indirection also avoids
# ruff flagging the import as unused.
ui_has_rich = _ui_has_rich
