"""Prompt helpers for the UI package.

Adapters for text prompts that integrate with the TUI adapter state
maintained by the orchestrator. They avoid any dependency on a legacy
top-level shim.
"""

from __future__ import annotations

import os as _os
import sys

from src.setup import console_helpers as ch


def ask_text(prompt: str, default: str | None = None) -> str:
    """Prompt the user for a line of text with TUI/Questionary fallbacks."""
    try:
        from src.setup.pipeline import (
            orchestrator as _orch,
        )  # local import to avoid cycles
    except Exception:
        _orch = None  # type: ignore[assignment]
    if (_orch is not None) and _orch._TUI_MODE and _orch._TUI_UPDATER is not None:
        if getattr(_orch, "_TUI_PROMPT_UPDATER", None) is not None:
            _orch._TUI_PROMPT_UPDATER(ch.Panel(f"{prompt}\n\n> ", title="Input"))
        if (
            _os.environ.get("PYTEST_CURRENT_TEST")
            or not getattr(sys.stdin, "isatty", lambda: False)()
        ):
            try:
                value = input("")
            except (EOFError, OSError):
                return default or ""
        else:
            try:
                import getpass

                value = getpass.getpass("")
            except Exception:
                try:
                    value = input("")
                except (EOFError, OSError):
                    return default or ""
        return (value or "").strip() or (default or "")
    try:
        is_tty = sys.stdin.isatty()
    except Exception:
        is_tty = False
    in_test = bool(_os.environ.get("PYTEST_CURRENT_TEST"))
    if (not is_tty) and (not in_test):
        return default or ""
    use_q = (
        getattr(ch, "_HAS_Q", False)
        and getattr(ch, "questionary", None) is not None
        and (
            ((not in_test) and is_tty)
            or (in_test and not hasattr(ch.questionary, "__file__"))
        )
    )
    if use_q:
        ans = ch.questionary.text(prompt, default=default or "").ask()
        return (ans or (default or "")).strip()
    try:
        return input(prompt).strip() or (default or "")
    except (EOFError, OSError):
        return default or ""


def ask_confirm(prompt: str, default_yes: bool = True) -> bool:
    """Prompt the user to confirm yes/no with sensible defaults."""
    try:
        from src.setup.pipeline import (
            orchestrator as _orch,
        )  # local import to avoid cycles
    except Exception:
        _orch = None  # type: ignore[assignment]
    if (_orch is not None) and _orch._TUI_MODE and _orch._TUI_UPDATER is not None:
        suffix = "(Y/n)" if default_yes else "(y/N)"
        if getattr(_orch, "_TUI_PROMPT_UPDATER", None) is not None:
            _orch._TUI_PROMPT_UPDATER(
                ch.Panel(f"{prompt}  {suffix}\n\n> ", title="Confirm")
            )
        if (
            _os.environ.get("PYTEST_CURRENT_TEST")
            or not getattr(sys.stdin, "isatty", lambda: False)()
        ):
            try:
                val = input("").strip().lower()
            except (EOFError, OSError):
                return default_yes
        else:
            try:
                import getpass

                val = getpass.getpass("").strip().lower()
            except Exception:
                try:
                    val = input("").strip().lower()
                except (EOFError, OSError):
                    return default_yes
        if not val:
            return default_yes
        return val in ("y", "j", "yes")
    try:
        is_tty = sys.stdin.isatty()
    except Exception:
        is_tty = False
    in_test = bool(_os.environ.get("PYTEST_CURRENT_TEST"))
    if (not is_tty) and (not in_test):
        return default_yes
    use_q = (
        getattr(ch, "_HAS_Q", False)
        and getattr(ch, "questionary", None) is not None
        and (
            ((not in_test) and is_tty)
            or (in_test and not hasattr(ch.questionary, "__file__"))
        )
    )
    if use_q:
        return bool(ch.questionary.confirm(prompt, default=default_yes).ask())
    try:
        val = input(prompt).strip().lower()
    except (EOFError, OSError):
        return default_yes
    if not val:
        return default_yes
    return val in ("y", "j", "yes")


def ask_select(prompt: str, choices: list[str]) -> str:
    """Prompt the user to select among choices with safe fallbacks."""
    try:
        is_tty = sys.stdin.isatty()
    except Exception:
        is_tty = False
    in_test = bool(_os.environ.get("PYTEST_CURRENT_TEST"))
    if (not is_tty) and (not in_test):
        return choices[-1]
    use_q = (
        getattr(ch, "_HAS_Q", False)
        and getattr(ch, "questionary", None) is not None
        and (
            ((not in_test) and is_tty)
            or (in_test and not hasattr(ch.questionary, "__file__"))
        )
    )
    if use_q:
        return str(ch.questionary.select(prompt, choices=choices).ask())
    ch.rprint(prompt)
    for idx, opt in enumerate(choices, start=1):
        ch.rprint(f"{idx}. {opt}")
    try:
        sel = input("> ").strip()
    except (EOFError, OSError):
        return choices[-1]
    try:
        i = int(sel) - 1
        return choices[i]
    except Exception:  # pragma: no cover - fallback path
        return sel  # pragma: no cover


__all__ = ["ask_text", "ask_confirm", "ask_select"]
