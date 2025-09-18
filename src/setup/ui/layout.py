"""Minimal layout helpers for the TUI.

Implements a light-weight layout object with named slots to satisfy tests
without requiring Rich to be installed.
"""

from __future__ import annotations

from typing import Any


class _Slot:
    def __init__(self, value: Any | None = None) -> None:
        self.value = value

    def update(self, value: Any) -> None:
        self.value = value


def build_dashboard_layout(*args: Any, **kwargs: Any) -> dict[str, _Slot]:
    """Build a simple dict-like layout with required slots.

    This helper accepts two calling conventions for backwards
    compatibility:

    - `build_dashboard_layout(translate, welcome_panel, venv_dir, lang)`
    - `build_dashboard_layout(welcome_panel, venv_dir=None, lang='en')`

    The latter is a convenience used by tests that only need a header
    panel to be supplied.
    """
    # Support old-style signature where the first arg is a translate callable
    if args and callable(args[0]):
        _, welcome_panel, _venv_dir, _lang = (
            args[0],
            args[1],
            args[2] if len(args) > 2 else None,
            (args[3] if len(args) > 3 else kwargs.get("lang", "en")),
        )
        wp = welcome_panel
    else:
        # New-style: first arg is welcome_panel
        wp = args[0] if args else kwargs.get("welcome_panel")
        _venv_dir = kwargs.get("venv_dir")
        _lang = kwargs.get("lang", "en")

    layout = {
        "header": _Slot(wp),
        "body": _Slot(None),
        "footer": _Slot(None),
        "content": _Slot(None),
        "prompt": _Slot(None),
    }
    return layout


__all__ = ["build_dashboard_layout"]
