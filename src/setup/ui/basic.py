"""Basic UI primitives for the setup TUI.

Contains minimal message/render helpers that do not depend on higher-level
dashboard logic.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from src.setup.console_helpers import (
    _RICH_CONSOLE,
    Panel,
    Rule,
    Table,
    rprint,
    ui_has_rich,
)


def ui_rule(title: str) -> None:
    """Render a horizontal rule or header line in the UI."""
    if ui_has_rich() and _RICH_CONSOLE:
        _RICH_CONSOLE.print(Rule(title, style="bold blue"))
    else:
        rprint("\n" + title)


def ui_header(title: str) -> None:
    """Render a header banner using Rich when available."""
    if ui_has_rich() and _RICH_CONSOLE:
        _RICH_CONSOLE.print(
            Panel.fit(title, style="bold white on blue", border_style="blue")
        )
    else:
        rprint(title)


def ui_status(message: str) -> AbstractContextManager[None]:
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        if ui_has_rich() and _RICH_CONSOLE:
            with _RICH_CONSOLE.status(message, spinner="dots"):
                yield
        else:
            rprint(message)
            yield

    return _ctx()


def ui_info(message: str) -> None:
    """Display an informational message to the user."""
    if ui_has_rich():
        rprint(f"[cyan]{message}[/cyan]")
    else:
        rprint(message)


def ui_success(message: str) -> None:
    """Display a success message to the user."""
    if ui_has_rich():
        rprint(f"[green]✓ {message}[/green]")
    else:
        rprint(message)


def ui_warning(message: str) -> None:
    """Display a warning message to the user."""
    if ui_has_rich():
        rprint(f"[yellow]⚠ {message}[/yellow]")
    else:
        rprint(message)


def ui_error(message: str) -> None:
    """Display an error message to the user."""
    if ui_has_rich():
        rprint(f"[bold red]✗ {message}[/bold red]")
    else:
        rprint(message)


def ui_menu(items: list[tuple[str, str]]) -> None:
    """Render a simple selection menu from a list of key/label pairs."""
    if ui_has_rich() and _RICH_CONSOLE:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("#", style="bold")
        table.add_column("Val")
        for key, label in items:
            table.add_row(key, label)
        _RICH_CONSOLE.print(table)
    else:
        for key, label in items:
            rprint(f"{key}. {label}")


__all__ = [
    "ui_rule",
    "ui_header",
    "ui_status",
    "ui_info",
    "ui_success",
    "ui_warning",
    "ui_error",
    "ui_menu",
]
