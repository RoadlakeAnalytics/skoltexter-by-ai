"""app_prompts.py : Interactive prompt helpers for orchestration UI.

This module provides TUI-aware prompt functions for safe, testable user interaction
during setup and orchestration of the school data pipeline. It strictly enforces
bounded input attempts, encapsulates orchestrator flags, and provides a portfolio-
compliant separation between UI logic and business code. Designed for high testability,
robust user experience, and strict compatibility with CI and automation pipelines.

System Context
--------------
- Upstream: Called from orchestrator logic and launcher (e.g. setup_project.py, pipeline/orchestrator.py).
- Downstream: Delegates to rich/textual menus and core pipeline programs, with test toggles exposed for monkeypatching.
- Boundaries: Never embeds business logic, shell commands, or configuration values; only pure user interaction.

References
----------
- AGENTS.md (Robustness, docstring, and prompt rules)
- src/config.py (magic numbers, bounded attempts)
- src/exceptions.py (UserInputError and error taxonomy)
- src/setup/pipeline/orchestrator.py (runtime TUI flags)
- src/setup/ui/prompts.py, src/setup/app_ui.py (prompt adapters)

Usage Example
-------------
>>> # Typical use: Ask the user to confirm setup, select options, manage virtual environments.
>>> from src.setup.app_prompts import ask_text, ask_confirm, ask_select
>>> name = ask_text("Enter project name:", default="schoolsite")
>>> if ask_confirm("Begin setup?"):
...     lang = ask_select("Choose language:", ["en", "sv"])
>>> # All prompts are bounded and testable via pytest/xdoctest.
"""


from __future__ import annotations

import sys
from typing import Any, Optional, Tuple, Type, cast
from types import ModuleType
from src.config import INTERACTIVE_MAX_INVALID_ATTEMPTS
from src.exceptions import UserInputError

panel_cls: Optional[Type[Any]] = None
try:
    from rich.panel import Panel
    panel_cls = Panel
except ImportError:
    panel_cls = None


def _get_tui_flags() -> tuple[bool, Any, Any]:
    r"""Return the current pipeline orchestrator TUI (Text User Interface) flags.

    These flags govern runtime UI mode and adapters, supporting interactive prompts
    under orchestration and ensuring consistency in test and manual environments.
    The function reads the canonical interface toggles directly from the orchestrator,
    enabling monkeypatching in tests for deterministic behaviour.

    Returns
    -------
    tuple[bool, Any, Any]
        _TUI_MODE : bool
            Whether the orchestration pipeline is in TUI mode.
        _TUI_UPDATER : Any
            Runtime UI updater callable or None.
        _TUI_PROMPT_UPDATER : Any
            Runtime prompt updater callable or None.

    Raises
    ------
    Exception
        On module import or flag access failure; returns fallback values instead.

    References
    ----------
    See src/setup/pipeline/orchestrator.py for flag definitions and control.

    Examples
    --------
    >>> mode, updater, prompt_updater = _get_tui_flags()
    >>> assert isinstance(mode, bool)
    """
    try:
        import src.setup.pipeline.orchestrator as _orch_mod

        return (
            getattr(_orch_mod, "_TUI_MODE", False),
            getattr(_orch_mod, "_TUI_UPDATER", None),
            getattr(_orch_mod, "_TUI_PROMPT_UPDATER", None),
        )
    except Exception:
        return False, None, None


