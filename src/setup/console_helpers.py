"""console_helpers.py — Portfolio-quality Rich/Questionary integration and fallback for terminal UI.

This module provides robust, file-local decoupling between orchestrator UI logic
and the optional third-party packages Rich and Questionary. All imports, stubs,
and dependency guards are local, yielding deterministic, reproducible behavior
in CI and tests regardless of environment.

Features
--------
- Exposes rprint and ui_has_rich as the canonical primitives for safe, feature-detecting 
  terminal output.
- Provides pure stubs for all essential Rich types, allowing test, monkeypatch, and 
  CI scenarios to operate without dependencies.
- Offers questionary wrapper for interactive prompts, always present/testable.

Boundaries
----------
- No code outside this module should import Rich or Questionary.
- All fallback logic (mutation, stub classes) is isolated and validated in tests/setup/test_console_helpers_unit.py.

Canonical Usage
---------------
>>> from src.setup.console_helpers import rprint, ui_has_rich
>>> rprint("Hello Rich!")                  # Prints via Rich if present, else builtin print
>>> print(ui_has_rich())                   # True if Rich detected, False otherwise

CI Integration
--------------
All stubs and detection logic are validated by both unit and mutation/integration tests.
Portfolio-grade: conforms to AGENTS.md (section 3: layer decoupling, section 4: documentation).

References
----------
- AGENTS.md: Section 3, Section 4
- Rich Docs: https://rich.readthedocs.io/en/latest/
- Questionary Docs: https://github.com/tmbo/questionary

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
        # Define simple, callable stubs for rich types to allow safe imports
        # and deterministic behaviour under tests where the real `rich`
        # package may be present or monkeypatched. These stubs mimic the
        # minimal interface used by the rest of the codebase and are
        # intentionally lightweight.
        class _FakePanel:
            def __init__(self, renderable: Any = "", title: str = "") -> None:
                r"""Stub implementation of Rich's Panel primitive.

                Provides a minimal constructor and attributes to permit safe usage and test
                monkeypatching when Rich is absent or forcibly mutated in CI environments.

                Parameters
                ----------
                renderable : Any, optional
                    Content to display inside the panel. Defaults to empty string.
                title : str, optional
                    The panel's title text. Defaults to the empty string.

                Returns
                -------
                None

                Raises
                ------
                None

                Notes
                -----
                Only `.renderable` and `.title` attributes are provided for tests and fallback.

                Examples
                --------
                >>> p = _FakePanel("stub", title="Edge")
                >>> assert p.renderable == "stub"
                >>> assert p.title == "Edge"
                """
                self.renderable = renderable
                self.title = title

        class _FakeGroup:
            def __init__(self, *items: Any) -> None:
                r"""Stub implementation of Rich's Group primitive.

                Minimal test/CI-friendly constructor to allow stable grouping/fallback behaviors.
                Used whenever Rich is missing, monkeypatched, or mutation-tested.

                Parameters
                ----------
                *items : Any
                    Arbitrary, file-local objects to group for fallback UI logic.

                Returns
                -------
                None

                Raises
                ------
                None

                Notes
                -----
                Only `.items` attribute is available for test/inspection.

                Examples
                --------
                >>> g = _FakeGroup(1, "a", None)
                >>> assert g.items == (1, "a", None)
                """
                self.items = tuple(items)

        Console: Any = object
        Group: Any = _FakeGroup
        Layout: Any = object
        Live: Any = object
        Markdown: Any = object
        Panel: Any = _FakePanel
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
    r"""Detect true presence of the Rich library for UI routines.

    Returns True if Rich is available for terminal output, False if dependency
    missing (monkeypatched, uninstalled, or mutated for CI/test).

    Returns
    -------
    bool
        True if Rich package is importable and present, else False.

    Raises
    ------
    None

    Notes
    -----
    Always dynamically re-checks importability, ensuring accurate fallback
    in test/CI scenarios including when Rich is forcibly removed/mutated.

    Examples
    --------
    >>> from src.setup.console_helpers import ui_has_rich
    >>> result = ui_has_rich()
    >>> result in (True, False)
    True
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
    r"""Print objects to the terminal using Rich if present; builtin print otherwise.

    All parameters mirror Python's builtin print. If Rich is unavailable (dependency, test,
    monkeypatch, CI), safely falls back to builtin print.

    Parameters
    ----------
    *objects : Any
        Objects to be printed, separated by sep.
    sep : str, optional
        Separator between objects, default ' '.
    end : str, optional
        Line ending, default newline.
    file : IO[str], optional
        File-like object to print to, default sys.stdout.
    flush : bool, optional
        Forcibly flush output.

    Returns
    -------
    None

    Raises
    ------
    None

    Notes
    -----
    - Uses Rich's print when available, else builtin print.
    - All exceptions (including misconfigured Rich) are handled gracefully.

    Examples
    --------
    >>> from src.setup.console_helpers import rprint
    >>> rprint("Rich or fallback!", 123)
    Rich or fallback! 123

    >>> import sys; sys.modules["rich"] = None
    >>> rprint("Stub only")
    Stub only

    >>> import io
    >>> buf = io.StringIO()
    >>> rprint("FileOut", file=buf)
    >>> "FileOut" in buf.getvalue()
    True
    """
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
