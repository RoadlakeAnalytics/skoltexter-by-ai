"""Status rendering helpers for pipeline package."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _status_label(lang: str, base: str) -> str:
    """Return a localized label for the given pipeline status base.

    Parameters
    ----------
    lang : str
        Language code (e.g. "en" or "sv").
    base : str
        Status base key such as ``'waiting'``, ``'running'``, ``'ok'`` or ``'fail'``.

    Returns
    -------
    str
        Localized status label.
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
    """Construct a table-like renderable summarising the pipeline status.

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

    # Be liberal about the concrete Table implementation: if Rich is
    # available we will get a rich.table.Table that accepts constructor
    # arguments. If not, fall back to a minimal table-like object that
    # exposes `add_column` and `add_row` so callers can render or inspect
    # it in tests.
    table: Any
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
            """A minimal table-like fallback for environments without Rich.

            The simple table stores column definitions and rows so tests can
            inspect the structure without requiring Rich's Table type.
            """

            def __init__(
                self,
                title: str | None = None,
                show_header: bool | None = None,
                header_style: str | None = None,
            ) -> None:
                """Create the simple table container.

                Parameters
                ----------
                title : str | None
                    Optional title for the table.
                show_header : bool | None
                    Whether to show the header row.
                header_style : str | None
                    Optional header style string.
                """
                self.title = title
                self.show_header = show_header
                self.header_style = header_style
                self.columns: list[tuple[str, Any]] = []
                self.rows: list[tuple[Any, ...]] = []

            def add_column(self, name: str, style: Any = None) -> None:
                """Add a named column to the simple table.

                Parameters
                ----------
                name : str
                    Column header text.
                style : Any, optional
                    Optional style information for consumers.
                """
                self.columns.append((name, style))

            def add_row(self, *cols: Any) -> None:
                """Append a row of values to the table.

                Parameters
                ----------
                *cols : Any
                    Column values for the row being added.
                """
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