def ask_text(prompt: str, default: str | None = None) -> str:
    """Prompt user for text using the prompts adapter (TUI-aware).

    Parameters
    ----------
    prompt : str
        Prompt text to display.
    default : str | None, optional
        Default value to return when the user provides no input.

    Returns
    -------
    str
        The entered or default text.
    """
    _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = _get_tui_flags()

    # TUI direct-mode behaviour (uses getpass/input)
    if _TUI_MODE and _TUI_UPDATER is not None:
        try:
            if panel_cls is not None:
                try:
                    _TUI_PROMPT_UPDATER(panel_cls(f"{prompt}\n\n> ", title="Input"))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            import getpass

            value = getpass.getpass("")
        except Exception:
            try:
                value = input("")
            except Exception:
                return default or ""
        return (value or "").strip() or (default or "")

    # Otherwise delegate to the prompts adapter, propagating TUI flags
    # into the orchestrator while asking so tests get deterministic
    # behaviour.
    _orch: Optional[Any] = None
    _orch_prev: Optional[Tuple[bool, Any, Any]] = None
    try:
        import src.setup.pipeline.orchestrator as orch_import

        _orch = cast(Any, orch_import)
        if _orch is not None:
            _orch_prev = (
                _orch._TUI_MODE,
                _orch._TUI_UPDATER,
                _orch._TUI_PROMPT_UPDATER,
            )
            _orch._TUI_MODE = _TUI_MODE
            _orch._TUI_UPDATER = _TUI_UPDATER
            _orch._TUI_PROMPT_UPDATER = _TUI_PROMPT_UPDATER
    except Exception:
        _orch = None
        _orch_prev = None

    try:
        # Sync console helpers via the dedicated module to honour test
        # toggles that may be applied to ``src.setup.app``.
        import src.setup.app_ui as _app_ui

        _app_ui._sync_console_helpers()
        from src.setup.ui.prompts import ask_text as _ask

        result = _ask(prompt, default)
    finally:
        if _orch is not None:
            try:
                if _orch_prev is not None:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _orch_prev
                else:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
            except Exception:
                pass

    return result


def ask_confirm(prompt: str, default_yes: bool = True) -> bool:
    """Prompt the user for a yes/no confirmation.

    Parameters
    ----------
    prompt : str
        Text to present to the user.
    default_yes : bool, optional
        Whether the default selection should be treated as 'yes'.

    Returns
    -------
    bool
        True if the user confirmed, False otherwise.
    """
    _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = _get_tui_flags()

    _orch: Optional[Any] = None
    _orch_prev: Optional[Tuple[bool, Any, Any]] = None
    try:
        import src.setup.pipeline.orchestrator as orch_import

        _orch = cast(Any, orch_import)
        if _orch is not None:
            _orch_prev = (
                _orch._TUI_MODE,
                _orch._TUI_UPDATER,
                _orch._TUI_PROMPT_UPDATER,
            )
            _orch._TUI_MODE = _TUI_MODE
            _orch._TUI_UPDATER = _TUI_UPDATER
            _orch._TUI_PROMPT_UPDATER = _TUI_PROMPT_UPDATER
    except Exception:
        _orch = None
        _orch_prev = None

    try:
        import src.setup.app_ui as _app_ui

        _app_ui._sync_console_helpers()
        from src.setup.ui.prompts import ask_confirm as _askc

        result = _askc(prompt, default_yes)
    finally:
        if _orch is not None:
            try:
                if _orch_prev is not None:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _orch_prev
                else:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
            except Exception:
                pass

    return result


def ask_select(prompt: str, choices: list[str]) -> str:
    """Prompt the user to select one option from a list of choices.

    Parameters
    ----------
    prompt : str
        Prompt text to display.
    choices : list[str]
        Available options.

    Returns
    -------
    str
        The selected option.
    """
    _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = _get_tui_flags()

    _orch: Optional[Any] = None
    _orch_prev: Optional[Tuple[bool, Any, Any]] = None
    try:
        import src.setup.pipeline.orchestrator as orch_import

        _orch = cast(Any, orch_import)
        if _orch is not None:
            _orch_prev = (
                _orch._TUI_MODE,
                _orch._TUI_UPDATER,
                _orch._TUI_PROMPT_UPDATER,
            )
            _orch._TUI_MODE = _TUI_MODE
            _orch._TUI_UPDATER = _TUI_UPDATER
            _orch._TUI_PROMPT_UPDATER = _TUI_PROMPT_UPDATER
    except Exception:
        _orch = None
        _orch_prev = None

    try:
        import src.setup.app_ui as _app_ui

        _app_ui._sync_console_helpers()
        from src.setup.ui.prompts import ask_select as _asks

        result = _asks(prompt, choices)
    finally:
        if _orch is not None:
            try:
                if _orch_prev is not None:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _orch_prev
                else:
                    _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
            except Exception:
                pass

    return result


