"""UI package exposing a cohesive interface for the setup UI.

This package gathers smaller UI modules under a single namespace so
callers can import from `src.setup.ui` while the implementation is split
into focused files.
"""

from __future__ import annotations

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
    "ui_rule",
    "ui_header",
    "ui_status",
    "ui_info",
    "ui_success",
    "ui_warning",
    "ui_error",
    "ui_menu",
    "ask_text",
    "ask_confirm",
    "ask_select",
    "_build_dashboard_layout",
    "get_program_descriptions",
    "view_program_descriptions",
    "_view_program_descriptions_tui",
    "_view_logs_tui",
    "view_logs",
]
from src.setup.console_helpers import ui_has_rich

__all__.append("ui_has_rich")
