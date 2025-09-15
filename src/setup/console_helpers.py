"""Console helpers for optional Rich and Questionary UI.

This module centralizes optional imports for `rich` and `questionary`,
provides a safe fallback for `rprint`, and exposes `ui_has_rich` flag.
"""

from typing import IO, Any

# Import Rich types if available to provide nicer UI elements. Avoid binding
# `rprint` directly to `rich.print` to remain resilient to tests that
# monkeypatch imports at runtime.
try:
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table

    _RICH_CONSOLE: Any = Console()
except Exception:
    # Define stubs for rich types to allow safe imports when rich is absent.
    Console = object  # type: ignore[assignment]
    Group = object  # type: ignore[assignment]
    Layout = object  # type: ignore[assignment]
    Live = object  # type: ignore[assignment]
    Markdown = object  # type: ignore[assignment]
    Panel = object  # type: ignore[assignment]
    Rule = object  # type: ignore[assignment]
    Syntax = object  # type: ignore[assignment]
    Table = object  # type: ignore[assignment]
    _RICH_CONSOLE = None

try:
    import questionary as _questionary

    questionary: Any = _questionary
    _HAS_Q = True
except Exception:
    questionary = None
    _HAS_Q = False


def ui_has_rich() -> bool:
    """Return True if the optional `rich` library can be imported now.

    This dynamic check ensures that tests which monkeypatch the import
    system to simulate a missing `rich` dependency observe `False` even if
    this module was previously imported in a context where `rich` existed.
    """
    try:  # re-check importability under test monkeypatching
        import rich  # type: ignore  # noqa: F401
    except Exception:
        return False
    return _RICH_CONSOLE is not None


def rprint(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: IO[str] | None = None,
    flush: bool = False,
) -> None:
    """Safe print function that prefers Rich but degrades gracefully."""
    try:
        if ui_has_rich():
            try:
                from rich import print as rich_print  # type: ignore

                rich_print(*objects, sep=sep, end=end, file=file, flush=flush)
                return
            except Exception:
                pass
    except Exception:
        pass
    print(*objects, sep=sep, end=end, file=file, flush=flush)


__all__ = [
    "_RICH_CONSOLE",
    "questionary",
    "_HAS_Q",
    "ui_has_rich",
    "rprint",
    "Console",
    "Group",
    "Layout",
    "Live",
    "Markdown",
    "Panel",
    "Rule",
    "Syntax",
    "Table",
]
