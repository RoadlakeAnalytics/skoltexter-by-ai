"""Utilities to safely remove generated artifacts and logs.

Functions in this module resolve project paths, enumerate generated
artifacts, and perform an interactive reset that removes generated data
and log files. All destructive operations validate paths before deletion.
"""

from __future__ import annotations

import logging
from pathlib import Path

import src.setup.ui.prompts as prompts
from src import config as _config
from src.setup.console_helpers import rprint
from src.setup.fs_utils import create_safe_path, safe_rmtree
from src.setup.i18n import translate
from src.setup.ui.basic import ui_rule


def _resolve_project_paths() -> tuple[Path, Path]:
    """Return the project root and log directory paths.

    The returned paths are derived from project configuration constants and
    are intended for use by reset operations.

    Returns
    -------
    tuple[Path, Path]
        ``(project_root, log_dir)``.
    
    Examples
    --------
    >>> from src.setup import reset
    >>> root, logdir = reset._resolve_project_paths()
    >>> assert root.is_dir() and logdir.is_dir()
    """


logger = logging.getLogger("setup_project.reset")


def _gather_generated_paths() -> list[Path]:
    """Collect generated files targeted for deletion.

    Returns a list of validated file paths that represent generated
    artefacts. The function returns an empty list if none are found.

    Returns
    -------
    list[Path]
        List of validated file Paths.
    
    Examples
    --------
    >>> from src.setup import reset
    >>> files = reset._gather_generated_paths()
    >>> assert isinstance(files, list)
    >>> # Edge case: no generated files
    >>> if not files:
    ...     assert files == []
    >>> else:
    ...     assert all(f.is_file() for f in files)
    """


def reset_project() -> None:
    """Interactively remove generated artefacts and logs.

    Prompts the user for confirmation before deleting configured directories
    that contain generated content. Each directory is validated before
    deletion to prevent accidental removal of unrelated files.

    Returns
    -------
    None

    Raises
    ------
    PermissionError
        If a directory cannot be validated for deletion.
    Exception
        Other unexpected errors are logged and skipped.
    """
    Examples
    --------
    >>> import builtins
    >>> from src.setup import reset
    >>> # Simulate cancellation
    >>> orig = builtins.input; builtins.input = lambda _: "n"
    >>> reset.reset_project()  # prints cancellation message, returns None
    >>> builtins.input = orig
    >>> # Simulate confirmation (prints and deletes)
    >>> # builtins.input = lambda _: "y"
    >>> # reset.reset_project()


    project_root, log_dir = _resolve_project_paths()
    try:
        ui_rule(translate("menu_option_5").split(". ")[1])
    except Exception:
        ui_rule("Reset Project")

    files_found = _gather_generated_paths()
    if not files_found:
        rprint(translate("no_logs") or "No generated files found to delete.")
        return

    rprint(f"Found {len(files_found)} generated files that will be deleted.")
    rprint("Directories that will be cleared:")

    dirs_to_check = [
        project_root / "data" / "generated_markdown_from_csv",
        project_root / "data" / "ai_processed_markdown",
        project_root / "data" / "ai_raw_responses",
        project_root / "data" / "generated_descriptions",
        project_root / "output",
        log_dir,
    ]

    for dir_path in dirs_to_check:
        if dir_path.exists() and any(dir_path.rglob("*")):
            try:
                rprint(f"  - {dir_path.relative_to(project_root)}")
            except Exception:
                rprint(f"  - {dir_path}")

    confirm = prompts.ask_text(translate("reset_confirm"), default="n").lower()
    if confirm not in ["y", "j"]:
        rprint(translate("reset_cancelled"))
        return

    deleted_dirs_count = 0
    for dir_path in dirs_to_check:
        try:
            if dir_path.exists():
                validated = create_safe_path(dir_path)
                safe_rmtree(validated)
                deleted_dirs_count += 1
        except PermissionError as e:
            logger.error(f"Could not reset directory '{dir_path}': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while resetting '{dir_path}': {e}")

    rprint(f"{translate('reset_complete')} ({deleted_dirs_count} directories cleared)")


__all__ = ["reset_project"]
