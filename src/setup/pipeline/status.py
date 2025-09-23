"""Rendering helpers for pipeline status and progress tables.

Provides functions to produce localized status labels and a table-like
renderable compatible with Rich or a simple fallback for environments
without Rich.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _status_label(lang: str, base: str) -> str:
    """Return a localized status label for a given pipeline status key.

    Parameters
    ----------
    lang : str
        Language code (e.g., ``'en'`` or ``'sv'``).
    base : str
        Status key such as ``'waiting'``, ``'running'``, ``'ok'`` or ``'fail'``.

    Returns
    -------
    str
        Localized status label.

    Examples
    --------
    >>> _status_label("sv", "ok")
    '✅ Klart'
    """
    if lang == "sv":
        labels = {
            "waiting": "⏳ Väntar",
            "running": "▶️  Körs",
            "ok": "✅ Klart",
            "fail": "❌ Misslyckades",
        }
    else:
        labels = {
            "waiting": "⏳ Waiting",
            "running": "▶️  Running",
            "ok": "✅ Done",
            "fail": "❌ Failed",
        }
    return labels.get(base, base)


def _render_pipeline_table(
    translate: Callable[[str], str], status1: str, status2: str, status3: str
) -> Any:
    """Construct a table-like renderable summarising pipeline status.

    Parameters
    ----------
    translate : Callable[[str], str]
        Translation function for i18n keys.
    status1, status2, status3 : str
        Labels representing each program's current state.

    Returns
    -------
    Any
        A table-like renderable compatible with Rich or a simple fallback.
    """
    from src.setup.console_helpers import Table as _Table

    try:
        table = _Table(
            title=translate("pipeline_title"),
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("Step", style="bold")
        table.add_column("Status")
        table.add_row("Program 1", status1)
        table.add_row("Program 2", status2)
        table.add_row("Program 3", status3)
        return table
    except Exception:

        class _SimpleTable:
            """A minimal table-like fallback for environments without Rich."""

            def __init__(
                self,
                title: str | None = None,
                show_header: bool | None = None,
                header_style: str | None = None,
            ) -> None:
                self.title = title
                self.show_header = show_header
                self.header_style = header_style
                self.columns: list[tuple[str, Any]] = []
                self.rows: list[tuple[Any, ...]] = []

            def add_column(self, name: str, style: Any = None) -> None:
                self.columns.append((name, style))

            def add_row(self, *cols: Any) -> None:
                self.rows.append(cols)

        table = _SimpleTable(
            title=translate("pipeline_title"),
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("Step", style="bold")
        table.add_column("Status")
        table.add_row("Program 1", status1)
        table.add_row("Program 2", status2)
        table.add_row("Program 3", status3)
        return table


__all__ = ["_render_pipeline_table", "_status_label"]

