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
    from src.setup.console_helpers import Table

    table = Table(
        title=translate("pipeline_title"), show_header=True, header_style="bold blue"
    )
    table.add_column("Step", style="bold")
    table.add_column("Status")
    table.add_row("Program 1", status1)
    table.add_row("Program 2", status2)
    table.add_row("Program 3", status3)
    return table


__all__ = ["_status_label", "_render_pipeline_table"]
