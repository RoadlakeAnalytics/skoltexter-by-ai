"""Orchestrator for pipeline sequencing and UI integration.

Provides the entrypoints used by setup and launcher code to sequence the
pipeline stages (markdown generation, AI processing, website generation)
and to update TUI dashboards. The orchestrator mediates user prompts,
status rendering and delegates execution to the pipeline runners.

This module focuses on orchestration and does not implement core data
processing logic.

Typical usage::

    from src.setup.pipeline import orchestrator
    orchestrator.run_pipeline()

"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, SRC_DIR
from src.pipeline.ai_processor.cli import main as ai_processor_main
from src.pipeline.markdown_generator.runner import run_from_config as run_markdown
from src.pipeline.website_generator.runner import run_from_config as run_website
from src.setup.console_helpers import Panel, rprint, ui_has_rich
from src.setup.i18n import LANG, translate
from src.setup.i18n import _ as _
from src.setup.ui.basic import ui_info, ui_rule, ui_success, ui_warning
from src.setup.ui.prompts import ask_confirm, ask_text

from ..azure_env import run_ai_connectivity_check_silent

# Avoid importing run_program at module import time to prevent circular
# imports with the run module. Import locally where needed.
from .status import _render_pipeline_table as _render_table_impl
from .status import _status_label as _status_label_impl

_TUI_MODE: bool = False
_TUI_UPDATER: Callable[[Any], None] | None = None
_TUI_PROMPT_UPDATER: Callable[[Any], None] | None = None
_STATUS_RENDERABLE: object | None = None
_PROGRESS_RENDERABLE: object | None = None

# Expose a modifiable symbol so tests can monkeypatch `orchestrator.run_program`
# without triggering circular imports. The real implementation is imported
# lazily inside functions that need it.
run_program = None


def _compose_and_update() -> None:
    """Compose the current status and progress renderables and push updates.

    When TUI mode is enabled the function builds a composite renderable
    (using Rich's Group when available) and calls the registered updater
    callback so the dashboard reflects the current pipeline state.
    """
    if not _TUI_MODE or _TUI_UPDATER is None:
        return
    content: Any
    if _STATUS_RENDERABLE is not None and _PROGRESS_RENDERABLE is not None:
        try:
            from src.setup.console_helpers import Group as _RichGroup

            a: Any = _STATUS_RENDERABLE
            b: Any = _PROGRESS_RENDERABLE
            content = _RichGroup(a, b)
            try:
                if not hasattr(content, "items"):
                    content.items = a, b
            except Exception:
                pass
        except Exception:

            class Group:
                r"""Lightweight container for environments without Rich.

                Stores two renderable items and exposes them for inspection.

                Examples
                --------
                >>> grp = Group("foo", "bar")
                >>> assert grp.items == ("foo", "bar")
                >>> # Used in TUI CI fallback or mutation flows—never in production logic.
                """

                def __init__(self, a: Any, b: Any) -> None:
                    r"""Initialize with two items; audit/test-only container.

                    Parameters
                    ----------
                    a : Any
                        First renderable/status item.
                    b : Any
                        Second renderable/progress item.

                    Examples
                    --------
                    >>> Group("A", "B").items
                    ('A', 'B')
                    """
                    self.items = (a, b)

            a: Any = _STATUS_RENDERABLE
            b: Any = _PROGRESS_RENDERABLE
            content = Group(a, b)
    elif _STATUS_RENDERABLE is not None:
        content = _STATUS_RENDERABLE
    elif _PROGRESS_RENDERABLE is not None:
        content = _PROGRESS_RENDERABLE
    else:
        return

    try:
        _TUI_UPDATER(content)
    except Exception:
        # Do not let updater errors crash the orchestrator; log and continue.
        try:
            rprint("[red]TUI update failed[/red]")
        except Exception:
            pass


def set_tui_mode(update_right: Callable[[Any], None] | None, update_prompt: Callable[[Any], None] | None = None):
    """Enable or disable TUI mode and register updater callbacks.

    Returns a restore function that reinstates the previous TUI state.
    """
    global _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
    prev = (_TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER)
    if update_right is None:
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = False, None, None
    else:
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = True, update_right, update_prompt

    def _restore() -> None:
        """Restore the previous TUI mode and updater callbacks.

        This function is returned to callers of ``set_tui_mode`` so the
        previous state can be reinstated when the TUI session ends.
        """
        global _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER
        _TUI_MODE, _TUI_UPDATER, _TUI_PROMPT_UPDATER = prev

    return _restore


def run_ai_connectivity_check_interactive() -> bool:
    """Run an interactive AI connectivity check and display the result.

    Returns
    -------
    bool
        True when the connectivity check succeeds, False otherwise.
    """
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
    """Return a localized status label for the given base key.

    Parameters
    ----------
    base : str
        One of the status base names such as ``'waiting'``, ``'running'``, ``'ok'`` or ``'fail'``.

    Returns
    -------
    str
        Localized human-readable label.
    """
    return _status_label_impl(LANG, base)


def _render_pipeline_table(status1: str, status2: str, status3: str) -> Any:
    """Render the pipeline status table using the status helper implementation.

    Parameters
    ----------
    status1, status2, status3 : str
        Labels representing the state of Program 1, Program 2 and Program 3.

    Returns
    -------
    Any
        A renderable object that can be presented in the TUI.
    """
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
    """Prompt the user and conditionally execute a pipeline program step.

    Parameters
    ----------
    prompt_key : str
        i18n key for the prompt text.
    program_name : str
        Canonical program name used by the runner (e.g. "program_1").
    program_path : Path
        Path to the fallback script when in subprocess mode.
    fail_key : str
        i18n key for a failure message.
    confirmation_key : str
        i18n key indicating successful completion text.
    skip_message : str | None, optional
        Optional i18n key for a skip message.
    stream_output : bool
        Whether to request streaming output from the program.

    Returns
    -------
    bool
        True if the step completed successfully or was skipped; False if it failed.
    """
    choice = ask_text(_(prompt_key), default="y").lower()
    if choice in ["y", "j"]:
        rp = globals().get("run_program")
        if rp is None:
            from .run import run_program as _rp

            rp = _rp

        ok = rp(program_name, program_path, stream_output=stream_output)
        if not ok:
            ui_warning(_(fail_key) + " Aborting pipeline.")
            return False
