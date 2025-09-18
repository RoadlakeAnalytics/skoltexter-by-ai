"""Status rendering helpers for pipeline package."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _status_label(lang: str, base: str) -> str:
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
    from src.setup.console_helpers import Table as _Table

    # Be liberal about the concrete Table implementation: if Rich is
    # available we will get a rich.table.Table that accepts constructor
    # arguments. If not, fall back to a minimal table-like object that
    # exposes `add_column` and `add_row` so callers can render or inspect
    # it in tests.
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


__all__ = ["_status_label", "_render_pipeline_table"]
