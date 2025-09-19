"""UI package exposing a cohesive interface for the setup UI.

This package gathers smaller UI modules under a single namespace so
callers can import from `src.setup.ui` while the implementation is split
into focused files.
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