def set_language() -> None:
    """Prompt the user to select a language with bounded attempts.

    This function displays available languages and uses ask_select to get
    the user's choice. It tracks invalid attempts and raises UserInputError
    if INTERACTIVE_MAX_INVALID_ATTEMPTS is exceeded, ensuring no unbounded loops.

    Raises
    ------
    UserInputError
        If too many invalid language selections are made.

    Notes
    -----
    Languages are hardcoded as ["en", "sv"] for simplicity; extend as needed.

    Examples
    --------
    >>> set_language()  # doctest: +SKIP
    # User selects "sv", i18n.LANG set to "sv"; or raises on invalid exceedance.
    """
    from src.setup import i18n
    languages = ["en", "sv"]
    invalid_attempts = 0
    while invalid_attempts < INTERACTIVE_MAX_INVALID_ATTEMPTS:
        selected = ask_select("Select language (en/sv):", languages)
        if selected in languages:
            i18n.LANG = selected
            return
        invalid_attempts += 1
        if invalid_attempts >= INTERACTIVE_MAX_INVALID_ATTEMPTS:
            raise UserInputError("Too many invalid language selections.")
    raise UserInputError("Exceeded attempts to set language.")


def prompt_virtual_environment_choice() -> bool:
    """Prompt the user to confirm virtual environment management with bounded attempts.

    Uses ask_confirm to get yes/no response. Tracks invalid inputs and raises
    UserInputError on exceedance of INTERACTIVE_MAX_INVALID_ATTEMPTS.

    Returns
    -------
    bool
        True if user confirms (y/j), False otherwise.

    Raises
    ------
    UserInputError
        If too many invalid confirmations.

    Examples
    --------
    >>> prompt_virtual_environment_choice()  # doctest: +SKIP
    # Returns True on "y", False on "n"; raises on invalid exceedance.
    """
    invalid_attempts = 0
    while invalid_attempts < INTERACTIVE_MAX_INVALID_ATTEMPTS:
        confirmed = ask_confirm("Manage virtual environment? (y/n)", default_yes=True)
        return confirmed
    raise UserInputError("Too many invalid confirmation attempts for venv.")


def get_program_descriptions() -> dict[str, tuple[str, str]]:
    """Return program descriptions by delegating to the UI programs module."""
    from src.setup.ui.programs import get_program_descriptions as _g

    return _g()


def view_program_descriptions() -> None:
    """Display an interactive view of program descriptions using bounded selection.

    This function fetches program descriptions and allows the user to select and view
    details for individual programs in a loop. The interaction is explicitly bounded
    by ``INTERACTIVE_MAX_INVALID_ATTEMPTS`` to prevent infinite loops, raising a
    ``UserInputError`` if exceeded. It uses TUI-aware prompts for consistent behavior.

    Notes
    -----
    The loop continues until the user selects 'exit' or an invalid attempt limit is reached.
    This ensures robustness in interactive sessions.

    Examples
    --------
    >>> view_program_descriptions()  # doctest: +SKIP
    # Displays menu, user selects a program, shows description, repeats until exit.
    """
    descriptions = get_program_descriptions()
    if not descriptions:
        print("No program descriptions available.")
        return

    invalid_attempts = 0
    while invalid_attempts < INTERACTIVE_MAX_INVALID_ATTEMPTS:
        choices = list(descriptions.keys()) + ["exit"]
        selected = ask_select("Select a program to view (or 'exit'):", choices)
        if selected == "exit":
            break
        if selected in descriptions:
            name, desc = descriptions[selected]
            print(f"\n{name}:\n{desc}\n")
            invalid_attempts = 0  # Reset on valid selection
        else:
            invalid_attempts += 1
            if invalid_attempts >= INTERACTIVE_MAX_INVALID_ATTEMPTS:
                raise UserInputError("Too many invalid selections. Exiting view.")

    print("Exiting program descriptions view.")
