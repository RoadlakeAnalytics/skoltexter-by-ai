"""Pipeline orchestrator: sequencing and TUI state.

This module contains high-level orchestration of the three pipeline steps
and centralizes a small set of TUI runtime variables so both the plain and
Rich dashboard flows can update UI consistently. It is intentionally
decoupled from any legacy shim modules.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, SRC_DIR
from src.setup.console_helpers import Panel, rprint, ui_has_rich
from src.setup.i18n import LANG, translate
from src.setup.i18n import _ as _
from src.setup.ui.basic import ui_info, ui_rule, ui_success, ui_warning
from src.setup.ui.prompts import ask_confirm, ask_text

from ..azure_env import run_ai_connectivity_check_silent
from .run import run_program
from .status import _render_pipeline_table as _render_table_impl
from .status import _status_label as _status_label_impl

_TUI_MODE: bool = False
_TUI_UPDATER: Callable[[Any], None] | None = None
_TUI_PROMPT_UPDATER: Callable[[Any], None] | None = None
_STATUS_RENDERABLE: object | None = None
_PROGRESS_RENDERABLE: object | None = None


def _compose_and_update() -> None:
    if not _TUI_MODE or _TUI_UPDATER is None:
        return
    if _STATUS_RENDERABLE is not None and _PROGRESS_RENDERABLE is not None:
        # Prefer Rich's Group when available; fall back to a lightweight
        # container named `Group` so tests that check the type name keep
        # working even when Rich is not callable in the current context.
        try:
            from src.setup.console_helpers import Group as _RichGroup

            content = _RichGroup(_STATUS_RENDERABLE, _PROGRESS_RENDERABLE)
        except Exception:

            class Group:
                def __init__(self, a: Any, b: Any) -> None:
                    self.items = (a, b)

            content = Group(_STATUS_RENDERABLE, _PROGRESS_RENDERABLE)
    elif _STATUS_RENDERABLE is not None:
        content = _STATUS_RENDERABLE
    elif _PROGRESS_RENDERABLE is not None:
        content = _PROGRESS_RENDERABLE
    else:
        content = Panel("", title="")
    _TUI_UPDATER(content)


def set_tui_mode(
    update_right: Callable[[Any], None] | None,
    update_prompt: Callable[[Any], None] | None = None,
) -> Callable[[], None]:
    """Enable or disable TUI mode and register updater callbacks.

    Parameters
    ----------
    update_right : Callable[[Any], None] | None
        Callback to update the main right-hand renderable.
    update_prompt : Callable[[Any], None] | None, optional
        Optional callback to update the prompt area.

    Returns
    -------
    Callable[[], None]
        A restore function that will revert previous TUI state when called.
    """
    global _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
    prev = (_TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER)
    if update_right is None:
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = False, None, None
    else:
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = True, update_right, update_prompt

    def _restore() -> None:
        global _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = prev

    return _restore


def run_ai_connectivity_check_interactive() -> bool:
    ok, detail = run_ai_connectivity_check_silent()
    if ok:
        try:
            rprint("[green]" + translate("ai_check_ok") + "[/green]")
        except Exception:
            rprint(translate("ai_check_ok"))
        return True
    try:
        rprint("[red]" + translate("ai_check_fail") + "[/red]")
        rprint("[red]Details:[/red] " + str(detail))
    except Exception:
        rprint(translate("ai_check_fail"))
        rprint("Details: " + str(detail))
    return False


def _status_label(base: str) -> str:
    return _status_label_impl(LANG, base)


def _render_pipeline_table(status1: str, status2: str, status3: str) -> Any:
    return _render_table_impl(translate, status1, status2, status3)


def _run_pipeline_step(
    prompt_key: str,
    program_name: str,
    program_path: Path,
    fail_key: str,
    confirmation_key: str,
    skip_message: str | None = None,
    stream_output: bool = False,
) -> bool:
    choice = ask_text(_(prompt_key), default="y").lower()
    if choice in ["y", "j"]:
        if not run_program(program_name, program_path, stream_output=stream_output):
            ui_warning(_(fail_key) + " Aborting pipeline.")
            return False
        ui_success(_(confirmation_key))
    elif choice in ["s", "skip", "h", "hoppa"]:
        if skip_message:
            ui_info(_(skip_message))
        else:
            ui_warning(_(fail_key))
    else:
        ui_warning(_(fail_key))
        return False
    return True


def _run_processing_pipeline_plain() -> None:
    ui_rule(_("pipeline_title"))
    rprint(
        f"[bold]{translate('ai_check_title')}[/bold]"
        if ui_has_rich()
        else translate("ai_check_title")
    )
    if ask_confirm(translate("ai_check_prompt"), default_yes=True):
        ok = run_ai_connectivity_check_interactive()
        if not ok:
            return
    if not _run_pipeline_step(
        "run_program_1_prompt",
        "program_1",
        SRC_DIR / "program1_generate_markdowns.py",
        "program_1_failed",
        "markdown_created",
    ):
        return
    _run_pipeline_step(
        "run_program_2_prompt",
        "program_2",
        SRC_DIR / "program2_ai_processor.py",
        "program_2_failed",
        "ai_descriptions_created",
        skip_message="program_2_skipped",
        stream_output=True,
    )
    program3_success = _run_pipeline_step(
        "run_program_3_prompt",
        "program_3",
        SRC_DIR / "program3_generate_website.py",
        "program_3_failed",
        "website_created",
    )
    ui_success(_("pipeline_complete"))
    if program3_success:
        html_path = PROJECT_ROOT / "output" / "index.html"
        open_msg = {
            "en": f"\nOpen the file in your browser by double-clicking it in your file explorer:\n  {html_path.resolve()}",
            "sv": f"\nÖppna filen i din webbläsare genom att dubbelklicka på den i Utforskaren:\n  {html_path.resolve()}",
        }
        rprint(open_msg.get(LANG, open_msg["en"]))


def _run_processing_pipeline_rich(content_updater=None) -> None:
    if content_updater is not None:
        set_tui_mode(content_updater)
        content_updater(Panel(translate("ai_check_title"), title="AI"))
    else:
        rprint(f"[bold]{translate('ai_check_title')}[/bold]")
    if ask_confirm(translate("ai_check_prompt"), default_yes=True):
        ok = run_ai_connectivity_check_interactive()
        if not ok:
            return
    s1 = _status_label("waiting")
    s2 = _status_label("waiting")
    s3 = _status_label("waiting")
    # Manual update flow using provided updater or fallback printing
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    # Step 1
    s1 = _status_label("running")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    ok1 = _run_pipeline_step(
        "run_program_1_prompt",
        "program_1",
        SRC_DIR / "program1_generate_markdowns.py",
        "program_1_failed",
        "markdown_created",
    )
    s1 = _status_label("ok" if ok1 else "fail")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    # Step 2
    s2 = _status_label("running")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    ok2 = _run_pipeline_step(
        "run_program_2_prompt",
        "program_2",
        SRC_DIR / "program2_ai_processor.py",
        "program_2_failed",
        "ai_descriptions_created",
        skip_message="program_2_skipped",
        stream_output=True,
    )
    s2 = _status_label("ok" if ok2 else "fail")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    # Step 3
    s3 = _status_label("running")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    ok3 = _run_pipeline_step(
        "run_program_3_prompt",
        "program_3",
        SRC_DIR / "program3_generate_website.py",
        "program_3_failed",
        "website_created",
    )
    s3 = _status_label("ok" if ok3 else "fail")
    globals()["_STATUS_RENDERABLE"] = _render_pipeline_table(s1, s2, s3)
    _compose_and_update()
    ui_success(_("pipeline_complete"))
    if ok3:
        html_path = PROJECT_ROOT / "output" / "index.html"
        if content_updater is not None:
            content_updater(
                Panel(
                    {
                        "en": f"\nOpen the file in your browser by double-clicking it in your file explorer:\n  {html_path.resolve()}",
                        "sv": f"\nÖppna filen i din webbläsare genom att dubbelklicka på den i Utforskaren:\n  {html_path.resolve()}",
                    }.get(LANG, ""),
                    title="Pipeline",
                )
            )
        else:
            rprint(
                {
                    "en": f"\nOpen the file in your browser by double-clicking it in your file explorer:\n  {html_path.resolve()}",
                    "sv": f"\nÖppna filen i din webbläsare genom att dubbelklicka på den i Utforskaren:\n  {html_path.resolve()}",
                }.get(LANG, "")
            )


def run_processing_pipeline(content_updater=None) -> None:
    """Run the processing pipeline, using TUI updater when provided."""
    if content_updater is not None or ui_has_rich():
        _run_processing_pipeline_rich(content_updater)
    else:
        _run_processing_pipeline_plain()


__all__ = [
    "run_ai_connectivity_check_interactive",
    "_status_label",
    "_render_pipeline_table",
    "_run_pipeline_step",
    "_run_processing_pipeline_plain",
    "_run_processing_pipeline_rich",
    "run_processing_pipeline",
    "_TUI_MODE",
    "_TUI_UPDATER",
    "_STATUS_RENDERABLE",
    "_PROGRESS_RENDERABLE",
    "_compose_and_update",
    "set_tui_mode",
]
