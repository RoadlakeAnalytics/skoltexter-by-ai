"""Minimal layout helpers for the TUI.

Implements a light-weight layout object with named slots to satisfy tests
without requiring Rich to be installed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class _Slot:
    def __init__(self, value: Any | None = None) -> None:
        self.value = value

    def update(self, value: Any) -> None:
        self.value = value


def build_dashboard_layout(
    translate: Callable[[str], str], welcome_panel: Any, venv_dir, lang: str
) -> dict[str, _Slot]:
    """Build a simple dict-like layout with required slots.

    Returns a mapping with at least keys: 'header', 'body', 'footer',
    'content', and 'prompt'.
    """
    layout = {
        "header": _Slot(welcome_panel),
        "body": _Slot(None),
        "footer": _Slot(None),
        "content": _Slot(None),
        "prompt": _Slot(None),
    }
    return layout


__all__ = ["build_dashboard_layout"]
