"""Tests for `src/setup/ui/layout.py`."""

import pytest

from src.setup.console_helpers import Panel, ui_has_rich
from src.setup.ui.layout import build_dashboard_layout as _build_dashboard_layout


def test_rich_build_dashboard_layout(monkeypatch):
    """Build the Rich layout and ensure it constructs without errors."""
    if not ui_has_rich():
        pytest.skip("Rich not available in this environment")
    layout = _build_dashboard_layout(Panel("Welcome"))
    # Basic shape assertions
    assert layout is not None
    # Access by named slots should succeed
    assert layout["header"] and layout["body"] and layout["footer"]
