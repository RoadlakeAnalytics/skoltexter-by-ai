"""Console helpers for optional Rich and Questionary UI.

This module centralizes optional imports for `rich` and `questionary`,
provides a safe fallback for `rprint`, and exposes `ui_has_rich` flag.
"""

import typing

Any = typing.Any
IO = typing.IO
TYPE_CHECKING = typing.TYPE_CHECKING

# Import Rich types when type-checking to provide correct type hints. At
# runtime perform a guarded import so the module can be used even when
# optional dependencies are missing.
if TYPE_CHECKING:
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table

    _RICH_CONSOLE: Any = ...
else:
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
        Console: Any = object
        Group: Any = object
        Layout: Any = object
        Live: Any = object
        Markdown: Any = object
        Panel: Any = object
        Rule: Any = object
        Syntax: Any = object
        Table: Any = object
        _RICH_CONSOLE = None

# Ensure questionary presence is checked regardless of the Rich import
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
        import rich  # noqa: F401
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
                from rich import print as rich_print

                rich_print(*objects, sep=sep, end=end, file=file, flush=flush)
                return
            except Exception:
                pass
    except Exception:
        pass
    print(*objects, sep=sep, end=end, file=file, flush=flush)


__all__ = [
    "_HAS_Q",
    "_RICH_CONSOLE",
    "Console",
    "Group",
    "Layout",
    "Live",
    "Markdown",
    "Panel",
    "Rule",
    "Syntax",
    "Table",
    "questionary",
    "rprint",
    "ui_has_rich",
]
