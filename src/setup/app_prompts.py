"""Prompt helpers extracted from src.setup.app.

These functions implement the interactive prompt behaviour. They read
runtime flags (TUI mode, updaters) from the main ``src.setup.app``
module so tests can monkeypatch the running state.
"""

from __future__ import annotations

import sys
from typing import Any


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
    app_mod = sys.modules.get("src.setup.app")
    _TUI_MODE = getattr(app_mod, "_TUI_MODE", False)
    _TUI_UPDATER = getattr(app_mod, "_TUI_UPDATER", None)
    _TUI_PROMPT_UPDATER = getattr(app_mod, "_TUI_PROMPT_UPDATER", None)

    # TUI direct-mode behaviour (uses getpass/input)
    if _TUI_MODE and _TUI_UPDATER is not None:
        if _TUI_PROMPT_UPDATER is not None:
            try:
                panel_cls = getattr(sys.modules.get("rich.panel"), "Panel", None)
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
    _orch = None
    _orch_prev = None
    try:
        import src.setup.pipeline.orchestrator as _orch

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
        if _orch is not None and _orch_prev is not None:
            try:
                _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = (
                    _orch_prev
                )
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
    app_mod = sys.modules.get("src.setup.app")
    _TUI_MODE = getattr(app_mod, "_TUI_MODE", False)
    _TUI_UPDATER = getattr(app_mod, "_TUI_UPDATER", None)
    _TUI_PROMPT_UPDATER = getattr(app_mod, "_TUI_PROMPT_UPDATER", None)

    _orch = None
    _orch_prev = None
    try:
        import src.setup.pipeline.orchestrator as _orch

        _orch_prev = (_orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER)
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
        if _orch is not None and _orch_prev is not None:
            try:
                _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = (
                    _orch_prev
                )
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
    app_mod = sys.modules.get("src.setup.app")
    _TUI_MODE = getattr(app_mod, "_TUI_MODE", False)
    _TUI_UPDATER = getattr(app_mod, "_TUI_UPDATER", None)
    _TUI_PROMPT_UPDATER = getattr(app_mod, "_TUI_PROMPT_UPDATER", None)

    _orch = None
    _orch_prev = None
    try:
        import src.setup.pipeline.orchestrator as _orch

        _orch_prev = (_orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER)
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
        if _orch is not None and _orch_prev is not None:
            try:
                _orch._TUI_MODE, _orch._TUI_UPDATER, _orch._TUI_PROMPT_UPDATER = (
                    _orch_prev
                )
            except Exception:
                pass

    return result


def get_program_descriptions() -> dict[str, tuple[str, str]]:
    """Return program descriptions by delegating to the UI programs module."""
    from src.setup.ui.programs import get_program_descriptions as _g

    return _g()


def view_program_descriptions() -> None:
    """Interactive view showing program descriptions using module-level prompts."""
    # Re-implement minimal forwarding behaviour to the UI/programs helpers
    import sys as _sys
    _app_mod = _sys.modules.get("src.setup.app")
    from src.setup import app_ui as _app_ui

    ui_rule = getattr(_app_mod, "ui_rule", _app_ui.ui_rule)
    ui_menu = getattr(_app_mod, "ui_menu", _app_ui.ui_menu)
    ui_has_rich = getattr(_app_mod, "ui_has_rich", _app_ui.ui_has_rich)
    _rprint = getattr(_app_mod, "rprint", getattr(_app_ui, "rprint", print))

    ui_rule("Programs")
    while True:
        _getprog = getattr(_app_mod, "get_program_descriptions", get_program_descriptions)
        descriptions = _getprog()
        items = [(k, v[0]) for k, v in descriptions.items()]
        items.append(("0", "Return"))
        ui_menu(items)
        # Prefer the central shim's patched ask_text when available so
        # tests that monkeypatch ``src.setup.app.ask_text`` affect this
        # behaviour.
        _ask = getattr(_app_mod, "ask_text", ask_text)
        choice = _ask("Select program")
        if choice == "0":
            break
        if choice in descriptions:
            _title, body = descriptions[choice]
            if ui_has_rich():
                try:
                    _rprint(body)
                    continue
                except Exception:
                    pass
            _rprint(body)


def set_language() -> None:
    """Prompt the user to select an interface language and set module state.

    This updates the global i18n module and is exercised by the CLI
    entrypoint. The implementation is intentionally small and delegates
    to ``ask_text`` so tests may monkeypatch the prompt helper on the
    central app module.
    """
    import src.setup.i18n as i18n

    prompt = i18n.TEXTS["en"]["language_prompt"]
    import sys as _sys
    _app_mod = _sys.modules.get("src.setup.app")
    _ask = getattr(_app_mod, "ask_text", ask_text)
    while True:
        try:
            choice = _ask(prompt)
        except KeyboardInterrupt:
            raise SystemExit from None
        if choice == "1":
            i18n.LANG = "en"
            break
        if choice == "2":
            i18n.LANG = "sv"
            break
        print(i18n.TEXTS["en"]["invalid_choice"])  # pragma: no cover - trivial loop

    # Synchronize the module-level LANG on the central app shim so callers
    # that read ``src.setup.app.LANG`` observe the change.
    try:
        app_mod = sys.modules.get("src.setup.app")
        if app_mod is not None:
            setattr(app_mod, "LANG", i18n.LANG)
    except Exception:
        pass


def prompt_virtual_environment_choice() -> bool:
    """Ask the user whether to create/manage a virtual environment.

    Returns
    -------
    bool
        True if the user chose to create/manage a venv, False if skipped.
    """
    from src.setup.app_ui import ui_rule, ui_menu
    import sys as _sys
    import src.setup.i18n as i18n
    _app_mod = _sys.modules.get("src.setup.app")
    _ask = getattr(_app_mod, "ask_text", ask_text)

    ui_rule(i18n.translate("venv_menu_title"))
    ui_menu([
        ("1", i18n.translate("venv_menu_option_1")[3:]),
        ("2", i18n.translate("venv_menu_option_2")[3:]),
    ])
    while True:
        choice = _ask(i18n.translate("venv_menu_prompt"))
        if choice == "1":
            return True
        if choice == "2":
            # Prefer patched ui_info on central app shim when present
            _ui = getattr(_app_mod, "ui_info", None)
            if _ui is None:
                from src.setup.app_ui import ui_info as _ui_info

                _ui = _ui_info
            _ui(i18n.translate("venv_skipped"))
            return False
        print(i18n.translate("invalid_choice"))


__all__ = [
    "ask_text",
    "ask_confirm",
    "ask_select",
    "get_program_descriptions",
    "view_program_descriptions",
    "set_language",
]
